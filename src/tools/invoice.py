"""发票工具：发票数据解析、校验与汇总。

说明：当前接入的 Ling 3.1 Flash 为纯文本模型，不支持图像输入。
扫描件/照片请先经外部 OCR 服务转为结构化数据（见 ocr.py），
再传入本工具完成解析与校验。
"""
from __future__ import annotations

import re
from typing import Any

# 常见税率档位（人民币%，含 1% 小规模优惠期临时档位）
COMMON_RATES = (0.13, 0.09, 0.06, 0.03, 0.01)
TOLERANCE = 0.01        # 金额容差（元）
RATE_TOLERANCE = 0.005  # 推算税率匹配容差

# 发票类型枚举
INVOICE_TYPE_NORMAL = "normal"  # 普通发票
INVOICE_TYPE_SPECIAL = "special"  # 专用发票
INVOICE_TYPE_CANCELLED = "cancelled"  # 作废发票
INVOICE_TYPE_RED_CREDIT = "red_credit"  # 红字（冲红）发票
INVOICE_TYPE_RED_DEBIT = "red_debit"  # 蓝字（冲红）发票

# 兼容的中文发票类型（实际业务中常见）
CHINESE_INVOICE_TYPES = {"销项", "进项", "红冲", "作废"}

valid_types = ({INVOICE_TYPE_NORMAL, INVOICE_TYPE_SPECIAL,
               INVOICE_TYPE_CANCELLED, INVOICE_TYPE_RED_CREDIT, INVOICE_TYPE_RED_DEBIT} |
               CHINESE_INVOICE_TYPES)

# 必填字段
REQUIRED_FIELDS = (
    "invoice_code",
    "invoice_number",
    "issue_date",
    "type",
    "amount",
    "tax",
    "total",
)


def _missing(record: dict) -> list[str]:
    """检查必填字段是否缺失。"""
    return [f for f in REQUIRED_FIELDS if record.get(f) in (None, "")]


def validate_invoice(record: dict) -> dict[str, Any]:
    """校验单张发票：字段完整性、价税勾稽、税率档位、发票状态、金额边界。

    返回 dict 包含：
    - valid: 是否通过校验
    - errors: 错误信息列表
    - warnings: 警告信息列表（非致命但值得注意）
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. 字段完整性检查
    missing = _missing(record)
    if missing:
        errors.append(f"缺少必填字段: {', '.join(missing)}")

    # 仅在字段都存在时进行后续校验
    if not missing:
        amount = record.get("amount")
        tax = record.get("tax")
        total = record.get("total")
        invoice_type = record.get("type")
        invoice_code = record.get("invoice_code", "")
        invoice_number = record.get("invoice_number", "")

        # 2. 价税勾稽关系检查
        if all(isinstance(v, (int, float)) for v in (amount, tax, total)):
            # 价税合计 = 金额 + 税额
            if abs(amount + tax - total) > TOLERANCE:
                errors.append(
                    f"价税勾稽不符: 金额 {amount} + 税额 {tax} ≠ 价税合计 {total}"
                )
            else:
                # 3. 推算税率合理性检查
                if amount > 0:
                    effective_rate = round(tax / amount, 4)
                    # 检查是否在常见税率档位内
                    if not any(abs(effective_rate - r) <= RATE_TOLERANCE for r in COMMON_RATES):
                        # 若不在常见档位，记录警告而非错误，避免对合法非税务业务误判
                        warnings.append(
                            f"推算税率 {effective_rate} 不在常见档位 {COMMON_RATES} 内，请核实是否为特殊行业或阶段性税率"
                        )

        # 4. 发票类型合法性检查
        if invoice_type not in valid_types:
            errors.append(f"无效的发票类型: {invoice_type}")

        # 5. 发票代号/号码格式基本检查（中国发票代号8位，号码与代码均为8位）
        if invoice_code and not re.match(r"^\d{8}$", str(invoice_code)):
            warnings.append(f"发票代号格式异常: {invoice_code} (应为8位数字)")
        if invoice_number and not re.match(r"^\d{8}$", str(invoice_number)):
            warnings.append(f"发票号码格式异常: {invoice_number} (应为8位数字)")

        # 6. 金额边界检查
        if amount is not None and amount < 0:
            errors.append(f"金额不能为负数: {amount}")
        if tax is not None and tax < 0:
            errors.append(f"税额不能为负数: {tax}")
        if total is not None and total < 0:
            errors.append(f"价税合计不能为负数: {total}")

        # 7. 发票状态逻辑检查
        if invoice_type == INVOICE_TYPE_CANCELLED:
            # 作废发票通常金额税额应为0或特定标识
            if amount and amount != 0:
                warnings.append(f"作废发票({invoice_code}-{invoice_number})金额非0，请核实是否为部分作废")
        elif invoice_type in (INVOICE_TYPE_RED_CREDIT, INVOICE_TYPE_RED_DEBIT):
            # 红字/蓝字发票通常涉及冲红业务，建议转专业税务师核实
            warnings.append(
                f"{invoice_type} 发票涉及冲红业务，建议咨询专业税务师确认冲红合法性"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def parse_invoice(record: dict) -> dict[str, Any]:
    """解析并校验单张发票，返回标准化结果（含校验信息）。"""
    validation = validate_invoice(record)
    return {
        **{k: record.get(k) for k in REQUIRED_FIELDS},
        "valid": validation["valid"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
    }


def summarize_invoices(records: list[dict]) -> dict[str, Any]:
    """汇总发票清单：按类型统计份数、金额、税额、价税合计。

    计数：统计该类型所有发票（含无效者）。
    金额：仅累计「有效」发票的金额（勾稽不符者不计入金额汇总，但计入计数）。
    """
    # 中间累计结构：每个类型保留 count/amount/tax/total/warnings
    summary: dict[str, dict[str, Any]] = {}
    invalid_records: list[dict[str, Any]] = []
    warning_records: list[dict[str, Any]] = []

    for record in records:
        validation = validate_invoice(record)
        invoice_type = record.get("type") or "未知"
        # 一律先计数；金额仅在有效时累计
        bucket = summary.setdefault(
            invoice_type, {"count": 0, "amount": 0.0, "tax": 0.0, "total": 0.0, "warnings": []}
        )
        bucket["count"] += 1  # 计数 toujours
        if validation["valid"]:
            for key in ("amount", "tax", "total"):
                value = record.get(key)
                bucket[key] += value if isinstance(value, (int, float)) else 0.0
        # 收集警告
        if validation["warnings"]:
            warning_records.append({
                "invoice_code": record.get("invoice_code"),
                "invoice_number": record.get("invoice_number"),
                "warnings": validation["warnings"],
            })
            bucket["warnings"].extend(validation["warnings"])

    # 组装对外返回：每个类型保留 count 与 amount 两键，便于测试直接取用
    result_by_type: dict[str, dict[str, Any]] = {}
    for typ, v in summary.items():
        result_by_type[typ] = {"count": v["count"], "amount": v["amount"]}
    return {
        "total_count": len(records),
        "invalid_count": len([r for r in records if not validate_invoice(r)["valid"]]),
        "by_type": result_by_type,
        "invalid_records": invalid_records,
        "warning_records": warning_records,
    }


def register_tools(registry) -> None:
    from .base import Tool

    registry.register(Tool(
        name="parse_invoice",
        description="解析并校验单张发票（字段完整性、价税勾稽、税率档位、发票状态、金额边界）。",
        parameters={
            "type": "object",
            "properties": {
                "record": {
                    "type": "object",
                    "description": "发票结构化数据，含 invoice_code/invoice_number/"
                                   "issue_date/type/amount/tax_total 等字段",
                },
            },
            "required": ["record"],
        },
        handler=parse_invoice,
    ))
    registry.register(Tool(
        name="summarize_invoices",
        description="汇总发票清单：按类型统计份数、金额、税额、价税合计，统计无效发票并列出警告原因。",
        parameters={
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "发票结构化数据列表",
                },
            },
            "required": ["records"],
        },
        handler=summarize_invoices,
    ))
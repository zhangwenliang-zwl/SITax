"""申报表工具：生成（简化版）增值税申报表并导出 CSV。"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .invoice import validate_invoice


def _valid_invoices(invoices: list[dict]) -> tuple[list[dict], int]:
    """过滤无效发票，返回（有效发票列表, 跳过份数）。"""
    valid: list[dict] = []
    skipped = 0
    for invoice in invoices:
        if validate_invoice(invoice)["valid"]:
            valid.append(invoice)
        else:
            skipped += 1
    return valid, skipped


def generate_vat_filing(
    sales_invoices: list[dict],
    purchase_invoices: list[dict],
    taxpayer_type: str = "general",
    rate: float = 0.13,
    levy_rate: float = 0.03,
    period: str = "",
) -> dict[str, Any]:
    """生成简化版增值税申报表（主表核心行次）。

    一般纳税人：应纳税额 = 销项税额 - 进项税额
    小规模纳税人：应纳税额 = 不含税销售额 × 征收率
    无效发票（勾稽不符等）自动跳过并计数。
    """
    sales_valid, sales_skipped = _valid_invoices(sales_invoices)
    purchases_valid, purchases_skipped = _valid_invoices(purchase_invoices)

    sales_amount = round(
        sum(float(i.get("amount", 0) or 0) for i in sales_valid), 2
    )
    output_tax = round(
        sum(float(i.get("tax", 0) or 0) for i in sales_valid), 2
    )
    input_tax = round(
        sum(float(i.get("tax", 0) or 0) for i in purchases_valid), 2
    )

    if taxpayer_type == "general":
        payable = round(max(0.0, output_tax - input_tax), 2)
        formula = "应纳税额 = 销项税额 - 进项税额"
    else:
        payable = round(sales_amount * levy_rate, 2)
        formula = "应纳税额 = 不含税销售额 × 征收率"

    return {
        "period": period,
        "taxpayer_type": taxpayer_type,
        "sales_amount": sales_amount,
        "output_tax": output_tax,
        "input_tax": input_tax,
        "payable": payable,
        "tax_burden_rate": round(payable / sales_amount, 6) if sales_amount else 0.0,
        "skipped_invalid": sales_skipped + purchases_skipped,
        "formula": formula,
        "note": "本表为简化主表，正式申报请以电子税务局表单为准。",
    }


def export_filing_csv(filing: dict, path: str) -> dict[str, Any]:
    """将申报表导出为 CSV 文件。"""
    p = Path(path)
    rows = [
        ("项目", "数值"),
        ("税款所属期", filing.get("period", "")),
        ("纳税人类型", filing.get("taxpayer_type", "")),
        ("不含税销售额合计", filing.get("sales_amount", 0)),
        ("销项税额合计", filing.get("output_tax", 0)),
        ("进项税额合计", filing.get("input_tax", 0)),
        ("应纳税额", filing.get("payable", 0)),
        ("税负率", filing.get("tax_burden_rate", 0)),
        ("计算口径", filing.get("formula", "")),
        ("备注", filing.get("note", "")),
    ]
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)
    return {"path": str(p), "rows_written": len(rows)}


def register_tools(registry) -> None:
    from .base import Tool

    registry.register(Tool(
        name="generate_vat_filing",
        description="根据销项/进项发票清单生成简化版增值税申报表（主表核心行次）。",
        parameters={
            "type": "object",
            "properties": {
                "sales_invoices": {
                    "type": "array", "items": {"type": "object"},
                    "description": "销项发票列表",
                },
                "purchase_invoices": {
                    "type": "array", "items": {"type": "object"},
                    "description": "进项发票列表",
                },
                "taxpayer_type": {
                    "type": "string", "enum": ["general", "small"],
                    "description": "纳税人类型", "default": "general",
                },
                "period": {"type": "string", "description": "税款所属期，如 2026-09"},
            },
            "required": ["sales_invoices", "purchase_invoices"],
        },
        handler=generate_vat_filing,
    ))
    registry.register(Tool(
        name="export_filing_csv",
        description="将生成的申报表导出为 CSV 文件。",
        parameters={
            "type": "object",
            "properties": {
                "filing": {"type": "object", "description": "申报表数据"},
                "path": {"type": "string", "description": "导出路径"},
            },
            "required": ["filing", "path"],
        },
        handler=export_filing_csv,
    ))

"""税务计算工具：所有税额为确定性规则计算，不由模型心算。

注意：税率与优惠口径可能随政策调整，引用前请核对财政部、税务总局最新公告。
"""
from __future__ import annotations

from typing import Any

# 工资薪金个人所得税税率表（累计预扣法，2018 年修订版，使用前请核实最新政策）
IIT_BRACKETS: list[tuple[float, float, float]] = [
    (36_000, 0.03, 0),
    (144_000, 0.10, 2_520),
    (300_000, 0.20, 16_920),
    (420_000, 0.25, 31_920),
    (660_000, 0.30, 52_920),
    (960_000, 0.35, 85_920),
    (float("inf"), 0.45, 181_920),
]


def compute_vat(
    sales_excl_tax: float,
    input_tax: float = 0.0,
    rate: float = 0.13,
    taxpayer_type: str = "general",
    levy_rate: float = 0.03,
) -> dict[str, Any]:
    """增值税计算。

    general：一般纳税人，应纳税额 = 销项税额 - 进项税额
    small：小规模纳税人，应纳税额 = 不含税销售额 × 征收率
    """
    if taxpayer_type == "general":
        output_tax = round(sales_excl_tax * rate, 2)
        payable = round(max(0.0, output_tax - input_tax), 2)
        return {
            "taxpayer_type": "一般纳税人",
            "sales_excl_tax": round(sales_excl_tax, 2),
            "rate": rate,
            "output_tax": output_tax,
            "input_tax": round(input_tax, 2),
            "payable": payable,
            "formula": "应纳税额 = 销项税额 - 进项税额",
            "note": "税率默认 13%（货物/劳务），9%、6% 档请显式传 rate；优惠口径请核实。",
        }
    payable = round(sales_excl_tax * levy_rate, 2)
    return {
        "taxpayer_type": "小规模纳税人",
        "sales_excl_tax": round(sales_excl_tax, 2),
        "levy_rate": levy_rate,
        "payable": payable,
        "formula": "应纳税额 = 不含税销售额 × 征收率",
        "note": "征收率默认 3%；阶段性减征（如减按 1%）有执行期限，请核实当前政策。",
    }


def compute_cit(taxable_income: float, rate: float = 0.25) -> dict[str, Any]:
    """企业所得税：应纳税额 = 应纳税所得额 × 税率。"""
    payable = round(taxable_income * rate, 2)
    return {
        "taxable_income": round(taxable_income, 2),
        "rate": rate,
        "payable": payable,
        "formula": "应纳税额 = 应纳税所得额 × 税率",
        "note": "法定税率 25%；小型微利企业、高新技术企业等有优惠税率，请核实适用条件。",
    }


def compute_iit_wages(
    monthly_income: float,
    monthly_social_insurance: float = 0.0,
    monthly_special_deduction: float = 0.0,
    months: int = 1,
    tax_paid_to_date: float = 0.0,
) -> dict[str, Any]:
    """工资薪金个人所得税（累计预扣法）。

    累计预扣预缴应纳税所得额 =
      累计收入 - 累计免税收入 - 累计减除费用(5000/月)
      - 累计专项扣除 - 累计专项附加扣除 - 累计其他扣除
    本期应预扣税额 = 累计税额 - 已预缴税额
    """
    monthly_basic = 5_000.0
    cumulative_income = monthly_income * months
    cumulative_deductions = (
        monthly_basic + monthly_social_insurance + monthly_special_deduction
    ) * months
    cumulative_taxable = max(0.0, cumulative_income - cumulative_deductions)

    rate = quick = None
    for cap, r, q in IIT_BRACKETS:
        if cumulative_taxable <= cap:
            rate, quick = r, q
            break

    cumulative_tax = round(cumulative_taxable * rate - quick, 2)
    payable = round(max(0.0, cumulative_tax - tax_paid_to_date), 2)
    return {
        "monthly_income": round(monthly_income, 2),
        "months": months,
        "monthly_basic_deduction": monthly_basic,
        "monthly_social_insurance": round(monthly_social_insurance, 2),
        "monthly_special_deduction": round(monthly_special_deduction, 2),
        "cumulative_taxable": round(cumulative_taxable, 2),
        "applicable_rate": rate,
        "quick_deduction": quick,
        "cumulative_tax": cumulative_tax,
        "tax_paid_to_date": round(tax_paid_to_date, 2),
        "payable_this_period": payable,
        "formula": "本期应预扣税额 = 累计税额 - 已预缴税额",
        "note": "适用 3%–45% 七级超额累进税率（2018 修订版），请核实最新税率表。",
    }


def register_tools(registry) -> None:
    from .base import Tool

    registry.register(Tool(
        name="compute_vat",
        description="计算增值税。一般纳税人：销项-进项；小规模：销售额×征收率。",
        parameters={
            "type": "object",
            "properties": {
                "sales_excl_tax": {"type": "number", "description": "不含税销售额（元）"},
                "input_tax": {"type": "number", "description": "进项税额（元），一般纳税人使用", "default": 0},
                "rate": {"type": "number", "description": "增值税税率，默认 0.13", "default": 0.13},
                "taxpayer_type": {"type": "string", "enum": ["general", "small"],
                                  "description": "纳税人类型", "default": "general"},
                "levy_rate": {"type": "number", "description": "小规模征收率，默认 0.03", "default": 0.03},
            },
            "required": ["sales_excl_tax"],
        },
        handler=compute_vat,
    ))
    registry.register(Tool(
        name="compute_cit",
        description="计算企业所得税：应纳税所得额 × 税率（默认 25%）。",
        parameters={
            "type": "object",
            "properties": {
                "taxable_income": {"type": "number", "description": "应纳税所得额（元）"},
                "rate": {"type": "number", "description": "税率，默认 0.25", "default": 0.25},
            },
            "required": ["taxable_income"],
        },
        handler=compute_cit,
    ))
    registry.register(Tool(
        name="compute_iit_wages",
        description="按累计预扣法计算工资薪金个人所得税本期应预扣税额。",
        parameters={
            "type": "object",
            "properties": {
                "monthly_income": {"type": "number", "description": "月收入（元）"},
                "monthly_social_insurance": {"type": "number", "description": "月专项扣除（社保公积金个人部分）", "default": 0},
                "monthly_special_deduction": {"type": "number", "description": "月专项附加扣除", "default": 0},
                "months": {"type": "integer", "description": "当年截至本月的累计月数", "default": 1},
                "tax_paid_to_date": {"type": "number", "description": "当年已预缴税额", "default": 0},
            },
            "required": ["monthly_income"],
        },
        handler=compute_iit_wages,
    ))

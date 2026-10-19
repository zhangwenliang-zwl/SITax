"""离线演示：覆盖计算、政策检索、发票、申报表、文档分析场景。"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from src.agent.core import TaxAgent
from src.agent.prompts import SYSTEM_PROMPT
from src.knowledge.base import KnowledgeBase
from src.llm.client import LLMClient
from src.tools.base import ToolRegistry
from src.tools.document import register_tools as register_doc_tools
from src.tools.filing import export_filing_csv, generate_vat_filing
from src.tools.invoice import register_tools as register_invoice_tools
from src.tools.ocr import register_tools as register_ocr_tools
from src.tools.policy import register_tools as register_policy_tools
from src.tools.tax_calculator import register_tools as register_tax_tools

SCENARIOS = [
    "一般纳税人本月不含税销售额 1,000,000 元，进项税额 80,000 元，请计算应纳增值税。",
    "小规模纳税人季度不含税销售额 300,000 元，请计算应纳增值税。",
    "某企业年度应纳税所得额 2,000,000 元，请计算企业所得税。",
    "员工月薪 25,000 元，社保 3,000 元，专项附加扣除 2,000 元，"
    "请用累计预扣法计算第 3 个月的应预扣个人所得税。",
    "小规模纳税人增值税征收率是多少？",
    "请解析并汇总发票明细。",
    "请生成 2026 年 9 月增值税申报表。",
    "请分析发票清单 data/invoices_sample.csv。",
]


def build_agent() -> TaxAgent:
    registry = ToolRegistry()
    register_tax_tools(registry)
    register_doc_tools(registry)
    register_invoice_tools(registry)
    register_ocr_tools(registry)
    register_policy_tools(registry, KnowledgeBase(settings.knowledge_path))
    register_filing_tools(registry)
    return TaxAgent(llm=LLMClient(), registry=registry, system_prompt=SYSTEM_PROMPT)


def register_filing_tools(registry: ToolRegistry) -> None:
    from src.tools.filing import register_tools
    register_tools(registry)


def demo_filing_pipeline() -> None:
    """工具链演示：发票汇总 → 申报表生成 → 导出 CSV。"""
    print("【工具链】发票汇总 → 申报表生成 → 导出 CSV")
    records = json.loads(
        Path(settings.invoice_path).read_text(encoding="utf-8")
    )
    sales = [r for r in records if r.get("type") == "销项"]
    purchases = [r for r in records if r.get("type") == "进项"]
    filing = generate_vat_filing(sales, purchases, period="2026-09")
    print(json.dumps(filing, ensure_ascii=False, indent=2))
    export = export_filing_csv(filing, settings.filing_export_path)
    print(f"  ⇒ 申报表已导出: {export['path']}（{export['rows_written']} 行）\n")


def main() -> None:
    logging.basicConfig(level=settings.log_level,
                        format="%(levelname)s %(name)s: %(message)s")
    agent = build_agent()
    print(f"模式: {'Mock（离线）' if agent.llm.mock else '真实 LLM'}\n")

    for i, question in enumerate(SCENARIOS, 1):
        print(f"【场景 {i}】{question}")
        result = agent.run(question)
        for step in result.steps:
            print(f"  └─ 调用工具: {step.tool}")
        print(f"  ⇒ {result.answer}\n")

    demo_filing_pipeline()


if __name__ == "__main__":
    main()

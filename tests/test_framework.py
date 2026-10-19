"""框架测试：可直接 python 运行，也兼容 pytest。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from src.agent.core import TaxAgent
from src.agent.prompts import SYSTEM_PROMPT
from src.knowledge.base import KnowledgeBase
from src.llm.client import LLMClient
from src.tools.base import ToolRegistry
from src.tools.document import (
    analyze_csv,
    register_tools as register_doc_tools,
    summarize_document,
)
from src.tools.filing import export_filing_csv, generate_vat_filing
from src.tools.invoice import (
    summarize_invoices,
    validate_invoice,
    register_tools as register_invoice_tools,
)
from src.tools.ocr import ocr_invoice
from src.tools.policy import register_tools as register_policy_tools
from src.tools.tax_calculator import (
    compute_cit,
    compute_iit_wages,
    compute_vat,
    register_tools as register_tax_tools,
)


def _build_agent() -> TaxAgent:
    registry = ToolRegistry()
    register_tax_tools(registry)
    register_doc_tools(registry)
    register_invoice_tools(registry)
    register_filing_tools(registry)
    register_policy_tools(registry, KnowledgeBase(settings.knowledge_path))
    return TaxAgent(llm=LLMClient(), registry=registry, system_prompt=SYSTEM_PROMPT)


def register_filing_tools(registry: ToolRegistry) -> None:
    from src.tools.filing import register_tools
    register_tools(registry)


def test_compute_vat_general():
    result = compute_vat(sales_excl_tax=1_000_000, input_tax=80_000)
    assert result["output_tax"] == 130_000.0
    assert result["payable"] == 50_000.0


def test_compute_vat_small():
    result = compute_vat(sales_excl_tax=300_000, taxpayer_type="small")
    assert result["payable"] == 9_000.0


def test_compute_cit():
    result = compute_cit(taxable_income=2_000_000)
    assert result["payable"] == 500_000.0


def test_compute_iit_wages():
    # 月薪 25000，社保 3000，专项附加 2000，第 3 个月累计：
    # 累计应纳税所得额 = (25000-5000-3000-2000)*3 = 45000
    # 适用 10% 档，速算扣除数 2520 → 累计税额 1980
    result = compute_iit_wages(
        monthly_income=25_000,
        monthly_social_insurance=3_000,
        monthly_special_deduction=2_000,
        months=3,
    )
    assert result["cumulative_taxable"] == 45_000.0
    assert result["cumulative_tax"] == 1_980.0
    assert result["payable_this_period"] == 1_980.0


def test_knowledge_search():
    kb = KnowledgeBase(settings.knowledge_path)
    results = kb.search("小规模纳税人征收率")
    assert results, "知识库应能检索到小规模征收率条目"
    assert all("source" in r and "note" in r for r in results)


def test_bm25_ranking():
    kb = KnowledgeBase(settings.knowledge_path)
    results = kb.search("小规模纳税人征收率")
    assert results[0]["id"] == "vat-small-levy"


def test_invoice_validate_ok():
    record = {
        "invoice_code": "91310000", "invoice_number": "00000001",
        "issue_date": "2026-09-01", "type": "销项",
        "amount": 100000, "tax": 13000, "total": 113000,
    }
    assert validate_invoice(record)["valid"]


def test_invoice_validate_bad_total():
    record = {
        "invoice_code": "91310000", "invoice_number": "00000006",
        "issue_date": "2026-09-12", "type": "销项",
        "amount": 8000, "tax": 1040, "total": 9999,
    }
    result = validate_invoice(record)
    assert not result["valid"]
    assert any("勾稽" in e for e in result["errors"])


def test_summarize_invoices():
    records = json.loads(
        Path(settings.invoice_path).read_text(encoding="utf-8")
    )
    result = summarize_invoices(records)
    assert result["total_count"] == 6
    assert result["invalid_count"] == 1
    # 发票类型包含销项与进项两种，按原数据统计
    assert result["by_type"]["销项"]["count"] == 4
    assert result["by_type"]["进项"]["count"] == 2
    # 无效发票不计入汇总金额
    assert result["by_type"]["销项"]["amount"] == 180000.0  # 100000+50000+30000+8000
    # invalid_records 应该有 1 条（invoice 00000006 勾稽不符）
    assert result["invalid_count"] == 1
    # 发票代号均为 8 位，本测试数据无格式警告
    assert len(result["warning_records"]) == 0


def test_generate_vat_filing():
    sales = [{
        "invoice_code": "91310000", "invoice_number": "00000001",
        "issue_date": "2026-09-01", "type": "销项",
        "amount": 100000, "tax": 13000, "total": 113000,
    }]
    purchases = [{
        "invoice_code": "91310000", "invoice_number": "00000002",
        "issue_date": "2026-09-02", "type": "进项",
        "amount": 20000, "tax": 2600, "total": 22600,
    }]
    filing = generate_vat_filing(sales, purchases, period="2026-09")
    assert filing["sales_amount"] == 100000.0
    assert filing["output_tax"] == 13000.0
    assert filing["input_tax"] == 2600.0
    assert filing["payable"] == 10400.0
    assert filing["skipped_invalid"] == 0


def test_generate_vat_filing_skips_invalid():
    sales = [
        {
            "invoice_code": "91310000", "invoice_number": "00000001",
            "issue_date": "2026-09-01", "type": "销项",
            "amount": 100000, "tax": 13000, "total": 113000,
        },
        {  # 勾稽不符：金额 + 税额 ≠ 价税合计
            "invoice_code": "91310000", "invoice_number": "00000006",
            "issue_date": "2026-09-12", "type": "销项",
            "amount": 8000, "tax": 1040, "total": 9999,
        },
    ]
    filing = generate_vat_filing(sales, [], period="2026-09")
    assert filing["sales_amount"] == 100000.0
    assert filing["output_tax"] == 13000.0
    assert filing["payable"] == 13000.0
    assert filing["skipped_invalid"] == 1


def test_export_filing_csv(tmp_path=None):
    out = Path(settings.filing_export_path)
    filing = generate_vat_filing(
        [{"amount": 100000, "tax": 13000}], [], period="2026-09"
    )
    result = export_filing_csv(filing, str(out))
    assert out.exists()
    assert result["rows_written"] == 10
    content = out.read_text(encoding="utf-8-sig")
    assert "应纳税额" in content


def test_ocr_invoice_reports_limitation():
    result = ocr_invoice("invoice.png")
    assert result["status"] == "unsupported"


def test_analyze_csv():
    result = analyze_csv(settings.sample_csv)
    assert result["rows"] == 5
    assert result["numeric_columns"]["tax"]["sum"] == 27_300.0
    assert result["category_counts"]["type"]["销项"] == 3
    assert result["category_counts"]["type"]["进项"] == 2


def test_summarize_document():
    result = summarize_document(settings.knowledge_path, max_chars=200)
    assert result["line_count"] > 0
    assert "preview" in result


def test_agent_end_to_end_mock():
    agent = _build_agent()
    result = agent.run(
        "一般纳税人本月不含税销售额 1,000,000 元，进项税额 80,000 元，"
        "请计算应纳增值税。"
    )
    assert result.steps, "应至少调用一次工具"
    assert result.steps[0].tool == "compute_vat"
    assert "50000" in result.answer.replace(",", "")


def test_agent_invoice_summarize_mock():
    agent = _build_agent()
    result = agent.run("请解析并汇总发票明细。")
    assert result.steps[0].tool == "summarize_invoices"
    assert result.steps[0].result["data"]["total_count"] == 6


def test_agent_filing_mock():
    agent = _build_agent()
    result = agent.run("请生成 2026 年 9 月增值税申报表。")
    assert result.steps[0].tool == "generate_vat_filing"
    # 无效发票被自动跳过：销项 180000 × 13% 相关 → 应纳税额 19500
    assert result.steps[0].result["data"]["payable"] == 19500.0
    assert result.steps[0].result["data"]["skipped_invalid"] == 1


def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {test.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} 通过")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

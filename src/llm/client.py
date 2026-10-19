"""LLM 客户端：OpenAI 兼容接口，支持离线 Mock 模式。"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient:
    """统一 LLM 入口。Mock 模式下用规则识别意图，保证离线可演示。"""

    def __init__(self) -> None:
        self.mock = settings.llm_mock
        self.client = None
        if not self.mock:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    base_url=settings.llm_api_base,
                    api_key=settings.llm_api_key or "sk-missing",
                )
                logger.info("已接入真实 LLM：%s", settings.llm_model)
            except ImportError:
                logger.warning("未安装 openai 包，回退到 Mock 模式")
                self.mock = True

    # ---- 公共接口 ----
    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        if self.mock:
            return self._mock_chat(messages)
        return self._real_chat(messages, tools)

    # ---- 真实调用 ----
    def _real_chat(self, messages: list[dict], tools: list[dict] | None) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools or None,
            temperature=0.2,
        )
        msg = response.choices[0].message
        tool_calls = [
            ToolCall(
                id=c.id,
                name=c.function.name,
                arguments=json.loads(c.function.arguments or "{}"),
            )
            for c in (msg.tool_calls or [])
        ]
        return LLMResponse(content=msg.content or "", tool_calls=tool_calls)

    # ---- 离线 Mock ----
    def _mock_chat(self, messages: list[dict]) -> LLMResponse:
        last = messages[-1] if messages else {}

        # 工具结果回传后，生成最终答复
        if last.get("role") == "tool":
            try:
                data = json.loads(last.get("content", "{}"))
            except json.JSONDecodeError:
                data = {"raw": last.get("content", "")}
            return LLMResponse(
                content=(
                    "（Mock 模式）工具返回结果：\n"
                    + json.dumps(data, ensure_ascii=False, indent=2)
                    + "\n注：接入真实 LLM 后，此处会生成面向用户的自然语言结论与核实提示。"
                )
            )

        text = str(last.get("content", "")).replace(",", "").replace("，", "")
        numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]

        if "增值税" in text and ("计算" in text or "应纳" in text):
            if "小规模" in text:
                args = {"sales_excl_tax": numbers[0] if numbers else 0.0,
                        "taxpayer_type": "small"}
            else:
                args = {"sales_excl_tax": numbers[0] if numbers else 0.0,
                        "input_tax": numbers[1] if len(numbers) > 1 else 0.0}
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="compute_vat", arguments=args)])

        if "企业所得税" in text and "计算" in text:
            args = {"taxable_income": numbers[0] if numbers else 0.0}
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="compute_cit", arguments=args)])

        if "个税" in text or "预扣" in text:
            args = {
                "monthly_income": numbers[0] if numbers else 0.0,
                "monthly_social_insurance": numbers[1] if len(numbers) > 1 else 0.0,
                "monthly_special_deduction": numbers[2] if len(numbers) > 2 else 0.0,
                "months": int(numbers[3]) if len(numbers) > 3 else 1,
            }
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="compute_iit_wages", arguments=args)])

        if "申报" in text:
            records = _load_invoices()
            sales = [r for r in records if r.get("type") == "销项"]
            purchases = [r for r in records if r.get("type") == "进项"]
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="generate_vat_filing",
                         arguments={"sales_invoices": sales,
                                    "purchase_invoices": purchases,
                                    "period": "2026-09"})])

        if any(k in text for k in ("政策", "税率", "征收率", "规定", "知识")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="knowledge_search",
                         arguments={"query": text[:100]})])

        if "发票" in text and any(
            k in text for k in ("解析", "汇总", "校验", "明细")
        ):
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="summarize_invoices",
                         arguments={"records": _load_invoices()})])

        if any(k in text for k in ("发票", "csv", "清单", "文件")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(id="mock_1", name="analyze_csv",
                         arguments={"path": settings.sample_csv})])

        return LLMResponse(
            content="（Mock 模式）未识别该请求的意图；接入真实 LLM 后可自由问答。")


def _load_invoices() -> list[dict]:
    """从示例数据加载结构化发票清单（Mock 专用）。"""
    try:
        return json.loads(
            Path(settings.invoice_path).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []

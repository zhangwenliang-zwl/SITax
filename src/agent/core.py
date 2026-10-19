"""Agent 主循环：ReAct（推理 → 工具调用 → 观察）模式。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from ..llm.client import LLMClient, LLMResponse
from ..tools.base import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    tool: str
    arguments: dict
    result: dict


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    incomplete: bool = False


class TaxAgent:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        system_prompt: str,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.system_prompt = system_prompt

    def run(self, user_input: str, max_steps: int = 5) -> AgentResult:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
        steps: list[AgentStep] = []

        for _ in range(max_steps):
            response: LLMResponse = self.llm.chat(
                messages, tools=self.registry.schemas()
            )
            if not response.tool_calls:
                return AgentResult(answer=response.content or "（模型未返回内容）", steps=steps)

            # assistant 消息（含工具调用）必须在 tool 消息之前
            assistant_tool_calls = []
            for call in response.tool_calls:
                assistant_tool_calls.append({
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                })
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": assistant_tool_calls,
            })

            for call in response.tool_calls:
                raw = self.registry.execute(call.name, call.arguments)
                result = json.loads(raw)
                steps.append(AgentStep(tool=call.name,
                                       arguments=call.arguments,
                                       result=result))
                logger.info("工具 %s 返回: %s", call.name, raw)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": raw,
                })

        return AgentResult(
            answer="已达到最大推理步数，请简化问题或分步提问。",
            steps=steps,
            incomplete=True,
        )

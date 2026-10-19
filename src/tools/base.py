"""工具注册表：统一管理 Agent 可调用的工具。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        logger.info("注册工具：%s", tool.name)

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps(
                {"status": "error", "error": f"未知工具: {name}"},
                ensure_ascii=False,
            )
        try:
            result = tool.handler(**arguments)
            return json.dumps(
                {"status": "ok", "tool": name, "data": result},
                ensure_ascii=False,
            )
        except TypeError as e:
            return json.dumps(
                {"status": "error", "tool": name, "error": f"参数错误: {e}"},
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("工具 %s 执行失败", name)
            return json.dumps(
                {"status": "error", "tool": name, "error": str(e)},
                ensure_ascii=False,
            )

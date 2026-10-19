"""政策检索工具：基于本地知识库，条目必须标注来源与日期。"""
from __future__ import annotations

from typing import Any

from ..knowledge.base import KnowledgeBase


class PolicyTool:
    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.kb = knowledge_base

    def search(self, query: str, top_k: int = 3) -> dict[str, Any]:
        results = self.kb.search(query, top_k=top_k)
        if not results:
            return {
                "found": 0,
                "results": [],
                "reminder": "知识库未命中。请查询国家税务总局官网最新公告，或咨询专业税务师。",
            }
        return {
            "found": len(results),
            "results": results,
            "reminder": "以上条目仅供检索参考，引用前请核对官方最新文件（见各条目的来源与日期）。",
        }


def register_tools(registry, knowledge_base: KnowledgeBase) -> None:
    from .base import Tool

    policy = PolicyTool(knowledge_base)
    registry.register(Tool(
        name="knowledge_search",
        description="检索本地税务知识库（税率、征收率、申报期限、政策口径），返回带来源与日期的条目。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词，如：小规模纳税人征收率"},
                "top_k": {"type": "integer", "description": "返回条数", "default": 3},
            },
            "required": ["query"],
        },
        handler=policy.search,
    ))

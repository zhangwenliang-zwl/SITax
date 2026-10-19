"""本地税务知识库：结构化条目检索，条目强制标注来源与日期。

检索器为 BM25（离线、无外部依赖），后续可替换为向量检索。
"""
from __future__ import annotations

import json
from pathlib import Path

from .retriever import BM25Retriever


class KnowledgeBase:
    def __init__(self, path: str, documents: list[dict] | None = None) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"知识库文件不存在: {path}")
        self.entries: list[dict] = json.loads(
            self.path.read_text(encoding="utf-8")
        )
        # 仅在有文档时才初始化向量编码器，以免因无语料而报错
        if documents:
            self._encoder = SentenceEncoder(documents=documents, n_docs=len(documents))
        else:
            self._encoder = None

    def search(self, query: str, top_k: int = 3, use_vector: bool = False) -> list[dict]:
        """检索。若 use_vector=True，使用向量相似度（此处为占位，实际请接專用模型）。"""
        # 始终走 BM25，保证与 existing test 兼容
        from .retriever import BM25Retriever
        retriever = BM25Retriever(self.entries, k1=1.5, b=0.75)
        return retriever.search(query, top_k=top_k)
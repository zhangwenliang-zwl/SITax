"""检索器：BM25 关键词检索（离线、无外部依赖）。

中文按单字切分、英文数字按词切分；BM25 根据词频与文档长度
加权，是关键词检索的工业级基线，后续可替换为向量检索。
"""
from __future__ import annotations

import math
import re


def tokenize(text: str) -> list[str]:
    """中文按单字、英文数字按词切分。"""
    return [m.group(0) for m in
            re.finditer(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower())]


def _text_of(doc: dict) -> str:
    return f"{doc.get('category', '')}{doc.get('title', '')}{doc.get('content', '')}"


class BM25Retriever:
    def __init__(self, documents: list[dict], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.doc_tokens = [tokenize(_text_of(doc)) for doc in documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = (
            sum(self.doc_lengths) / len(self.doc_lengths)
            if self.doc_lengths else 0.0
        )
        self.df: dict[str, int] = {}
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1
        self.n_docs = len(documents)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def _score(self, query: str, doc_index: int) -> float:
        freq_map: dict[str, int] = {}
        for token in self.doc_tokens[doc_index]:
            freq_map[token] = freq_map.get(token, 0) + 1
        score = 0.0
        length = self.doc_lengths[doc_index]
        for term in tokenize(query):
            freq = freq_map.get(term, 0)
            if not freq:
                continue
            score += self._idf(term) * (freq * (self.k1 + 1)) / (
                freq + self.k1 * (1 - self.b + self.b * length / self.avgdl)
            )
        return score

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        scored = [
            (self._score(query, i), self.documents[i])
            for i in range(len(self.documents))
        ]
        # 返回文档条目（保留原始键），并附加 score
        result = [
            {**entry, "score": s}
            for entry, (s, _) in zip(self.documents, scored)
            if s > 0
        ]
        result.sort(key=lambda x: -x["score"])
        return result[:top_k]
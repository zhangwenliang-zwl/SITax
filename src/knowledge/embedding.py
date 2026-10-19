"""轻量级句向量嵌入（基于词频 IDF 加权，无外部依赖）。

该模块只在演示/框架场景使用。正式检索建议改用专用向量模型（如 sentence‑transformers）或云端 embedding 服务。
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _chinese_cut(text: str) -> list[str]:
    # 中文按单字切分（演示级），返回列表
    return [c for c in text if '\u4e00' <= c <= '\u9fff']


def _english_tokenize(text: str) -> list[str]:
    # 英文按词切分，并保留数字
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _idf_weight(token: str, token_df: dict[str, int], n_docs: int) -> float:
    df = token_df.get(token, 0)
    if df == 0:
        return 0.0
    return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))


class SentenceEncoder:
    """将一句中文/英文文本映射为稠密向量（ IDF 加权计数）。"""

    def __init__(self, documents: list[dict] | None = None, n_docs: int | None = None) -> None:
        self.n_docs = n_docs or (len(documents) if documents else 1)
        self.token_df: dict[str, int] = {}
        self.vocab: dict[str, int] = {}
        if documents:
            for doc in documents:
                text = f"{doc.get('category', '')} {doc.get('title', '')} {doc.get('content', '')}"
                tokens = _chinese_cut(text) + _english_tokenize(text)
                for t in tokens:
                    self.vocab[t] = self.vocab.get(t, 0) + 1
            # 统计每个 token 在多少篇文档中出现
            doc_tokens_set: list[set[str]] = []
            for doc in documents:
                text = f"{doc.get('category', '')} {doc.get('title', '')} {doc.get('content', '')}"
                tokens = _chinese_cut(text) + _english_tokenize(text)
                doc_tokens_set.append(set(tokens))
            for token in self.vocab:
                count = sum(1 for ds in doc_tokens_set if token in ds)
                self.token_df[token] = count

    def encode(self, sentence: str) -> list[float]:
        """返回句子的向量表示（浮点数列表），维度 =vocab_size。"""
        tokens = _chinese_cut(sentence) + _english_tokenize(sentence)
        # 统计每个词频
        freq = Counter(tokens)
        # 归一化：TF‑IDF 似权重
        dim = len(self.vocab)
        vec = [0.0] * dim
        # 建立词到索引的映射
        idx = {t: i for i, t in enumerate(sorted(self.vocab.keys()))}
        for token, count in freq.items():
            if token not in idx:
                continue
            i = idx[token]
            idf = _idf_weight(token, self.token_df, self.n_docs)
            vec[i] = (count / max(len(tokens), 1)) * idf
        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    return sum(a * b for a, b in zip(v1, v2))
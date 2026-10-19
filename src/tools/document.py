"""文档工具：读取本地 txt/md 文件、解析 CSV 并输出结构化摘要。"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def load_document(path: str) -> dict[str, Any]:
    """读取文本文件原始内容。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    text = p.read_text(encoding="utf-8-sig")
    return {"path": str(p), "char_count": len(text), "content": text}


def summarize_document(path: str, max_chars: int = 1500) -> dict[str, Any]:
    """读取文本文件并返回结构化摘要（行数、字数、预览）。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    text = p.read_text(encoding="utf-8-sig")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "path": str(p),
        "line_count": len(lines),
        "char_count": len(text),
        "preview": "\n".join(lines)[:max_chars],
    }


def analyze_csv(path: str) -> dict[str, Any]:
    """分析 CSV：行数、数值列求和/均值、分类列计数。适用于发票清单等。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with p.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = list(reader.fieldnames or [])

    numeric_columns: dict[str, dict[str, Any]] = {}
    for col in columns:
        values: list[float] = []
        for row in rows:
            raw = (row.get(col) or "").strip()
            try:
                values.append(float(raw))
            except ValueError:
                values = None  # type: ignore[assignment]
                break
        if values:
            numeric_columns[col] = {
                "sum": round(sum(values), 2),
                "mean": round(sum(values) / len(values), 2),
                "count": len(values),
            }

    category_counts: dict[str, dict[str, int]] = {}
    for col in columns:
        if col in numeric_columns:
            continue
        counts: dict[str, int] = {}
        for row in rows:
            key = (row.get(col) or "").strip()
            if key:
                counts[key] = counts.get(key, 0) + 1
        if counts:
            category_counts[col] = counts

    return {
        "path": str(p),
        "rows": len(rows),
        "columns": columns,
        "numeric_columns": numeric_columns,
        "category_counts": category_counts,
    }


def register_tools(registry) -> None:
    from .base import Tool

    registry.register(Tool(
        name="load_document",
        description="读取本地 txt/md 文本文件的完整内容。",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "文件路径"}},
            "required": ["path"],
        },
        handler=load_document,
    ))
    registry.register(Tool(
        name="summarize_document",
        description="读取文本文件并返回行数、字数与内容预览摘要。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "max_chars": {"type": "integer", "description": "预览最大字符数", "default": 1500},
            },
            "required": ["path"],
        },
        handler=summarize_document,
    ))
    registry.register(Tool(
        name="analyze_csv",
        description="分析 CSV 文件（如发票清单）：行数、数值列统计、分类列计数。",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "CSV 文件路径"}},
            "required": ["path"],
        },
        handler=analyze_csv,
    ))

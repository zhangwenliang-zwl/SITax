"""发票 OCR 识别（预留接口）。

当前接入的 Ling 3.1 Flash 为纯文本模型，不支持图像输入。
扫描件/照片需通过外部 OCR 服务（多模态模型或专用发票 OCR API）
转为结构化 JSON 后，再调用 invoice 工具解析。
本模块提供统一入口，便于后续替换实现。
"""
from __future__ import annotations

from typing import Any


def ocr_invoice(image_path: str) -> dict[str, Any]:
    """发票 OCR 识别（当前为占位实现，如实报告能力边界）。"""
    return {
        "status": "unsupported",
        "image_path": str(image_path),
        "message": "当前模型不支持图像输入，无法直接 OCR。",
        "suggestion": "请使用外部 OCR 服务或多模态模型（如 Ling-3.0-flash-VL）"
                      "将发票转为 JSON，再调用 parse_invoice 解析。",
    }


def register_tools(registry) -> None:
    from .base import Tool

    registry.register(Tool(
        name="ocr_invoice",
        description="发票 OCR 识别（预留接口）：当前模型不支持图像输入，"
                    "需先经外部 OCR 服务转为结构化数据。",
        parameters={
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "发票图片路径"},
            },
            "required": ["image_path"],
        },
        handler=ocr_invoice,
    ))

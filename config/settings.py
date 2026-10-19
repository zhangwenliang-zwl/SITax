"""配置管理：从环境变量读取，提供项目内默认值。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # 可选依赖：有 dotenv 就自动加载 .env
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    # OpenCode 本地服务默认端点（通过 LLM_API_BASE 环境变量自行覆盖）
    llm_api_base: str = os.getenv("LLM_API_BASE", "http://127.0.0.1:49374")
    # 优先读取 OpenCode 本地服务的 API Key（见 service.json password），兼容 LLM_API_KEY
    llm_api_key: str = os.getenv("OPENCODE_API_KEY", os.getenv("LLM_API_KEY", ""))
    llm_model: str = os.getenv("LLM_MODEL", "ling-3.1-flash-free")
    # 1=离线 Mock 演示（默认，无需 API Key），0=调用真实 OpenCode 本地服务
    llm_mock: bool = os.getenv("LLM_MOCK", "1") == "1"
    knowledge_path: str = str(PROJECT_ROOT / "data" / "tax_knowledge.json")
    sample_csv: str = str(PROJECT_ROOT / "data" / "invoices_sample.csv")
    invoice_path: str = str(PROJECT_ROOT / "data" / "invoices_detail.json")
    filing_export_path: str = str(PROJECT_ROOT / "data" / "vat_filing.csv")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
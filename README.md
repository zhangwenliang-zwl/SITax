# 税务管理智能体（Tax Management Agent）

面向企业税务管理的智能体框架：税务计算、政策检索、文档分析。

## 设计原则

1. **税额计算全部走确定性工具**：不允许模型心算金额，所有计算由规则代码完成并保留过程。
2. **政策检索走本地知识库**：每条知识强制标注来源与日期，未命中时明确提示"以官方最新公告为准"，禁止编造条文。
3. **ReAct 循环**：推理 → 工具调用 → 观察结果 → 继续推理，最多 N 步。
4. **Mock 模式**：不配置 API Key 也能离线跑通完整流程，便于开发调试。

## 快速开始

```bash
pip install -r requirements.txt
python examples/demo.py        # 离线演示（Mock 模式）
python tests/test_framework.py # 运行测试
```

## 目录结构

```
D:\SITax\
├── config/settings.py       # 配置（环境变量）
├── src/
│   ├── llm/client.py        # LLM 客户端（OpenAI 兼容，支持 Mock）
│   ├── tools/               # 工具层
│   │   ├── base.py          # 工具注册表
│   │   ├── tax_calculator.py# 增值税/企税/个税计算
│   │   ├── invoice.py       # 发票解析、校验、汇总
│   │   ├── filing.py        # 申报表生成与 CSV 导出
│   │   ├── document.py      # 文档读取与 CSV 分析
│   │   ├── ocr.py           # 发票 OCR（预留接口）
│   │   └── policy.py        # 政策检索
│   ├── knowledge/
│   │   ├── base.py          # 本地知识库
│   │   └── retriever.py     # BM25 检索器（可换向量检索）
│   └── agent/
│       ├── prompts.py       # 系统提示词（含合规护栏）
│       └── core.py          # Agent 主循环
├── data/                    # 知识库与示例数据
└── examples/demo.py         # 演示入口
```

## 配置

复制 `.env.example` 为 `.env` 并填写：

| 变量 | 说明 |
|---|---|
| `LLM_API_BASE` | OpenAI 兼容端点 |
| `LLM_API_KEY` | API 密钥 |
| `LLM_MODEL` | 模型 ID，默认 `ling-3.1-flash-free` |
| `LLM_MOCK` | `1`=离线 Mock（默认），`0`=调用真实 LLM |

## 功能一览

| 模块 | 能力 |
|---|---|
| tax_calculator | 增值税（一般/小规模）、企业所得税、个税累计预扣 |
| invoice | 发票解析、字段完整性、价税勾稽、税率档位校验、清单汇总 |
| filing | 简化版增值税申报表生成、CSV 导出（自动跳过无效发票） |
| document | 文本读取/摘要、CSV 发票清单统计 |
| ocr | 发票 OCR 预留接口（当前模型纯文本，需外部 OCR） |
| policy/knowledge | BM25 政策检索，条目强制标注来源与日期 |

## 合规护栏

- 模型只做计算、检索、整理；不做具体税务筹划建议。
- 涉及重组、跨境、大额交易等复杂情形，提示咨询专业税务师。
- 所有政策类输出必须带来源与日期，并提示核实。

## 路线图

- 发票 OCR 接入多模态模型（如 Ling-3.0-flash-VL）或专用 OCR API
- 知识库向量检索（RAG）与联网政策核实
- 完整申报表附列资料与电子税务局对接
- 进销项发票自动勾选认证

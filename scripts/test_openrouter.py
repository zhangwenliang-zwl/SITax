"""测试 OpenRouter 密钥与免费模型可用性。

请通过环境变量传入密钥，切勿硬编码：
    $env:OPENROUTER_API_KEY = "sk-or-..."
"""
import json
import os
import urllib.request

KEY = os.getenv("OPENROUTER_API_KEY", "")
if not KEY:
    print("请设置环境变量 OPENROUTER_API_KEY 后再运行")
    raise SystemExit(1)

# 1. 列出模型中是否有 ling
req = urllib.request.Request("https://openrouter.ai/api/v1/models")
req.add_header("Authorization", f"Bearer {KEY}")
try:
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    models = [m["id"] for m in data.get("data", [])]
    ling = [m for m in models if "ling" in m.lower()]
    print(f"共 {len(models)} 个模型；含 ling 的模型: {ling}")
except Exception as e:
    print("models 列表错误:", e)

# 2. 调用 inclusionai/ling-3.1-flash
payload = json.dumps({
    "model": "inclusionai/ling-3.1-flash",
    "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
    "max_tokens": 100,
}).encode()
req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=payload)
req.add_header("Authorization", f"Bearer {KEY}")
req.add_header("Content-Type", "application/json")
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    print("\n调用成功:", resp["choices"][0]["message"]["content"][:200])
    print("用量:", resp.get("usage"))
except Exception as e:
    print("\n调用错误:", e)

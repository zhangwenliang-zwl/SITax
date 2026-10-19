"""深度扫描桌面应用 Local Storage，提取 JSON 编码的令牌。"""
import base64
import json
import re
from pathlib import Path

LS = Path(r"C:\Users\Administrator\AppData\Roaming\ai.opencode.desktop\Local Storage\leveldb")

for f in LS.iterdir():
    if f.suffix not in (".ldb", ".log"):
        continue
    try:
        data = f.read_bytes()
    except OSError:
        continue
    text = data.decode("utf-8", errors="replace")
    # 查找长字符串（可能是 token）
    for m in re.finditer(r"[A-Za-z0-9_\-]{40,}", text):
        token = m.group(0)
        # 过滤掉明显的哈希/会话ID
        if re.match(r"^[a-f0-9]{40,}$", token):
            continue
        print(f"{f.name}: {token[:120]}")

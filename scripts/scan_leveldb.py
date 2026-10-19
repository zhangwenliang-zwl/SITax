"""扫描桌面应用 Local Storage 中的令牌。"""
import re
from pathlib import Path

LS = Path(r"C:\Users\Administrator\AppData\Roaming\ai.opencode.desktop\Local Storage\leveldb")

for f in LS.iterdir():
    if f.suffix not in (".ldb", ".log"):
        continue
    try:
        data = f.read_bytes()
    except OSError as e:
        print(f"{f.name}: 锁定/跳过 ({e})")
        continue
    text = data.decode("utf-8", errors="replace")
    # 查找 key/token 相关字符串
    for m in re.finditer(r".{0,60}(api[_-]?key|access_token|refresh_token|session|Bearer|sk-[a-z0-9]{8,}).{0,100}", text, re.IGNORECASE):
        snippet = re.sub(r"[^\x20-\x7e]", " ", m.group(0))
        print(f"{f.name}: {snippet}")

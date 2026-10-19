"""解析 OpenCode 模型目录（嵌套 body）中的提供商配置。"""
import json
import sqlite3

DB = r"C:\Users\Administrator\.local\share\opencode\opencode.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT value FROM kv WHERE key='models-dev:catalog'")
row = cur.fetchone()
conn.close()

catalog = json.loads(row[0])
body = json.loads(catalog["body"])
print("providers:", list(body.keys()))

oc = body.get("opencode")
if oc:
    print("\n== opencode provider ==")
    print(json.dumps(oc, indent=2, ensure_ascii=False)[:3000])

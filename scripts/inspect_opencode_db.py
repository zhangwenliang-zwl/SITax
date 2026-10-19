"""查询 OpenCode 账号认证令牌。"""
import sqlite3

DB = r"C:\Users\Administrator\.local\share\opencode\opencode.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("== account_state ==")
cur.execute("SELECT * FROM account_state")
for row in cur.fetchall():
    print(row)

print("\n== account ==")
cur.execute("SELECT id, email, url, length(access_token), length(refresh_token), token_expiry FROM account")
for row in cur.fetchall():
    print(row)

print("\n== account access_token (前缀) ==")
cur.execute("SELECT id, email, url, substr(access_token, 1, 20), token_expiry FROM account")
for row in cur.fetchall():
    print(row)

print("\n== control_account ==")
cur.execute("SELECT email, url, substr(access_token, 1, 20), active FROM control_account")
for row in cur.fetchall():
    print(row)

print("\n== kv ==")
cur.execute("SELECT key, substr(value, 1, 200) FROM kv")
for row in cur.fetchall():
    print(row)

conn.close()

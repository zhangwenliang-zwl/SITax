"""检查数据库状态。"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sitax.db")
print("DB exists:", os.path.exists(db_path))
print("DB path:", os.path.abspath(db_path))

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t[0]}")
        count = cursor.fetchone()[0]
        print(f"  {t[0]}: {count} rows")
    conn.close()
else:
    print("Database not found, running init...")
    import subprocess
    subprocess.run(["python", "src/db/init_db.py"], check=True)

"""SITax 数据库初始化脚本：创建 SQLite 数据库并导入初始数据。"""
import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sitax.db")


def init_database():
    """初始化数据库并创建表结构。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 发票表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_code TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('normal', 'special', 'cancelled', 'red_credit', 'red_debit', '销项', '进项')),
            amount REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            buyer_code TEXT,
            buyer_name TEXT,
            seller_code TEXT,
            seller_name TEXT,
            status TEXT DEFAULT 'valid' CHECK(status IN ('valid', 'invalid', 'cancelled')),
            warnings TEXT,
            errors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 税务知识库表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tax_knowledge (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            effective_date TEXT,
            verified INTEGER DEFAULT 0,
            note TEXT
        )
    """)

    # 申报记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS filing_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            taxpayer_type TEXT NOT NULL,
            sales_amount REAL DEFAULT 0,
            output_tax REAL DEFAULT 0,
            input_tax REAL DEFAULT 0,
            payable REAL DEFAULT 0,
            tax_burden_rate REAL DEFAULT 0,
            skipped_invalid INTEGER DEFAULT 0,
            formula TEXT,
            note TEXT,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'submitted', 'approved', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 计算历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calc_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calc_type TEXT NOT NULL,
            input_params TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 导入发票数据（JSON 文件在项目根 data/ 目录下）
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    invoice_path = os.path.join(base_dir, "data", "invoices_detail.json")
    if os.path.exists(invoice_path):
        with open(invoice_path, "r", encoding="utf-8") as f:
            invoices = json.load(f)
        for inv in invoices:
            cursor.execute("""
                INSERT OR IGNORE INTO invoices (invoice_code, invoice_number, issue_date, type, amount, tax, total, buyer_code, buyer_name, seller_code, seller_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv.get("invoice_code"),
                inv.get("invoice_number"),
                inv.get("issue_date"),
                inv.get("type"),
                inv.get("amount"),
                inv.get("tax"),
                inv.get("total"),
                inv.get("buyer_code"),
                inv.get("buyer_name"),
                inv.get("seller_code"),
                inv.get("seller_name"),
            ))

    # 导入知识库
    knowledge_path = os.path.join(base_dir, "data", "tax_knowledge.json")
    if os.path.exists(knowledge_path):
        with open(knowledge_path, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
        for item in knowledge:
            cursor.execute("""
                INSERT OR IGNORE INTO tax_knowledge (id, category, title, content, source, effective_date, verified, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("id"),
                item.get("category"),
                item.get("title"),
                item.get("content"),
                item.get("source"),
                item.get("effective_date"),
                1 if item.get("verified") else 0,
                item.get("note"),
            ))

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_database()

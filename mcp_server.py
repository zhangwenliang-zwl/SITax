"""SITax MCP 服务器：基于 JSON-RPC 2.0 的数据库服务。

支持操作：
- query_invoices: 查询发票
- query_tax_knowledge: 查询税务知识库
- add_filing_record: 添加申报记录
- query_filing_records: 查询申报记录
- add_calc_history: 添加计算记录
- query_calc_history: 查询计算记录
- get_db_stats: 获取数据库统计信息

使用 stdio 通信，适配 OpenCode MCP 协议。
"""
import json
import os
import sqlite3
import sys
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sitax.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """处理 JSON-RPC 请求。"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    result = None
    error = None

    try:
        if method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "query_invoices",
                        "description": "查询发票列表，支持按类型、日期、状态筛选",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "description": "发票类型：normal/special/销项/进项"},
                                "status": {"type": "string", "description": "状态：valid/invalid/cancelled"},
                                "limit": {"type": "integer", "description": "返回条数，默认 10"},
                                "offset": {"type": "integer", "description": "偏移量，默认 0"},
                            },
                        },
                    },
                    {
                        "name": "query_tax_knowledge",
                        "description": "查询税务知识库，支持关键词搜索",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "keyword": {"type": "string", "description": "搜索关键词"},
                                "category": {"type": "string", "description": "分类筛选"},
                                "limit": {"type": "integer", "description": "返回条数，默认 5"},
                            },
                        },
                    },
                    {
                        "name": "add_filing_record",
                        "description": "添加申报记录",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "period": {"type": "string", "description": "申报期，如 2026-09"},
                                "taxpayer_type": {"type": "string", "description": "纳税人类型：general/small"},
                                "sales_amount": {"type": "number", "description": "销售额"},
                                "output_tax": {"type": "number", "description": "销项税额"},
                                "input_tax": {"type": "number", "description": "进项税额"},
                                "payable": {"type": "number", "description": "应纳税额"},
                                "formula": {"type": "string", "description": "计算公式"},
                                "note": {"type": "string", "description": "备注"},
                            },
                            "required": ["period", "taxpayer_type"],
                        },
                    },
                    {
                        "name": "query_filing_records",
                        "description": "查询申报记录",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "period": {"type": "string", "description": "按申报期筛选"},
                                "status": {"type": "string", "description": "状态筛选"},
                                "limit": {"type": "integer", "description": "返回条数"},
                            },
                        },
                    },
                    {
                        "name": "add_calc_history",
                        "description": "添加计算历史记录",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "calc_type": {"type": "string", "description": "计算类型：vat/cit/iit"},
                                "input_params": {"type": "string", "description": "输入参数 JSON"},
                                "result": {"type": "string", "description": "计算结果 JSON"},
                            },
                            "required": ["calc_type", "input_params", "result"],
                        },
                    },
                    {
                        "name": "query_calc_history",
                        "description": "查询计算历史",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "calc_type": {"type": "string", "description": "计算类型筛选"},
                                "limit": {"type": "integer", "description": "返回条数"},
                            },
                        },
                    },
                    {
                        "name": "get_db_stats",
                        "description": "获取数据库统计信息",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = call_tool(tool_name, arguments)
        else:
            error = {"code": -32601, "message": f"Method not found: {method}"}
    except Exception as e:
        error = {"code": -32603, "message": str(e)}

    response = {"jsonrpc": "2.0", "id": req_id}
    if error:
        response["error"] = error
    else:
        response["result"] = result
    return response


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """执行具体工具调用。"""
    conn = get_db()
    cursor = conn.cursor()

    if name == "query_invoices":
        sql = "SELECT * FROM invoices WHERE 1=1"
        params_list: list[Any] = []
        if args.get("type"):
            sql += " AND type = ?"
            params_list.append(args["type"])
        if args.get("status"):
            sql += " AND status = ?"
            params_list.append(args["status"])
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params_list.extend([args.get("limit", 10), args.get("offset", 0)])
        cursor.execute(sql, params_list)
        rows = [dict(row) for row in cursor.fetchall()]
        return {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, indent=2)}]}

    elif name == "query_tax_knowledge":
        sql = "SELECT * FROM tax_knowledge WHERE 1=1"
        params_list = []
        if args.get("keyword"):
            sql += " AND (title LIKE ? OR content LIKE ?)"
            params_list.extend([f"%{args['keyword']}%", f"%{args['keyword']}%"])
        if args.get("category"):
            sql += " AND category = ?"
            params_list.append(args["category"])
        sql += " ORDER BY id LIMIT ?"
        params_list.append(args.get("limit", 5))
        cursor.execute(sql, params_list)
        rows = [dict(row) for row in cursor.fetchall()]
        return {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, indent=2)}]}

    elif name == "add_filing_record":
        cursor.execute("""
            INSERT INTO filing_records (period, taxpayer_type, sales_amount, output_tax, input_tax, payable, formula, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            args.get("period"),
            args.get("taxpayer_type"),
            args.get("sales_amount", 0),
            args.get("output_tax", 0),
            args.get("input_tax", 0),
            args.get("payable", 0),
            args.get("formula", ""),
            args.get("note", ""),
        ))
        conn.commit()
        return {"content": [{"type": "text", "text": f"申报记录已添加，ID: {cursor.lastrowid}"}]}

    elif name == "query_filing_records":
        sql = "SELECT * FROM filing_records WHERE 1=1"
        params_list = []
        if args.get("period"):
            sql += " AND period = ?"
            params_list.append(args["period"])
        if args.get("status"):
            sql += " AND status = ?"
            params_list.append(args["status"])
        sql += " ORDER BY created_at DESC LIMIT ?"
        params_list.append(args.get("limit", 10))
        cursor.execute(sql, params_list)
        rows = [dict(row) for row in cursor.fetchall()]
        return {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, indent=2)}]}

    elif name == "add_calc_history":
        cursor.execute("""
            INSERT INTO calc_history (calc_type, input_params, result)
            VALUES (?, ?, ?)
        """, (args.get("calc_type"), args.get("input_params"), args.get("result")))
        conn.commit()
        return {"content": [{"type": "text", "text": f"计算记录已添加，ID: {cursor.lastrowid}"}]}

    elif name == "query_calc_history":
        sql = "SELECT * FROM calc_history WHERE 1=1"
        params_list = []
        if args.get("calc_type"):
            sql += " AND calc_type = ?"
            params_list.append(args["calc_type"])
        sql += " ORDER BY created_at DESC LIMIT ?"
        params_list.append(args.get("limit", 10))
        cursor.execute(sql, params_list)
        rows = [dict(row) for row in cursor.fetchall()]
        return {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, indent=2)}]}

    elif name == "get_db_stats":
        stats = {}
        for table in ["invoices", "tax_knowledge", "filing_records", "calc_history"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        return {"content": [{"type": "text", "text": json.dumps(stats, ensure_ascii=False, indent=2)}]}

    else:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


def main():
    """MCP 服务器主循环。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as e:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }
            print(json.dumps(error_resp), flush=True)


if __name__ == "__main__":
    main()

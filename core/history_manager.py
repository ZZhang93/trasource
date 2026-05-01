"""
搜索历史管理器 — 基于 SQLite 存储
最多保留 200 条（FIFO）
"""

import json
import time
from typing import Optional
from core.db import get_connection

MAX_HISTORY = 200


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _row_to_dict(row) -> dict:
    if not row:
        return None
    d = dict(row)
    # expansion 字段是 JSON 字符串，解析为 dict
    if isinstance(d.get("expansion"), str):
        try:
            d["expansion"] = json.loads(d["expansion"])
        except (json.JSONDecodeError, TypeError):
            d["expansion"] = {}
    return d


def add_history(
    project_name: str,
    query: str,
    language: str = "zh",
    expansion: Optional[dict] = None,
    total_found: int = 0,
    ai_output: str = "",
) -> dict:
    """添加一条搜索历史，自动裁剪到 MAX_HISTORY 条。"""
    now = _now()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO search_history (project_name, query, language, expansion, total_found, ai_output, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_name, query, language,
         json.dumps(expansion or {}, ensure_ascii=False),
         total_found, ai_output, now),
    )
    entry_id = cursor.lastrowid

    # 裁剪：保留最新 MAX_HISTORY 条
    conn.execute(
        "DELETE FROM search_history WHERE id NOT IN (SELECT id FROM search_history ORDER BY created_at DESC LIMIT ?)",
        (MAX_HISTORY,),
    )
    conn.commit()

    entry = {
        "id": entry_id,
        "project_name": project_name,
        "query": query,
        "language": language,
        "expansion": expansion or {},
        "total_found": total_found,
        "ai_output": ai_output,
        "created_at": now,
    }
    conn.close()
    return entry


def list_history(project_name: Optional[str] = None, limit: int = 50) -> list:
    """返回历史列表（可按项目筛选），按时间倒序。"""
    conn = get_connection()
    if project_name:
        rows = conn.execute(
            "SELECT * FROM search_history WHERE project_name = ? ORDER BY created_at DESC LIMIT ?",
            (project_name, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM search_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_history(history_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM search_history WHERE id = ?", (history_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def update_history(history_id: int, updates: dict) -> bool:
    """更新历史记录的指定字段。"""
    if not updates:
        return False
    conn = get_connection()
    parts = []
    values = []
    for key, val in updates.items():
        if key == "expansion":
            parts.append("expansion = ?")
            values.append(json.dumps(val, ensure_ascii=False))
        elif key in ("ai_output", "total_found"):
            parts.append(f"{key} = ?")
            values.append(val)
    if not parts:
        conn.close()
        return False
    values.append(history_id)
    conn.execute(f"UPDATE search_history SET {', '.join(parts)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


def delete_history(history_id: int) -> bool:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM search_history WHERE id = ?", (history_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def clear_project_history(project_name: str) -> int:
    """清空某项目的所有历史，返回删除数量。"""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM search_history WHERE project_name = ?", (project_name,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    return deleted

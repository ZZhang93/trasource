"""
笔记管理器 — 基于 SQLite 存储
"""

import json
import time
from typing import Optional
from core.db import get_connection


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _row_to_dict(row) -> dict:
    return dict(row) if row else None


def list_notes(project_name: Optional[str] = None) -> list:
    """返回所有笔记（可按项目筛选），按 updated_at 降序"""
    conn = get_connection()
    if project_name:
        rows = conn.execute(
            "SELECT * FROM notes WHERE project_name = ? ORDER BY updated_at DESC",
            (project_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_note(note_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def create_note(
    title: str,
    content_md: str = "",
    project_name: Optional[str] = None,
    tags: str = "",
) -> dict:
    now = _now()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO notes (project_name, title, content_md, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (project_name or "", title, content_md, tags, now, now),
    )
    conn.commit()
    note = {
        "id": cursor.lastrowid,
        "project_name": project_name or "",
        "title": title,
        "content_md": content_md,
        "tags": tags,
        "created_at": now,
        "updated_at": now,
    }
    conn.close()
    return note


def update_note(
    note_id: int,
    title: Optional[str] = None,
    content_md: Optional[str] = None,
    tags: Optional[str] = None,
) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        conn.close()
        return None

    now = _now()
    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if content_md is not None:
        updates.append("content_md = ?")
        params.append(content_md)
    if tags is not None:
        updates.append("tags = ?")
        params.append(tags)
    updates.append("updated_at = ?")
    params.append(now)
    params.append(note_id)

    conn.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()

    updated = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return _row_to_dict(updated)


def delete_note(note_id: int) -> bool:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

"""
core/db.py — SQLite 连接管理 + 建表
用于 notes 和 search_history 的持久化存储
"""

import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "app.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_app_db():
    """建表（首次启动时执行）。"""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            content_md TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_name);
        CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC);

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            query TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'zh',
            expansion TEXT NOT NULL DEFAULT '{}',
            total_found INTEGER NOT NULL DEFAULT 0,
            ai_output TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_history_project ON search_history(project_name);
        CREATE INDEX IF NOT EXISTS idx_history_created ON search_history(created_at DESC);
    """)
    conn.close()

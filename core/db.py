"""
core/db.py — SQLite 连接管理 + 建表 + JSON 数据迁移
用于 notes 和 search_history 的持久化存储
"""

import json
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
    """建表 + 迁移旧 JSON 数据（首次启动时执行）。"""
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

    _migrate_json_to_sqlite()


def _migrate_json_to_sqlite():
    """将旧的 JSON 文件数据迁移到 SQLite，迁移后重命名为 .json.bak"""
    notes_file = os.path.join("data", "notes.json")
    history_file = os.path.join("data", "history.json")

    if os.path.exists(notes_file):
        try:
            with open(notes_file, "r", encoding="utf-8") as f:
                notes = json.load(f)
            if notes:
                conn = get_connection()
                # 检查是否已有数据（避免重复迁移）
                count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
                if count == 0:
                    for n in notes:
                        conn.execute(
                            "INSERT INTO notes (project_name, title, content_md, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (n.get("project_name", ""), n.get("title", ""), n.get("content_md", ""),
                             n.get("tags", ""), n.get("created_at", ""), n.get("updated_at", "")),
                        )
                    conn.commit()
                    logger.info(f"迁移 {len(notes)} 条笔记到 SQLite")
                conn.close()
            os.rename(notes_file, notes_file + ".bak")
            logger.info("notes.json 已迁移并重命名为 notes.json.bak")
        except Exception as e:
            logger.error(f"迁移 notes.json 失败: {e}", exc_info=True)

    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            if history:
                conn = get_connection()
                count = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
                if count == 0:
                    for h in history:
                        conn.execute(
                            "INSERT INTO search_history (project_name, query, language, expansion, total_found, ai_output, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (h.get("project_name", ""), h.get("query", ""), h.get("language", "zh"),
                             json.dumps(h.get("expansion", {}), ensure_ascii=False),
                             h.get("total_found", 0), h.get("ai_output", ""), h.get("created_at", "")),
                        )
                    conn.commit()
                    logger.info(f"迁移 {len(history)} 条搜索历史到 SQLite")
                conn.close()
            os.rename(history_file, history_file + ".bak")
            logger.info("history.json 已迁移并重命名为 history.json.bak")
        except Exception as e:
            logger.error(f"迁移 history.json 失败: {e}", exc_info=True)

"""
史料检索引擎 — FastAPI 后端服务
运行方式：python backend/server.py
监听端口：8765
"""

import sys
import os
import logging

# ────────────────────────────────────────────────
# 路径初始化：区分 PyInstaller 打包模式与开发模式
# ────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后运行
    # 代码资源在 sys._MEIPASS，数据写入 ~/Library/Application Support/trasource/
    sys.path.insert(0, sys._MEIPASS)
    DATA_DIR = os.path.join(
        os.path.expanduser('~'), 'Library', 'Application Support', 'trasource'
    )
    os.makedirs(DATA_DIR, exist_ok=True)
    for _d in ['data', 'logs', 'projects', 'uploads_tmp']:
        os.makedirs(os.path.join(DATA_DIR, _d), exist_ok=True)
    os.chdir(DATA_DIR)
else:
    # 开发模式：从项目根目录加载
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, ROOT)
    os.chdir(ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.routes.projects import router as projects_router
from backend.routes.search import router as search_router
from backend.routes.import_files import router as import_router
from backend.routes.library import router as library_router
from backend.routes.chat import router as chat_router
from backend.routes.notes import router as notes_router
from backend.routes.settings import router as settings_router
from backend.routes.history import router as history_router

# ────────────────────────────────────────────────
# 初始化 SQLite 数据库（notes + history）
# ────────────────────────────────────────────────
from core.db import init_app_db
init_app_db()

# ────────────────────────────────────────────────
# 日志
# ────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend")

# ────────────────────────────────────────────────
# FastAPI 应用
# ────────────────────────────────────────────────
app = FastAPI(
    title="史料检索引擎 API",
    version="0.1.0",
    docs_url="/docs",
)

# 允许前端 Vite dev server 跨域（开发模式）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",   # Vite dev server
        "http://127.0.0.1:1420",
        "tauri://localhost",       # Tauri production
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────
# 路由注册
# ────────────────────────────────────────────────
app.include_router(projects_router)
app.include_router(search_router)
app.include_router(import_router)
app.include_router(library_router)
app.include_router(chat_router)
app.include_router(notes_router)
app.include_router(settings_router)
app.include_router(history_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ────────────────────────────────────────────────
# 启动
# ────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("启动 问渠 后端服务，端口 8765")
    # PyInstaller 打包后必须传 app 对象而非模块字符串（无法动态导入）
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )

"""
史料检索引擎 — FastAPI 后端服务
运行方式：python backend/server.py
监听端口：8765
"""

import sys
import os
import hmac
import logging

# ────────────────────────────────────────────────
# 路径初始化：区分 PyInstaller 打包模式与开发模式
# ────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后运行
    # 代码资源在 sys._MEIPASS，数据写入当前平台的用户数据目录。
    sys.path.insert(0, sys._MEIPASS)
    from core.platform_paths import get_app_data_dir, migrate_legacy_app_data
    DATA_DIR = get_app_data_dir("trasource")
    migrate_legacy_app_data(DATA_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)
    for _d in ['data', 'logs', 'projects', 'uploads_tmp']:
        os.makedirs(os.path.join(DATA_DIR, _d), exist_ok=True)
    os.chdir(DATA_DIR)

    # ── 孤儿进程防护 ──────────────────────────────
    # 应用退出时 Tauri 用 SIGKILL 杀 sidecar，但只能杀到 PyInstaller 的
    # 引导进程，信号无法传递给真正的 Python 子进程，会留下孤儿后端
    # 继续占用 8765 端口（导致下次启动连到旧后端）。
    # 这里监视 stdin（Tauri 持有的管道）：主程序退出 → 管道关闭 →
    # read() 返回 EOF → 后端自行退出。同时覆盖主程序崩溃的情况。
    def _exit_when_parent_dies(
        stdin_fd=sys.stdin.fileno(),
        read_fd=os.read,
        force_exit=os._exit,
    ):
        try:
            # Read the file descriptor directly instead of holding the
            # buffered stdin lock.  A daemon thread blocked in
            # `sys.stdin.buffer.read()` can otherwise make CPython abort while
            # it finalizes after a graceful signal (for example Ctrl-C).
            while read_fd(stdin_fd, 4096):
                pass
        except OSError:
            pass
        force_exit(0)

    import threading
    threading.Thread(target=_exit_when_parent_dies, daemon=True).start()
else:
    # 开发模式：从项目根目录加载
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, ROOT)
    os.chdir(ROOT)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
INSTANCE_TOKEN = os.environ.get("TRASOURCE_INSTANCE_TOKEN", "")
AUTH_HEADER = "X-Trasource-Token"

# ────────────────────────────────────────────────
# FastAPI 应用
# ────────────────────────────────────────────────
app = FastAPI(
    title="史料检索引擎 API",
    version="1.4.1",
    docs_url="/docs",
)

# 只接受本应用自身的浏览器来源。CORS 本身不会阻止恶意网页发送某些
# “simple requests”，因此额外做 Origin 门禁，保护监听在本机的写接口。
FRONTEND_ORIGINS = {
    "http://localhost:1420",   # Vite dev server
    "http://127.0.0.1:1420",
    "tauri://localhost",       # Tauri production (macOS/Linux)
    "http://tauri.localhost",  # Tauri production (Windows)
    "https://tauri.localhost",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(FRONTEND_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_frontend_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in FRONTEND_ORIGINS:
        return JSONResponse(status_code=403, content={"detail": "不允许的请求来源"})
    # Custom headers trigger a browser CORS preflight. The preflight carries
    # only Access-Control-Request-Headers, not the secret itself, so let the
    # CORS middleware answer OPTIONS and authenticate the actual request.
    is_api_request = request.url.path == "/api" or request.url.path.startswith("/api/")
    if is_api_request and request.method != "OPTIONS" and INSTANCE_TOKEN:
        supplied = request.headers.get(AUTH_HEADER, "")
        if not hmac.compare_digest(
            supplied.encode("utf-8"), INSTANCE_TOKEN.encode("utf-8")
        ):
            return JSONResponse(
                status_code=401,
                content={"detail": "后端认证失败"},
                headers={"Cache-Control": "no-store"},
            )
    # Run before FastAPI/Starlette parses multipart form data, otherwise an
    # oversized upload may already have consumed temporary disk by the time the
    # endpoint-level size check runs.
    if request.url.path == "/api/upload":
        length = request.headers.get("content-length")
        if request.headers.get("content-type", "").startswith("multipart/") and not length:
            return JSONResponse(status_code=411, content={"detail": "上传必须提供 Content-Length"})
        if length:
            try:
                if int(length) > 501 * 1024 * 1024:
                    return JSONResponse(status_code=413, content={"detail": "文件超过 500MB 上限"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "无效的 Content-Length"})
    return await call_next(request)

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
    return {
        "status": "ok",
        "version": "1.4.1",
        # A successful authenticated response already proves ownership. Never
        # echo the bearer secret back over HTTP.
        "instance_authenticated": bool(INSTANCE_TOKEN),
    }


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

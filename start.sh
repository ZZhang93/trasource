#!/bin/bash
# 史料检索引擎 — 开发环境启动脚本
# 用法：./start.sh
# 会自动清理旧进程、启动 FastAPI 后端、再启动 Tauri 窗口

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 启动史料检索引擎..."

# ── 清理旧的后端进程 ──
OLD_PID=$(lsof -ti :8765 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    echo "🧹 清理旧后端进程 (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
fi

# ── 检查 Python ──
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

# ── 检查并安装 Python 依赖 ──
if ! python3 -c "import fastapi, uvicorn, duckdb" &>/dev/null 2>&1; then
    echo "📦 安装 Python 依赖..."
    pip3 install -r requirements.txt
fi

# ── 建立必要目录 ──
mkdir -p data logs projects uploads_tmp

# ── 启动 Python 后端（后台）──
echo "🐍 启动 Python FastAPI 后端 (端口 8765)..."
python3 -m uvicorn backend.server:app \
    --host 127.0.0.1 \
    --port 8765 \
    --log-level warning &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# ── 等待后端就绪 ──
echo -n "   等待后端启动"
for i in $(seq 1 10); do
    if curl -sf http://127.0.0.1:8765/api/health > /dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 0.5
done

# ── 启动 Tauri 开发窗口 ──
echo "🖥️  启动 Tauri 应用窗口..."
source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
npm run tauri dev

# ── 退出时清理 ──
echo ""
echo "🛑 关闭后端 (PID $BACKEND_PID)..."
kill $BACKEND_PID 2>/dev/null || true

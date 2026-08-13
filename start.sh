#!/bin/bash
# 史料检索引擎 — 开发环境启动脚本
# 用法：./start.sh
# Tauri 开发版会自行启动唯一的 FastAPI 后端。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 启动史料检索引擎..."

# ── 检查 Node.js / 前端依赖 ──
if ! command -v npm &>/dev/null; then
    echo "❌ 未找到 npm，请先安装 Node.js 22+"
    exit 1
fi
if [ ! -d node_modules ]; then
    echo "📦 安装前端依赖..."
    npm ci
fi

# ── 检查 Python ──
if [ -x ".venv/bin/python" ]; then
    TRASOURCE_DEV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    TRASOURCE_DEV_PYTHON="$(command -v python3)"
else
    echo "❌ 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

# ── 检查并安装锁定的 Python 依赖 ──
# 只探测几个 import 会漏掉 SDK 迁移或版本漂移。这里逐项核对 lock；
# 已满足时完全离线且只需一次 Python 启动。
if ! "$TRASOURCE_DEV_PYTHON" - "$SCRIPT_DIR/requirements.lock" <<'PY' &>/dev/null
import importlib.metadata
import pathlib
import sys

for raw in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    name, expected = line.split("==", 1)
    if importlib.metadata.version(name) != expected:
        raise SystemExit(1)
PY
then
    echo "📦 安装 Python 依赖..."
    "$TRASOURCE_DEV_PYTHON" -m pip install -r requirements.lock
fi

# ── 启动 Tauri 开发窗口 ──
echo "🖥️  启动 Tauri 应用窗口..."
if [ -f "${HOME}/.cargo/env" ]; then
    # shellcheck disable=SC1091
    source "${HOME}/.cargo/env"
fi
if ! command -v cargo &>/dev/null; then
    echo "❌ 未找到 Rust/Cargo，请先安装 rustup"
    exit 1
fi
TRASOURCE_PYTHON="$TRASOURCE_DEV_PYTHON" npm run desktop:dev

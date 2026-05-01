# ============================================================
# core/settings_manager.py
# 用户配置持久化（读写 settings.json）
# ============================================================

import json
import logging
import os

logger = logging.getLogger(__name__)


def load_settings(path: str) -> dict:
    """
    从 JSON 文件加载设置。
    文件不存在或解析失败时返回空 dict（调用方使用 config.py 默认值）。
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning(f"读取设置文件失败，使用默认值: {e}")
    return {}


def save_settings(path: str, settings: dict) -> None:
    """将设置字典写入 JSON 文件（原子写入）。"""
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"保存设置文件失败: {e}")

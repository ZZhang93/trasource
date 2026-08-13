# ============================================================
# core/settings_manager.py
# 用户配置持久化（读写 settings.json）
# ============================================================

import json
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def load_settings(path: str, *, strict: bool = False) -> dict:
    """
    从 JSON 文件加载设置。
    文件不存在时返回空 dict。后台运行路径可在解析失败时回退默认值；
    设置读写界面应传 strict=True，避免用默认值覆盖一份损坏但可恢复的配置。
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"读取设置文件失败，使用默认值: {e}")
        if strict:
            raise ValueError(f"设置文件无法读取：{e}") from e
        return {}
    if not isinstance(data, dict):
        message = "设置文件顶层必须是 JSON 对象"
        logger.warning(message)
        if strict:
            raise ValueError(message)
        return {}
    return data


def save_settings(path: str, settings: dict) -> None:
    """将设置字典写入 JSON 文件（原子写入）。"""
    directory = os.path.dirname(os.path.abspath(path))
    fd = -1
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(prefix=".settings-", suffix=".tmp", dir=directory)
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = -1
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        if os.name == "posix":
            os.chmod(path, 0o600)
    except Exception as e:
        logger.error(f"保存设置文件失败: {e}")
        if fd >= 0:
            os.close(fd)
        if tmp:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
        raise

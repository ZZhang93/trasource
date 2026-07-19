# ============================================================
# core/project_manager.py
# 项目管理模块：创建、列出、删除项目
# ============================================================

import os
import json
import shutil
import logging
from datetime import datetime
from config import PROJECTS_DIR

logger = logging.getLogger(__name__)

# 全局共享文件库的固定项目名（不显示在项目列表中）
SHARED_PROJECT = "_shared"


def get_project_dir(project_name: str) -> str:
    return os.path.join(PROJECTS_DIR, project_name)


def get_db_path(project_name: str) -> str:
    return os.path.join(get_project_dir(project_name), "db", "history.duckdb")


def get_meta_path(project_name: str) -> str:
    return os.path.join(get_project_dir(project_name), "project.json")


def get_shared_db_path() -> str:
    """返回全局共享文件库的数据库路径"""
    return get_db_path(SHARED_PROJECT)


def _default_meta(name: str) -> dict:
    now = datetime.now().isoformat()
    return {
        "name": name,
        "description": "",
        "created_at": now,
        "updated_at": now,
        "record_count": 0,
        "shared_files": [],
    }


def _write_meta_atomic(meta_path: str, meta: dict):
    """原子写入 project.json（tmp + rename），进程被杀也不会留下半截文件。"""
    tmp = meta_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, meta_path)


def _load_or_repair_meta(name: str) -> dict:
    """
    读取项目元数据；project.json 缺失或损坏时自动重建（自愈）。
    这保证了「目录存在的项目一定能显示出来」——不会再出现
    建项目提示已存在、列表里却看不到的幽灵状态。
    """
    meta_path = get_meta_path(name)
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if isinstance(meta, dict) and meta.get("name"):
            meta.setdefault("shared_files", [])
            return meta
        raise ValueError("project.json 内容无效")
    except Exception as e:
        logger.warning(f"项目「{name}」的 project.json 缺失或损坏（{e}），自动重建")
        meta = _default_meta(name)
        try:
            ts = datetime.fromtimestamp(os.path.getmtime(get_project_dir(name))).isoformat()
            meta["created_at"] = meta["updated_at"] = ts
        except OSError:
            pass
        try:
            _write_meta_atomic(meta_path, meta)
        except Exception as we:
            logger.error(f"重建 project.json 失败: {we}")
        return meta


def ensure_shared_project():
    """确保共享文件库目录存在（启动时调用一次）"""
    project_dir = get_project_dir(SHARED_PROJECT)
    if not os.path.exists(project_dir):
        try:
            create_project(SHARED_PROJECT, "全局共享文件库（供所有项目引用）")
            logger.info("共享文件库已创建")
        except Exception as e:
            logger.warning(f"创建共享文件库失败: {e}")


def list_projects() -> list:
    """
    列出所有项目（不含共享库）。
    单个项目的 project.json 损坏/缺失时自动修复，绝不因一个坏项目
    导致整个列表接口失败。
    """
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)
        return []
    projects = []
    for name in os.listdir(PROJECTS_DIR):
        if name == SHARED_PROJECT:
            continue
        if not os.path.isdir(get_project_dir(name)):
            continue  # 跳过 .DS_Store 等杂项文件
        projects.append(_load_or_repair_meta(name))
    projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return projects


def get_project_shared_files(project_name: str) -> list:
    """读取该项目已选中的共享文件列表"""
    try:
        meta = get_project_meta(project_name)
        return meta.get("shared_files", [])
    except Exception:
        return []


def set_project_shared_files(project_name: str, files: list):
    """保存项目选中的共享文件列表到 project.json（原子写入）"""
    try:
        meta = _load_or_repair_meta(project_name)
        meta["shared_files"] = files
        meta["updated_at"] = datetime.now().isoformat()
        _write_meta_atomic(get_meta_path(project_name), meta)
    except Exception as e:
        logger.warning(f"保存共享文件列表失败: {e}")


def create_project(name: str, description: str = "") -> dict:
    """
    创建新项目。
    目录已存在且 project.json 有效 → 报「已存在」（此时列表里一定能看到它）；
    目录存在但 project.json 缺失/损坏（历史残留）→ 自动修复并沿用，不再卡死用户。
    """
    project_dir = get_project_dir(name)
    if os.path.exists(project_dir):
        meta_path = get_meta_path(name)
        valid = False
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    valid = bool(json.load(f).get("name"))
            except Exception:
                valid = False
        if valid:
            raise ValueError(f"项目「{name}」已存在")
        logger.warning(f"检测到残留项目目录「{name}」（缺少有效 project.json），自动修复")

    os.makedirs(os.path.join(project_dir, "db"), exist_ok=True)

    meta = _default_meta(name)
    meta["description"] = description
    _write_meta_atomic(get_meta_path(name), meta)
    return meta


def delete_project(project_name: str):
    """删除项目及其所有数据"""
    project_dir = get_project_dir(project_name)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)


def get_project_meta(project_name: str) -> dict:
    if not os.path.isdir(get_project_dir(project_name)):
        raise ValueError(f"项目「{project_name}」不存在")
    return _load_or_repair_meta(project_name)

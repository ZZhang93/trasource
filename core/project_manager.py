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


def get_raw_files_dir(project_name: str) -> str:
    return os.path.join(get_project_dir(project_name), "raw_files")


def get_shared_db_path() -> str:
    """返回全局共享文件库的数据库路径"""
    return get_db_path(SHARED_PROJECT)


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
    """列出所有项目（不含共享库），返回项目信息列表"""
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)
        return []
    projects = []
    for name in os.listdir(PROJECTS_DIR):
        if name == SHARED_PROJECT:
            continue
        meta_path = get_meta_path(name)
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            projects.append(meta)
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
    """保存项目选中的共享文件列表到 project.json"""
    meta_path = get_meta_path(project_name)
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["shared_files"] = files
        meta["updated_at"] = datetime.now().isoformat()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存共享文件列表失败: {e}")


def create_project(name: str, description: str = "") -> dict:
    """创建新项目"""
    project_dir = get_project_dir(name)
    if os.path.exists(project_dir):
        raise ValueError(f"项目「{name}」已存在")

    os.makedirs(os.path.join(project_dir, "db"))
    os.makedirs(os.path.join(project_dir, "raw_files"))

    meta = {
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "file_count": 0,
        "record_count": 0,
        "files": [],
        "shared_files": [],
    }
    with open(get_meta_path(name), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def update_project_meta(project_name: str, **kwargs):
    """更新项目元数据"""
    meta_path = get_meta_path(project_name)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta.update(kwargs)
    meta["updated_at"] = datetime.now().isoformat()
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def delete_project(project_name: str):
    """删除项目及其所有数据"""
    project_dir = get_project_dir(project_name)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)


def get_project_meta(project_name: str) -> dict:
    meta_path = get_meta_path(project_name)
    if not os.path.exists(meta_path):
        raise ValueError(f"项目「{project_name}」不存在")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)

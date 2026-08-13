# ============================================================
# core/project_manager.py
# 项目管理模块：创建、列出、删除项目
# ============================================================

import os
import json
import shutil
import logging
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from config import PROJECTS_DIR

logger = logging.getLogger(__name__)

# 全局共享文件库的固定项目名（不显示在项目列表中）
SHARED_PROJECT = "_shared"
_project_locks: dict[str, threading.RLock] = {}
_project_locks_guard = threading.Lock()


class ProjectIdentityMismatchError(ValueError):
    """The project name now refers to a different project lifecycle."""


def _get_project_lock(project_name: str) -> threading.RLock:
    # Serialize case variants too. This is required on the case-insensitive
    # filesystems commonly used by Windows and macOS; on a case-sensitive
    # filesystem it only causes harmless extra serialization.
    key = validate_project_name(project_name).casefold()
    with _project_locks_guard:
        return _project_locks.setdefault(key, threading.RLock())


@contextmanager
def lock_projects(project_names):
    """Hold project lifecycle locks in a stable order for a multi-project update."""
    names_by_key = {}
    for project_name in project_names:
        name = validate_project_name(project_name)
        names_by_key.setdefault(name.casefold(), name)
    locks = [_get_project_lock(names_by_key[key]) for key in sorted(names_by_key)]
    for lock in locks:
        lock.acquire()
    try:
        yield
    finally:
        for lock in reversed(locks):
            lock.release()


def validate_project_name(project_name: str, *, allow_shared: bool = True) -> str:
    """Validate a project name before it is used as a filesystem component.

    Project names are directory names, not paths.  Keeping this check in the
    core layer is important because not every caller goes through the HTTP
    route's validation.
    """
    if not isinstance(project_name, str):
        raise ValueError("项目名称必须是字符串")
    if not project_name or project_name != project_name.strip():
        raise ValueError("项目名称不能为空或包含首尾空格")
    if project_name in (".", ".."):
        raise ValueError("项目名称不能为 . 或 ..")
    if project_name == SHARED_PROJECT and not allow_shared:
        raise ValueError("保留项目名称不可使用")
    forbidden = set('/\\:*?"<>|')
    if any(c in forbidden or ord(c) < 32 for c in project_name):
        raise ValueError("项目名称包含非法字符")
    if project_name.endswith((".", " ")):
        raise ValueError("项目名称不能以句点或空格结尾")
    windows_stem = project_name.split(".", 1)[0].upper()
    windows_reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    }
    if windows_stem in windows_reserved:
        raise ValueError("项目名称是系统保留名")
    if os.path.isabs(project_name):
        raise ValueError("项目名称不能是绝对路径")
    if len(os.fsencode(project_name)) > 255:
        raise ValueError("项目名称过长")
    return project_name


def _projects_root() -> str:
    return os.path.realpath(os.path.abspath(PROJECTS_DIR))


def get_project_dir(project_name: str) -> str:
    """Return a canonical path that is strictly contained by PROJECTS_DIR."""
    name = validate_project_name(project_name)
    root = _projects_root()
    candidate = os.path.realpath(os.path.join(root, name))
    try:
        contained = os.path.commonpath([root, candidate]) == root
    except ValueError:
        contained = False
    if not contained or candidate == root:
        raise ValueError("项目路径越界")
    return candidate


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
        "project_id": str(uuid.uuid4()),
        "name": name,
        "description": "",
        "created_at": now,
        "updated_at": now,
        "record_count": 0,
        "shared_files": [],
    }


def _write_meta_atomic(meta_path: str, meta: dict):
    """原子写入 project.json（tmp + rename），进程被杀也不会留下半截文件。"""
    directory = os.path.dirname(meta_path)
    fd, tmp = tempfile.mkstemp(prefix=".project-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, meta_path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _load_or_repair_meta(name: str) -> dict:
    """
    读取项目元数据；project.json 缺失或损坏时自动重建（自愈）。
    这保证了「目录存在的项目一定能显示出来」——不会再出现
    建项目提示已存在、列表里却看不到的幽灵状态。
    """
    with _get_project_lock(name):
        meta_path = get_meta_path(name)
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
            repair_reason = error
        else:
            if isinstance(meta, dict) and meta.get("name"):
                changed = False
                if not isinstance(meta.get("project_id"), str) or not meta["project_id"]:
                    # Give pre-project-id metadata a persistent lifecycle identity.
                    # Persistence errors must propagate: an ephemeral ID would make
                    # a running import compare against a different value later.
                    meta["project_id"] = str(uuid.uuid4())
                    changed = True
                if "shared_files" not in meta:
                    meta["shared_files"] = []
                    changed = True
                if changed:
                    _write_meta_atomic(meta_path, meta)
                return meta
            repair_reason = ValueError("project.json 内容无效")

        logger.warning(
            f"项目「{name}」的 project.json 缺失或损坏（{repair_reason}），自动重建"
        )
        meta = _default_meta(name)
        try:
            ts = datetime.fromtimestamp(os.path.getmtime(get_project_dir(name))).isoformat()
            meta["created_at"] = meta["updated_at"] = ts
        except OSError:
            pass
        _write_meta_atomic(meta_path, meta)
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
        try:
            project_dir = get_project_dir(name)
        except ValueError as e:
            logger.warning(f"跳过不安全的项目目录「{name}」：{e}")
            continue
        if not os.path.isdir(project_dir):
            continue  # 跳过 .DS_Store 等杂项文件
        projects.append(_load_or_repair_meta(name))
    projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return projects


def get_project_shared_files(project_name: str) -> list:
    """读取该项目已选中的共享文件列表"""
    meta = get_project_meta(project_name)
    files = meta.get("shared_files", [])
    if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
        raise ValueError(f"项目「{project_name}」的共享文件列表损坏")
    return list(files)


def _assert_project_identity(meta: dict, project_name: str, expected_project_id: str | None):
    if expected_project_id is not None and meta.get("project_id") != expected_project_id:
        raise ProjectIdentityMismatchError(f"项目「{project_name}」已被删除或重建")


def set_project_shared_files(
    project_name: str,
    files: list,
    *,
    expected_project_id: str | None = None,
):
    """保存项目选中的共享文件列表到 project.json（原子写入）"""
    if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
        raise ValueError("共享文件列表格式无效")
    with _get_project_lock(project_name):
        try:
            meta = get_project_meta(project_name)
        except ValueError as error:
            if expected_project_id is not None:
                raise ProjectIdentityMismatchError(
                    f"项目「{project_name}」已被删除或重建"
                ) from error
            raise
        _assert_project_identity(meta, project_name, expected_project_id)
        meta["shared_files"] = list(dict.fromkeys(files))
        meta["updated_at"] = datetime.now().isoformat()
        _write_meta_atomic(get_meta_path(project_name), meta)


def add_project_shared_file(
    project_name: str,
    filename: str,
    *,
    expected_project_id: str | None = None,
) -> list:
    """Atomically add one shared-file reference and return the new list."""
    if not isinstance(filename, str) or not filename:
        raise ValueError("文件名无效")
    with _get_project_lock(project_name):
        try:
            meta = get_project_meta(project_name)
        except ValueError as error:
            if expected_project_id is not None:
                raise ProjectIdentityMismatchError(
                    f"项目「{project_name}」已被删除或重建"
                ) from error
            raise
        _assert_project_identity(meta, project_name, expected_project_id)
        files = meta.get("shared_files", [])
        if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
            raise ValueError(f"项目「{project_name}」的共享文件列表损坏")
        if filename not in files:
            set_project_shared_files(
                project_name,
                [*files, filename],
                expected_project_id=expected_project_id,
            )
        return get_project_shared_files(project_name)


def remove_project_shared_file(
    project_name: str,
    filename: str,
    *,
    expected_project_id: str | None = None,
) -> list:
    """Atomically remove one shared-file reference and return the new list."""
    with _get_project_lock(project_name):
        try:
            meta = get_project_meta(project_name)
        except ValueError as error:
            if expected_project_id is not None:
                raise ProjectIdentityMismatchError(
                    f"项目「{project_name}」已被删除或重建"
                ) from error
            raise
        _assert_project_identity(meta, project_name, expected_project_id)
        files = meta.get("shared_files", [])
        if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
            raise ValueError(f"项目「{project_name}」的共享文件列表损坏")
        if filename in files:
            set_project_shared_files(
                project_name,
                [f for f in files if f != filename],
                expected_project_id=expected_project_id,
            )
        return get_project_shared_files(project_name)


def create_project(name: str, description: str = "") -> dict:
    """
    创建新项目。
    目录已存在且 project.json 有效 → 报「已存在」（此时列表里一定能看到它）；
    目录存在但 project.json 缺失/损坏（历史残留）→ 自动修复并沿用，不再卡死用户。
    """
    name = validate_project_name(name)
    with _get_project_lock(name):
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
    validate_project_name(project_name, allow_shared=False)
    with _get_project_lock(project_name):
        project_dir = get_project_dir(project_name)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)


def get_project_meta(project_name: str) -> dict:
    with _get_project_lock(project_name):
        if not os.path.isdir(get_project_dir(project_name)):
            raise ValueError(f"项目「{project_name}」不存在")
        return _load_or_repair_meta(project_name)

"""
/api/library + /api/upload — 文献库管理 + 文件上传

架构说明
────────
共享库（_shared）是唯一的文献存储库，所有文件的 DuckDB 记录都存在这里。
项目不复制数据，只在 project.json 的 shared_files 列表中保存「引用了哪些文件」。
搜索时，retriever 会查询共享库中被本项目引用的文件记录。
"""

import os
import logging
from urllib.parse import unquote
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel, Field

import core.project_manager as pm
import core.retriever as retriever
import core.ingest as ingest
from backend.routes.import_files import (
    release_filename,
    reserve_filename,
)

router = APIRouter()
logger = logging.getLogger("backend.library")

# 临时上传目录（使用 cwd，因为 server.py 已将工作目录设为正确位置）
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads_tmp")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


# ── 文件上传 ──────────────────────────────────────────────────

@router.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(None)):
    """接收上传文件，支持两种方式：
    1. multipart/form-data（浏览器标准上传）
    2. application/octet-stream + X-Filename header（Tauri WKWebView 兼容方式）
    """
    content_type = request.headers.get("content-type", "")
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_BYTES + 1024 * 1024:
                raise HTTPException(status_code=413, detail="文件超过 500MB 上限")
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的 Content-Length")

    if "multipart" in content_type and file is not None:
        # 标准 FormData 上传
        filename = file.filename or "upload"
        dest, fd = _reserve_unique_dest(filename)
        try:
            total = 0
            with os.fdopen(fd, "wb") as f:
                fd = -1
                while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                    total += len(chunk)
                    if total > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="文件超过 500MB 上限")
                    f.write(chunk)
        except HTTPException:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(dest)
            except FileNotFoundError:
                pass
            raise
        except Exception as e:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(dest)
            except FileNotFoundError:
                pass
            logger.error(f"文件上传失败（multipart）：{e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # 二进制流上传（Tauri 兼容）
        raw_name = request.headers.get("x-filename", "upload")
        filename = unquote(raw_name)
        dest, fd = _reserve_unique_dest(filename)
        try:
            total = 0
            with os.fdopen(fd, "wb") as f:
                fd = -1
                async for chunk in request.stream():
                    total += len(chunk)
                    if total > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="文件超过 500MB 上限")
                    f.write(chunk)
        except HTTPException:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(dest)
            except FileNotFoundError:
                pass
            raise
        except Exception as e:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(dest)
            except FileNotFoundError:
                pass
            logger.error(f"文件上传失败（binary）：{e}")
            raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"文件上传成功：{dest} ({os.path.getsize(dest):,} bytes)")
    return {"path": dest, "filename": os.path.basename(dest)}


def _sanitize_filename(filename: str) -> str:
    """只保留文件名本身，剥离目录成分，防止路径穿越写入 UPLOAD_DIR 之外。
    兼容 Windows 风格分隔符（POSIX 的 os.path.basename 不认 \\）。"""
    name = filename.replace("\\", "/").split("/")[-1]
    if name in ("", ".", ".."):
        name = "upload"
    return name


def _reserve_unique_dest(filename: str) -> tuple[str, int]:
    """原子占用一个不重复的目标路径，避免并发上传互删文件。"""
    filename = _sanitize_filename(filename)
    base, ext = os.path.splitext(filename)
    counter = 0
    while True:
        candidate = filename if counter == 0 else f"{base}_{counter}{ext}"
        dest = os.path.join(UPLOAD_DIR, candidate)
        try:
            fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            return dest, fd
        except FileExistsError:
            counter += 1


# ── 共享库统计 ────────────────────────────────────────────────

@router.get("/api/library/stats/_shared")
def shared_stats():
    """共享库所有文件及总记录数"""
    db = pm.get_shared_db_path()
    if not os.path.exists(db):
        return {"files": [], "total": 0}
    try:
        files = retriever.get_all_source_files(db)
        total = ingest.get_record_count(db)
        return {"files": files, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/library/stats/{project_name}")
def project_stats(project_name: str):
    """项目的文件列表（= shared_files 引用）及记录数统计"""
    if project_name == "_shared":
        return shared_stats()

    try:
        pm.validate_project_name(project_name, allow_shared=False)
        pm.get_project_meta(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    project_files = pm.get_project_shared_files(project_name)
    if not project_files:
        return {"files": [], "total": 0}

    shared_db = pm.get_shared_db_path()
    total = 0
    if os.path.exists(shared_db):
        try:
            total = ingest.get_records_count_for_files(shared_db, project_files)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取共享库统计失败：{e}")
    return {"files": project_files, "total": total}


# ── 项目文件引用管理 ──────────────────────────────────────────

class AddFileRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=1024)


@router.post("/api/projects/{project_name}/add-file")
async def add_file_to_project(project_name: str, req: AddFileRequest):
    """将共享库文件加入项目引用列表（不复制数据）"""
    try:
        pm.validate_project_name(project_name, allow_shared=False)
        project_meta = pm.get_project_meta(project_name)
        operation = "reference:add"
        if not reserve_filename(req.filename, operation):
            raise HTTPException(status_code=409, detail="文件正在处理，请稍后重试")
        try:
            db = pm.get_shared_db_path()
            if not os.path.exists(db) or req.filename not in retriever.get_all_source_files(db):
                raise HTTPException(status_code=404, detail="共享库中不存在该文件")
            current = pm.add_project_shared_file(
                project_name,
                req.filename,
                expected_project_id=project_meta["project_id"],
            )
            return {"project": project_name, "files": current}
        finally:
            release_filename(req.filename, operation)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存项目文件引用失败：{e}")


@router.delete("/api/projects/{project_name}/file/{filename:path}")
async def remove_file_from_project(project_name: str, filename: str):
    """从项目引用列表中移除文件（不删除共享库数据）"""
    try:
        pm.validate_project_name(project_name, allow_shared=False)
        project_meta = pm.get_project_meta(project_name)
        operation = "reference:remove"
        if not reserve_filename(filename, operation):
            raise HTTPException(status_code=409, detail="文件正在处理，请稍后重试")
        try:
            current = pm.remove_project_shared_file(
                project_name,
                filename,
                expected_project_id=project_meta["project_id"],
            )
            return {"project": project_name, "files": current}
        finally:
            release_filename(filename, operation)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存项目文件引用失败：{e}")


# ── 共享库文件删除 ────────────────────────────────────────────

@router.get("/api/library/files/{filename:path}/usage")
async def get_file_usage(filename: str):
    """查询哪些项目引用了此共享库文件"""
    projects_using = []
    for proj in pm.list_projects():
        if filename in pm.get_project_shared_files(proj["name"]):
            projects_using.append(proj["name"])
    return {"filename": filename, "projects": projects_using}


@router.delete("/api/library/files/_shared/{filename:path}")
def delete_shared_file(filename: str):
    """从共享库删除文件，并自动清除所有项目中的引用"""
    # Import owns this source name until both DuckDB rows and the project
    # reference are committed. Deleting in the middle could otherwise leave a
    # dangling reference or report success while the task later reappears.
    if not reserve_filename(filename, "delete"):
        raise HTTPException(status_code=409, detail="文件正在处理，暂时不能删除")
    try:
        db = pm.get_shared_db_path()
        if not os.path.exists(db):
            raise HTTPException(status_code=404, detail="共享库不存在")

        project_names = [proj["name"] for proj in pm.list_projects()]
        # Keep each affected project's lifecycle lock from snapshot through DB
        # commit/rollback. Otherwise a full-list PUT that starts after our
        # temporary reference removal can return success and then be changed by
        # the rollback of a failed delete.
        with pm.lock_projects(project_names):
            project_snapshots = {}
            for proj_name in project_names:
                try:
                    meta = pm.get_project_meta(proj_name)
                except ValueError:
                    # The project may have been deleted since list_projects().
                    continue
                files = meta.get("shared_files", [])
                if filename in files:
                    project_snapshots[proj_name] = meta["project_id"]
            projects_using = list(project_snapshots)

            # 先清理引用，再删除 DuckDB 数据。如果任一元数据写入失败，
            # 原文数据仍在，并尽力回滚已修改的项目引用。
            updated_projects = []
            try:
                for proj_name, project_id in project_snapshots.items():
                    pm.remove_project_shared_file(
                        proj_name,
                        filename,
                        expected_project_id=project_id,
                    )
                    updated_projects.append((proj_name, project_id))
                count = ingest.delete_source_file(db, filename)
            except Exception as e:
                # Roll back only the single reference removed by this operation.
                # Restoring an entire stale snapshot would erase unrelated references
                # that another request successfully wrote in the meantime.
                for proj_name, project_id in reversed(updated_projects):
                    try:
                        pm.add_project_shared_file(
                            proj_name,
                            filename,
                            expected_project_id=project_id,
                        )
                    except pm.ProjectIdentityMismatchError:
                        continue
                    except Exception as rollback_error:
                        logger.error(f"回滚项目 [{proj_name}] 的文件引用失败：{rollback_error}")
                raise HTTPException(status_code=500, detail=f"删除共享文件失败：{e}")
    finally:
        release_filename(filename, "delete")

    logger.info(f"已从共享库删除文件 [{filename}]，影响项目：{projects_using}")
    return {
        "deleted": count,
        "filename": filename,
        "cleaned_projects": projects_using,
    }

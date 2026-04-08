"""
/api/library + /api/upload — 文献库管理 + 文件上传

架构说明
────────
共享库（_shared）是唯一的文献存储库，所有文件的 DuckDB 记录都存在这里。
项目不复制数据，只在 project.json 的 shared_files 列表中保存「引用了哪些文件」。
搜索时，retriever 会查询共享库中被本项目引用的文件记录。
"""

import os
import shutil
import logging
from urllib.parse import unquote
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel

import core.project_manager as pm
import core.retriever as retriever
import core.ingest as ingest

router = APIRouter()
logger = logging.getLogger("backend.library")

# 临时上传目录（使用 cwd，因为 server.py 已将工作目录设为正确位置）
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads_tmp")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── 文件上传 ──────────────────────────────────────────────────

@router.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(None)):
    """接收上传文件，支持两种方式：
    1. multipart/form-data（浏览器标准上传）
    2. application/octet-stream + X-Filename header（Tauri WKWebView 兼容方式）
    """
    content_type = request.headers.get("content-type", "")

    if "multipart" in content_type and file is not None:
        # 标准 FormData 上传
        filename = file.filename or "upload"
        dest = _unique_dest(filename)
        try:
            with open(dest, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(f"文件上传失败（multipart）：{e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # 二进制流上传（Tauri 兼容）
        raw_name = request.headers.get("x-filename", "upload")
        filename = unquote(raw_name)
        dest = _unique_dest(filename)
        try:
            body = await request.body()
            with open(dest, "wb") as f:
                f.write(body)
        except Exception as e:
            logger.error(f"文件上传失败（binary）：{e}")
            raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"文件上传成功：{dest} ({os.path.getsize(dest):,} bytes)")
    return {"path": dest, "filename": os.path.basename(dest)}


def _unique_dest(filename: str) -> str:
    """生成不重复的目标路径。"""
    dest = os.path.join(UPLOAD_DIR, filename)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(UPLOAD_DIR, f"{base}_{counter}{ext}")
        counter += 1
    return dest


# ── 共享库统计 ────────────────────────────────────────────────

@router.get("/api/library/stats/_shared")
async def shared_stats():
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
async def project_stats(project_name: str):
    """项目的文件列表（= shared_files 引用）及记录数统计"""
    if project_name == "_shared":
        return await shared_stats()

    project_files = pm.get_project_shared_files(project_name)
    if not project_files:
        return {"files": [], "total": 0}

    shared_db = pm.get_shared_db_path()
    total = 0
    if os.path.exists(shared_db):
        try:
            total = ingest.get_records_count_for_files(shared_db, project_files)
        except Exception:
            pass
    return {"files": project_files, "total": total}


# ── 项目文件引用管理 ──────────────────────────────────────────

class AddFileRequest(BaseModel):
    filename: str


@router.post("/api/projects/{project_name}/add-file")
async def add_file_to_project(project_name: str, req: AddFileRequest):
    """将共享库文件加入项目引用列表（不复制数据）"""
    current = pm.get_project_shared_files(project_name)
    if req.filename not in current:
        current.append(req.filename)
        pm.set_project_shared_files(project_name, current)
    return {"project": project_name, "files": current}


@router.delete("/api/projects/{project_name}/file/{filename:path}")
async def remove_file_from_project(project_name: str, filename: str):
    """从项目引用列表中移除文件（不删除共享库数据）"""
    current = pm.get_project_shared_files(project_name)
    if filename in current:
        current = [f for f in current if f != filename]
        pm.set_project_shared_files(project_name, current)
    return {"project": project_name, "files": current}


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
async def delete_shared_file(filename: str):
    """从共享库删除文件，并自动清除所有项目中的引用"""
    db = pm.get_shared_db_path()
    if not os.path.exists(db):
        raise HTTPException(status_code=404, detail="共享库不存在")

    # 找出引用了此文件的项目，用于返回信息
    projects_using = []
    for proj in pm.list_projects():
        if filename in pm.get_project_shared_files(proj["name"]):
            projects_using.append(proj["name"])

    # 从共享库 DuckDB 删除
    try:
        count = ingest.delete_source_file(db, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 清除各项目的引用
    for proj_name in projects_using:
        current = pm.get_project_shared_files(proj_name)
        pm.set_project_shared_files(proj_name, [f for f in current if f != filename])

    logger.info(f"已从共享库删除文件 [{filename}]，影响项目：{projects_using}")
    return {
        "deleted": count,
        "filename": filename,
        "cleaned_projects": projects_using,
    }


# ── 兼容旧接口（保留，转发到新逻辑）────────────────────────────

@router.delete("/api/library/files/{project_name}/{filename:path}")
async def delete_library_file_compat(project_name: str, filename: str):
    """兼容旧调用：根据 project_name 决定是删除还是移除引用"""
    if project_name == "_shared":
        return await delete_shared_file(filename)
    else:
        # 旧逻辑：从项目引用中移除
        return await remove_file_from_project(project_name, filename)


@router.get("/api/library/files")
async def list_all_files():
    """列出共享库所有文件（供其他模块使用）"""
    shared_db = pm.get_shared_db_path()
    if not os.path.exists(shared_db):
        return []
    try:
        files = retriever.get_all_source_files(shared_db)
        return [{"filename": f, "project": "_shared", "project_label": "共享库"} for f in files]
    except Exception:
        return []

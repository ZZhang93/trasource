"""
/api/projects — 项目管理端点
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated, Optional
import core.project_manager as pm
import core.ingest as ingest
import core.retriever as retriever
from backend.routes.import_files import release_filenames, reserve_filenames

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field("", max_length=5000)


class SharedFilesRequest(BaseModel):
    files: list[Annotated[str, Field(min_length=1, max_length=1024)]] = Field(
        ..., max_length=500
    )


@router.get("/api/projects")
def list_projects():
    """列出所有项目（不含共享库），record_count 按项目引用文件从共享库实时统计"""
    try:
        projects = pm.list_projects()
        shared_db = pm.get_shared_db_path()
        if os.path.exists(shared_db):
            for p in projects:
                files = p.get("shared_files") or []
                try:
                    p["record_count"] = ingest.get_records_count_for_files(shared_db, files)
                except Exception:
                    p["record_count"] = 0
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects")
async def create_project(req: CreateProjectRequest):
    """创建新项目"""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    # 基本字符检验
    forbidden = set('/\\:*?"<>|')
    if any(c in forbidden for c in name):
        raise HTTPException(status_code=400, detail="项目名称包含非法字符")
    try:
        pm.validate_project_name(name, allow_shared=False)
        return pm.create_project(name, req.description or "")
    except ValueError as e:
        status = 409 if "已存在" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_name}")
async def get_project(project_name: str):
    """获取项目详情"""
    try:
        return pm.get_project_meta(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api/projects/{project_name}")
async def delete_project(project_name: str):
    """删除项目"""
    try:
        pm.delete_project(project_name)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_name}/shared-files")
async def get_shared_files(project_name: str):
    try:
        pm.get_project_meta(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"files": pm.get_project_shared_files(project_name)}


@router.put("/api/projects/{project_name}/shared-files")
async def set_shared_files(project_name: str, body: SharedFilesRequest):
    try:
        pm.validate_project_name(project_name, allow_shared=False)
        project_meta = pm.get_project_meta(project_name)
        current_files = project_meta.get("shared_files", [])
        reserved_files = list(dict.fromkeys([*current_files, *body.files]))
        operation = "reference:set"
        if not reserve_filenames(reserved_files, operation):
            raise HTTPException(status_code=409, detail="文件正在处理，请稍后重试")
        try:
            shared_db = pm.get_shared_db_path()
            available = set(retriever.get_all_source_files(shared_db)) if os.path.exists(shared_db) else set()
            unknown = [filename for filename in body.files if filename not in available]
            if unknown:
                raise HTTPException(status_code=400, detail=f"共享库中不存在文件：{unknown[0]}")
            pm.set_project_shared_files(
                project_name,
                body.files,
                expected_project_id=project_meta["project_id"],
            )
            return {"ok": True}
        finally:
            release_filenames(reserved_files, operation)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存项目文件引用失败：{e}")

"""
/api/projects — 项目管理端点
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import core.project_manager as pm

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""


@router.get("/api/projects")
async def list_projects():
    """列出所有项目（不含共享库）"""
    try:
        return pm.list_projects()
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
        return pm.create_project(name, req.description or "")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_name}/shared-files")
async def get_shared_files(project_name: str):
    return {"files": pm.get_project_shared_files(project_name)}


@router.put("/api/projects/{project_name}/shared-files")
async def set_shared_files(project_name: str, body: dict):
    files = body.get("files", [])
    pm.set_project_shared_files(project_name, files)
    return {"ok": True}

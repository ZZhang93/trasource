"""
/api/history — 搜索历史端点
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import core.history_manager as hm

router = APIRouter()
logger = logging.getLogger("backend.history")


class HistoryAddRequest(BaseModel):
    project_name: str
    query: str
    language: str = "zh"
    expansion: Optional[dict] = None
    total_found: int = 0
    ai_output: str = ""


@router.get("/api/history")
async def list_history(project_name: Optional[str] = None, limit: int = 50):
    return hm.list_history(project_name=project_name, limit=limit)


@router.get("/api/history/{history_id}")
async def get_history(history_id: int):
    entry = hm.get_history(history_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return entry


@router.post("/api/history")
async def add_history(req: HistoryAddRequest):
    try:
        entry = hm.add_history(
            project_name=req.project_name,
            query=req.query,
            language=req.language,
            expansion=req.expansion,
            total_found=req.total_found,
            ai_output=req.ai_output,
        )
        return entry
    except Exception as e:
        logger.error(f"add_history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class HistoryUpdateRequest(BaseModel):
    ai_output: Optional[str] = None
    total_found: Optional[int] = None
    expansion: Optional[dict] = None


@router.patch("/api/history/{history_id}")
async def update_history(history_id: int, req: HistoryUpdateRequest):
    """更新历史记录（如 AI 摘录完成后追加 ai_output）"""
    entry = hm.get_history(history_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    try:
        hm.update_history(history_id, req.model_dump(exclude_none=True))
        return {"updated": True}
    except Exception as e:
        logger.error(f"update_history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/history/{history_id}")
async def delete_history(history_id: int):
    ok = hm.delete_history(history_id)
    if not ok:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return {"deleted": True}


@router.delete("/api/history")
async def clear_history(project_name: Optional[str] = None):
    if project_name:
        deleted = hm.clear_project_history(project_name)
        return {"deleted": deleted}
    return {"deleted": 0, "message": "请指定 project_name"}

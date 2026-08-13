"""
/api/notes — 笔记 CRUD 端点
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

import core.notes_manager as nm

router = APIRouter()
logger = logging.getLogger("backend.notes")


class NoteCreateRequest(BaseModel):
    title: str = Field(..., max_length=1000)
    content_md: str = Field("", max_length=5_000_000)
    project_name: Optional[str] = Field(None, max_length=255)
    tags: str = Field("", max_length=5000)


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=1000)
    content_md: Optional[str] = Field(None, max_length=5_000_000)
    tags: Optional[str] = Field(None, max_length=5000)


@router.get("/api/notes")
async def list_notes(project_name: Optional[str] = None):
    return nm.list_notes(project_name=project_name)


@router.get("/api/notes/{note_id}")
async def get_note(note_id: int):
    note = nm.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@router.post("/api/notes")
async def create_note(req: NoteCreateRequest):
    try:
        note = nm.create_note(
            title=req.title,
            content_md=req.content_md,
            project_name=req.project_name,
            tags=req.tags,
        )
        return note
    except Exception as e:
        logger.error(f"create_note error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/notes/{note_id}")
async def update_note(note_id: int, req: NoteUpdateRequest):
    note = nm.update_note(
        note_id=note_id,
        title=req.title,
        content_md=req.content_md,
        tags=req.tags,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@router.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    ok = nm.delete_note(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return {"deleted": True}

"""
/api/chat — AI 对话端点（SSE 流式）
"""

import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List

import core.chat as chat

router = APIRouter()
logger = logging.getLogger("backend.chat")


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str = Field(..., min_length=1, max_length=50000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=50)
    context: str = ""
    language: str = "zh"
    project_name: str = ""
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None


@router.post("/api/chat/stream")
async def stream_chat(req: ChatRequest):
    """AI 对话 — SSE 流式响应"""

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async def generate():
        try:
            for chunk in chat.stream_chat(
                messages=messages,
                context_text=req.context,
                model_name=req.model_name,
                language=req.language,
                system_prompt=req.system_prompt,
            ):
                data = json.dumps({"text": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"stream_chat error: {e}", exc_info=True)
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

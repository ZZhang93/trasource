"""
/api/chat — AI 对话端点（SSE 流式）
"""

import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool
from typing import Optional, List

import core.chat as chat
from core.llm import LLMError
from backend.routes.search import get_cached_context

router = APIRouter()
logger = logging.getLogger("backend.chat")


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str = Field(..., min_length=1, max_length=50000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=50)
    search_id: str = ""            # 引用服务端缓存的检索 context
    language: str = "zh"
    project_name: str = ""
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None


@router.post("/api/chat/stream")
async def stream_chat(req: ChatRequest):
    """AI 对话 — SSE 流式响应；错误以独立 error 事件下发"""

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    context_text = get_cached_context(req.search_id) or "" if req.search_id else ""

    async def generate():
        try:
            stream = chat.stream_chat(
                messages=messages,
                context_text=context_text,
                model_name=req.model_name,
                language=req.language,
                system_prompt=req.system_prompt,
            )
            async for chunk in iterate_in_threadpool(stream):
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except LLMError as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"stream_chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

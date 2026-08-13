"""
/api/chat — AI 对话端点（SSE 流式）
"""

import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from starlette.concurrency import iterate_in_threadpool
from typing import Optional, List, Literal

import core.chat as chat
from core.llm import LLMError
from backend.routes.search import get_cached_context

router = APIRouter()
logger = logging.getLogger("backend.chat")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=50000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=50)
    search_id: str = Field("", max_length=64)
    language: Literal["zh", "en", "mixed"] = "zh"
    project_name: str = Field("", max_length=255)
    model_name: Optional[str] = Field(None, max_length=200)
    system_prompt: Optional[str] = Field(None, max_length=100_000)

    @model_validator(mode="after")
    def validate_turn_order(self):
        if self.messages[-1].role != "user":
            raise ValueError("对话的最后一条消息必须来自用户")
        return self


@router.post("/api/chat/stream")
async def stream_chat(req: ChatRequest):
    """AI 对话 — SSE 流式响应；错误以独立 error 事件下发"""

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    cached_context = (
        get_cached_context(req.search_id, req.project_name) if req.search_id else ""
    )

    async def generate():
        if req.search_id and cached_context is None:
            yield f"data: {json.dumps({'error': '检索结果已过期或不属于当前项目。', 'stale': True}, ensure_ascii=False)}\n\n"
            return
        try:
            stream = chat.stream_chat(
                messages=messages,
                context_text=cached_context or "",
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

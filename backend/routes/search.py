"""
/api/search — 搜索端点（含 SSE 流式摘录）

性能设计
────────
- expand / execute 是同步阻塞操作（LLM 调用、DuckDB 扫描），声明为 def 路由，
  由 FastAPI 自动放入线程池执行，不阻塞事件循环。
- 检索结果的 context（可达百万字符）缓存在服务端（LRU），响应只返回 search_id；
  摘录与对话通过 search_id 引用，避免大文本在前后端往返三次。
- 记录列表只返回内容预览（前 PREVIEW_CHARS 字符），详情弹窗按 id 取全文。
"""

import json
import logging
import threading
import uuid
from collections import OrderedDict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool
from typing import Optional, List

import core.project_manager as pm
import core.retriever as retriever
import core.query_expander as qe
import core.llm as llm
import core.settings_manager as sm

router = APIRouter()
logger = logging.getLogger("backend.search")

# ── context 服务端缓存（LRU，容量 8） ──────────────────────
_CONTEXT_CACHE_MAX = 8
_context_cache: "OrderedDict[str, str]" = OrderedDict()
_context_lock = threading.Lock()

PREVIEW_CHARS = 240


def _cache_context(context: str) -> str:
    search_id = uuid.uuid4().hex
    with _context_lock:
        _context_cache[search_id] = context
        while len(_context_cache) > _CONTEXT_CACHE_MAX:
            _context_cache.popitem(last=False)
    return search_id


def get_cached_context(search_id: str) -> Optional[str]:
    with _context_lock:
        ctx = _context_cache.get(search_id)
        if ctx is not None:
            _context_cache.move_to_end(search_id)
        return ctx


def _trim_record(rec: dict) -> dict:
    """记录列表只带预览内容，全文由 /api/search/record/{id} 提供。"""
    content = rec.get("content") or ""
    if len(content) > PREVIEW_CHARS:
        rec = {**rec, "content": content[:PREVIEW_CHARS], "content_truncated": True}
    else:
        rec = {**rec, "content_truncated": False}
    return rec


# ── 请求模型 ──────────────────────────────────────────────

class ExpandRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    language: str = "zh"
    project_name: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    language: str = "zh"
    project_name: str
    weighted_tokens: Optional[List[List]] = None   # [[term, weight], ...]
    date_from: Optional[str] = ""
    date_to: Optional[str] = ""
    file_filter_list: Optional[List[str]] = None   # 多选文件名列表
    top_k: Optional[int] = Field(50, ge=1, le=500)


class ExtractRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    search_id: str
    language: str = "zh"
    project_name: str
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None


# ── 端点 ─────────────────────────────────────────────────

@router.post("/api/search/expand")
def expand_query(req: ExpandRequest):
    """AI 查询扩展 — 返回关键词+权重 JSON（线程池执行，不阻塞事件循环）"""
    try:
        shared_db = pm.get_shared_db_path()
        sources = retriever.get_db_context_summary(shared_db)

        # 读取设置中的自定义拓词提示词
        settings = sm.load_settings("settings.json")
        expansion_override = settings.get("expansion_prompt_override", "")
        prompt_template = expansion_override.strip() if expansion_override else None
        if prompt_template:
            logger.info("[拓词] 使用设置中的自定义提示词")

        return qe.expand_query(
            user_query=req.query,
            language=req.language,
            sources=sources,
            prompt_template=prompt_template,
            model_name=None,
        )
    except Exception as e:
        logger.error(f"expand_query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/search/execute")
def execute_search(req: SearchRequest):
    """加权检索 — 返回记录预览列表 + search_id（context 留在服务端）"""
    try:
        shared_db = pm.get_shared_db_path()
        shared_files = pm.get_project_shared_files(req.project_name)

        tokens = None
        if req.weighted_tokens:
            tokens = [(str(t[0]), int(t[1])) for t in req.weighted_tokens]

        result = retriever.search(
            db_path=shared_db,
            query=req.query,
            date_from=req.date_from or "",
            date_to=req.date_to or "",
            file_filter=req.file_filter_list or None,
            top_k=req.top_k or 50,
            weighted_tokens=tokens,
            language=req.language,
            allowed_files=shared_files or None,
        )

        search_id = _cache_context(result["context"]) if result["context"] else ""
        return {
            "records":       [_trim_record(r) for r in result["records"]],
            "total_found":   result["total_found"],
            "search_id":     search_id,
            "context_chars": result["context_chars"],
            "truncated":     result["truncated"],
            "tokens":        result["tokens"],
        }
    except Exception as e:
        logger.error(f"execute_search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/search/record/{record_id}")
def get_record(record_id: int):
    """按 id 返回单条完整记录（详情弹窗取全文）"""
    shared_db = pm.get_shared_db_path()
    rec = retriever.get_record_by_id(shared_db, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return rec


@router.post("/api/search/extract")
async def stream_extract(req: ExtractRequest):
    """AI 史料摘录 — SSE 流式响应；错误以独立 error 事件下发"""
    context = get_cached_context(req.search_id)

    async def generate():
        if context is None:
            yield f"data: {json.dumps({'error': '检索结果已过期，请重新搜索。', 'stale': True}, ensure_ascii=False)}\n\n"
            return
        try:
            effective_prompt = req.system_prompt
            settings = sm.load_settings("settings.json")
            if not effective_prompt:
                override = settings.get("system_prompt_override", "")
                if override and override.strip():
                    effective_prompt = override.strip()
                    logger.info("[摘录] 使用设置中的自定义提示词")

            from core.llm_provider import get_extraction_model
            extraction_model = req.model_name or get_extraction_model(settings)

            # 先发送模型信息事件
            yield f"data: {json.dumps({'model': extraction_model or ''}, ensure_ascii=False)}\n\n"

            # 同步 LLM 流放到线程池迭代，避免阻塞事件循环
            stream = llm.stream_query(
                user_query=req.query,
                context=context,
                language=req.language,
                model_name=extraction_model,
                system_prompt=effective_prompt,
            )
            async for chunk in iterate_in_threadpool(stream):
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except llm.LLMError as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"stream_extract error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

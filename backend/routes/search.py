"""
/api/search — 搜索端点（含 SSE 流式摘录）
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List

import core.project_manager as pm
import core.retriever as retriever
import core.query_expander as qe
import core.llm as llm
import core.settings_manager as sm

router = APIRouter()
logger = logging.getLogger("backend.search")


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
    file_filter: Optional[str] = ""                # 旧接口兼容
    file_filter_list: Optional[List[str]] = None   # 多选文件名列表
    doc_type_filter: Optional[str] = ""
    top_k: Optional[int] = Field(50, ge=1, le=500)


class ExtractRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    context: str = Field(..., max_length=2_000_000)
    language: str = "zh"
    project_name: str
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None


# ── 端点 ─────────────────────────────────────────────────

@router.post("/api/search/expand")
async def expand_query(req: ExpandRequest):
    """AI 查询扩展 — 返回关键词+权重 JSON"""
    try:
        shared_db = pm.get_shared_db_path()
        sources = retriever.get_db_context_summary(shared_db)

        # 读取设置中的自定义拓词提示词和模型
        settings = sm.load_settings("settings.json")
        expansion_override = settings.get("expansion_prompt_override", "")
        prompt_template = expansion_override.strip() if expansion_override else None
        if prompt_template:
            logger.info("[拓词] 使用设置中的自定义提示词")

        result = qe.expand_query(
            user_query=req.query,
            language=req.language,
            sources=sources,
            prompt_template=prompt_template,
            model_name=None,
        )
        return result
    except Exception as e:
        logger.error(f"expand_query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/search/execute")
async def execute_search(req: SearchRequest):
    """BM25 搜索 — 返回记录列表 + context"""
    try:
        # 新架构：所有数据在共享库，项目只保存引用列表
        shared_db = pm.get_shared_db_path()
        shared_files = pm.get_project_shared_files(req.project_name)

        tokens = None
        if req.weighted_tokens:
            tokens = [(str(t[0]), int(t[1])) for t in req.weighted_tokens]

        # 多选文件筛选优先于旧的单文件筛选
        effective_filter = req.file_filter_list if req.file_filter_list else (req.file_filter or "")
        logger.info(f"[搜索] query={req.query!r}, file_filter_list={req.file_filter_list}, effective_filter={effective_filter}, shared_files_count={len(shared_files) if shared_files else 0}")

        result = retriever.search(
            db_path=shared_db,
            query=req.query,
            date_from=req.date_from or "",
            date_to=req.date_to or "",
            file_filter=effective_filter,
            doc_type_filter=req.doc_type_filter or "",
            top_k=req.top_k or 50,
            weighted_tokens=tokens,
            language=req.language,
            allowed_files=shared_files or None,
        )
        return result
    except Exception as e:
        logger.error(f"execute_search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/search/extract")
async def stream_extract(req: ExtractRequest):
    """AI 史料摘录 — SSE 流式响应"""

    async def generate():
        try:
            # 优先使用请求中的 system_prompt，其次使用设置中的自定义提示词
            effective_prompt = req.system_prompt
            settings = sm.load_settings("settings.json")
            if not effective_prompt:
                override = settings.get("system_prompt_override", "")
                if override and override.strip():
                    effective_prompt = override.strip()
                    logger.info("[摘录] 使用设置中的自定义提示词")

            # 读取摘录模型（由 provider 层自动选择，req.model_name 可覆盖）
            from core.llm_provider import get_extraction_model
            extraction_model = req.model_name or get_extraction_model(settings)

            # 先发送模型信息事件
            model_info = json.dumps({"model": extraction_model or ""}, ensure_ascii=False)
            yield f"data: {model_info}\n\n"

            for chunk in llm.stream_query(
                user_query=req.query,
                context=req.context,
                language=req.language,
                model_name=extraction_model,
                system_prompt=effective_prompt,
            ):
                data = json.dumps({"text": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"stream_extract error: {e}", exc_info=True)
            err_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

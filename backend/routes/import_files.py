"""
/api/import — 文件导入端点（含 SSE 进度流）
"""

import json
import os
import uuid
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import core.project_manager as pm
import core.ingest as ingest

router = APIRouter()
logger = logging.getLogger("backend.import")

# 存放进行中任务的内存字典  { task_id: { status, progress, message, error } }
_tasks: dict = {}


class ImportStartRequest(BaseModel):
    project_name: str
    file_path: str                  # 服务器可访问的绝对路径
    use_shared: bool = False        # True → 导入到共享库
    # 学术元数据（书籍/论文/访谈时填写）
    doc_type: str = "newspaper"     # newspaper / book / paper / interview
    title: Optional[str] = None
    author: Optional[str] = None
    pub_year: Optional[str] = None
    publisher: Optional[str] = None
    interviewee: Optional[str] = None
    interview_date: Optional[str] = None
    interview_location: Optional[str] = None


ALLOWED_EXTENSIONS = {".csv", ".pdf", ".docx", ".doc", ".txt", ".epub", ".mobi", ".azw3"}
MAX_FILE_SIZE_MB = 500


@router.post("/api/import/start")
async def start_import(req: ImportStartRequest):
    """
    启动导入任务，返回 task_id。
    调用方随后 GET /api/import/{task_id}/progress 获取 SSE 进度。
    """
    if not os.path.isfile(req.file_path):
        raise HTTPException(status_code=400, detail=f"文件不存在：{req.file_path}")

    # 文件扩展名校验
    ext = os.path.splitext(req.file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式：{ext}（支持：{', '.join(sorted(ALLOWED_EXTENSIONS))}）")

    # 文件大小校验
    size_mb = os.path.getsize(req.file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"文件过大：{size_mb:.0f}MB（最大 {MAX_FILE_SIZE_MB}MB）")

    # 所有文件统一导入到共享库（新架构：项目只保存引用）
    pm.ensure_shared_project()
    db_path = pm.get_shared_db_path()
    project_name = req.project_name  # 记录来源项目，用于导入后自动添加引用

    # 初始化数据库（如果不存在）
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        ingest.init_database(db_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库初始化失败：{e}")

    # 检查重复导入
    filename = os.path.basename(req.file_path)
    if ingest.check_file_already_imported(db_path, filename):
        raise HTTPException(status_code=409, detail=f"文件已导入：{filename}")

    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "等待开始…",
        "imported": 0,
        "error": None,
    }

    meta = {
        "doc_type":           req.doc_type,
        "title":              req.title or filename,
        "author":             req.author or "",
        "pub_year":           req.pub_year or "",
        "publisher":          req.publisher or "",
        "interviewee":        req.interviewee or "",
        "interview_date":     req.interview_date or "",
        "interview_location": req.interview_location or "",
    }

    # 后台异步执行导入
    asyncio.create_task(
        _run_import(task_id, db_path, req.file_path, filename, meta, project_name)
    )

    return {"task_id": task_id}


async def _run_import(task_id: str, db_path: str, filepath: str,
                      filename: str, meta: dict, project_name: str):
    """异步包装同步导入函数，通过回调更新进度。"""
    task = _tasks[task_id]
    task["status"] = "running"
    task["message"] = f"正在导入 {filename}…"

    def progress_cb(pct: float, count: int):
        task["progress"] = round(pct * 100, 1)
        task["imported"] = count
        task["message"] = f"已处理 {count:,} 条…"

    ext = os.path.splitext(filename)[1].lower()
    loop = asyncio.get_event_loop()

    try:
        if ext == ".csv":
            result = await loop.run_in_executor(
                None, lambda: ingest.ingest_csv(db_path, filepath, progress_cb)
            )
        elif ext == ".pdf":
            result = await loop.run_in_executor(
                None, lambda: ingest.ingest_pdf(db_path, filepath, meta, progress_cb)
            )
        elif ext in (".docx", ".doc"):
            result = await loop.run_in_executor(
                None, lambda: ingest.ingest_docx(db_path, filepath, meta, progress_cb)
            )
        elif ext == ".txt":
            result = await loop.run_in_executor(
                None, lambda: ingest.ingest_txt(db_path, filepath, meta, progress_cb)
            )
        elif ext == ".epub":
            result = await loop.run_in_executor(
                None, lambda: ingest.ingest_epub(db_path, filepath, meta, progress_cb)
            )
        elif ext in (".mobi", ".azw3"):
            result = await loop.run_in_executor(
                None, lambda: ingest.ingest_mobi(db_path, filepath, meta, progress_cb)
            )
        else:
            raise ValueError(f"不支持的文件格式：{ext}")

        total = result.get("total_imported", 0)
        task.update({
            "status": "done",
            "progress": 100.0,
            "imported": total,
            "message": f"导入完成：{total:,} 条记录",
        })

        # 自动将文件引用加入来源项目（新架构：项目只保存引用）
        if project_name and project_name != pm.SHARED_PROJECT:
            try:
                current_refs = pm.get_project_shared_files(project_name)
                if filename not in current_refs:
                    current_refs.append(filename)
                    pm.set_project_shared_files(project_name, current_refs)
                    logger.info(f"已自动将 [{filename}] 添加到项目 [{project_name}] 的引用列表")
            except Exception as e:
                logger.warning(f"自动添加项目引用失败: {e}")

        logger.info(f"导入完成：{filename}，{total} 条，项目={project_name}")

    except Exception as e:
        logger.error(f"导入失败：{filename}，{e}", exc_info=True)
        task.update({
            "status": "error",
            "error": str(e),
            "message": f"导入失败：{e}",
        })


@router.get("/api/import/{task_id}/progress")
async def import_progress(task_id: str):
    """SSE 进度流：每 500ms 推送一次进度，完成/失败后关闭。"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def generate():
        while True:
            task = _tasks.get(task_id, {})
            data = json.dumps(task, ensure_ascii=False)
            yield f"data: {data}\n\n"

            if task.get("status") in ("done", "error"):
                # 清理任务（稍后）
                await asyncio.sleep(5)
                _tasks.pop(task_id, None)
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/import/{task_id}/status")
async def import_status(task_id: str):
    """一次性获取任务状态（非流式）。"""
    task = _tasks.get(task_id)
    if task is None:
        return {"status": "not_found"}
    return task

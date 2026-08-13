"""
/api/import — 文件导入端点（含 SSE 进度流）
"""

import json
import os
import time
import uuid
import logging
import asyncio
import threading
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import core.project_manager as pm
import core.ingest as ingest

router = APIRouter()
logger = logging.getLogger("backend.import")
UPLOAD_DIR = os.path.realpath(os.path.join(os.getcwd(), "uploads_tmp"))

# 存放进行中任务的内存字典  { task_id: { status, progress, message, error, finished_at } }
_tasks: dict = {}
_active_filenames: dict[str, str] = {}
_active_filenames_lock = threading.Lock()


def is_filename_importing(filename: str) -> bool:
    with _active_filenames_lock:
        return _active_filenames.get(filename) == "import"


def reserve_filenames(filenames, operation: str) -> bool:
    """Atomically reserve every source name for one operation.

    Batch reservation is needed by the project ``shared-files`` PUT endpoint:
    reserving names one-by-one would expose a partial acquisition window and
    would require error-prone rollback when one of the later names is busy.
    """
    unique_filenames = list(dict.fromkeys(filenames))
    with _active_filenames_lock:
        if any(filename in _active_filenames for filename in unique_filenames):
            return False
        for filename in unique_filenames:
            _active_filenames[filename] = operation
        return True


def release_filenames(filenames, operation: str):
    with _active_filenames_lock:
        for filename in dict.fromkeys(filenames):
            if _active_filenames.get(filename) == operation:
                _active_filenames.pop(filename, None)


def reserve_filename(filename: str, operation: str) -> bool:
    """Atomically reserve a source name across import/delete workflows."""
    return reserve_filenames([filename], operation)


def release_filename(filename: str, operation: str):
    release_filenames([filename], operation)


def _purge_finished_tasks(max_age_seconds: float = 600):
    """清理已完成/失败超过 max_age 的任务，防止无人订阅进度流时内存泄漏。"""
    now = time.time()
    stale = [
        tid for tid, t in _tasks.items()
        if t.get("status") in ("done", "error")
        and now - t.get("finished_at", now) > max_age_seconds
    ]
    for tid in stale:
        _tasks.pop(tid, None)


class ImportStartRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=4096)
    # 学术元数据（书籍/论文/访谈时填写）
    doc_type: Literal["newspaper", "book", "paper", "interview"] = "newspaper"
    title: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = Field(None, max_length=1000)
    pub_year: Optional[str] = Field(None, max_length=100)
    publisher: Optional[str] = Field(None, max_length=1000)
    interviewee: Optional[str] = Field(None, max_length=1000)
    interview_date: Optional[str] = Field(None, max_length=100)
    interview_location: Optional[str] = Field(None, max_length=1000)


ALLOWED_EXTENSIONS = {".csv", ".pdf", ".docx", ".txt", ".epub", ".mobi", ".azw3"}
MAX_FILE_SIZE_MB = 500


def _cleanup_staged_upload(filepath: str):
    real_path = os.path.realpath(filepath)
    try:
        is_staged_upload = (
            os.path.commonpath([UPLOAD_DIR, real_path]) == UPLOAD_DIR
            and real_path != UPLOAD_DIR
        )
    except ValueError:
        is_staged_upload = False
    if is_staged_upload:
        try:
            os.unlink(real_path)
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            logger.warning(f"清理上传临时文件失败：{cleanup_error}")


@router.post("/api/import/start")
async def start_import(req: ImportStartRequest):
    """
    启动导入任务，返回 task_id。
    调用方随后 GET /api/import/{task_id}/progress 获取 SSE 进度。
    """
    try:
        pm.validate_project_name(req.project_name, allow_shared=False)
        project_meta = pm.get_project_meta(req.project_name)
    except ValueError as e:
        _cleanup_staged_upload(req.file_path)
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isfile(req.file_path):
        raise HTTPException(status_code=400, detail=f"文件不存在：{req.file_path}")

    # 文件扩展名校验
    ext = os.path.splitext(req.file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        _cleanup_staged_upload(req.file_path)
        raise HTTPException(status_code=400, detail=f"不支持的文件格式：{ext}（支持：{', '.join(sorted(ALLOWED_EXTENSIONS))}）")

    # 文件大小校验
    size_mb = os.path.getsize(req.file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        _cleanup_staged_upload(req.file_path)
        raise HTTPException(status_code=400, detail=f"文件过大：{size_mb:.0f}MB（最大 {MAX_FILE_SIZE_MB}MB）")

    # 所有文件统一导入到共享库（新架构：项目只保存引用）
    pm.ensure_shared_project()
    db_path = pm.get_shared_db_path()
    project_name = req.project_name  # 记录来源项目，用于导入后自动添加引用
    project_id = project_meta["project_id"]

    # 初始化数据库（如果不存在）
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        ingest.init_database(db_path)
    except Exception as e:
        _cleanup_staged_upload(req.file_path)
        raise HTTPException(status_code=500, detail=f"数据库初始化失败：{e}")

    # 原子占用来源名之后再做重复检查；这样 delete/import 以及两个并发
    # import 不会在 check→write 窗口里互相穿透。
    filename = os.path.basename(req.file_path)
    if not reserve_filename(filename, "import"):
        _cleanup_staged_upload(req.file_path)
        raise HTTPException(status_code=409, detail=f"文件正在处理：{filename}")

    try:
        if ingest.check_file_already_imported(db_path, filename):
            _cleanup_staged_upload(req.file_path)
            raise HTTPException(status_code=409, detail=f"文件已导入：{filename}")
    except Exception:
        release_filename(filename, "import")
        raise

    try:
        _purge_finished_tasks()
        task_id = str(uuid.uuid4())
        _tasks[task_id] = {
            "status": "pending",
            "progress": 0.0,
            "message": "等待开始…",
            "imported": 0,
            "error": None,
        }
    except Exception:
        release_filename(filename, "import")
        raise

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
        _run_import(
            task_id, db_path, req.file_path, filename, meta, project_name, project_id
        )
    )

    return {"task_id": task_id}


async def _run_import(task_id: str, db_path: str, filepath: str,
                      filename: str, meta: dict, project_name: str,
                      project_id: str):
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
        elif ext == ".docx":
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
        if total <= 0:
            raise ValueError("文件中没有可导入的有效正文记录，请检查文件内容和列名。")

        # 自动将文件引用加入来源项目（新架构：项目只保存引用）
        if project_name and project_name != pm.SHARED_PROJECT:
            try:
                pm.add_project_shared_file(
                    project_name,
                    filename,
                    expected_project_id=project_id,
                )
            except Exception:
                # Do not leave an unreachable document in the shared DB if
                # persisting its project reference fails.
                ingest.delete_source_file(db_path, filename)
                raise
            logger.info(f"已自动将 [{filename}] 添加到项目 [{project_name}] 的引用列表")

        task.update({
            "status": "done",
            "progress": 100.0,
            "imported": total,
            "message": f"导入完成：{total:,} 条记录",
            "finished_at": time.time(),
        })

        logger.info(f"导入完成：{filename}，{total} 条，项目={project_name}")

    except Exception as e:
        logger.error(f"导入失败：{filename}，{e}", exc_info=True)
        task.update({
            "status": "error",
            "error": str(e),
            "message": f"导入失败：{e}",
            "finished_at": time.time(),
        })
    finally:
        release_filename(filename, "import")
        # Browser uploads are staging files.  Delete only files canonically
        # contained by uploads_tmp; native Tauri selections point at user files
        # elsewhere and must never be removed.
        _cleanup_staged_upload(filepath)


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

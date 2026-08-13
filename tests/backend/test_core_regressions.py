import asyncio
import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

import core.ingest as ingest
import core.project_manager as pm
import core.retriever as retriever
from backend.routes import import_files
from backend.routes import library
from backend.routes.projects import SharedFilesRequest, set_shared_files
from backend.routes.search import (
    SearchRequest,
    _cache_context,
    _context_cache,
    get_cached_context,
    get_cached_context_entry,
    get_record,
)
from backend.routes.settings import SettingsUpdateRequest, _mask_key, get_settings, update_settings
from core.platform_paths import get_app_data_dir, migrate_legacy_app_data
from core.settings_manager import load_settings, save_settings


DOCUMENTS_SCHEMA = """
CREATE TABLE documents (
    id INTEGER, source_file TEXT, file_type TEXT, doc_type TEXT,
    year TEXT, date TEXT, page TEXT, title TEXT,
    author TEXT, pub_year TEXT, publisher TEXT,
    chapter TEXT, section TEXT, page_num TEXT,
    interviewee TEXT, interview_date TEXT, interview_location TEXT,
    content TEXT
)
"""


def make_search_db(path: str) -> None:
    conn = duckdb.connect(path)
    conn.execute(DOCUMENTS_SCHEMA)
    rows = [
        (1, "a.txt", "txt", "book", "", "", "", "", "", "", "", "", "", "", "", "", "", "needle"),
        (2, "b.txt", "txt", "book", "", "", "", "", "", "", "", "", "", "", "", "", "", "other"),
        (3, "c.txt", "txt", "book", "", "", "", "", "", "", "", "", "", "", "", "", "", "needle other"),
    ]
    conn.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.close()


class ProjectPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = os.path.join(self.temp.name, "projects")
        os.mkdir(self.projects)
        self.old_projects_dir = pm.PROJECTS_DIR
        pm.PROJECTS_DIR = self.projects
        self.addCleanup(setattr, pm, "PROJECTS_DIR", self.old_projects_dir)

    def test_dot_segments_and_path_components_are_rejected(self):
        for name in (".", "..", "...", "../escape", "a/b", "a\\b", "/absolute", "CON"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pm.get_project_dir(name)

    def test_symlink_escape_is_rejected_by_canonical_containment(self):
        outside = os.path.join(self.temp.name, "outside")
        os.mkdir(outside)
        try:
            os.symlink(
                outside,
                os.path.join(self.projects, "linked"),
                target_is_directory=True,
            )
        except OSError as error:
            if getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows runner does not grant symlink privileges")
            raise
        with self.assertRaises(ValueError):
            pm.get_project_dir("linked")

    def test_shared_project_cannot_be_deleted(self):
        shared = pm.create_project(pm.SHARED_PROJECT)
        self.assertEqual(shared["name"], pm.SHARED_PROJECT)
        with self.assertRaises(ValueError):
            pm.delete_project(pm.SHARED_PROJECT)
        self.assertTrue(os.path.isdir(pm.get_project_dir(pm.SHARED_PROJECT)))

    def test_shared_file_write_error_propagates(self):
        pm.create_project("p")
        with patch("core.project_manager._write_meta_atomic", side_effect=PermissionError("read-only")):
            with self.assertRaises(PermissionError):
                pm.set_project_shared_files("p", ["a.txt"])

    def test_recreated_project_rejects_stale_lifecycle_write(self):
        original = pm.create_project("p")
        pm.delete_project("p")
        replacement = pm.create_project("p")

        self.assertNotEqual(original["project_id"], replacement["project_id"])
        with self.assertRaises(pm.ProjectIdentityMismatchError):
            pm.add_project_shared_file(
                "p",
                "old-import.txt",
                expected_project_id=original["project_id"],
            )
        self.assertEqual(pm.get_project_shared_files("p"), [])


class RetrieverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = os.path.join(self.temp.name, "search.duckdb")
        make_search_db(self.db)

    def test_multiple_tokens_use_sql_placeholder_order(self):
        result = retriever.search(
            self.db,
            "query",
            weighted_tokens=[("needle", 10), ("other", 1)],
            allowed_files=None,
        )
        self.assertEqual(result["total_found"], 3)
        self.assertEqual(
            [(row["id"], row["relevance_score"]) for row in result["records"]],
            [(3, 11), (1, 10), (2, 1)],
        )

    def test_empty_allowlist_matches_nothing_but_none_means_all(self):
        denied = retriever.search(
            self.db, "query", weighted_tokens=[("needle", 1)], allowed_files=[]
        )
        unrestricted = retriever.search(
            self.db, "query", weighted_tokens=[("needle", 1)], allowed_files=None
        )
        self.assertEqual(denied["total_found"], 0)
        self.assertEqual(unrestricted["total_found"], 2)

    def test_context_ids_and_source_lines_reflect_actual_truncation(self):
        with patch.object(retriever, "MAX_CONTEXT_CHARS", 125):
            result = retriever.search(
                self.db,
                "query",
                weighted_tokens=[("needle", 1), ("other", 1)],
                allowed_files=None,
            )
        self.assertEqual(len(result["context_record_ids"]), 1)
        record_id = result["context_record_ids"][0]
        self.assertIn(f"【文献信息】【记录ID：{record_id}】", result["context"])
        self.assertTrue(result["truncated"])

    def test_terms_are_case_insensitive_literal_substrings(self):
        conn = duckdb.connect(self.db)
        conn.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [4, "d.txt", "txt", "book", "", "", "", "", "", "", "", "", "", "", "", "", "", "Roosevelt reached 100%"],
        )
        conn.close()
        lower_case = retriever.search(
            self.db, "query", weighted_tokens=[("roosevelt", 1)], allowed_files=None
        )
        literal_percent = retriever.search(
            self.db, "query", weighted_tokens=[("%", 1)], allowed_files=None
        )
        self.assertEqual([row["id"] for row in lower_case["records"]], [4])
        self.assertEqual([row["id"] for row in literal_percent["records"]], [4])

    def test_search_can_run_while_same_process_has_write_connection(self):
        writer = duckdb.connect(self.db)
        try:
            result = retriever.search(
                self.db, "query", weighted_tokens=[("needle", 1)], allowed_files=None
            )
        finally:
            writer.close()
        self.assertEqual(result["total_found"], 2)


class ContextCacheTests(unittest.TestCase):
    def setUp(self):
        _context_cache.clear()
        self.addCleanup(_context_cache.clear)

    def test_cache_is_project_bound_and_retains_record_ids(self):
        search_id = _cache_context("context", [4, 8], "project-a")
        self.assertEqual(get_cached_context(search_id, "project-a"), "context")
        self.assertIsNone(get_cached_context(search_id, "project-b"))
        self.assertEqual(
            get_cached_context_entry(search_id, "project-a")["record_ids"], [4, 8]
        )

    def test_full_record_requires_project_or_search_scope(self):
        with self.assertRaises(HTTPException) as raised:
            get_record(1)
        self.assertEqual(raised.exception.status_code, 400)


class SettingsPersistenceTests(unittest.TestCase):
    def test_short_api_keys_are_never_returned_verbatim(self):
        self.assertEqual(_mask_key(""), "")
        self.assertNotIn("abc", _mask_key("abc"))

    def test_save_is_private_and_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            save_settings(path, {"api_key": "secret"})
            self.assertEqual(json.loads(Path(path).read_text()), {"api_key": "secret"})
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_save_error_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_parent = os.path.join(directory, "missing", "settings.json")
            with self.assertRaises(OSError):
                save_settings(missing_parent, {"x": 1})

    def test_strict_load_does_not_hide_corrupt_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            Path(path).write_text("{not-json", encoding="utf-8")
            self.assertEqual(load_settings(path), {})
            with self.assertRaisesRegex(ValueError, "设置文件无法读取"):
                load_settings(path, strict=True)

            Path(path).write_text("[]", encoding="utf-8")
            self.assertEqual(load_settings(path), {})
            with self.assertRaisesRegex(ValueError, "JSON 对象"):
                load_settings(path, strict=True)


class ImportTests(unittest.TestCase):
    def test_doc_binary_format_is_not_advertised(self):
        self.assertNotIn(".doc", import_files.ALLOWED_EXTENSIONS)
        self.assertIn(".docx", import_files.ALLOWED_EXTENSIONS)

    def test_csv_missing_content_column_fails_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "bad.csv")
            Path(path).write_text("年份,日期,版次,标题,正文\n1960,1960-01-01,1,题目,这是一段足够长的正文内容\n", encoding="utf-8")
            db = os.path.join(directory, "db.duckdb")
            ingest.init_database(db)
            with self.assertRaisesRegex(ValueError, "CSV 缺少"):
                ingest.ingest_csv(db, path)
            conn = duckdb.connect(db, read_only=True)
            count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            conn.close()
            self.assertEqual(count, 0)

    def test_mobi_passes_original_filename_to_epub_ingester(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "original.mobi")
            Path(source).write_bytes(b"mobi")

            def fake_convert(args, **_kwargs):
                Path(args[2]).write_bytes(b"epub")

            with (
                patch("shutil.which", return_value="/usr/bin/ebook-convert"),
                patch("subprocess.run", side_effect=fake_convert),
                patch("core.ingest.ingest_epub", return_value={"total_imported": 1}) as ingest_epub,
            ):
                result = ingest.ingest_mobi("db", source, {"doc_type": "book"})

            self.assertEqual(result["total_imported"], 1)
            self.assertEqual(ingest_epub.call_args.kwargs["source_filename"], "original.mobi")
            self.assertEqual(ingest_epub.call_args.kwargs["source_file_type"], "mobi")

    def test_oversized_upload_is_rejected_and_partial_file_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            app = FastAPI()
            app.include_router(library.router)
            with (
                patch.object(library, "UPLOAD_DIR", directory),
                patch.object(library, "MAX_UPLOAD_BYTES", 3),
                TestClient(app) as client,
            ):
                response = client.post(
                    "/api/upload",
                    content=b"four",
                    headers={"content-type": "application/octet-stream", "x-filename": "large.txt"},
                )
            self.assertEqual(response.status_code, 413)
            self.assertEqual(os.listdir(directory), [])

    def test_concurrent_upload_reservations_never_share_a_path(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(library, "UPLOAD_DIR", directory):
            first_path, first_fd = library._reserve_unique_dest("same.txt")
            second_path, second_fd = library._reserve_unique_dest("same.txt")
            os.close(first_fd)
            os.close(second_fd)
            self.assertNotEqual(first_path, second_path)
            self.assertTrue(os.path.exists(first_path))
            self.assertTrue(os.path.exists(second_path))

    def test_shared_delete_is_blocked_while_same_file_imports(self):
        import_files._active_filenames["busy.txt"] = "import"
        try:
            with self.assertRaises(HTTPException) as raised:
                library.delete_shared_file("busy.txt")
        finally:
            import_files._active_filenames.pop("busy.txt", None)
        self.assertEqual(raised.exception.status_code, 409)

    def test_delete_reservation_blocks_new_import_reservation(self):
        self.assertTrue(import_files.reserve_filename("race.txt", "delete"))
        try:
            self.assertFalse(import_files.reserve_filename("race.txt", "import"))
        finally:
            import_files.release_filename("race.txt", "delete")

    def test_delete_failure_rolls_back_only_its_own_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            projects = os.path.join(directory, "projects")
            os.mkdir(projects)
            with patch.object(pm, "PROJECTS_DIR", projects):
                pm.create_project(pm.SHARED_PROJECT)
                pm.create_project("p")
                ingest.init_database(pm.get_shared_db_path())
                pm.set_project_shared_files("p", ["x.txt"])

                real_remove = pm.remove_project_shared_file

                def remove_then_concurrently_add(*args, **kwargs):
                    result = real_remove(*args, **kwargs)
                    pm.add_project_shared_file("p", "y.txt")
                    return result

                with (
                    patch.object(pm, "remove_project_shared_file", side_effect=remove_then_concurrently_add),
                    patch.object(ingest, "delete_source_file", side_effect=OSError("write failed")),
                    self.assertRaises(HTTPException),
                ):
                    library.delete_shared_file("x.txt")

                self.assertEqual(set(pm.get_project_shared_files("p")), {"x.txt", "y.txt"})

    def test_project_write_waits_for_delete_rollback_to_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            projects = os.path.join(directory, "projects")
            os.mkdir(projects)
            with patch.object(pm, "PROJECTS_DIR", projects):
                pm.create_project(pm.SHARED_PROJECT)
                project = pm.create_project("p")
                ingest.init_database(pm.get_shared_db_path())
                pm.set_project_shared_files("p", ["x.txt"])

                delete_entered = threading.Event()
                release_delete = threading.Event()
                set_finished = threading.Event()
                unexpected = []

                def failing_delete(*_args):
                    delete_entered.set()
                    if not release_delete.wait(2):
                        raise TimeoutError("test did not release delete")
                    raise OSError("write failed")

                def run_delete():
                    try:
                        library.delete_shared_file("x.txt")
                    except HTTPException as error:
                        if error.status_code != 500:
                            unexpected.append(error)
                    except Exception as error:  # pragma: no cover - diagnostic
                        unexpected.append(error)

                def run_set():
                    try:
                        pm.set_project_shared_files(
                            "p",
                            ["y.txt"],
                            expected_project_id=project["project_id"],
                        )
                    except Exception as error:  # pragma: no cover - diagnostic
                        unexpected.append(error)
                    finally:
                        set_finished.set()

                with patch.object(ingest, "delete_source_file", side_effect=failing_delete):
                    delete_thread = threading.Thread(target=run_delete)
                    delete_thread.start()
                    self.assertTrue(delete_entered.wait(1))

                    set_thread = threading.Thread(target=run_set)
                    set_thread.start()
                    self.assertFalse(set_finished.wait(0.05))

                    release_delete.set()
                    delete_thread.join(2)
                    set_thread.join(2)

                self.assertFalse(delete_thread.is_alive())
                self.assertFalse(set_thread.is_alive())
                self.assertEqual(unexpected, [])
                self.assertEqual(pm.get_project_shared_files("p"), ["y.txt"])


class RequestValidationTests(unittest.TestCase):
    def test_search_language_and_weighted_tokens_are_validated(self):
        valid = SearchRequest(
            query="q", project_name="p", weighted_tokens=[[" term ", 5], ["term", 5]]
        )
        self.assertEqual(valid.weighted_tokens, [("term", 5)])
        invalid_payloads = [
            {"language": "xx"},
            {"weighted_tokens": [["", 5]]},
            {"weighted_tokens": [["term", 0]]},
            {"weighted_tokens": [["term", 11]]},
            {"weighted_tokens": [["term"]]},
        ]
        for extra in invalid_payloads:
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                SearchRequest(query="q", project_name="p", **extra)

    def test_settings_provider_top_k_and_url_are_bounded(self):
        SettingsUpdateRequest(provider="openai", top_k=10, local_base_url="http://localhost")
        for payload in (
            {"provider": "unknown"},
            {"top_k": 9},
            {"top_k": 501},
            {"local_base_url": "x" * 2049},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                SettingsUpdateRequest(**payload)


class ApiWriteFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_settings_get_reports_corrupt_file_instead_of_returning_defaults(self):
        with patch(
            "backend.routes.settings.sm.load_settings",
            side_effect=ValueError("corrupt"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_settings()
        self.assertEqual(raised.exception.status_code, 500)

    async def test_settings_endpoint_reports_persistence_failure(self):
        with patch(
            "backend.routes.settings.sm.save_settings",
            side_effect=PermissionError("read-only"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_settings(SettingsUpdateRequest(provider="openai"))
        self.assertEqual(raised.exception.status_code, 500)

    async def test_project_refs_endpoint_reports_persistence_failure(self):
        with (
            patch(
                "backend.routes.projects.pm.get_project_meta",
                return_value={"project_id": "p1", "shared_files": []},
            ),
            patch(
                "backend.routes.projects.pm.set_project_shared_files",
                side_effect=PermissionError("read-only"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await set_shared_files("p", SharedFilesRequest(files=[]))
        self.assertEqual(raised.exception.status_code, 500)

    async def test_reference_writes_are_blocked_during_source_delete(self):
        self.assertTrue(import_files.reserve_filename("x.txt", "delete"))
        try:
            with (
                patch("backend.routes.library.pm.get_project_meta", return_value={"project_id": "p1", "shared_files": []}),
                self.assertRaises(HTTPException) as add_error,
            ):
                await library.add_file_to_project("p", library.AddFileRequest(filename="x.txt"))
            self.assertEqual(add_error.exception.status_code, 409)

            with (
                patch("backend.routes.projects.pm.get_project_meta", return_value={"project_id": "p1", "shared_files": []}),
                self.assertRaises(HTTPException) as set_error,
            ):
                await set_shared_files("p", SharedFilesRequest(files=["x.txt"]))
            self.assertEqual(set_error.exception.status_code, 409)
        finally:
            import_files.release_filename("x.txt", "delete")

    async def test_zero_record_import_is_an_error(self):
        task_id = "zero-record-test"
        import_files._tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "",
            "imported": 0,
            "error": None,
        }
        self.addAsyncCleanup(self._remove_task, task_id)
        with patch("backend.routes.import_files.ingest.ingest_txt", return_value={"total_imported": 0}):
            await import_files._run_import(
                task_id,
                "unused.duckdb",
                "/tmp/empty.txt",
                "empty.txt",
                {"doc_type": "book"},
                "project",
                "project-id",
            )
        self.assertEqual(import_files._tasks[task_id]["status"], "error")
        self.assertIn("没有可导入", import_files._tasks[task_id]["error"])

    async def _remove_task(self, task_id):
        import_files._tasks.pop(task_id, None)


class PlatformPathTests(unittest.TestCase):
    def test_platform_specific_data_directories(self):
        self.assertEqual(
            get_app_data_dir(platform="darwin", env={}, home="/Users/a"),
            os.path.abspath(
                os.path.join("/Users/a", "Library", "Application Support", "trasource")
            ),
        )
        self.assertEqual(
            get_app_data_dir(platform="win32", env={"LOCALAPPDATA": "C:/Data"}, home="C:/Users/a"),
            os.path.abspath(os.path.join("C:/Data", "trasource")),
        )
        self.assertEqual(
            get_app_data_dir(platform="linux", env={"XDG_DATA_HOME": "/data"}, home="/home/a"),
            os.path.abspath(os.path.join("/data", "trasource")),
        )

    def test_legacy_cross_platform_data_is_migrated_without_overwrite(self):
        with tempfile.TemporaryDirectory() as home:
            legacy = Path(home, "Library", "Application Support", "trasource")
            legacy.mkdir(parents=True)
            (legacy / "settings.json").write_text("{}", encoding="utf-8")
            target = Path(home, ".local", "share", "trasource")
            self.assertTrue(migrate_legacy_app_data(str(target), home=home))
            self.assertTrue((target / "settings.json").exists())
            self.assertFalse(legacy.exists())
            self.assertFalse(migrate_legacy_app_data(str(target), home=home))

    def test_failed_cross_volume_copy_never_leaves_a_partial_final_directory(self):
        with tempfile.TemporaryDirectory() as home:
            legacy = Path(home, "Library", "Application Support", "trasource")
            legacy.mkdir(parents=True)
            (legacy / "complete.db").write_text("complete", encoding="utf-8")
            target = Path(home, ".local", "share", "trasource")

            def fail_after_partial_copy(_source, staging, *, dirs_exist_ok):
                Path(staging, "partial.db").write_text("partial", encoding="utf-8")
                raise OSError("disk full")

            with (
                patch("core.platform_paths.os.replace", side_effect=OSError("cross-device")),
                patch("core.platform_paths.shutil.copytree", side_effect=fail_after_partial_copy),
                self.assertRaisesRegex(OSError, "disk full"),
            ):
                migrate_legacy_app_data(str(target), home=home)

            self.assertFalse(target.exists())
            self.assertEqual((legacy / "complete.db").read_text(encoding="utf-8"), "complete")
            leftovers = list(target.parent.glob(".trasource-migrating-*"))
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()

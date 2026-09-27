from __future__ import annotations

import io
import json
import mimetypes
import os
import re
import secrets
import threading
import urllib.parse
import webbrowser
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .. import ai
from ..ai import AiError, AiSession
from ..curriculum import load_curriculum, parse_test_command
from ..diagnostic import QUESTIONS, collect_answers, persist_diagnostic, run_diagnostics, validate_answers_data
from ..envcheck import run_action
from ..errors import BlockedError, DataError, LearnctlError, UsageError
from ..practice import find_section, load_draft, run_validation, save_draft
from ..progress import load_progress
from ..test_runner import run_exercise_capture
from ..workflow import (
    complete_section,
    assert_section_unlocked,
    module_status,
    section_completed,
    task_payload,
    today_payload,
    update_lesson_position,
    update_module,
    update_option,
    update_task,
)
from .storage import atomic_write_text, normalize_relative_path, read_utf8, resolve_under_root


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

MAX_REQUEST_BYTES = 256 * 1024

# 每个服务进程内存中最多保存的变式题数量；超出按最早生成顺序淘汰，避免无限增长。
MAX_STORED_VARIATIONS = 50


def _new_variation_id() -> str:
    return secrets.token_urlsafe(16)


def _drain_body(stream: Any, length: int) -> None:
    """分块丢弃超限请求体，不驻留内存，让客户端完成发送后收到明确拒绝。"""
    remaining = length
    while remaining > 0:
        chunk = stream.read(min(65_536, remaining))
        if not chunk:
            return
        remaining -= len(chunk)


def _status_for_error(error: LearnctlError) -> int:
    if isinstance(error, UsageError):
        return HTTPStatus.BAD_REQUEST
    if isinstance(error, BlockedError):
        return HTTPStatus.CONFLICT
    if isinstance(error, DataError):
        return HTTPStatus.UNPROCESSABLE_ENTITY
    return HTTPStatus.INTERNAL_SERVER_ERROR


def _json_error(message: str, exit_code: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": False, "error": message}
    if exit_code is not None:
        payload["exit_code"] = exit_code
    return payload


def _task_id_from_path(path: str, prefix: str) -> str:
    value = urllib.parse.unquote(path[len(prefix) :])
    if not value or "/" in value or "\\" in value:
        raise UsageError("资源 ID 无效")
    return value


def _safe_artifact_path(artifact: str) -> str | None:
    if artifact.endswith(("/", "\\")):
        return None
    try:
        return normalize_relative_path(artifact)
    except UsageError:
        return None


def allowed_task_files(curriculum: dict[str, Any], task: dict[str, Any], root: Path | None = None) -> list[dict[str, str]]:
    paths: dict[str, str] = {}
    for artifact in task["artifacts"]:
        normalized = _safe_artifact_path(artifact)
        if normalized and (root is None or not resolve_under_root(root, normalized).is_dir()):
            paths[normalized] = "artifact"
    for exercise_id in task["exercise_ids"]:
        exercise = curriculum["_index"]["exercises"][exercise_id]
        for token in parse_test_command(exercise["test_command"], f"exercise[{exercise_id}].test_command")[3:]:
            if token != "-q":
                paths[normalize_relative_path(token)] = "exercise"
    return [{"path": path, "kind": paths[path]} for path in sorted(paths)]


class LearnctlServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.state_lock = threading.RLock()
        self.env_lock = threading.RLock()
        self.running_lock = threading.Lock()
        self.running_exercises: set[str] = set()
        self.ai_session = AiSession()
        # 变式题只保存在当前服务进程内存（按生成顺序淘汰），不落盘、不跨服务共享。
        self.variations: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
        self.variations_lock = threading.RLock()
        super().__init__(server_address, LearnctlRequestHandler)

    @property
    def host(self) -> str:
        return "127.0.0.1"

    def paths(self) -> tuple[Path, Path, Path]:
        learn_dir = self.project_root / ".learn"
        return (
            self.project_root / "data" / "curriculum.json",
            learn_dir / "progress.json",
            learn_dir / "diagnostic-report.json",
        )


def create_server(project_root: Path, host: str = "127.0.0.1", port: int = 8765) -> LearnctlServer:
    if host != "127.0.0.1":
        raise UsageError("serve 只允许绑定 host=127.0.0.1")
    if not 0 <= port <= 65535:
        raise UsageError("端口必须是 0 到 65535 的整数")
    root = project_root.resolve()
    curriculum_path = root / "data" / "curriculum.json"
    load_curriculum(curriculum_path)
    return LearnctlServer((host, port), root)


def serve(project_root: Path, host: str, port: int, open_browser: bool = False) -> int:
    server = create_server(project_root, host, port)
    url = f"http://{host}:{server.server_port}/"
    print(f"学习工作台已启动：{url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


class LearnctlRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def log_message(self, format: str, *args: Any) -> None:
        return

    @property
    def app_server(self) -> LearnctlServer:
        return self.server  # type: ignore[return-value]

    def _dispatch(self, method: str) -> None:
        try:
            if method in {"POST", "PUT"} and not self._check_same_origin():
                return
            parsed = urllib.parse.urlsplit(self.path)
            path = urllib.parse.unquote(parsed.path)
            if path.startswith("/api/"):
                payload = self._api(method, path, urllib.parse.parse_qs(parsed.query))
                self._send_json(HTTPStatus.OK, payload)
                return
            if method != "GET":
                self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, _json_error("该路径不支持此 HTTP 方法"))
                return
            self._send_static(path)
        except LearnctlError as exc:
            self._send_json(_status_for_error(exc), _json_error(str(exc), exc.exit_code))
        except (OSError, ValueError) as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, _json_error(f"本地操作失败：{exc}"))

    def _check_same_origin(self) -> bool:
        expected_host = f"127.0.0.1:{self.app_server.server_port}"
        if self.headers.get("Host") != expected_host:
            self._send_json(HTTPStatus.FORBIDDEN, _json_error("写操作需要同源 Host"))
            return False
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{expected_host}":
            self._send_json(HTTPStatus.FORBIDDEN, _json_error("写操作需要同源 Origin"))
            return False
        return True

    def _send_json(self, status: int | HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_common_headers(len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: int | HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self._send_common_headers(len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_common_headers(self, length: int) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(length))
        self.send_header("Connection", "close")

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise UsageError("JSON 请求缺少 Content-Length")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise UsageError("Content-Length 无效") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            _drain_body(self.rfile, length)
            raise UsageError(f"请求体超过上限 {MAX_REQUEST_BYTES} 字节")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise UsageError("请求体必须是有效的 UTF-8 JSON") from exc
        if not isinstance(data, dict):
            raise UsageError("JSON 请求体必须是对象")
        return data

    def _context(self) -> tuple[dict[str, Any], dict[str, Any], Path, Path, Path]:
        curriculum_path, progress_path, report_path = self.app_server.paths()
        curriculum = load_curriculum(curriculum_path)
        progress = load_progress(progress_path, curriculum)
        return curriculum, progress, curriculum_path, progress_path, report_path

    def _api(self, method: str, path: str, query: dict[str, list[str]]) -> dict[str, Any]:
        if path == "/api/bootstrap" and method == "GET":
            return self._bootstrap()
        if path == "/api/catalog" and method == "GET":
            return self._catalog(query)
        if path == "/api/diagnostic/questions" and method == "GET":
            return self._diagnostic_questions()
        if path == "/api/diagnostic/run" and method == "POST":
            return self._diagnostic_run()
        if path == "/api/files" and method == "GET":
            return self._files_get(query)
        if path == "/api/files" and method == "PUT":
            return self._files_put()
        if path == "/api/env/action" and method == "POST":
            return self._env_action()
        if path == "/api/ai/status" and method == "GET":
            return self._ai_status()
        if path == "/api/ai/session-key" and method == "POST":
            return self._ai_session_key()
        if path == "/api/ai/test" and method == "POST":
            return self._ai_test()
        if path == "/api/ai/chat" and method == "POST":
            return self._ai_chat()
        if path == "/api/ai/generate" and method == "POST":
            return self._ai_generate()
        if path == "/api/ai/review" and method == "POST":
            return self._ai_review()
        task_status_match = re.fullmatch(r"/api/tasks/([^/]+)/status", path)
        if task_status_match and method == "POST":
            return self._task_status(urllib.parse.unquote(task_status_match.group(1)))
        lesson_position_match = re.fullmatch(r"/api/tasks/([^/]+)/lesson-position", path)
        if lesson_position_match and method == "POST":
            return self._lesson_position(urllib.parse.unquote(lesson_position_match.group(1)))
        section_draft_match = re.fullmatch(r"/api/tasks/([^/]+)/sections/([^/]+)/draft", path)
        if section_draft_match and method == "PUT":
            return self._section_draft(
                urllib.parse.unquote(section_draft_match.group(1)),
                urllib.parse.unquote(section_draft_match.group(2)),
            )
        section_validate_match = re.fullmatch(r"/api/tasks/([^/]+)/sections/([^/]+)/validate", path)
        if section_validate_match and method == "POST":
            return self._section_validate(
                urllib.parse.unquote(section_validate_match.group(1)),
                urllib.parse.unquote(section_validate_match.group(2)),
            )
        task_match = re.fullmatch(r"/api/tasks/([^/]+)", path)
        if task_match and method == "GET":
            return self._task_get(urllib.parse.unquote(task_match.group(1)))
        note_match = re.fullmatch(r"/api/notes/([^/]+)", path)
        if note_match:
            task_id = urllib.parse.unquote(note_match.group(1))
            if method == "GET":
                return self._notes_get(task_id)
            if method == "PUT":
                return self._notes_put(task_id)
        module_match = re.fullmatch(r"/api/modules/([^/]+)/status", path)
        if module_match and method == "POST":
            return self._module_status(urllib.parse.unquote(module_match.group(1)))
        option_match = re.fullmatch(r"/api/options/([^/]+)", path)
        if option_match and method == "POST":
            return self._option_status(urllib.parse.unquote(option_match.group(1)))
        exercise_match = re.fullmatch(r"/api/exercises/([^/]+)/run", path)
        if exercise_match and method == "POST":
            return self._exercise_run(urllib.parse.unquote(exercise_match.group(1)))
        if path == "/api/workspace" and method == "GET":
            return self._workspace_tree(query)
        workspace_file_match = re.fullmatch(r"/api/workspace/files/(.+)", path)
        if workspace_file_match and method == "GET":
            return self._workspace_file_get(urllib.parse.unquote(workspace_file_match.group(1)))
        if workspace_file_match and method == "PUT":
            return self._workspace_file_put(urllib.parse.unquote(workspace_file_match.group(1)))
        raise UsageError("API 路径不存在")

    def _bootstrap(self) -> dict[str, Any]:
        curriculum, progress, _, _, _ = self._context()
        current = today_payload(curriculum, progress)
        stages: list[dict[str, Any]] = []
        for stage in curriculum["stages"]:
            tasks = []
            for task_id in stage["task_ids"]:
                task = curriculum["_index"]["tasks"][task_id]
                payload = task_payload(curriculum, progress, task)
                lesson = payload["task"]["lesson"]
                tasks.append(
                    {
                        "id": task_id,
                        "title": task["title"],
                        "status": payload["task"]["status"],
                        "blocked": payload["blocked"],
                        "missing_prerequisites": payload["missing_prerequisites"],
                        "current_section": lesson["current_section"],
                        "completed_sections": lesson["completed_count"],
                    }
                )
            done = sum(item["status"] == "done" for item in tasks)
            stages.append(
                {
                    "id": stage["id"],
                    "title": stage["title"],
                    "goal": stage["goal"],
                    "deliverable": stage["deliverable"],
                    "done": done,
                    "total": len(tasks),
                    "tasks": tasks,
                }
            )
        modules = []
        for module in curriculum["modules"]:
            optional_track = module.get("optional_track_id")
            enabled = not optional_track or progress["options"].get(optional_track, False)
            modules.append(
                {
                    "id": module["id"],
                    "title": module["title"],
                    "topics": module["topics"],
                    "catalog_refs": module["catalog_refs"],
                    "status": module_status(module, progress),
                    "optional_track_id": optional_track,
                    "enabled": enabled,
                    "supplemental": module.get("supplemental", False),
                }
            )
        recent_tests = sorted(
            progress["tests"].values(), key=lambda record: record.get("run_at", ""), reverse=True
        )[:8]
        task_done = sum(item["status"] == "done" for stage in stages for item in stage["tasks"])
        return {
            "curriculum_version": curriculum["curriculum_version"],
            "progress": {"done": task_done, "total": len(curriculum["tasks"])},
            "current": current,
            "stages": stages,
            "modules": modules,
            "options": progress["options"],
            "optional_tracks": curriculum["optional_tracks"],
            "recent_tests": recent_tests,
            "catalog_count": len(curriculum["source_catalog"]),
        }

    def _task_get(self, task_id: str) -> dict[str, Any]:
        curriculum, progress, _, _, _ = self._context()
        task = curriculum["_index"]["tasks"].get(task_id)
        if task is None:
            raise UsageError(f"任务 ID 不存在：{task_id}")
        payload = task_payload(curriculum, progress, task)
        for section in payload["task"]["lesson"]["sections"]:
            draft = load_draft(self.app_server.project_root, task_id, section["id"])
            if draft is not None:
                section["draft"] = draft["content"]
        files = []
        for item in allowed_task_files(curriculum, task, self.app_server.project_root):
            file_path = resolve_under_root(self.app_server.project_root, item["path"])
            files.append({**item, "exists": file_path.is_file()})
        payload["editable_files"] = files
        payload["note_path"] = f".learn/notes/{task_id}.md"
        return payload

    def _lesson_position(self, task_id: str) -> dict[str, Any]:
        body = self._read_json()
        section_id = body.get("section_id")
        if not isinstance(section_id, str) or not section_id:
            raise UsageError("课程定位需要非空 section_id")
        with self.app_server.state_lock:
            curriculum, progress, _, progress_path, _ = self._context()
            return {"lesson_progress": update_lesson_position(curriculum, progress, progress_path, task_id, section_id)}

    def _section_draft(self, task_id: str, section_id: str) -> dict[str, Any]:
        body = self._read_json()
        content = body.get("content")
        if not isinstance(content, str):
            raise UsageError("草稿保存需要字符串 content")
        curriculum, _, _, _, _ = self._context()
        find_section(curriculum, task_id, section_id)
        with self.app_server.state_lock:
            payload = save_draft(self.app_server.project_root, task_id, section_id, content)
        return {"task_id": task_id, "section_id": section_id, "saved": True, "updated_at": payload["updated_at"]}

    def _section_validate(self, task_id: str, section_id: str) -> dict[str, Any]:
        body = self._read_json()
        content = body.get("content")
        if not isinstance(content, str):
            raise UsageError("验证需要字符串 content")
        curriculum, progress, _, _, _ = self._context()
        task, _ = find_section(curriculum, task_id, section_id)
        assert_section_unlocked(curriculum, progress, task, section_id)
        result = run_validation(curriculum, task_id, section_id, content, self.app_server.project_root)
        completed = False
        if result.get("passed"):
            with self.app_server.state_lock:
                curriculum, progress, _, progress_path, _ = self._context()
                complete_section(curriculum, progress, progress_path, task_id, section_id)
                completed = True
        else:
            # 失败保留草稿，避免学习者丢失内容
            with self.app_server.state_lock:
                find_section(curriculum, task_id, section_id)
                save_draft(self.app_server.project_root, task_id, section_id, content)
        result["completed"] = completed
        return result

    def _env_action(self) -> dict[str, Any]:
        body = self._read_json()
        action = body.get("action")
        if not isinstance(action, str) or not action:
            raise UsageError("环境动作需要非空 action")
        # 联网安装动作必须后端强制二次确认；其他动作不读取 confirmed，不受其影响
        if action == "install" and body.get("confirmed") is not True:
            raise UsageError("联网安装动作需要二次确认：请确认后再发送")
        # env_lock 全程串行化环境动作，避免双击同时创建/安装
        with self.app_server.env_lock:
            curriculum, progress, _, _, _ = self._context()
            gated_sections = [
                (task, section)
                for task in curriculum["tasks"]
                for section in task["lesson"]
                if section["practice"].get("kind") == "env_action" and section["practice"].get("action") == action
            ]
            for task, section in gated_sections:
                assert_section_unlocked(curriculum, progress, task, section["id"])
            result = run_action(action, self.app_server.project_root)
            completed = False
            if result.get("passed"):
                with self.app_server.state_lock:
                    curriculum, progress, _, progress_path, _ = self._context()
                    for task in curriculum["tasks"]:
                        for section in task["lesson"]:
                            practice = section["practice"]
                            if practice.get("kind") == "env_action" and practice.get("action") == action:
                                complete_section(curriculum, progress, progress_path, task["id"], section["id"])
                                completed = True
            result["completed"] = completed
            return result

    def _catalog(self, query: dict[str, list[str]]) -> dict[str, Any]:
        curriculum, _, _, _, _ = self._context()
        series = query.get("series", [""])[0].strip()
        keyword = query.get("q", [""])[0].strip().casefold()
        items = [
            item
            for item in curriculum["source_catalog"]
            if (not series or item["series"] == series)
            and (not keyword or keyword in item["title"].casefold() or keyword in item["id"].casefold())
        ]
        return {"items": items, "total": len(items), "series": series, "q": query.get("q", [""])[0]}

    def _files_get(self, query: dict[str, list[str]]) -> dict[str, Any]:
        task_id = query.get("task_id", [""])[0]
        path = query.get("path", [""])[0]
        curriculum, _, _, _, _ = self._context()
        task = curriculum["_index"]["tasks"].get(task_id)
        if task is None:
            raise UsageError(f"任务 ID 不存在：{task_id}")
        allowed = allowed_task_files(curriculum, task, self.app_server.project_root)
        allowed_by_path = {item["path"]: item for item in allowed}
        if not path:
            return {
                "task_id": task_id,
                "files": [
                    {
                        **item,
                        "exists": resolve_under_root(self.app_server.project_root, item["path"]).is_file(),
                    }
                    for item in allowed
                ],
            }
        normalized = normalize_relative_path(path)
        if normalized not in allowed_by_path:
            raise UsageError("文件不在当前任务白名单中")
        target = resolve_under_root(self.app_server.project_root, normalized)
        return {
            "task_id": task_id,
            "path": normalized,
            "kind": allowed_by_path[normalized]["kind"],
            "exists": target.is_file(),
            "content": read_utf8(target) if target.is_file() else "",
        }

    def _files_put(self) -> dict[str, Any]:
        body = self._read_json()
        task_id = body.get("task_id")
        path = body.get("path")
        content = body.get("content")
        if not isinstance(task_id, str) or not isinstance(path, str) or not isinstance(content, str):
            raise UsageError("文件保存需要 task_id、path 和字符串 content")
        curriculum, _, _, _, _ = self._context()
        task = curriculum["_index"]["tasks"].get(task_id)
        if task is None:
            raise UsageError(f"任务 ID 不存在：{task_id}")
        normalized = normalize_relative_path(path)
        if normalized not in {item["path"] for item in allowed_task_files(curriculum, task, self.app_server.project_root)}:
            raise UsageError("文件不在当前任务白名单中")
        target = resolve_under_root(self.app_server.project_root, normalized)
        with self.app_server.state_lock:
            atomic_write_text(target, content)
        return {"task_id": task_id, "path": normalized, "saved": True, "bytes": len(content.encode("utf-8"))}

    def _notes_get(self, task_id: str) -> dict[str, Any]:
        curriculum, _, _, _, _ = self._context()
        if task_id not in curriculum["_index"]["tasks"]:
            raise UsageError(f"任务 ID 不存在：{task_id}")
        path = resolve_under_root(self.app_server.project_root, f".learn/notes/{task_id}.md")
        return {"task_id": task_id, "exists": path.is_file(), "content": read_utf8(path) if path.is_file() else ""}

    def _notes_put(self, task_id: str) -> dict[str, Any]:
        body = self._read_json()
        content = body.get("content")
        if not isinstance(content, str):
            raise UsageError("笔记保存需要字符串 content")
        curriculum, _, _, _, _ = self._context()
        if task_id not in curriculum["_index"]["tasks"]:
            raise UsageError(f"任务 ID 不存在：{task_id}")
        path = resolve_under_root(self.app_server.project_root, f".learn/notes/{task_id}.md")
        with self.app_server.state_lock:
            atomic_write_text(path, content)
        return {"task_id": task_id, "saved": True, "bytes": len(content.encode("utf-8"))}

    def _task_status(self, task_id: str) -> dict[str, Any]:
        body = self._read_json()
        status = body.get("status")
        evidence = body.get("evidence", "")
        if not isinstance(status, str) or not isinstance(evidence, str):
            raise UsageError("任务状态需要 status 和可选字符串 evidence")
        with self.app_server.state_lock:
            curriculum, progress, _, progress_path, _ = self._context()
            update_task(curriculum, progress, progress_path, task_id, status, evidence)
            return self._task_get(task_id)

    def _module_status(self, module_id: str) -> dict[str, Any]:
        body = self._read_json()
        status = body.get("status")
        if not isinstance(status, str):
            raise UsageError("模块状态需要 status")
        with self.app_server.state_lock:
            curriculum, progress, _, progress_path, _ = self._context()
            update_module(curriculum, progress, progress_path, module_id, status)
        return {"module_id": module_id, "status": status}

    def _option_status(self, option_id: str) -> dict[str, Any]:
        body = self._read_json()
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise UsageError("选修项更新需要布尔 enabled")
        with self.app_server.state_lock:
            curriculum, progress, _, progress_path, _ = self._context()
            update_option(curriculum, progress, progress_path, option_id, enabled)
        return {"option_id": option_id, "enabled": enabled}

    def _diagnostic_questions(self) -> dict[str, Any]:
        curriculum, _, _, _, _ = self._context()
        diagnostics = []
        for diagnostic in curriculum["diagnostics"]:
            if diagnostic["id"] == "D0":
                continue
            diagnostics.append(
                {
                    "id": diagnostic["id"],
                    "title": diagnostic["title"],
                    "cases": [
                        {"id": case_id, "prompt": QUESTIONS[diagnostic["id"]][case_id][0]}
                        for case_id in diagnostic["critical_cases"]
                    ],
                }
            )
        return {"diagnostics": diagnostics}

    def _diagnostic_run(self) -> dict[str, Any]:
        body = self._read_json()
        answers = body.get("answers")
        if not isinstance(answers, dict):
            raise UsageError("诊断提交需要 answers 对象")
        validate_answers_data(answers, "请求 answers")
        with self.app_server.state_lock:
            curriculum, progress, _, progress_path, report_path = self._context()
            collected = collect_answers(curriculum, answers, prompt_stream=io.StringIO(), input_stream=io.StringIO())
            report = run_diagnostics(curriculum, collected, progress["options"])
            persist_diagnostic(report, curriculum, progress, report_path, progress_path)
        return report

    def _exercise_run(self, exercise_id: str) -> dict[str, Any]:
        with self.app_server.running_lock:
            if exercise_id in self.app_server.running_exercises:
                raise BlockedError(f"练习 {exercise_id} 正在运行，请等待本次运行结束")
            self.app_server.running_exercises.add(exercise_id)
        try:
            with self.app_server.state_lock:
                curriculum, progress, _, progress_path, _ = self._context()
                exercise = curriculum["_index"]["exercises"].get(exercise_id)
                if exercise is None:
                    raise UsageError(f"练习 ID 不存在：{exercise_id}")
                return run_exercise_capture(exercise, self.app_server.project_root, progress, progress_path)
        finally:
            with self.app_server.running_lock:
                self.app_server.running_exercises.discard(exercise_id)

    # ------------------------------------------------------------------
    # AI 助教（DeepSeek）
    # ------------------------------------------------------------------

    def _ai_status(self) -> dict[str, Any]:
        session = self.app_server.ai_session
        source: str | None = None
        if session._key is not None:
            source = "session"
        elif os.environ.get("DEEPSEEK_API_KEY"):
            source = "env"
        return {
            "provider": "deepseek",
            "model": ai.MODEL,
            "base_url": ai.BASE_URL,
            "configured": session.configured(),
            "key_source": source,
        }

    def _ai_session_key(self) -> dict[str, Any]:
        body = self._read_json()
        key = body.get("key")
        if not isinstance(key, str):
            raise UsageError("需要字符串 key")
        key = key.strip()
        if not 8 <= len(key) <= 512:
            raise UsageError("API Key 长度必须在 8 到 512 之间")
        self.app_server.ai_session.set_key(key)
        return {"ok": True, "configured": True, "key_source": "session"}

    def _ai_test(self) -> dict[str, Any]:
        try:
            content = ai.chat(self.app_server.ai_session, [{"role": "user", "content": "ping"}])
        except AiError as exc:
            return _json_error(str(exc))
        return {"ok": True, "content": content[:200]}

    def _ai_chat(self) -> dict[str, Any]:
        body = self._read_json()
        task_id = body.get("task_id")
        section_id = body.get("section_id")
        question = body.get("question")
        history = body.get("history", [])
        if not isinstance(task_id, str) or not isinstance(section_id, str):
            raise UsageError("chat 需要 task_id 与 section_id")
        curriculum, _, _, _, _ = self._context()
        try:
            answer = ai.tutor_chat(
                self.app_server.ai_session,
                curriculum,
                task_id,
                section_id,
                question,
                history,
            )
        except AiError as exc:
            return _json_error(str(exc))
        return {"ok": True, "answer": answer}

    def _ai_generate(self) -> dict[str, Any]:
        body = self._read_json()
        task_id = body.get("task_id")
        section_id = body.get("section_id")
        if not isinstance(task_id, str) or not isinstance(section_id, str):
            raise UsageError("generate 需要 task_id 与 section_id")
        # 完成状态由服务端从当前进度派生，忽略前端 body 传入的 completed
        curriculum, progress, _, _, _ = self._context()
        task, section = find_section(curriculum, task_id, section_id)
        completed = section_completed(progress, task, section_id)
        try:
            data = ai.generate(self.app_server.ai_session, curriculum, task_id, section_id, completed)
        except AiError as exc:
            return _json_error(str(exc))
        variation_id = _new_variation_id()
        # 变式题与其 task/section 绑定只保存在当前服务进程内存，供 review 按 id 回取；
        # 用生成顺序淘汰制上限，避免无限增长。
        with self.app_server.variations_lock:
            self.app_server.variations[variation_id] = {
                "variation_id": variation_id,
                "task_id": task_id,
                "section_id": section_id,
                "variation": data,
            }
            while len(self.app_server.variations) > MAX_STORED_VARIATIONS:
                self.app_server.variations.popitem(last=False)
        # variation 内嵌 variation_id，便于前端按小节保存唯一绑定；权威数据始终在服务端。
        return {"ok": True, "variation_id": variation_id, "variation": {**data, "variation_id": variation_id}}

    def _variation_lookup(self, variation_id: str, task_id: str, section_id: str) -> dict[str, Any]:
        """按 id 回取变式题并校验绑定；不存在/错配明确报错，绝不静默回退到固定练习。"""
        with self.app_server.variations_lock:
            record = self.app_server.variations.get(variation_id)
            if record is None:
                raise UsageError("变式题 ID 不存在或已过期：请重新生成后再评审")
            if record["task_id"] != task_id or record["section_id"] != section_id:
                raise UsageError("变式题与当前任务/小节不匹配")
            return record["variation"]

    def _ai_review(self) -> dict[str, Any]:
        body = self._read_json()
        task_id = body.get("task_id")
        section_id = body.get("section_id")
        content = body.get("content")
        if not isinstance(task_id, str) or not isinstance(section_id, str) or not isinstance(content, str):
            raise UsageError("review 需要 task_id、section_id 与字符串 content")
        validation_summary = body.get("validation_summary", "")
        if not isinstance(validation_summary, str):
            validation_summary = ""
        has_variation_id = "variation_id" in body
        variation_id = body.get("variation_id")
        if has_variation_id and (not isinstance(variation_id, str) or not variation_id.strip()):
            raise UsageError("review 需要非空字符串 variation_id")
        curriculum, _, _, _, _ = self._context()
        try:
            if has_variation_id:
                variation = self._variation_lookup(variation_id, task_id, section_id)
                data = ai.review_variation(
                    self.app_server.ai_session,
                    curriculum,
                    task_id,
                    section_id,
                    variation,
                    content,
                    validation_summary,
                )
            else:
                data = ai.review(
                    self.app_server.ai_session,
                    curriculum,
                    task_id,
                    section_id,
                    content,
                    validation_summary,
                )
        except AiError as exc:
            return _json_error(str(exc))
        return {"ok": True, "review": data}

    # ------------------------------------------------------------------
    # 工作区（workspace）文件树
    # ------------------------------------------------------------------

    def _workspace_tree(self, query: dict[str, list[str]]) -> dict[str, Any]:
        from ..practice import _workspace_dir as ws_dir

        ws = ws_dir(self.app_server.project_root)
        files: list[dict[str, Any]] = []
        if ws.is_dir():
            for file_path in sorted(ws.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(ws).as_posix()
                    files.append({
                        "path": rel,
                        "size": file_path.stat().st_size,
                        "exists": True,
                    })
        # 补充课程声明的 project_file（即使尚未落盘）
        curriculum, _, _, _, _ = self._context()
        declared: dict[str, str] = {}
        for task in curriculum["tasks"]:
            for section in task["lesson"]:
                pf = section.get("practice", {}).get("project_file")
                if pf and pf not in declared:
                    declared[pf] = section["id"]
        for path_str, section_id in sorted(declared.items()):
            if not any(item["path"] == path_str for item in files):
                files.append({"path": path_str, "size": 0, "exists": False})
        return {"workspace_root": str(ws.relative_to(self.app_server.project_root)), "files": files}

    def _workspace_file_get(self, rel_path: str) -> dict[str, Any]:
        from ..practice import _workspace_dir as ws_dir

        normalized = normalize_relative_path(rel_path)
        curriculum, _, _, _, _ = self._context()
        # 白名单：只允许课程声明的 project_file
        declared: set[str] = set()
        for task in curriculum["tasks"]:
            for section in task["lesson"]:
                pf = section.get("practice", {}).get("project_file")
                if pf:
                    declared.add(pf)
        if normalized not in declared:
            raise UsageError("文件不在项目白名单中")
        target = ws_dir(self.app_server.project_root) / normalized
        return {
            "path": normalized,
            "exists": target.is_file(),
            "content": read_utf8(target) if target.is_file() else "",
        }

    def _workspace_file_put(self, rel_path: str) -> dict[str, Any]:
        from ..practice import _workspace_dir as ws_dir

        body = self._read_json()
        content = body.get("content")
        if not isinstance(content, str):
            raise UsageError("文件保存需要字符串 content")
        normalized = normalize_relative_path(rel_path)
        curriculum, _, _, _, _ = self._context()
        declared: set[str] = set()
        for task in curriculum["tasks"]:
            for section in task["lesson"]:
                pf = section.get("practice", {}).get("project_file")
                if pf:
                    declared.add(pf)
        if normalized not in declared:
            raise UsageError("文件不在项目白名单中")
        target = ws_dir(self.app_server.project_root) / normalized
        with self.app_server.state_lock:
            atomic_write_text(target, content)
        return {"path": normalized, "saved": True, "bytes": len(content.encode("utf-8"))}

    def _send_static(self, path: str) -> None:
        static_root = Path(__file__).with_name("static").resolve()
        if path == "/":
            relative = "index.html"
        elif path.startswith("/static/"):
            relative = path[len("/static/") :]
        else:
            self._send_json(HTTPStatus.NOT_FOUND, _json_error("静态资源不存在"))
            return
        if not relative or any(part in {"", ".", ".."} for part in PurePosixPath(relative).parts):
            self._send_json(HTTPStatus.BAD_REQUEST, _json_error("静态资源路径无效"))
            return
        if PurePosixPath(relative).is_absolute() or PureWindowsPath(relative).is_absolute():
            self._send_json(HTTPStatus.BAD_REQUEST, _json_error("静态资源路径不得是绝对路径"))
            return
        target = (static_root / relative).resolve(strict=False)
        try:
            target.relative_to(static_root)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, _json_error("静态资源路径不安全"))
            return
        if not target.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, _json_error("静态资源不存在"))
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send_bytes(
            HTTPStatus.OK,
            target.read_bytes(),
            f"{content_type}; charset=utf-8" if content_type.startswith("text/") or content_type == "application/javascript" else content_type,
        )

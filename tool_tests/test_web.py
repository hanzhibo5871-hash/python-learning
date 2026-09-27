from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from conftest import REPOSITORY, request
from learnctl import ai
from learnctl.errors import UsageError
import learnctl.web.server as web_server_module
from learnctl.web.server import create_server
from learnctl.progress import load_progress, save_progress
from learnctl.curriculum import load_curriculum


PUBLIC_PRACTICE_KEYS = {"kind", "file_name", "scenario", "instructions", "starter_content", "input_examples", "expected_behavior", "hints"}


def _unlock_d02(server: Any) -> None:
    path = server.project_root / ".learn" / "progress.json"
    curriculum = load_curriculum(server.project_root / "data" / "curriculum.json")
    state = load_progress(path, curriculum)
    state["tasks"]["D01"] = {"status": "done", "evidence": ["测试准备：D01 环境已验证"]}
    state["lesson_progress"]["D02"]["completed_sections"] = ["D02-execution"]
    save_progress(path, state)


def _unlock_d01_detect(server: Any) -> None:
    path = server.project_root / ".learn" / "progress.json"
    curriculum = load_curriculum(server.project_root / "data" / "curriculum.json")
    state = load_progress(path, curriculum)
    state["lesson_progress"]["D01"]["completed_sections"] = ["D01-onboarding"]
    save_progress(path, state)


def test_serve_rejects_non_loopback_host(project: Path) -> None:
    with pytest.raises(UsageError, match="127.0.0.1"):
        create_server(project, host="0.0.0.0", port=0)


def test_static_page_security_and_no_external_resources(web_server: Any) -> None:
    status, html, headers = request(web_server, "GET", "/")
    assert status == 200
    assert "learnctl" in html
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    for name in ("index.html", "app.js", "styles.css"):
        content = (REPOSITORY / "learnctl" / "web" / "static" / name).read_text(encoding="utf-8")
        assert "src=\"http" not in content
        assert "href=\"http" not in content
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    for marker in (
        "lesson-panel",
        "practice-editor",
        "save-draft",
        "run-validate",
        "data-reset",
        "ai-panel",
        "data-env-action",
        "variation_id",
        "当前批改对象",
        "ai-chat-input",
        "ai-chat-send",
        "ai-chat-clear",
        "当前小节对话",
    ):
        assert marker in app_js
    assert 'type="radio"' not in app_js
    status, payload, _ = request(web_server, "GET", "/static/%2e%2e/%2e%2e/README.md")
    assert status in {400, 404}
    assert payload["ok"] is False


def test_d01_environment_ui_explains_windows_commands_and_evidence(web_server: Any) -> None:
    status, payload, _ = request(web_server, "GET", "/api/tasks/D01")
    assert status == 200
    sections = {item["id"]: item for item in payload["task"]["lesson"]["sections"]}
    assert "where.exe python" in sections["D01-detect"]["explanation"][0]
    assert "ExecutionPolicy" in sections["D01-create-venv"]["explanation"][2]
    assert ".venv\\Scripts\\python.exe -m pip" in sections["D01-install"]["practice"]["instructions"]
    assert "成功标准" in sections["D01-verify"]["explanation"][2]
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    for marker in ("where.exe python", "python --version", "Get-Location", ".venv\\Scripts\\python.exe", "ExecutionPolicy", "validation-result", "stdout", "stderr", "exit_code"):
        assert marker in app_js, marker


def test_successful_validation_and_env_action_refresh_authoritative_task_state(web_server: Any) -> None:
    """连续完成 D01 与普通 D02 小节后，GET payload 才是前端应渲染的锁状态来源。"""
    content = "今天我要配置 Python 开发环境：确认解释器版本，创建虚拟环境 venv，并用 pip 安装 pytest 依赖，最后验证工具可编辑安装。"
    status, result, _ = request(
        web_server,
        "POST",
        "/api/tasks/D01/sections/D01-onboarding/validate",
        {"content": content},
    )
    assert status == 200 and result["passed"] is True
    status, task_payload, _ = request(web_server, "GET", "/api/tasks/D01")
    assert status == 200
    d01_sections = {section["id"]: section for section in task_payload["task"]["lesson"]["sections"]}
    assert task_payload["task"]["lesson"]["required_completed"] == 1
    assert task_payload["task"]["lesson"]["completed_count"] == 1
    assert d01_sections["D01-onboarding"]["completed"] is True
    assert d01_sections["D01-detect"]["locked"] is False

    status, result, _ = request(web_server, "POST", "/api/env/action", {"action": "detect"})
    assert status == 200 and result["passed"] is True
    status, task_payload, _ = request(web_server, "GET", "/api/tasks/D01")
    assert status == 200
    d01_sections = {section["id"]: section for section in task_payload["task"]["lesson"]["sections"]}
    assert task_payload["task"]["lesson"]["required_completed"] == 2
    assert task_payload["task"]["lesson"]["completed_count"] == 2
    assert d01_sections["D01-detect"]["completed"] is True
    assert d01_sections["D01-create-venv"]["locked"] is False

    _unlock_d02(web_server)
    solution = "value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))\n"
    status, result, _ = request(
        web_server,
        "POST",
        "/api/tasks/D02/sections/D02-names/validate",
        {"content": solution},
    )
    assert status == 200 and result["passed"] is True
    status, task_payload, _ = request(web_server, "GET", "/api/tasks/D02")
    assert status == 200
    d02_sections = {section["id"]: section for section in task_payload["task"]["lesson"]["sections"]}
    assert task_payload["task"]["lesson"]["required_completed"] == 2
    assert task_payload["task"]["lesson"]["completed_count"] == 2
    assert d02_sections["D02-names"]["completed"] is True
    assert d02_sections["D02-numbers"]["locked"] is False

    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "async function refreshTaskState" in app_js
    assert app_js.count("await refreshTaskState();") >= 2
    assert "lesson.completed_count += 1" not in app_js


def test_successful_refresh_restores_complete_validation_evidence_in_new_dom(web_server: Any) -> None:
    """刷新重建 section DOM 后，普通验证和 env action 的证据仍须可见。"""
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderValidationResult" in app_js
    assert "state.lastValidation = { section_id: section.id, ...result }" in app_js
    assert "state.lastValidation?.section_id === section.id" in app_js
    assert "renderValidationResult(storedResult, kind)" in app_js
    for marker in ("result.command", "result.stdout", "result.stderr", "result.exit_code", "result.checks"):
        assert marker in app_js, marker
    # 两条成功路径都必须在权威刷新后重建页面，不能只更新旧 DOM。
    assert app_js.count("await refreshTaskState();") >= 2
    assert app_js.count("await renderTask(state.taskId);") >= 2


def test_route_navigation_handles_global_data_route_and_hash_history(web_server: Any) -> None:
    """课程正文的 data-route 也必须走统一 hash 路由，避免返回按钮失效。"""
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'document.addEventListener("click"' in app_js
    assert 'event.target.closest("[data-route]")' in app_js
    assert 'window.addEventListener("hashchange"' in app_js
    assert "function normaliseRoute" in app_js
    assert 'history.replaceState(null, "", "#/dashboard")' in app_js
    assert "normaliseRoute(window.location.hash)" in app_js
    assert "renderTask" in app_js and "isProjectTask" in app_js
    assert "section.objective" in app_js and "section.examples" in app_js and "section.common_errors" in app_js
    assert 'isProjectTask ? renderWorkspacePanel() : ""' in app_js
    route_body = app_js[app_js.index("function navigate"):app_js.index('window.addEventListener("hashchange"')]
    assert "render();" not in route_body
    assert '$("#nav").addEventListener("click"' not in app_js


def test_static_markers_and_no_legacy_copy(web_server: Any) -> None:
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    css = (REPOSITORY / "learnctl" / "web" / "static" / "styles.css").read_text(encoding="utf-8")
    # 项目文件区已改为 textarea 编辑器 + 保存按钮，不再“不可手动编辑”
    assert "保存项目文件" in app_js
    assert 'data-ws-path' in app_js
    assert "PUT" in app_js and "/api/workspace/files/" in app_js
    assert "不可手动编辑" not in app_js
    assert "不可手动编辑" not in css
    # 本节真实产物：真实路径 + 原子落盘；continues_file 说明继续编辑前一节真实文件
    assert "本节真实产物" in app_js
    assert "learner_workspace/task-manager/" in app_js
    assert "原子" in app_js
    assert "continues_file" in app_js
    assert "继续编辑" in app_js
    # 未创建文件也可手动保存，但不自动完成章节
    assert "不会自动完成" in app_js
    # mark-done 需全部必修小节验证通过，并展示后端权威 x/y
    assert "required_completed" in app_js and "required_sections" in app_js
    assert "后端权威" in app_js


def test_bootstrap_counts_and_route(web_server: Any) -> None:
    status, bootstrap, _ = request(web_server, "GET", "/api/bootstrap")
    assert status == 200
    assert bootstrap["progress"] == {"done": 0, "total": 28}
    assert len(bootstrap["stages"]) == 4
    assert [stage["id"] for stage in bootstrap["stages"]] == ["S1", "S2", "S3", "S4"]
    assert bootstrap["curriculum_version"] == "3.0.0"
    assert bootstrap["catalog_count"] == 131


def test_curriculum_version_and_project_artifact_count(web_server: Any) -> None:
    # 锁定 curriculum v3 的章节数；并校验 D18-D24 共声明 15 个唯一真实产物
    data = json.loads((web_server.project_root / "data" / "curriculum.json").read_text(encoding="utf-8"))
    assert data["curriculum_version"] == "3.0.0"
    total_sections = sum(len(task["lesson"]) for task in data["tasks"])
    assert total_sections == 122
    project_files = {
        section.get("practice", {}).get("project_file")
        for task in data["tasks"]
        for section in task["lesson"]
    }
    project_files.discard(None)
    assert len(project_files) == 15


def test_task_get_hides_validator_and_quiz(web_server: Any) -> None:
    status, task, _ = request(web_server, "GET", "/api/tasks/D02")
    assert status == 200
    serialized = json.dumps(task, ensure_ascii=False)
    assert "quiz" not in serialized
    assert "answer_index" not in serialized
    # validator 内部检查名与实现细节绝不返回
    for secret in ("clean_name 正常", "_harness.py", "_check.py", "_CODE_VALIDATORS", "M."):
        assert secret not in serialized
    section = next(s for s in task["task"]["lesson"]["sections"] if s["id"] == "D02-names")
    assert section["practice"]["kind"] == "code"
    assert section["objective"]
    assert len(section["explanation"]) >= 3
    assert len(section["examples"]) >= 2
    assert section["locked"] is True
    assert set(section["practice"].keys()) == PUBLIC_PRACTICE_KEYS


def test_draft_put_and_get_roundtrip(web_server: Any) -> None:
    status, saved, _ = request(
        web_server,
        "PUT",
        "/api/tasks/D02/sections/D02-names/draft",
        {"content": "value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))"},
    )
    assert status == 200
    assert saved["saved"] is True
    status, task, _ = request(web_server, "GET", "/api/tasks/D02")
    section = next(s for s in task["task"]["lesson"]["sections"] if s["id"] == "D02-names")
    assert section["draft"] == "value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))"
    draft_file = web_server.project_root / ".learn" / "lesson-submissions" / "D02" / "D02-names.json"
    assert draft_file.is_file()
    data = json.loads(draft_file.read_text(encoding="utf-8"))
    assert data["section_id"] == "D02-names"


def test_locked_section_cannot_validate_or_mark_done_via_api(web_server: Any) -> None:
    """直接访问后续 URL/API 只能预览，不能绕过前置小节。"""
    status, task_payload, _ = request(web_server, "GET", "/api/tasks/D03")
    assert status == 200
    locked = next(section for section in task_payload["task"]["lesson"]["sections"] if section["id"] == "D03-if")
    assert locked["locked"] is True
    assert "D02" in locked["lock_reason"]

    status, payload, _ = request(
        web_server,
        "POST",
        "/api/tasks/D03/sections/D03-if/validate",
        {"content": "if True:\n    print('绕过')\n"},
    )
    assert status == 409
    assert payload["ok"] is False
    assert "D02" in payload["error"]

    status, payload, _ = request(
        web_server,
        "POST",
        "/api/tasks/D03/status",
        {"status": "done", "evidence": "手动伪造"},
    )
    assert status == 409
    assert payload["ok"] is False
    assert "D02" in payload["error"]

    # 已完成/未锁定的旧课仍可回看，不因门禁阻止 GET。
    status, previous_task, _ = request(web_server, "GET", "/api/tasks/D02")
    assert status == 200
    assert previous_task["task"]["id"] == "D02"


def test_validate_code_passes_and_completes_section_without_auto_done(web_server: Any) -> None:
    _unlock_d02(web_server)
    solution = "value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))\n"
    status, result, _ = request(
        web_server,
        "POST",
        "/api/tasks/D02/sections/D02-names/validate",
        {"content": solution},
    )
    assert status == 200
    assert result["passed"] is True
    assert result["completed"] is True
    assert result["exit_code"] == 0
    progress = json.loads((web_server.project_root / ".learn" / "progress.json").read_text(encoding="utf-8"))
    assert progress["lesson_progress"]["D02"]["completed_sections"] == ["D02-execution", "D02-names"]
    assert progress["tasks"].get("D02", {}).get("status", "todo") == "todo", "验证不自动完成任务"
    # 重复验证幂等
    status, result2, _ = request(web_server, "POST", "/api/tasks/D02/sections/D02-names/validate", {"content": solution})
    assert result2["completed"] is True
    progress = json.loads((web_server.project_root / ".learn" / "progress.json").read_text(encoding="utf-8"))
    assert progress["lesson_progress"]["D02"]["completed_sections"] == ["D02-execution", "D02-names"]


def test_validate_failure_keeps_draft_and_does_not_complete(web_server: Any) -> None:
    _unlock_d02(web_server)
    bad = "value = 7\nprint(value)\n"
    status, result, _ = request(web_server, "POST", "/api/tasks/D02/sections/D02-names/validate", {"content": bad})
    assert status == 200
    assert result["passed"] is False
    assert result["completed"] is False
    draft_file = web_server.project_root / ".learn" / "lesson-submissions" / "D02" / "D02-names.json"
    assert draft_file.is_file(), "失败应保留草稿"


def test_validate_text_section(web_server: Any) -> None:
    content = "今天我要配置 Python 开发环境：确认解释器版本，创建虚拟环境 venv，并用 pip 安装 pytest 依赖，最后验证工具可编辑安装。"
    status, result, _ = request(web_server, "POST", "/api/tasks/D01/sections/D01-onboarding/validate", {"content": content})
    assert status == 200
    assert result["passed"] is True
    assert result["completed"] is True


def test_env_action_detect_and_injection(web_server: Any) -> None:
    _unlock_d01_detect(web_server)
    status, result, _ = request(web_server, "POST", "/api/env/action", {"action": "detect"})
    assert status == 200
    assert result["passed"] is True
    assert "env" in result
    for key in ("command", "stdout", "stderr", "exit_code", "checks", "completed"):
        assert key in result, key
    assert "where.exe python" in result["command"]
    status, payload, _ = request(web_server, "POST", "/api/env/action", {"action": "detect; rm -rf ."})
    assert status == 409
    assert payload["ok"] is False
    # 安装动作必须带 confirmed 才会真正执行；无确认直接拒绝
    status, payload, _ = request(web_server, "POST", "/api/env/action", {"action": "install"})
    assert status == 400
    assert "二次确认" in payload["error"]
    status, payload, _ = request(web_server, "POST", "/api/env/action", {"action": "install", "confirmed": True})
    assert status == 409
    assert "D01-create-venv" in payload["error"]


def test_env_install_without_confirmed_never_calls_run_action(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def fake_run_action(action: str, root: object) -> dict:
        called.append(action)
        return {"action": action, "passed": True, "checks": [], "stdout": "", "stderr": "", "exit_code": 0, "env": {}}

    monkeypatch.setattr(web_server_module, "run_action", fake_run_action)
    status, payload, _ = request(web_server, "POST", "/api/env/action", {"action": "install"})
    assert status == 400
    assert payload["ok"] is False
    assert called == [], "未确认的 install 不得触发 run_action/pip"
    # 其他动作不受 confirmed 影响：非 install 即使带 confirmed 也不改变行为
    _unlock_d01_detect(web_server)
    status, payload, _ = request(web_server, "POST", "/api/env/action", {"action": "detect", "confirmed": False})
    assert status == 200
    assert called == ["detect"]


def test_request_body_limit_is_enforced(web_server: Any) -> None:
    big = json.dumps({"content": "x" * (web_server_module.MAX_REQUEST_BYTES + 10)})
    status, payload, _ = request(web_server, "PUT", "/api/tasks/D02/sections/D02-names/draft", json.loads(big))
    assert status == 400
    assert "超过上限" in payload["error"]


def test_ai_session_key_length_validation(web_server: Any) -> None:
    status, payload, _ = request(web_server, "POST", "/api/ai/session-key", {"key": "short"})
    assert status == 400
    assert "8 到 512" in payload["error"]
    status, payload, _ = request(web_server, "POST", "/api/ai/session-key", {"key": "k" * 513})
    assert status == 400
    assert "8 到 512" in payload["error"]


def test_same_origin_is_required_for_writes(web_server: Any) -> None:
    status, payload, _ = request(
        web_server,
        "PUT",
        "/api/tasks/D02/sections/D02-names/draft",
        {"content": "x"},
        Origin="http://evil.example",
    )
    assert status == 403
    assert payload["ok"] is False


def test_file_whitelist_and_notes(web_server: Any) -> None:
    status, saved, _ = request(
        web_server,
        "PUT",
        "/api/files",
        {"task_id": "D02", "path": "exercises/form.py", "content": "# 练习\n"},
    )
    assert status == 200
    assert (web_server.project_root / "exercises" / "form.py").read_text(encoding="utf-8") == "# 练习\n"
    for bad_path in ("../README.md", ".learn/progress.json", "learner_tests/*.py", "C:/outside.py"):
        status, payload, _ = request(web_server, "GET", f"/api/files?task_id=D02&path={bad_path.replace('/', '%2F')}")
        assert status == 400
        assert payload["ok"] is False


def test_ai_status_and_session_key_never_leak(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    status, status_data, _ = request(web_server, "GET", "/api/ai/status")
    assert status == 200
    assert status_data["provider"] == "deepseek"
    assert status_data["configured"] is False
    assert "key" not in status_data
    status, saved, _ = request(web_server, "POST", "/api/ai/session-key", {"key": "sk-secret-abc"})
    assert status == 200
    status, status_data, _ = request(web_server, "GET", "/api/ai/status")
    assert status_data["configured"] is True
    assert status_data["key_source"] == "session"
    assert "sk-secret-abc" not in json.dumps(status_data)


def test_ai_generate_and_review_are_mocked_offline(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"count": 0, "prompt": ""}

    def fake_request(url, payload, api_key, timeout=60):
        called["count"] += 1
        called["prompt"] = payload["messages"][0]["content"]
        content = json.dumps(
            {"title": "变式", "scenario": "场景", "instructions": "要求", "starter_content": "起始", "review_rubric": "标准"},
            ensure_ascii=False,
        )
        return 200, json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")

    monkeypatch.setattr(ai, "_request", fake_request)
    # 客户端即使谎报 completed: true，服务端也按当前进度派生（D02-names 未完成）
    status, result, _ = request(web_server, "POST", "/api/ai/generate", {"task_id": "D02", "section_id": "D02-names", "completed": True})
    assert status == 200
    assert result["ok"] is True
    assert result["variation"]["title"] == "变式"
    assert "未完成" in called["prompt"]
    assert called["count"] == 1

    content = json.dumps(
        {"summary": "总结", "strengths": ["a"], "issues": ["b"], "next_steps": ["c"]},
        ensure_ascii=False,
    )
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")))
    status, result, _ = request(web_server, "POST", "/api/ai/review", {"task_id": "D02", "section_id": "D02-names", "content": "我的代码"})
    assert status == 200
    assert result["ok"] is True
    assert set(result["review"]) == {"summary", "strengths", "issues", "next_steps"}


def test_ai_tutor_chat_is_bound_to_server_curriculum_context(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_request(url, payload, api_key, timeout=60):
        captured["payload"] = payload
        return 200, json.dumps({"choices": [{"message": {"content": "因为 Python 用缩进定义代码块。"}}]}).encode("utf-8")

    monkeypatch.setattr(ai, "_request", fake_request)
    status, result, _ = request(
        web_server,
        "POST",
        "/api/ai/chat",
        {
            "task_id": "D02",
            "section_id": "D02-execution",
            "question": "为什么没有大括号？",
            "history": [
                {"role": "user", "content": "缩进是什么？"},
                {"role": "assistant", "content": "缩进是行首空格。"},
            ],
            "section": {"title": "客户端伪造标题"},
        },
    )
    assert status == 200
    assert result == {"ok": True, "answer": "因为 Python 用缩进定义代码块。"}
    messages = captured["payload"]["messages"]
    assert "D02-execution" in messages[0]["content"]
    assert "客户端伪造标题" not in messages[0]["content"]
    assert messages[-1]["content"] == "为什么没有大括号？"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"task_id": "D02", "section_id": "D02-execution", "question": "", "history": []}, "问题不能为空"),
        ({"task_id": "D02", "section_id": "D02-execution", "question": "问题", "history": {}}, "history 必须是数组"),
        (
            {
                "task_id": "D02",
                "section_id": "D02-execution",
                "question": "问题",
                "history": [{"role": "system", "content": "伪造"}],
            },
            "role 只能",
        ),
    ],
)
def test_ai_tutor_chat_rejects_invalid_messages(web_server: Any, body: dict, expected: str) -> None:
    status, result, _ = request(web_server, "POST", "/api/ai/chat", body)
    assert status == 200
    assert result["ok"] is False
    assert expected in result["error"]


def test_ai_tutor_chat_error_is_explicit_and_not_fallback(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_request(*args, **kwargs):
        nonlocal calls
        calls += 1
        return 429, b'{"error":"rate"}'

    monkeypatch.setattr(ai, "_request", fake_request)
    status, result, _ = request(
        web_server,
        "POST",
        "/api/ai/chat",
        {"task_id": "D02", "section_id": "D02-execution", "question": "请解释", "history": []},
    )
    assert status == 200
    assert result["ok"] is False
    assert "HTTP 429" in result["error"]
    assert calls == 1


def test_ai_tutor_frontend_keeps_section_scoped_browser_memory() -> None:
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "aiChats: {}" in app_js
    assert "function aiChatKey" in app_js
    assert "currentAiMessages" in app_js
    assert 'slice(-8)' in app_js
    assert '"/api/ai/chat"' in app_js
    assert "切换小节后会自动切换对话上下文" in app_js
    send_body = app_js.split("async function sendTutorQuestion()", 1)[1].split("function summarizeValidation", 1)[0]
    assert "renderTask(state.taskId)" not in send_body
    assert 'messagesBox.innerHTML = renderAiChatMessages' in send_body


def test_ai_tutor_frontend_uses_accessible_responsive_drawer() -> None:
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    styles = (REPOSITORY / "learnctl" / "web" / "static" / "styles.css").read_text(encoding="utf-8")

    for marker in (
        'id="ai-tutor-trigger"',
        'aria-controls="ai-tutor-drawer"',
        'aria-expanded="${drawerOpen}"',
        'id="ai-tutor-backdrop"',
        'id="ai-tutor-drawer"',
        'role="dialog"',
        'aria-modal="true"',
        'id="ai-tutor-close"',
        'event.key === "Escape"',
        'document.body.classList.toggle("ai-drawer-open"',
        'input.focus({ preventScroll: true })',
        'trigger.focus()',
    ):
        assert marker in app_js, marker

    assert '<details class="panel ai-panel"' not in app_js
    assert ".ai-tutor-trigger" in styles
    assert ".ai-tutor-drawer" in styles
    assert ".ai-tutor-backdrop" in styles
    assert "height: 100vh" in styles
    assert "overflow-y: auto" in styles
    assert "@media (max-width: 760px)" in styles
    assert "width: 100%" in styles

    click_body = app_js.split('document.addEventListener("click", async (event) => {', 1)[1].split(
        'const sectionBtn = event.target.closest("[data-section]")', 1
    )[0]
    assert click_body.count("event.preventDefault()") == 2
    drawer_focus = app_js.split("function openAiTutorDrawer()", 1)[1].split(
        "function closeAiTutorDrawer()", 1
    )[0]
    assert "AI_DRAWER_FOCUS_DELAY_MS = 220" in app_js
    assert "window.clearTimeout(aiDrawerFocusTimer)" in drawer_focus
    assert "window.setTimeout" in drawer_focus
    assert "input.focus({ preventScroll: true })" in drawer_focus
    assert 'document.addEventListener("pointerdown"' in app_js


def test_ai_tutor_frontend_invalidates_stale_requests_and_caps_memory() -> None:
    app_js = (REPOSITORY / "learnctl" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    send_body = app_js.split("async function sendTutorQuestion()", 1)[1].split("function summarizeValidation", 1)[0]
    clear_body = app_js.split("const aiChatClear =", 1)[1].split("const catalogSearch =", 1)[0]

    assert "aiChatGenerations: {}" in app_js
    assert "aiChatPending: {}" in app_js
    assert "state.aiChatGenerations[key] !== requestGeneration" in send_body
    assert "aiChatKey() !== key" in send_body
    assert ".slice(-8)" in send_body
    assert "state.aiChatGenerations[key]" in clear_body
    assert "delete state.aiChatPending[key]" in clear_body
    assert 'input.value = ""' in clear_body


def test_ai_variation_id_binds_review_to_server_context(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []
    variation = {
        "title": "服务端绑定变式标题",
        "scenario": "服务端绑定变式场景",
        "instructions": "服务端绑定变式要求",
        "starter_content": "服务端绑定变式起始内容",
        "review_rubric": "服务端绑定变式评审标准",
    }
    review_result = {"summary": "总结", "strengths": ["a"], "issues": ["b"], "next_steps": ["c"]}
    responses = [variation, review_result]

    def fake_request(url, payload, api_key, timeout=60):
        prompts.append(payload["messages"][0]["content"])
        return 200, json.dumps({"choices": [{"message": {"content": json.dumps(responses.pop(0), ensure_ascii=False)}}]}).encode("utf-8")

    monkeypatch.setattr(ai, "_request", fake_request)
    status, generated, _ = request(web_server, "POST", "/api/ai/generate", {"task_id": "D02", "section_id": "D02-names"})
    assert status == 200
    variation_id = generated["variation_id"]
    assert isinstance(variation_id, str) and variation_id

    status, reviewed, _ = request(
        web_server,
        "POST",
        "/api/ai/review",
        {
            "task_id": "D02",
            "section_id": "D02-names",
            "variation_id": variation_id,
            "content": "我的代码",
            "variation": {"title": "客户端伪造标题", "instructions": "客户端伪造要求"},
        },
    )
    assert status == 200
    assert reviewed["review"] == review_result
    for value in variation.values():
        assert value in prompts[1]
    assert "客户端伪造标题" not in prompts[1]
    assert "客户端伪造要求" not in prompts[1]


def test_ai_variation_invalid_or_mismatched_id_never_falls_back(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    variation = {"title": "t", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        return 200, json.dumps({"choices": [{"message": {"content": json.dumps(variation)}}]}).encode("utf-8")

    monkeypatch.setattr(ai, "_request", fake_request)
    status, generated, _ = request(web_server, "POST", "/api/ai/generate", {"task_id": "D02", "section_id": "D02-names"})
    assert status == 200
    variation_id = generated["variation_id"]

    status, payload, _ = request(
        web_server,
        "POST",
        "/api/ai/review",
        {"task_id": "D02", "section_id": "D02-names", "variation_id": "missing-id", "content": "内容"},
    )
    assert status == 400
    assert payload["ok"] is False
    assert "不存在" in payload["error"]

    status, payload, _ = request(
        web_server,
        "POST",
        "/api/ai/review",
        {"task_id": "D02", "section_id": "D02-numbers", "variation_id": variation_id, "content": "内容"},
    )
    assert status == 400
    assert payload["ok"] is False
    assert "不匹配" in payload["error"]
    assert calls == 1


def test_ai_variation_id_is_lost_after_server_restart(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    variation = {"title": "t", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}
    monkeypatch.setattr(
        ai,
        "_request",
        lambda *a, **k: (200, json.dumps({"choices": [{"message": {"content": json.dumps(variation)}}]}).encode("utf-8")),
    )
    status, generated, _ = request(web_server, "POST", "/api/ai/generate", {"task_id": "D02", "section_id": "D02-names"})
    assert status == 200
    variation_id = generated["variation_id"]

    restarted = create_server(web_server.project_root, port=0)
    thread = threading.Thread(target=restarted.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload, _ = request(
            restarted,
            "POST",
            "/api/ai/review",
            {"task_id": "D02", "section_id": "D02-names", "variation_id": variation_id, "content": "内容"},
        )
    finally:
        restarted.shutdown()
        restarted.server_close()
        thread.join(timeout=2)
    assert status == 400
    assert payload["ok"] is False
    assert "不存在" in payload["error"]


def test_ai_error_returns_json_error(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (401, b'{"error":"unauthorized"}'))
    status, result, _ = request(web_server, "POST", "/api/ai/generate", {"task_id": "D02", "section_id": "D02-names"})
    assert status == 200
    assert result["ok"] is False
    assert "HTTP 401" in result["error"]


def test_exercise_run_returns_real_output(web_server: Any) -> None:
    tests_dir = web_server.project_root / "learner_tests"
    tests_dir.mkdir()
    (tests_dir / "passing.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    curriculum_path = web_server.project_root / "data" / "curriculum.json"
    data = json.loads(curriculum_path.read_text(encoding="utf-8"))
    exercise = next(item for item in data["exercises"] if item["id"] == "form")
    exercise["test_command"] = "python -m pytest -q learner_tests/passing.py"
    curriculum_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    status, result, _ = request(web_server, "POST", "/api/exercises/form/run", {})
    assert status == 200
    assert result["exit_code"] == 0
    progress = json.loads((web_server.project_root / ".learn" / "progress.json").read_text(encoding="utf-8"))
    assert progress["tests"]["form"]["exit_code"] == 0


def test_exercise_serializes_state_writes(web_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    tests_dir = web_server.project_root / "learner_tests"
    tests_dir.mkdir()
    (tests_dir / "passing.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    curriculum_path = web_server.project_root / "data" / "curriculum.json"
    data = json.loads(curriculum_path.read_text(encoding="utf-8"))
    exercise = next(item for item in data["exercises"] if item["id"] == "form")
    exercise["test_command"] = "python -m pytest -q learner_tests/passing.py"
    curriculum_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    started = threading.Event()
    release = threading.Event()
    state_write_waiting = threading.Event()
    original = web_server_module.run_exercise_capture

    class ObservableLock:
        def __init__(self, lock: Any) -> None:
            self.lock = lock

        def __enter__(self) -> "ObservableLock":
            if started.is_set() and not release.is_set():
                state_write_waiting.set()
            self.lock.acquire()
            return self

        def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
            self.lock.release()
            return False

    def slow_run(*args: Any, **kwargs: Any) -> dict:
        started.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(web_server_module, "run_exercise_capture", slow_run)
    web_server.state_lock = ObservableLock(web_server.state_lock)
    exercise_result: dict = {}
    module_result: dict = {}

    def run_exercise() -> None:
        exercise_result["response"] = request(web_server, "POST", "/api/exercises/form/run", {})

    def update_module() -> None:
        module_result["response"] = request(web_server, "POST", "/api/modules/py-basics/status", {"status": "practice"})

    exercise_thread = threading.Thread(target=run_exercise)
    exercise_thread.start()
    assert started.wait(timeout=5)
    module_thread = threading.Thread(target=update_module)
    module_thread.start()
    assert state_write_waiting.wait(timeout=5)
    release.set()
    exercise_thread.join(timeout=5)
    module_thread.join(timeout=5)

    assert exercise_result["response"][0] == 200
    assert exercise_result["response"][1]["exit_code"] == 0
    assert module_result["response"][0] == 200
    progress = json.loads((web_server.project_root / ".learn" / "progress.json").read_text(encoding="utf-8"))
    assert progress["tests"]["form"]["exit_code"] == 0
    assert progress["modules"]["py-basics"] == "practice"


def test_package_data_contains_static_assets() -> None:
    static_root = REPOSITORY / "learnctl" / "web" / "static"
    assert all((static_root / name).is_file() for name in ("index.html", "app.js", "styles.css"))
    pyproject = (REPOSITORY / "pyproject.toml").read_text(encoding="utf-8")
    assert 'learnctl = ["web/static/*.html", "web/static/*.js", "web/static/*.css"]' in pyproject


# ---------------------------------------------------------------------------
# 工作区 API
# ---------------------------------------------------------------------------

def test_workspace_tree_returns_declared_files(web_server: Any) -> None:
    status, data, _ = request(web_server, "GET", "/api/workspace")
    assert status == 200
    assert "files" in data
    files_by_path = {item["path"]: item for item in data["files"]}
    # D19-config 的 project_file 应为 taskproj/config.py
    assert "taskproj/config.py" in files_by_path


def test_workspace_file_whitelist_enforced(web_server: Any) -> None:
    # 未在课程中声明的路径被拒绝
    status, data, _ = request(web_server, "GET", "/api/workspace/files/../README.md")
    assert status == 400
    assert data["ok"] is False
    # 浏览器文件保存（PUT）同样受白名单约束：路径穿越与未声明路径一律拒绝
    for bad_path in ("../README.md", "learner_workspace/elsewhere.py", "taskproj/secret.py"):
        status, data, _ = request(web_server, "PUT", f"/api/workspace/files/{bad_path}", {"content": "x"})
        assert status == 400
        assert data["ok"] is False
    # 未声明的路径不得被 PUT 创建出来
    assert not (web_server.project_root / "learner_workspace" / "task-manager" / "taskproj" / "secret.py").exists()


def test_workspace_file_put_writes_and_reflects_in_tree(web_server: Any) -> None:
    # 浏览器“保存项目文件”所调用的 PUT 白名单接口：写入后文件树标记为已创建
    content = "import os\nfrom pathlib import Path\n\ndef get_db_path():\n    return Path(os.environ.get('TASKPROJ_DB', 'taskproj.db'))\n"
    status, result, _ = request(web_server, "PUT", "/api/workspace/files/taskproj/config.py", {"content": content})
    assert status == 200
    assert result["saved"] is True
    assert result["bytes"] == len(content.encode("utf-8"))
    ws_file = web_server.project_root / "learner_workspace" / "task-manager" / "taskproj" / "config.py"
    assert ws_file.read_text(encoding="utf-8") == content
    status, tree, _ = request(web_server, "GET", "/api/workspace")
    files_by_path = {item["path"]: item for item in tree["files"]}
    assert files_by_path["taskproj/config.py"]["exists"] is True


def test_workspace_file_read_write(web_server: Any) -> None:
    # 先通过验证写入文件，再通过 API 读取
    curriculum = load_curriculum(web_server.project_root / "data" / "curriculum.json")
    progress_path = web_server.project_root / ".learn" / "progress.json"
    state = load_progress(progress_path, curriculum)
    state["tasks"]["D18"] = {"status": "done", "evidence": ["测试准备"]}
    state["lesson_progress"]["D19"]["completed_sections"] = ["D19-pyproject", "D19-package"]
    package = web_server.project_root / "learner_workspace" / "task-manager" / "taskproj" / "__init__.py"
    package.parent.mkdir(parents=True, exist_ok=True)
    package.write_text("__version__ = '0.1.0'\n", encoding="utf-8")
    save_progress(progress_path, state)
    status, result, _ = request(
        web_server,
        "POST",
        "/api/tasks/D19/sections/D19-config/validate",
        {"content": "import os\nfrom pathlib import Path\n\ndef get_db_path():\n    return Path(os.environ.get('TASKPROJ_DB', 'taskproj.db'))\n\ndef get_int_env(name, default):\n    try:\n        return int(os.environ.get(name))\n    except (TypeError, ValueError):\n        return default\n"},
    )
    assert status == 200 and result["passed"] is True

    status, data, _ = request(web_server, "GET", "/api/workspace/files/taskproj/config.py")
    assert status == 200
    assert data["exists"] is True
    assert "def get_db_path" in data["content"]


def test_task_done_blocked_by_api_without_all_sections(web_server: Any) -> None:
    import copy
    from pathlib import Path as _Path

    from learnctl.curriculum import load_curriculum
    from learnctl.progress import load_progress, save_progress
    from learnctl.workflow import complete_section

    project_root = web_server.project_root
    # 复制 pyproject.toml 到临时项目目录，否则 install 等动作需要项目元数据
    repo = _Path(__file__).resolve().parents[1]
    import shutil as _shutil
    _shutil.copy2(str(repo / "pyproject.toml"), str(project_root / "pyproject.toml"))

    # 标记 D01 所有环境小节为已完成（因为在临时测试目录中，env action 无法完成完整安装）
    c = load_curriculum(project_root / "data" / "curriculum.json")
    progress_path = project_root / ".learn" / "progress.json"
    with web_server.state_lock:
        progress = load_progress(progress_path, c)
        for section_id in ["D01-onboarding", "D01-detect", "D01-create-venv", "D01-install", "D01-verify"]:
            complete_section(c, progress, progress_path, "D01", section_id)

    # 通过 API 验证 D01-onboarding 文本小节
    status_validate, result_validate, _ = request(
        web_server,
        "POST",
        "/api/tasks/D01/sections/D01-onboarding/validate",
        {"content": "今天我要配置 Python 开发环境：确认解释器版本，创建虚拟环境 venv，并用 pip 安装 pytest 依赖，最后验证工具可编辑安装。"},
    )
    assert status_validate == 200
    assert result_validate["passed"] is True

    # 标记 D01 done
    status, _, _ = request(web_server, "POST", "/api/tasks/D01/status", {"status": "done", "evidence": "环境验证完成"})
    assert status == 200

    # 尝试通过 API 标记 D02 done，但小节未完成 → 被拒绝
    status, data, _ = request(
        web_server,
        "POST",
        "/api/tasks/D02/status",
        {"status": "done", "evidence": "手动"},
    )
    assert status == 409
    assert data["ok"] is False
    assert "尚未通过全部必修小节验证" in data["error"]


def test_lesson_payload_includes_required_section_count(web_server: Any) -> None:
    status, task, _ = request(web_server, "GET", "/api/tasks/D02")
    assert status == 200
    lesson = task["task"]["lesson"]
    assert "required_sections" in lesson
    assert "required_completed" in lesson
    # D02 有 6 个必修语法小节，必须逐节验证
    assert lesson["required_sections"] == 6
    assert lesson["required_completed"] == 0  # 初始状态


# ---------------------------------------------------------------------------
# D18-D24 项目端到端：走公开 validate API 逐步落盘真实产物，直到 D24 验收
# ---------------------------------------------------------------------------

# 各小节真实产物内容（与 tool_tests/test_practice.py 的 GOOD 系列一致，抽到本地常量）
_GOOD_CONFIG = (
    "import os\nfrom pathlib import Path\n\n"
    "def get_db_path():\n    return Path(os.environ.get('TASKPROJ_DB', 'taskproj.db'))\n\n"
    "def get_int_env(name, default):\n"
    "    try:\n"
    "        return int(os.environ.get(name))\n"
    "    except (TypeError, ValueError):\n"
    "        return default\n"
)

_GOOD_DB = (
    "import sqlite3\n\n"
    "def create_connection(path):\n"
    "    conn = sqlite3.connect(str(path))\n"
    "    init_db(conn)\n"
    "    return conn\n\n"
    "def init_db(conn):\n"
    "    conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')\n"
    "    conn.commit()\n\n"
    "def add_task(conn, title):\n"
    "    cur = conn.execute('INSERT INTO tasks (title) VALUES (?)', (title,))\n"
    "    conn.commit()\n"
    "    return cur.lastrowid\n\n"
    "def list_tasks(conn):\n"
    "    rows = conn.execute('SELECT id, title, done FROM tasks ORDER BY id').fetchall()\n"
    "    return [{'id': r[0], 'title': r[1], 'done': bool(r[2])} for r in rows]\n\n"
    "def complete_task(conn, task_id):\n"
    "    conn.execute('UPDATE tasks SET done = 1 WHERE id = ?', (task_id,))\n"
    "    conn.commit()\n\n"
    "def delete_task(conn, task_id):\n"
    "    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))\n"
    "    conn.commit()\n"
)

_GOOD_API_FULL = (
    "from fastapi import FastAPI, HTTPException\n"
    "from fastapi.responses import FileResponse\n"
    "from pydantic import BaseModel\n"
    "from pathlib import Path\n"
    "from taskproj.db import add_task, complete_task, create_connection, delete_task, list_tasks\n"
    "from taskproj.config import get_db_path\n\n"
    "class TaskIn(BaseModel):\n    title: str\n\n"
    "class Task(BaseModel):\n    id: int\n    title: str\n    done: bool\n\n"
    "app = FastAPI()\n\n"
    "def _conn():\n    return create_connection(get_db_path())\n\n"
    "def _get_task_or_404(task_id: int):\n"
    "    conn = _conn()\n"
    "    rows = conn.execute('SELECT id FROM tasks WHERE id = ?', (task_id,)).fetchall()\n"
    "    if not rows:\n"
    "        raise HTTPException(status_code=404, detail='任务不存在')\n"
    "    return conn\n\n"
    "@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n\n"
    "@app.get('/')\ndef index():\n    return FileResponse(Path('taskproj/static/index.html'))\n\n"
    "@app.get('/api/tasks')\ndef read_tasks():\n    return list_tasks(_conn())\n\n"
    "@app.post('/api/tasks')\ndef create_task(task: TaskIn):\n"
    "    if not task.title.strip():\n"
    "        raise HTTPException(status_code=422, detail='标题不能为空')\n"
    "    conn = _conn()\n"
    "    tid = add_task(conn, task.title)\n"
    "    return next(t for t in list_tasks(conn) if t['id'] == tid)\n\n"
    "@app.patch('/api/tasks/{task_id}/done')\ndef complete(task_id: int):\n"
    "    conn = _get_task_or_404(task_id)\n"
    "    complete_task(conn, task_id)\n"
    "    return next(t for t in list_tasks(conn) if t['id'] == task_id)\n\n"
    "@app.delete('/api/tasks/{task_id}')\ndef remove(task_id: int):\n"
    "    conn = _get_task_or_404(task_id)\n"
    "    delete_task(conn, task_id)\n"
    "    return {'ok': True}\n"
)

_GOOD_CLI = (
    "import argparse\n"
    "from taskproj.db import add_task, complete_task, create_connection, delete_task, init_db, list_tasks\n"
    "from taskproj.config import get_db_path\n\n"
    "def main(argv=None):\n"
    "    parser = argparse.ArgumentParser()\n"
    "    sub = parser.add_subparsers(dest='command', required=True)\n"
    "    add = sub.add_parser('add')\n"
    "    add.add_argument('title')\n"
    "    sub.add_parser('list')\n"
    "    done = sub.add_parser('done')\n"
    "    done.add_argument('task_id', type=int)\n"
    "    rm = sub.add_parser('rm')\n"
    "    rm.add_argument('task_id', type=int)\n"
    "    args = parser.parse_args(argv)\n"
    "    conn = create_connection(get_db_path())\n"
    "    if args.command == 'add':\n"
    "        add_task(conn, args.title)\n"
    "    elif args.command == 'list':\n"
    "        for t in list_tasks(conn):\n"
    "            done_flag = '[done]' if t['done'] else '[]'\n"
    "            print(f\"{t['id']}. {t['title']} {done_flag}\")\n"
    "    elif args.command == 'done':\n"
    "        complete_task(conn, args.task_id)\n"
    "    elif args.command == 'rm':\n"
    "        delete_task(conn, args.task_id)\n"
    "    return 0\n\n"
    "if __name__ == '__main__':\n"
    "    raise SystemExit(main())\n"
)

_GOOD_MAIN = (
    "def main(argv=None):\n"
    "    print('任务管理项目已启动')\n"
    "    return 0\n\n"
    "if __name__ == '__main__':\n"
    "    raise SystemExit(main())\n"
)

_GOOD_PYPROJECT = (
    '[build-system]\nrequires = ["setuptools>=68"]\nbuild-backend = "setuptools.build_meta"\n\n'
    '[project]\nname = "taskproj"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'
    'dependencies = ["fastapi>=0.100", "uvicorn[standard]>=0.23", "pydantic>=2"]\n\n'
    '[project.optional-dependencies]\ndev = ["pytest>=8", "httpx>=0.24"]\n'
)

_GOOD_INDEX_HTML = (
    "<!doctype html>\n<html>\n<body>\n"
    '<input id="title" placeholder="新任务">\n<button id="add">添加</button>\n'
    "<ul id=\"list\"></ul>\n"
    "<script>\n"
    "fetch('/api/tasks').then(r => r.json()).then(items => {\n"
    "  items.forEach(t => {\n"
    "    const li = document.createElement('li');\n"
    "    li.textContent = t.title;\n"
    "    const done = document.createElement('button');\n"
    "    done.textContent = '完成';\n"
    "    done.onclick = () => fetch('/api/tasks/' + t.id + '/done', {method: 'PATCH'});\n"
    "    const del = document.createElement('button');\n"
    "    del.textContent = '删除';\n"
    "    del.onclick = () => fetch('/api/tasks/' + t.id, {method: 'DELETE'});\n"
    "    li.appendChild(done); li.appendChild(del);\n"
    "    document.getElementById('list').appendChild(li);\n"
    "  });\n"
    "});\n"
    "</script>\n"
    "</body>\n</html>\n"
)

_TEST_DB = (
    "import sqlite3\n"
    "from taskproj.db import init_db, add_task, list_tasks, complete_task, delete_task\n\n"
    "def test_crud(tmp_path):\n"
    "    conn = sqlite3.connect(str(tmp_path / 't.db'))\n"
    "    init_db(conn)\n"
    "    tid = add_task(conn, 'test')\n"
    "    assert list_tasks(conn)[0]['title'] == 'test'\n"
    "    complete_task(conn, tid)\n"
    "    assert list_tasks(conn)[0]['done'] is True\n"
    "    delete_task(conn, tid)\n"
    "    assert len(list_tasks(conn)) == 0\n"
)

_TEST_API = (
    "import os\n"
    "from fastapi.testclient import TestClient\n"
    "from taskproj.api import app\n\n"
    "client = TestClient(app)\n\n"
    "def test_health(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    resp = client.get('/api/tasks')\n"
    "    assert resp.status_code == 200\n"
    "    assert resp.json() == []\n\n"
    "def test_crud(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    resp = client.post('/api/tasks', json={'title': '买牛奶'})\n"
    "    assert resp.status_code == 200\n"
    "    task = resp.json()\n"
    "    assert task['title'] == '买牛奶'\n"
    "    assert task['done'] is False\n"
    "    tid = task['id']\n"
    "    assert any(t['id'] == tid for t in client.get('/api/tasks').json())\n"
    "    resp = client.patch(f'/api/tasks/{tid}/done')\n"
    "    assert resp.status_code == 200\n"
    "    assert client.get('/api/tasks').json()[0]['done'] is True\n"
    "    resp = client.delete(f'/api/tasks/{tid}')\n"
    "    assert resp.status_code == 200\n"
    "    assert client.get('/api/tasks').json() == []\n\n"
    "def test_404(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    assert client.patch('/api/tasks/999999/done').status_code == 404\n"
    "    assert client.delete('/api/tasks/999999').status_code == 404\n\n"
    "def test_422(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    assert client.post('/api/tasks', json={'title': ''}).status_code == 422\n"
)

# 按 D18-D24 课程顺序：每小节提交真实可通过内容，全部小节通过后再标该任务 done。
_PL_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("D18", [
        ("D18-scope", "## 用户故事与非目标\n\n实现一个本机任务管理应用，用 SQLite 持久化任务数据，提供 CLI 命令行与网页界面来管理任务；非目标是不做账号系统。"),
        ("D18-acceptance", "## 验收\n\n成功场景是新增、列表、完成、删除返回正确结果；失败场景包含空标题 422、未知 ID 404，逐项记录状态码和错误 detail。"),
        ("D18-data-contract", json.dumps({
            "task": {"id": 1, "title": "写需求", "done": False},
            "endpoints": [
                {"method": "GET", "path": "/api/tasks"},
                {"method": "POST", "path": "/api/tasks"},
                {"method": "PATCH", "path": "/api/tasks/{id}/done"},
                {"method": "DELETE", "path": "/api/tasks/{id}"},
            ],
        }, ensure_ascii=False)),
        ("D18-api-contract", json.dumps({
            "task": {"id": 1, "title": "写需求", "done": False},
            "endpoints": [
                {"method": "GET", "path": "/api/tasks"},
                {"method": "POST", "path": "/api/tasks"},
                {"method": "PATCH", "path": "/api/tasks/{id}/done"},
                {"method": "DELETE", "path": "/api/tasks/{id}"},
            ],
        }, ensure_ascii=False)),
    ]),
    ("D19", [
        ("D19-pyproject", _GOOD_PYPROJECT),
        ("D19-package", "# 任务管理本地包\n# __init__.py 暴露版本常量。\n__version__ = '0.1.0'\n"),
        ("D19-config", _GOOD_CONFIG),
        ("D19-main", _GOOD_MAIN),
        ("D19-readme", "# 任务管理\n\n安装：pip install -e .\n启动：uvicorn taskproj.api:app --host 127.0.0.1:8000\n"),
    ]),
    ("D20", [
        ("D20-connection", _GOOD_DB),
        ("D20-create-list", _GOOD_DB),
        ("D20-update-delete", _GOOD_DB),
        ("D20-db-tests", _TEST_DB),
    ]),
    ("D21", [
        ("D21-app", _GOOD_API_FULL),
        ("D21-schema", _GOOD_API_FULL),
        ("D21-crud-routes", _GOOD_API_FULL),
        ("D21-static", _GOOD_API_FULL),
    ]),
    ("D22", [
        ("D22-db-fixtures", _TEST_DB),
        ("D22-api-tests", _TEST_API),
        ("D22-api-errors", _TEST_API),
        ("D22-acceptance", _TEST_API),
    ]),
    ("D23", [
        ("D23-cli-parser", _GOOD_CLI),
        ("D23-cli-mutate", _GOOD_CLI),
        ("D23-html-structure", _GOOD_INDEX_HTML),
        ("D23-html-fetch", _GOOD_INDEX_HTML),
    ]),
    ("D24", [
        ("D24-rebuild", "python -m venv .venv\n.venv\\Scripts\\activate\npip install -e .\npytest\nuvicorn taskproj.api:app --reload\n"),
        ("D24-integrate", "## 集成\n\n启动 API 后用 CLI 新增任务，再在网页查看、完成和删除；pytest 通过后记录 API、CLI、网页的预期结果。"),
        ("D24-artifacts", "## 15 个文件\n\n对照 contract、runbook 清点 15 个真实文件、依赖链和验收输出，确认文件集合完整。"),
        ("D24-review", "## 复盘\n\n本次项目已交付，复用了数据库层，重建了 API 接口，并在复盘后改进界面。"),
    ]),
]


def test_project_learning_path_end_to_end(web_server: Any) -> None:
    """D18-D24 端到端：走公开 validate API 逐个落盘真实产物，每任务标 done，最终 D24 触发真实验收。"""
    from learnctl.curriculum import load_curriculum
    from learnctl.practice import validate_project_acceptance, _workspace_dir
    from learnctl.progress import initial_progress, save_progress

    project_root = web_server.project_root
    curriculum = load_curriculum(project_root / "data" / "curriculum.json")
    progress_path = project_root / ".learn" / "progress.json"

    # 在 state 中准备 D01-D17 done（前置阶段），不伪造 D18-D24 任何小节完成
    progress = initial_progress(curriculum)
    for task in curriculum["tasks"]:
        if int(task["id"][1:]) <= 17:
            progress["tasks"][task["id"]] = {"status": "done", "evidence": ["前置准备"]}
    save_progress(progress_path, progress)

    # 按课程顺序：逐小节 validate → 断言 completed + 产物落盘；每任务全部小节后标 done
    for task_id, sections in _PL_SECTIONS:
        for section_id, content in sections:
            status, result, _ = request(
                web_server,
                "POST",
                f"/api/tasks/{task_id}/sections/{section_id}/validate",
                {"content": content},
            )
            assert status == 200, f"{section_id} HTTP {status}: {result}"
            assert result["passed"] is True, f"{section_id} 未通过：{result.get('checks')}"
            assert result["completed"] is True, f"{section_id} 通过后未标记完成"
            section = next(s for s in next(t for t in curriculum["tasks"] if t["id"] == task_id)["lesson"] if s["id"] == section_id)
            project_file = section.get("practice", {}).get("project_file")
            if project_file:
                artifact = _workspace_dir(project_root) / project_file
                assert artifact.is_file(), f"{section_id} 产物未写入 {artifact}"
                assert artifact.read_text(encoding="utf-8") == content
        status, payload, _ = request(
            web_server,
            "POST",
            f"/api/tasks/{task_id}/status",
            {"status": "done", "evidence": f"{task_id} 全部小节验证通过"},
        )
        assert status == 200, f"{task_id} 标 done 失败 HTTP {status}: {payload}"
        assert payload["task"]["status"] == "done", f"{task_id} 未成功标为 done"

    # 最终断言 1：15 个唯一真实产物全部存在
    project_files = {
        section.get("practice", {}).get("project_file")
        for task in curriculum["tasks"]
        if task["id"] in {"D18", "D19", "D20", "D21", "D22", "D23", "D24"}
        for section in task["lesson"]
    }
    project_files.discard(None)
    assert len(project_files) == 15, f"唯一产物数应为 15，实际 {len(project_files)}"
    ws = _workspace_dir(project_root)
    for rel in project_files:
        assert (ws / rel).is_file(), f"产物缺失：{rel}"

    # 最终断言 2：GET /api/workspace 全部 exists
    status, tree, _ = request(web_server, "GET", "/api/workspace")
    assert status == 200
    files_by_path = {item["path"]: item for item in tree["files"]}
    for rel in project_files:
        assert rel in files_by_path, f"工作区树缺少 {rel}"
        assert files_by_path[rel]["exists"] is True, f"工作区 {rel} exists 应为 True"

    # 最终断言 3：progress D18-D24 均 done，且每任务 completed_sections 等于其课程小节
    final_progress = json.loads(progress_path.read_text(encoding="utf-8"))
    for task_id, sections in _PL_SECTIONS:
        assert final_progress["tasks"][task_id]["status"] == "done", f"{task_id} 未 done"
        expected = {section_id for section_id, _ in sections}
        completed = set(final_progress["lesson_progress"][task_id]["completed_sections"])
        assert completed == expected, f"{task_id} completed_sections 不符：{completed} != {expected}"

    # 最终断言 4：直接调用 validate_project_acceptance 仍 passed
    accept = validate_project_acceptance(project_root)
    assert accept["passed"] is True, (
        f"项目验收未通过：{[(c['name'], c['passed'], c.get('detail')) for c in accept['checks']]}"
    )

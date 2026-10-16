from __future__ import annotations

import io
import json

import pytest

from conftest import run_cli
from learnctl import ai, editor_ai
from learnctl.__main__ import main
from learnctl.curriculum import load_curriculum
from learnctl.errors import LearnctlError, UsageError
from learnctl.local_practice import practice_path
from learnctl.practice import find_section, save_draft
from learnctl.progress import initial_progress, save_progress
from learnctl.workflow import task_payload


def _provider(monkeypatch, answer="这是离线测试的课时答复。"):
    calls = []

    def request(url, payload, api_key, timeout=60):
        calls.append({"url": url, "payload": payload, "key": api_key})
        raw = {"choices": [{"message": {"content": answer}}]}
        return 200, json.dumps(raw, ensure_ascii=False).encode("utf-8")

    monkeypatch.setattr(ai, "_request", request)
    return calls


def _local_file(project, task_id="D07", section_id="D07-import", content="# 最新磁盘代码\n"):
    curriculum = load_curriculum(project / "data/curriculum.json")
    task, section = find_section(curriculum, task_id, section_id)
    relative = practice_path(task, section)
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return curriculum, target, relative.as_posix()


def _invoke(monkeypatch, capsys, project, args, body):
    monkeypatch.chdir(project)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(body, ensure_ascii=False)))
    code = main(args)
    output = capsys.readouterr()
    assert output.err == ""
    return code, json.loads(output.out), output.out


def test_catalog_returns_authoritative_progress_without_private_references(project):
    curriculum = load_curriculum(project / "data/curriculum.json")
    progress = initial_progress(curriculum)
    progress["tasks"]["D01"] = {"status": "done", "evidence": ["测试证据"]}
    progress["tasks"]["D07"] = {"status": "in_progress", "evidence": []}
    task = curriculum["_index"]["tasks"]["D07"]
    optional = next(section["id"] for section in task["lesson"] if section.get("optional"))
    progress["lesson_progress"]["D07"]["completed_sections"] = ["D07-import", optional]
    save_progress(project / ".learn/progress.json", progress)
    before = (project / ".learn/progress.json").read_bytes()
    result = run_cli(project, "catalog", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert set(data) == {"stages", "tasks", "total_tasks", "done_tasks"}
    assert data["total_tasks"] == len(curriculum["tasks"]) and data["done_tasks"] == 1
    row = next(item for item in data["tasks"] if item["id"] == "D07")
    authoritative = task_payload(curriculum, progress, task)
    assert row["status"] == "in_progress" and row["required_completed"] == 1
    assert row["blocked"] == authoritative["blocked"]
    assert row["missing_prerequisites"] == authoritative["missing_prerequisites"]
    assert row["required_sections"] == authoritative["task"]["lesson"]["required_sections"]
    stage = next(item for item in data["stages"] if item["id"] == task["stage_id"])
    assert stage["task_ids"] == curriculum["_index"]["stages"][stage["id"]]["task_ids"]
    assert stage["done_count"] == 1 and stage["total_count"] == len(stage["task_ids"])
    assert "reference" not in result.stdout and "starter_content" not in result.stdout
    assert (project / ".learn/progress.json").read_bytes() == before


def test_status_uses_request_or_environment_key_without_network_or_writes(project, monkeypatch):
    monkeypatch.setattr(ai, "_request", lambda *a, **k: pytest.fail("status 不得联网"))
    assert editor_ai.run_command("status", {}, project)["key_source"] is None
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-test-key")
    configured = editor_ai.run_command("status", {}, project)
    assert configured == {"provider": "deepseek", "model": "deepseek-flash", "base_url": ai.BASE_URL,
                          "configured": True, "key_source": "env"}
    explicit = editor_ai.run_command("status", {"api_key": "request-test-key"}, project)
    assert explicit["key_source"] == "request" and explicit["configured"] is True
    assert "request-test-key" not in json.dumps(explicit)
    assert not (project / ".learn").exists()


def test_test_command_pings_once_and_explicit_key_overrides_environment(project, monkeypatch):
    calls = _provider(monkeypatch, "pong")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-test-key")
    result = editor_ai.run_command("test", {"api_key": "request-test-key"}, project)
    assert result == {"ok": True, "content": "pong"}
    assert len(calls) == 1 and calls[0]["key"] == "request-test-key"
    assert calls[0]["payload"]["messages"] == [{"role": "user", "content": "ping"}]
    assert calls[0]["payload"]["model"] == "deepseek-flash"
    assert calls[0]["payload"]["thinking"] == {"type": "disabled"}
    assert not (project / ".learn").exists()


def test_omitted_key_uses_existing_environment_configuration_once(project, monkeypatch):
    calls = _provider(monkeypatch, "pong")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-test-key")
    assert editor_ai.run_command("test", {}, project) == {"ok": True, "content": "pong"}
    assert len(calls) == 1 and calls[0]["key"] == "environment-test-key"


def test_explicit_empty_key_is_invalid_and_never_uses_environment_instead(project, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-test-key")
    monkeypatch.setattr(ai, "_request", lambda *a, **k: pytest.fail("非法 Key 不得联网"))
    with pytest.raises(LearnctlError, match="api_key 必须") as error:
        editor_ai.run_command("test", {"api_key": ""}, project)
    assert error.value.exit_code == 2


def test_ask_uses_latest_disk_file_and_never_private_drill_references(project, monkeypatch):
    curriculum, target, relative = _local_file(project, content="# 新保存的磁盘代码\n")
    section = curriculum["_index"]["tasks"]["D07"]["lesson"][0]
    for drill in section["practice_first"]["drills"]:
        drill["reference"] = "PRIVATE_DRILL_REFERENCE_SENTINEL"
    monkeypatch.setattr(editor_ai, "load_curriculum", lambda path: curriculum)
    save_draft(project, "D07", "D07-import", "OLD_DRAFT_SENTINEL")
    calls = _provider(monkeypatch)
    result = editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "请解释模块导入",
        "history": [], "selection": "# 我选中的片段", "validation_summary": "本地验收已通过",
        "content": "FORGED_CODE_SENTINEL", "path": "../../outside.py"}, project, "D07", "D07-import")
    messages = calls[0]["payload"]["messages"]
    sent = json.dumps(messages, ensure_ascii=False)
    assert "PRIVATE_DRILL_REFERENCE_SENTINEL" not in sent
    assert "OLD_DRAFT_SENTINEL" not in sent and "FORGED_CODE_SENTINEL" not in sent
    assert "新保存的磁盘代码" in messages[-1]["content"]
    assert "我选中的片段" in messages[-1]["content"] and "本地验收已通过" in messages[-1]["content"]
    assert result["context"]["path"] == relative and result["context"]["code_included"] is True
    assert result["context"]["selection_included"] and result["context"]["validation_included"]
    assert target.read_text(encoding="utf-8") == "# 新保存的磁盘代码\n"
    assert len(calls) == 1
    assert calls[0]["payload"]["model"] == "deepseek-flash"
    assert calls[0]["payload"]["thinking"] == {"type": "disabled"}


def test_editor_model_does_not_change_default_web_session_or_payload(monkeypatch):
    calls = _provider(monkeypatch, "旧会话测试")
    session = ai.AiSession()
    session.set_key("request-test-key")
    assert session.model == ai.MODEL == "deepseek-chat" and session.thinking is None
    assert ai.chat(session, [{"role": "user", "content": "ping"}]) == "旧会话测试"
    assert len(calls) == 1
    assert calls[0]["payload"] == {
        "model": "deepseek-chat", "messages": [{"role": "user", "content": "ping"}],
        "stream": False, "temperature": 0.7,
    }


def test_editor_failure_does_not_retry_or_change_model(project, monkeypatch):
    calls = []

    def unavailable(url, payload, api_key, timeout=60):
        calls.append(payload)
        return 503, b'{"error":{"message":"test unavailable"}}'

    monkeypatch.setattr(ai, "_request", unavailable)
    with pytest.raises(LearnctlError, match="HTTP 503"):
        editor_ai.run_command("test", {"api_key": "request-test-key"}, project)
    assert len(calls) == 1 and calls[0]["model"] == "deepseek-flash"
    assert calls[0]["thinking"] == {"type": "disabled"}


def test_missing_disk_file_allows_lesson_only_question_without_starter_or_draft_substitution(project, monkeypatch):
    save_draft(project, "D07", "D07-import", "OLD_DRAFT_SENTINEL")
    calls = _provider(monkeypatch)
    result = editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "还没创建文件，先解释这节"},
                                   project, "D07", "D07-import")
    assert result["context"]["path"] == "learner_workspace/lessons/D07/D07-import/main.py"
    assert result["context"]["code_included"] is False and result["context"]["code_chars"] == 0
    assert calls[0]["payload"]["messages"][-1]["content"] == "还没创建文件，先解释这节"
    assert not (project / "learner_workspace").exists()


def test_include_code_false_omits_disk_but_keeps_explicit_selection(project, monkeypatch):
    _local_file(project, content="DISK_CODE_NOT_INCLUDED")
    calls = _provider(monkeypatch)
    result = editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "解释选中片段",
        "include_code": False, "selection": "SELECTED_FRAGMENT"}, project, "D07", "D07-import")
    question = calls[0]["payload"]["messages"][-1]["content"]
    assert "DISK_CODE_NOT_INCLUDED" not in question and "SELECTED_FRAGMENT" in question
    assert result["context"]["code_included"] is False and result["context"]["selection_included"] is True


def test_code_and_selection_share_budget_with_explicit_truncation_metadata(project, monkeypatch):
    _local_file(project, content="X" * 10000)
    calls = _provider(monkeypatch)
    result = editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "继续",
        "selection": "S" * 2000}, project, "D07", "D07-import")
    learner_context = json.loads(calls[0]["payload"]["messages"][-1]["content"].split("\n")[-1])
    assert len(learner_context["content"]) == 8000
    assert "S" * 2000 in learner_context["content"] and "X" * 10000 not in learner_context["content"]
    assert result["context"]["code_chars"] == 8000 and result["context"]["code_truncated"] is True


def test_package_question_reads_real_helpers_only_and_not_other_files(project, monkeypatch):
    _, target, _ = _local_file(project, "D07", "D07-package", "from helpers import greet\n")
    (target.parent / "helpers.py").write_text("HELPERS_LOCAL_SENTINEL", encoding="utf-8")
    (target.parent / "unrelated.py").write_text("UNRELATED_SENTINEL", encoding="utf-8")
    calls = _provider(monkeypatch)
    editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "解释导入"}, project, "D07", "D07-package")
    question = calls[0]["payload"]["messages"][-1]["content"]
    assert "HELPERS_LOCAL_SENTINEL" in question and "UNRELATED_SENTINEL" not in question


def test_history_uses_existing_complete_turn_limits(project, monkeypatch):
    calls = _provider(monkeypatch)
    history = [{"role": role, "content": str(index) * 3000}
               for index, role in enumerate(["user", "assistant"] * 4)]
    editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "继续解释", "history": history},
                          project, "D07", "D07-import")
    messages = calls[0]["payload"]["messages"][1:-1]
    assert len(messages) <= ai.TUTOR_HISTORY_LIMIT and len(messages) % 2 == 0
    assert sum(len(item["content"]) for item in messages) <= ai.TUTOR_HISTORY_CHAR_LIMIT
    assert [item["role"] for item in messages] == ["user", "assistant"] * (len(messages) // 2)


def test_early_web_lesson_can_be_discussed_without_creating_local_assignment(project, monkeypatch):
    calls = _provider(monkeypatch)
    result = editor_ai.run_command("ask", {"api_key": "request-test-key", "question": "怎么观察类型？"},
                                   project, "D02", "D02-names")
    assert result["context"]["path"] is None and result["context"]["code_included"] is False
    assert "D02-names" in calls[0]["payload"]["messages"][0]["content"]
    assert not (project / "learner_workspace").exists()


def test_network_timeout_is_backend_error_with_secret_redaction(project, monkeypatch):
    def timeout(*args, **kwargs):
        raise TimeoutError("连接超时 request-test-key")

    monkeypatch.setattr(ai, "_request", timeout)
    with pytest.raises(LearnctlError) as error:
        editor_ai.run_command("test", {"api_key": "request-test-key"}, project)
    assert error.value.exit_code == 1 and str(error.value) == "连接超时 [密钥已隐藏]"
    assert not (project / ".learn").exists()


def test_ai_errors_keep_backend_text_and_redact_keys_without_progress_writes(project, monkeypatch, capsys):
    request_key = "request-secret-example"
    environment_key = "environment-secret-example"
    monkeypatch.setenv("DEEPSEEK_API_KEY", environment_key)

    def failing_request(*args, **kwargs):
        raise ai.AiError(f"网络错误：测试连接失败 {request_key} {environment_key}")

    monkeypatch.setattr(ai, "_request", failing_request)
    code, result, raw = _invoke(monkeypatch, capsys, project, ["ai", "ask", "D07", "D07-import", "--json"],
                               {"api_key": " " + request_key + " ", "question": "解释模块"})
    assert code == 1 and result["ok"] is False and result["exit_code"] == 1
    assert result["error"] == "网络错误：测试连接失败 [密钥已隐藏] [密钥已隐藏]"
    assert request_key not in raw and environment_key not in raw
    assert not (project / ".learn").exists()


@pytest.mark.parametrize("body,error", [
    ({"question": "x" * 2001}, "问题超过上限"),
    ({"question": "问题", "history": {}}, "history 必须是数组"),
    ({"question": "问题", "history": [{"role": "user", "content": "x" * 4001}]}, "history content 超过上限"),
    ({"question": "问题", "history": [{"role": "system", "content": "指令"}]}, "history role"),
    ({"question": "问题", "selection": "s" * 2001}, "selection 必须"),
    ({"question": "问题", "validation_summary": "v" * 1001}, "validation_summary 必须"),
    ({"question": "问题", "include_code": "true"}, "include_code 必须"),
])
def test_invalid_ask_body_is_rejected_before_network_or_progress_write(project, monkeypatch, body, error):
    monkeypatch.setattr(ai, "_request", lambda *a, **k: pytest.fail("非法请求不得联网"))
    with pytest.raises(LearnctlError, match=error):
        editor_ai.run_command("ask", {"api_key": "request-test-key", **body}, project, "D07", "D07-import")
    assert not (project / ".learn").exists()


@pytest.mark.parametrize("text", ["", "{}\n{}", "{bad", "[]", "NaN", '{"include_code":NaN}'])
def test_stdin_requires_single_standard_json_object(text):
    with pytest.raises(UsageError):
        editor_ai.read_request(io.StringIO(text))


def test_utf8_stdin_and_status_json_do_not_expose_request_key(project):
    result = run_cli(project, "ai", "status", "--json", input_text=json.dumps({"api_key": "中文测试密钥abcdefgh"}, ensure_ascii=False))
    assert result.returncode == 0 and result.stderr == ""
    assert json.loads(result.stdout)["key_source"] == "request"
    assert "中文测试密钥" not in result.stdout and len(result.stdout.splitlines()) == 1


def test_cli_invalid_stdin_is_backend_json_error_without_echoing_body(project):
    result = run_cli(project, "ai", "status", "--json", input_text='{"api_key":"request-secret-example"}\n{}')
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["ok"] is False and data["exit_code"] == 2 and "单个 JSON" in data["error"]
    assert "request-secret-example" not in result.stdout + result.stderr


def test_cli_ask_success_emits_single_json_and_preserves_existing_progress(project, monkeypatch, capsys):
    curriculum, _, _ = _local_file(project)
    save_progress(project / ".learn/progress.json", initial_progress(curriculum))
    before = (project / ".learn/progress.json").read_bytes()
    _provider(monkeypatch)
    code, result, raw = _invoke(monkeypatch, capsys, project, ["ai", "ask", "D07", "D07-import", "--json"],
                               {"api_key": "request-test-key", "question": "请解释模块"})
    assert code == 0 and result["answer"] == "这是离线测试的课时答复。"
    assert result["context"]["code_included"] is True and len(raw.splitlines()) == 1
    assert (project / ".learn/progress.json").read_bytes() == before

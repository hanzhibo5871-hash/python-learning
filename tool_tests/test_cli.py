from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import REPOSITORY, run_cli


def _run_raw(project: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """在 Windows 默认环境（不设置 PYTHONIOENCODING/PYTHONUTF8）下运行 CLI，返回原始字节。"""
    environment = os.environ.copy()
    environment.pop("PYTHONIOENCODING", None)
    environment.pop("PYTHONUTF8", None)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(REPOSITORY) if not existing else os.pathsep.join((str(REPOSITORY), existing))
    return subprocess.run(
        [sys.executable, "-m", "learnctl", *args],
        cwd=project,
        env=environment,
        capture_output=True,
        check=False,
    )


def test_cli_json_output_is_strict_utf8_without_pythonioencoding(project: Path) -> None:
    """Windows 默认 GBK 控制台下，CLI 的 JSON 中文必须是有效 UTF-8 字节。"""
    result = _run_raw(project, "today", "--json")
    assert result.returncode == 0
    text = result.stdout.decode("utf-8")  # 严格解码，失败即回归
    payload = json.loads(text)
    assert "环境" in payload["task"]["title"]
    assert payload["task"]["id"] == "D01"


def test_cli_schema1_error_is_strict_utf8_without_pythonioencoding(project: Path) -> None:
    state_dir = project / ".learn"
    state_dir.mkdir()
    old = {"schema_version": 1, "curriculum_version": "1.0.0", "tasks": {}, "courses": {}}
    (state_dir / "progress.json").write_text(json.dumps(old), encoding="utf-8")

    result = _run_raw(project, "today", "--json")
    assert result.returncode == 3
    text = result.stdout.decode("utf-8")
    payload = json.loads(text)
    assert payload["ok"] is False
    assert "不支持自动迁移" in payload["error"]


def test_cli_bad_json_error_is_strict_utf8_without_pythonioencoding(project: Path) -> None:
    (project / "data" / "curriculum.json").write_text("{broken", encoding="utf-8")

    result = _run_raw(project, "today", "--json")
    assert result.returncode == 3
    text = result.stdout.decode("utf-8")
    payload = json.loads(text)
    assert "JSON 无效" in payload["error"]


def test_cli_missing_test_file_error_is_strict_utf8_without_pythonioencoding(project: Path) -> None:
    result = _run_raw(project, "test", "form")
    assert result.returncode == 3
    stderr = result.stderr.decode("utf-8")
    assert "测试文件不存在" in stderr


def test_initial_today_returns_d01_environment(curriculum_data: dict, project: Path) -> None:
    result = run_cli(project, "today", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    task = payload["task"]
    assert task["id"] == "D01"
    assert payload["blocked"] is False
    assert "环境" in task["title"]
    lesson = task["lesson"]
    assert lesson["total_sections"] == 5
    assert not (project / ".learn" / "progress.json").exists()


def test_lesson_directly_returns_blocked_task(curriculum_data: dict, project: Path) -> None:
    result = run_cli(project, "lesson", "D02", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert "D01" in payload["missing_tasks"]
    assert payload["task"]["id"] == "D02"


def test_done_requires_evidence_and_prerequisites(project: Path) -> None:
    no_evidence = run_cli(project, "progress", "mark", "D01", "--status", "done")
    assert no_evidence.returncode == 1
    assert "evidence" in no_evidence.stderr
    blocked = run_cli(project, "progress", "mark", "D09", "--status", "done", "--evidence", "手工验收")
    assert blocked.returncode == 1
    assert "D08" in blocked.stderr


def test_marking_in_order_advances_today(project: Path) -> None:
    # 可信完成机制要求所有必修小节先通过验证。先通过一次写操作创建进度文件，
    # 再直接注入已完成小节状态，最后测试任务标记。
    from learnctl.progress import initial_progress, save_progress
    from learnctl.curriculum import load_curriculum

    curriculum = load_curriculum(project / "data" / "curriculum.json")
    progress_path = project / ".learn" / "progress.json"
    state = initial_progress(curriculum)
    # 标记 D01 所有必修小节完成
    state["lesson_progress"]["D01"]["completed_sections"] = [
        "D01-onboarding", "D01-detect", "D01-create-venv", "D01-install", "D01-verify"
    ]
    # 标记 D02 所有必修小节完成
    state["lesson_progress"]["D02"]["completed_sections"] = [
        "D02-execution", "D02-names", "D02-numbers", "D02-bool-none", "D02-strings", "D02-string-methods"
    ]
    save_progress(progress_path, state)
    first = run_cli(project, "progress", "mark", "D01", "--status", "done", "--evidence", "环境验证通过")
    second = run_cli(project, "progress", "mark", "D02", "--status", "done", "--evidence", "本地验证通过")
    today = run_cli(project, "today", "--json")
    assert first.returncode == second.returncode == today.returncode == 0
    assert json.loads(today.stdout)["task"]["id"] == "D03"


def test_module_and_option_commands(project: Path) -> None:
    module = run_cli(project, "progress", "module", "py-basics", "--status", "practice")
    assert module.returncode == 0
    option = run_cli(project, "progress", "option", "langchain-cloud", "--enabled")
    assert option.returncode == 0
    state = json.loads((project / ".learn" / "progress.json").read_text(encoding="utf-8"))
    assert state["modules"]["py-basics"] == "practice"
    assert state["options"]["langchain-cloud"] is True


def test_unknown_ids_return_usage_error(project: Path) -> None:
    commands = [
        ("progress", "mark", "missing", "--status", "todo"),
        ("progress", "module", "missing", "--status", "learn"),
        ("progress", "option", "missing", "--enabled"),
        ("test", "missing"),
    ]
    for command in commands:
        result = run_cli(project, *command)
        assert result.returncode == 2


def test_progress_preserves_unknown_fields(project: Path) -> None:
    state_dir = project / ".learn"
    state_dir.mkdir()
    original = {
        "schema_version": 2,
        "curriculum_version": "2.1.0",
        "tasks": {"D01": {"status": "todo", "evidence": [], "note": "保留"}},
        "modules": {},
        "module_decisions": {},
        "options": {"langchain-cloud": False},
        "tests": {},
        "extension": {"owner": "user"},
    }
    (state_dir / "progress.json").write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    result = run_cli(project, "progress", "mark", "D01", "--status", "in_progress")
    saved = json.loads((state_dir / "progress.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert saved["extension"] == {"owner": "user"}
    assert saved["tasks"]["D01"]["note"] == "保留"


def test_schema_one_state_is_rejected(project: Path) -> None:
    state_dir = project / ".learn"
    state_dir.mkdir()
    old = {"schema_version": 1, "curriculum_version": "1.0.0", "tasks": {}, "courses": {}}
    (state_dir / "progress.json").write_text(json.dumps(old), encoding="utf-8")
    result = run_cli(project, "today", "--json")
    assert result.returncode == 3
    assert "不支持自动迁移" in json.loads(result.stdout)["error"]


def test_test_command_rejects_missing_learner_tests(project: Path) -> None:
    result = run_cli(project, "test", "form")
    assert result.returncode == 3
    assert "测试文件不存在" in result.stderr


def test_serve_rejects_non_loopback(project: Path) -> None:
    result = run_cli(project, "serve", "--host", "0.0.0.0", "--port", "8765")
    assert result.returncode == 2
    assert "127.0.0.1" in result.stderr

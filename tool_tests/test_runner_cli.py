from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import run_cli
from learnctl.errors import DataError
from learnctl.test_runner import run_exercise


def _set_form_target(project: Path, target: str) -> None:
    curriculum_path = project / "data" / "curriculum.json"
    data = json.loads(curriculum_path.read_text(encoding="utf-8"))
    exercise = next(item for item in data["exercises"] if item["id"] == "form")
    exercise["test_command"] = f"python -m pytest -q {target}"
    curriculum_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_success_exit_code_and_evidence_without_done(project: Path) -> None:
    tests_dir = project / "learner_tests"
    tests_dir.mkdir()
    (tests_dir / "passing.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _set_form_target(project, "learner_tests/passing.py")

    result = run_cli(project, "test", "form")
    state = json.loads((project / ".learn" / "progress.json").read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert state["tests"]["form"]["exit_code"] == 0
    assert state["tasks"]["D02"]["status"] == "todo"
    assert state["tasks"]["D02"]["evidence"]


def test_failure_preserves_pytest_exit_code_and_records_no_success(project: Path) -> None:
    tests_dir = project / "learner_tests"
    tests_dir.mkdir()
    (tests_dir / "failing.py").write_text("def test_no():\n    assert False\n", encoding="utf-8")
    _set_form_target(project, "learner_tests/failing.py")

    result = run_cli(project, "test", "form")

    assert result.returncode == 1
    assert not (project / ".learn" / "progress.json").exists()


def test_missing_learner_tests_target_fails(project: Path) -> None:
    _set_form_target(project, "learner_tests")

    result = run_cli(project, "test", "form")

    assert result.returncode == 3
    assert not (project / ".learn" / "progress.json").exists()


def test_success_preserves_existing_test_record_fields(project: Path) -> None:
    tests_dir = project / "learner_tests"
    tests_dir.mkdir()
    (tests_dir / "passing.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _set_form_target(project, "learner_tests/passing.py")
    state_dir = project / ".learn"
    state_dir.mkdir()
    state = {
        "schema_version": 2,
        "curriculum_version": "2.1.0",
        "tasks": {},
        "modules": {},
        "module_decisions": {},
        "options": {"langchain-cloud": False},
        "tests": {"form": {"owner_note": "保留"}},
    }
    (state_dir / "progress.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    result = run_cli(project, "test", "form")
    saved = json.loads((state_dir / "progress.json").read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert saved["tests"]["form"]["owner_note"] == "保留"


@pytest.mark.parametrize("option", ["--version", "--collect-only", "--setup-only", "--setup-plan", "-h", "--"])
def test_runner_rejects_options_without_execution_or_state(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    option: str,
) -> None:
    called = False

    def unexpected_run(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("learnctl.test_runner.subprocess.run", unexpected_run)
    exercise = {
        "id": "bypass",
        "task_id": "D02",
        "test_command": f"python -m pytest {option} learner_tests/test_form.py",
    }

    with pytest.raises(DataError, match="不允许 pytest 选项"):
        run_exercise(
            exercise,
            project,
            {"tasks": {}, "tests": {}},
            project / ".learn" / "progress.json",
            verbose=False,
        )
    assert called is False
    assert not (project / ".learn" / "progress.json").exists()

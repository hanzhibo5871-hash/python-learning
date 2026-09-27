from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from learnctl.diagnostic import collect_answers, load_answers, persist_diagnostic, run_diagnostics
from learnctl.errors import BlockedError


def _answers() -> dict:
    return {
        "D1": {"convert_input": "12.5", "format_output": "007-PY"},
        "D2": {"filter_loop": "[1, 3, 5]", "boundary_case": "[2, 4, 6]"},
        "D3": {"transform_dicts": '[{"name":"a","score":4}]', "group_and_count": '{"a":2,"b":1}'},
        "D4": {"read_utf8": "utf-8", "missing_path_error": "FileNotFoundError"},
        "D5": {"navigate_files": "a/b.txt", "pipe_and_redirect": "HELLO"},
    }


def test_run_diagnostics_with_mocked_d0(tmp_path: Path, curriculum_data: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    import learnctl.diagnostic as diagnostic

    def fake_d0() -> dict:
        return {
            "python_version": (True, "Python 3.11"),
            "venv_create": (True, "venv 可创建"),
            "pip_in_venv": (True, "pip 可运行"),
        }

    monkeypatch.setattr(diagnostic, "_run_d0", fake_d0)
    collected = collect_answers(
        curriculum_data,
        _answers(),
        prompt_stream=io.StringIO(),
        input_stream=io.StringIO(),
    )
    report = run_diagnostics(curriculum_data, collected, {"langchain-cloud": False})
    assert [item["id"] for item in report["diagnostics"]] == ["D0", "D1", "D2", "D3", "D4", "D5"]
    assert all(item["passed"] for item in report["diagnostics"])
    assert report["module_decisions"]["py-basics"]["status"] == "mastered"


def test_diagnose_no_longer_auto_completes_d01(tmp_path: Path, curriculum_data: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    import learnctl.diagnostic as diagnostic
    from learnctl.progress import initial_progress, task_status

    monkeypatch.setattr(diagnostic, "_run_d0", lambda: {
        "python_version": (True, "Python 3.11"),
        "venv_create": (True, "ok"),
        "pip_in_venv": (True, "ok"),
    })
    report_path = tmp_path / ".learn" / "diagnostic-report.json"
    progress_path = tmp_path / ".learn" / "progress.json"
    state = initial_progress(curriculum_data)
    collected = collect_answers(curriculum_data, _answers(), prompt_stream=io.StringIO(), input_stream=io.StringIO())
    report = run_diagnostics(curriculum_data, collected, state["options"])
    persist_diagnostic(report, curriculum_data, state, report_path, progress_path)
    assert report_path.is_file()
    assert task_status(state, "D01") == "todo", "诊断不再自动完成 D01"


def test_diagnose_scoring_and_no_reference_leak(curriculum_data: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    import learnctl.diagnostic as diagnostic

    monkeypatch.setattr(diagnostic, "_run_d0", lambda: {
        "python_version": (True, "Python 3.11"),
        "venv_create": (True, "ok"),
        "pip_in_venv": (True, "ok"),
    })
    answers = _answers()
    answers["D3"]["transform_dicts"] = "错误答案"
    collected = collect_answers(curriculum_data, answers, prompt_stream=io.StringIO(), input_stream=io.StringIO())
    report = run_diagnostics(curriculum_data, collected, {"langchain-cloud": False})
    d3 = next(item for item in report["diagnostics"] if item["id"] == "D3")
    assert d3["score"] == 50
    assert d3["critical_passed"] is False
    serialized = json.dumps(report, ensure_ascii=False)
    assert "score\":4" not in serialized


def test_missing_answer_is_explicit_error(curriculum_data: dict) -> None:
    answers = _answers()
    del answers["D4"]["read_utf8"]
    with pytest.raises(BlockedError, match="D4.read_utf8"):
        collect_answers(curriculum_data, answers, prompt_stream=io.StringIO(), input_stream=io.StringIO())


def test_load_answers_validates_shape(tmp_path: Path) -> None:
    path = tmp_path / "answers.json"
    path.write_text(json.dumps({"D9": {"x": "y"}}), encoding="utf-8")
    from learnctl.errors import DataError

    with pytest.raises(DataError, match="未知诊断"):
        load_answers(path)

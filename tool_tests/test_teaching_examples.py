from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import run_cli
from learnctl.curriculum import load_curriculum
from learnctl.errors import UsageError
from learnctl.experiments import run_experiment
from learnctl.practice import find_section
from learnctl.teaching_examples import prepare_example


@pytest.fixture
def course():
    return load_curriculum(Path("data/curriculum.json"))


@pytest.mark.parametrize("source", ["card", "example"])
def test_prepare_copies_only_declared_public_code(course, tmp_path, source):
    _, section = find_section(course, "D07", "D07-import")
    item = section["examples"][0] if source == "example" else section["practice_first"]["cards"][0]
    public_code = item["code"]
    section["practice"]["starter_content"] = "PRIVATE_STARTER"
    section["practice"]["reference"] = "PRIVATE_ANSWER"
    for drill in section.get("practice_first", {}).get("drills", []):
        drill["reference"] = "PRIVATE_DRILL_REFERENCE"
    result = prepare_example(course, "D07", "D07-import", source, 0, tmp_path)
    assert result == {
        "path": f"learner_workspace/examples/D07/D07-import/{source}-1.py",
        "created": True,
        "content": public_code,
    }
    assert (tmp_path / result["path"]).read_text(encoding="utf-8") == public_code
    assert "PRIVATE" not in json.dumps(result)
    assert not (tmp_path / ".learn").exists()


def test_prepare_preserves_learner_changes(course, tmp_path):
    first = prepare_example(course, "D07", "D07-import", "example", 1, tmp_path)
    target = tmp_path / first["path"]
    target.write_text("# 我修改的教学代码\nprint('继续试跑')\n", encoding="utf-8")
    second = prepare_example(course, "D07", "D07-import", "example", 1, tmp_path)
    assert second == {
        "path": "learner_workspace/examples/D07/D07-import/example-2.py",
        "created": False,
        "content": "# 我修改的教学代码\nprint('继续试跑')\n",
    }
    assert target.read_text(encoding="utf-8") == second["content"]


def test_prepare_does_not_run_code_or_create_progress(course, tmp_path):
    _, section = find_section(course, "D07", "D07-import")
    section["examples"][0]["code"] = "raise RuntimeError('prepare must never execute code')\n"
    result = prepare_example(course, "D07", "D07-import", "example", 0, tmp_path)
    assert result["created"] is True
    assert not (tmp_path / ".learn").exists()


@pytest.mark.parametrize("source", ["drill", "", None, []])
def test_invalid_source_has_explicit_error(course, tmp_path, source):
    with pytest.raises(UsageError, match="来源必须"):
        prepare_example(course, "D07", "D07-import", source, 0, tmp_path)
    assert not (tmp_path / "learner_workspace").exists()


@pytest.mark.parametrize("index", [-1, True, False, 0.5, "0", None])
def test_invalid_index_has_explicit_error(course, tmp_path, index):
    with pytest.raises(UsageError, match="非负整数"):
        prepare_example(course, "D07", "D07-import", "example", index, tmp_path)


def test_missing_index_has_explicit_error(course, tmp_path):
    with pytest.raises(UsageError, match="编号不存在"):
        prepare_example(course, "D07", "D07-import", "example", 99, tmp_path)


@pytest.mark.parametrize("task_id,section_id", [("D18", "D18-scope"), ("D21", "D21-app")])
def test_file_fragments_are_not_prepared_as_python(course, tmp_path, task_id, section_id):
    with pytest.raises(UsageError, match="可独立运行"):
        prepare_example(course, task_id, section_id, "example", 0, tmp_path)
    assert not (tmp_path / "learner_workspace").exists()


def test_runnable_metadata_must_be_explicit(course, tmp_path):
    _, section = find_section(course, "D07", "D07-import")
    section["examples"][0]["runnable"] = 1
    with pytest.raises(UsageError, match="可独立运行"):
        prepare_example(course, "D07", "D07-import", "example", 0, tmp_path)


def test_missing_code_never_uses_assignment_starter(course, tmp_path):
    _, section = find_section(course, "D07", "D07-import")
    section["examples"][0].pop("code")
    with pytest.raises(UsageError, match="代码不能为空"):
        prepare_example(course, "D07", "D07-import", "example", 0, tmp_path)


def test_path_must_remain_under_examples_directory(course, tmp_path):
    task, section = find_section(course, "D07", "D07-import")
    bad_course = copy.deepcopy(course)
    bad_task = copy.deepcopy(task)
    bad_task["id"] = "../outside"
    bad_course["_index"]["tasks"]["../outside"] = bad_task
    with pytest.raises(UsageError, match="路径穿越"):
        prepare_example(bad_course, "../outside", section["id"], "example", 0, tmp_path)
    assert not (tmp_path / "learner_workspace").exists()


def test_cli_allows_knowledge_preview_without_reading_or_writing_progress(project):
    progress_path = project / ".learn/progress.json"
    progress_path.parent.mkdir()
    original = b"invalid progress must not be loaded or overwritten"
    progress_path.write_bytes(original)
    result = run_cli(project, "example", "prepare", "D07", "D07-import",
                     "--source", "card", "--index", "0", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert set(payload) == {"path", "created", "content"}
    assert payload["created"] is True
    assert "print" in payload["content"]
    assert progress_path.read_bytes() == original


def test_cli_unrunnable_example_returns_backend_json_error(project):
    result = run_cli(project, "example", "prepare", "D21", "D21-app",
                     "--source", "example", "--index", "0", "--json")
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False and payload["exit_code"] == 2
    assert "可独立运行" in payload["error"]
    assert not (project / ".learn").exists()
    assert not (project / "learner_workspace").exists()


@pytest.mark.parametrize("source,index", [("card", 0), ("example", 1)])
@pytest.mark.parametrize("same_cwd", [False, True], ids=["different-cwd", "script-cwd"])
def test_labels_example_runs_real_saved_file_without_changing_assignment_or_progress(
    course, tmp_path, source, index, same_cwd,
):
    # 真实文件执行时 Python 从脚本所在目录导入，与终端工作目录无关。
    kept_files = {
        ".learn/progress.json": '{"learner": "keep progress"}',
        "learner_workspace/lessons/D07/D07-package/main.py": "# 我的正式作业\n",
        "learner_workspace/lessons/D07/D07-package/helpers.py": "# 我的教学夹具\n",
    }
    for name, content in kept_files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    before = {name: (tmp_path / name).read_bytes() for name in kept_files}
    prepared = prepare_example(course, "D07", "D07-package", source, index, tmp_path)
    script = tmp_path / prepared["path"]
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent if same_cwd else tmp_path,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "快跑!\n"
    labels = script.with_name("labels.py")
    assert labels.read_text(encoding="utf-8") == "def emphasize(text):\n    return text + '!'\n"
    assert b"\\n" not in labels.read_bytes()
    assert not (tmp_path / "labels.py").exists()
    for name, original in before.items():
        assert (tmp_path / name).read_bytes() == original


def test_labels_example_also_runs_with_documented_manual_filename(course, tmp_path):
    _, section = find_section(course, "D07", "D07-package")
    directory = tmp_path / "my_examples"
    directory.mkdir()
    script = directory / "import_example.py"
    script.write_text(section["examples"][1]["code"], encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "快跑!\n"
    assert script.with_name("labels.py").is_file()
    assert not (tmp_path / "labels.py").exists()
    assert not (tmp_path / ".learn").exists()
    assert not (tmp_path / "learner_workspace").exists()


@pytest.mark.parametrize("source,index", [("card", 0), ("example", 1)])
def test_labels_example_still_runs_in_web_experiment_real_file(course, source, index):
    _, section = find_section(course, "D07", "D07-package")
    result = run_experiment(section, {"mode": source, "index": index})
    assert result["passed"], result
    assert result["stdout"].replace("\r\n", "\n") == "快跑!\n"
    assert result["completed"] is False


def test_labels_card_example_and_drill_share_the_same_file_location_instruction(course):
    _, section = find_section(course, "D07", "D07-package")
    card = section["practice_first"]["cards"][0]
    example = section["examples"][1]
    drill = next(item for item in section["practice_first"]["drills"] if item["id"] == "prep-module-import")
    assert card["code"] == example["code"] == drill["reference"]
    assert drill["starter"].replace(
        "emphasize = None  # TODO：从labels导入emphasize", "from labels import emphasize",
    ) == drill["reference"]
    for code in (card["code"], drill["starter"]):
        assert code.startswith("from pathlib import Path\n")
        assert "Path(__file__).with_name('labels.py')" in code
        assert "sys.path" not in code
    for text in (card["rule"], example["explanation"], drill["instructions"]):
        assert "import_example.py" in text and "插件生成" in text
        assert "helpers.py" in text


@pytest.mark.parametrize("source,index", [("card", 0), ("example", 1)])
def test_pathlib_teaching_file_can_run_repeatedly(course, tmp_path, source, index):
    _, section = find_section(course, "D08", "D08-pathlib")
    item = section["practice_first"]["cards"][index] if source == "card" else section["examples"][index]
    prepared = prepare_example(course, "D08", "D08-pathlib", source, index, tmp_path)
    script = tmp_path / prepared["path"]
    # 同一学习文件保留目录产物，第二次实际运行仍应得到公开的教学输出。
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(script)], cwd=tmp_path,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.rstrip("\n") == item["output"]
    assert not (tmp_path / ".learn").exists()
    assert not (tmp_path / "learner_workspace/lessons").exists()

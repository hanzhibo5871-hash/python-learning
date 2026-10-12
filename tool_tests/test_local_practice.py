from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import request, run_cli
from learnctl import local_practice
from learnctl.curriculum import load_curriculum
from learnctl.errors import BlockedError, UsageError
from learnctl.practice import find_section, load_draft, save_draft
from learnctl.progress import initial_progress, save_progress, task_status


@pytest.fixture
def course():
    return load_curriculum(Path("data/curriculum.json"))


def _unlocked(course, task_id, section_id):
    progress = initial_progress(course)
    progress["tasks"] = {task["id"]: {"status": "done", "evidence": []} for task in course["tasks"]}
    progress["tasks"][task_id]["status"] = "in_progress"
    task, _ = find_section(course, task_id, section_id)
    ids = [section["id"] for section in task["lesson"]]
    progress["lesson_progress"][task_id]["completed_sections"] = ids[:ids.index(section_id)]
    return progress


def test_paths_use_lessons_or_declared_project_file(course):
    task, section = find_section(course, "D07", "D07-package")
    assert local_practice.practice_path(task, section).as_posix() == "learner_workspace/lessons/D07/D07-package/main.py"
    task, section = find_section(course, "D20", "D20-db-tests")
    assert local_practice.practice_path(task, section).as_posix() == "learner_workspace/lessons/D20/D20-db-tests/tests/test_project.py"
    task, section = find_section(course, "D28", "D28-review")
    assert local_practice.practice_path(task, section).name == "review.md"
    task, section = find_section(course, "D19", "D19-config")
    assert local_practice.practice_path(task, section).as_posix() == "learner_workspace/task-manager/taskproj/config.py"


def test_prepare_keeps_existing_local_file_and_teaching_fixture(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-package")
    first = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    target = tmp_path / first["path"]
    fixture = target.parent / "helpers.py"
    assert first["created"] and first["source"] == "starter"
    assert "def greet(name)" in fixture.read_text(encoding="utf-8")
    target.write_text("# 编辑器里的代码\n", encoding="utf-8")
    fixture.write_text("# 学习者修改的教学文件\n", encoding="utf-8")
    save_draft(tmp_path, "D07", "D07-package", "# 旧网页草稿\n")
    second = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    assert second["created"] is False and second["source"] == "local"
    assert second["content"] == "# 编辑器里的代码\n"
    assert fixture.read_text(encoding="utf-8") == "# 学习者修改的教学文件\n"


def test_prepare_uses_starter_and_keeps_old_web_draft(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-import")
    save_draft(tmp_path, "D07", "D07-import", "# 学习者网页草稿\n")
    result = local_practice.prepare_practice(course, progress, "D07", "D07-import", tmp_path)
    _, section = find_section(course, "D07", "D07-import")
    assert result["created"] and result["source"] == "starter"
    assert (tmp_path / result["path"]).read_text(encoding="utf-8") == section["practice"]["starter_content"]
    assert load_draft(tmp_path, "D07", "D07-import")["content"] == "# 学习者网页草稿\n"


def test_prepare_does_not_overwrite_file_created_during_publication(course, tmp_path, monkeypatch):
    progress = _unlocked(course, "D07", "D07-import")
    task, section = find_section(course, "D07", "D07-import")
    target = tmp_path / local_practice.practice_path(task, section)
    original_write = local_practice.atomic_write_text

    def competing_write(path, content):
        original_write(path, content)
        target.write_text("# 另一进程已准备\n", encoding="utf-8")

    monkeypatch.setattr(local_practice, "atomic_write_text", competing_write)
    result = local_practice.prepare_practice(course, progress, "D07", "D07-import", tmp_path)
    assert result["created"] is False and result["source"] == "local"
    assert result["content"] == "# 另一进程已准备\n"


@pytest.mark.parametrize("operation", ["prepare", "check"])
def test_locked_sections_cannot_prepare_or_check(course, tmp_path, operation):
    progress = initial_progress(course)
    with pytest.raises(BlockedError, match="前置"):
        if operation == "prepare":
            local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
        else:
            local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert not (tmp_path / "learner_workspace").exists()


def test_local_practice_starts_at_d07(course, tmp_path):
    progress = _unlocked(course, "D06", "D06-with")
    with pytest.raises(UsageError, match="D07"):
        local_practice.prepare_practice(course, progress, "D06", "D06-with", tmp_path)


def test_failed_file_is_saved_as_draft_without_completion(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-package")
    prepared = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    (tmp_path / prepared["path"]).write_text("value = 1\n", encoding="utf-8")
    result = local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert result["passed"] is False
    assert "D07-package" not in progress["lesson_progress"]["D07"]["completed_sections"]
    assert load_draft(tmp_path, "D07", "D07-package")["content"] == "value = 1\n"


def test_passed_file_completes_section_but_not_task(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-package")
    prepared = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    content = "from helpers import greet\n"
    (tmp_path / prepared["path"]).write_text(content, encoding="utf-8")
    result = local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert result["passed"] is True
    assert result["content"] == content and result["path"] == prepared["path"]
    assert "D07-package" in result["lesson_progress"]["completed_sections"]
    assert task_status(progress, "D07") == "in_progress"
    assert load_draft(tmp_path, "D07", "D07-package")["content"] == content


def test_local_teaching_file_behavior_is_validated_and_never_replaced(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-package")
    prepared = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    target = tmp_path / prepared["path"]
    target.write_text("from helpers import greet\n", encoding="utf-8")
    fixture = target.parent / "helpers.py"
    changed = "def greet(name):\n    return '错误输出'\n"
    fixture.write_text(changed, encoding="utf-8")
    result = local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert result["passed"] is False
    assert "D07-package" not in progress["lesson_progress"]["D07"]["completed_sections"]
    assert fixture.read_text(encoding="utf-8") == changed


def test_missing_local_teaching_file_cannot_use_hidden_template(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-package")
    prepared = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    target = tmp_path / prepared["path"]
    target.write_text("from helpers import greet\n", encoding="utf-8")
    (target.parent / "helpers.py").unlink()
    with pytest.raises(BlockedError, match="教学文件不存在"):
        local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert "D07-package" not in progress["lesson_progress"]["D07"]["completed_sections"]


def test_project_sections_continue_same_file(course, tmp_path):
    progress = _unlocked(course, "D20", "D20-connection")
    first = local_practice.prepare_practice(course, progress, "D20", "D20-connection", tmp_path)
    (tmp_path / first["path"]).write_text("# 上一节的数据库代码\n", encoding="utf-8")
    progress["lesson_progress"]["D20"]["completed_sections"].append("D20-connection")
    second = local_practice.prepare_practice(course, progress, "D20", "D20-create-list", tmp_path)
    assert second["path"] == first["path"]
    assert second["created"] is False and second["content"] == "# 上一节的数据库代码\n"


def test_missing_continued_file_is_not_replaced_by_starter_or_draft(course, tmp_path):
    progress = _unlocked(course, "D20", "D20-create-list")
    save_draft(tmp_path, "D20", "D20-create-list", "# 旧网页草稿\n")
    with pytest.raises(BlockedError, match="续编文件不存在"):
        local_practice.prepare_practice(course, progress, "D20", "D20-create-list", tmp_path)
    assert not (tmp_path / "learner_workspace/task-manager/taskproj/db.py").exists()


@pytest.mark.parametrize("field,value", [("project_file", "../../outside.py"), ("file_name", "../../outside.py"), ("file_name", "C:/outside.py")])
def test_paths_reject_traversal_and_absolute_paths(course, field, value):
    task, section = find_section(course, "D07", "D07-import")
    section = {**section, "practice": {**section["practice"], field: value}}
    with pytest.raises(UsageError):
        local_practice.practice_path(task, section)


def test_missing_file_never_uses_web_draft(course, tmp_path):
    progress = _unlocked(course, "D07", "D07-package")
    save_draft(tmp_path, "D07", "D07-package", "from helpers import greet\n")
    with pytest.raises(BlockedError, match="文件不存在"):
        local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert "D07-package" not in progress["lesson_progress"]["D07"]["completed_sections"]


def test_file_changed_during_validation_cannot_complete_or_save_old_draft(course, tmp_path, monkeypatch):
    progress = _unlocked(course, "D07", "D07-package")
    prepared = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    target = tmp_path / prepared["path"]
    target.write_text("from helpers import greet\n", encoding="utf-8")

    def changing_validator(*args, **kwargs):
        assert kwargs["write_artifact"] is False
        target.write_text("# 刚保存的新版本\n", encoding="utf-8")
        return {"passed": True, "checks": []}

    monkeypatch.setattr(local_practice, "run_validation", changing_validator)
    with pytest.raises(BlockedError, match="发生变化"):
        local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert "D07-package" not in progress["lesson_progress"]["D07"]["completed_sections"]
    assert load_draft(tmp_path, "D07", "D07-package") is None
    assert target.read_text(encoding="utf-8") == "# 刚保存的新版本\n"


def test_teaching_file_changed_during_validation_cannot_complete(course, tmp_path, monkeypatch):
    progress = _unlocked(course, "D07", "D07-package")
    prepared = local_practice.prepare_practice(course, progress, "D07", "D07-package", tmp_path)
    target = tmp_path / prepared["path"]
    target.write_text("from helpers import greet\n", encoding="utf-8")
    fixture = target.parent / "helpers.py"

    def changing_validator(*args, **kwargs):
        assert kwargs["support_files"]["helpers.py"] == fixture.read_text(encoding="utf-8")
        fixture.write_text("# 刚保存的新版本\n", encoding="utf-8")
        return {"passed": True, "checks": []}

    monkeypatch.setattr(local_practice, "run_validation", changing_validator)
    with pytest.raises(BlockedError, match="教学文件在检查期间发生变化"):
        local_practice.check_practice(course, progress, tmp_path / ".learn/progress.json", "D07", "D07-package", tmp_path)
    assert "D07-package" not in progress["lesson_progress"]["D07"]["completed_sections"]
    assert load_draft(tmp_path, "D07", "D07-package") is None


def test_cli_prepare_and_check_json_and_exit_codes(course, project):
    progress = _unlocked(course, "D07", "D07-package")
    save_progress(project / ".learn/progress.json", progress)
    prepared = run_cli(project, "practice", "prepare", "D07", "D07-package", "--json")
    assert prepared.returncode == 0
    path = project / json.loads(prepared.stdout)["path"]
    path.write_text("value = 1\n", encoding="utf-8")
    failed = run_cli(project, "practice", "check", "D07", "D07-package", "--json")
    assert failed.returncode == 1 and json.loads(failed.stdout)["passed"] is False
    path.write_text("from helpers import greet\n", encoding="utf-8")
    passed = run_cli(project, "practice", "check", "D07", "D07-package", "--json")
    assert passed.returncode == 0 and json.loads(passed.stdout)["passed"] is True
    saved = json.loads((project / ".learn/progress.json").read_text(encoding="utf-8"))
    assert saved["tasks"]["D07"]["status"] == "in_progress"


def test_cli_missing_local_file_reports_blocked_error(course, project):
    progress = _unlocked(course, "D07", "D07-package")
    save_progress(project / ".learn/progress.json", progress)
    save_draft(project, "D07", "D07-package", "from helpers import greet\n")
    failed = run_cli(project, "practice", "check", "D07", "D07-package", "--json")
    assert failed.returncode == 1
    assert "文件不存在" in json.loads(failed.stdout)["error"]


def test_web_prepare_read_and_validate_use_disk_ignoring_forged_content(course, web_server):
    root = web_server.project_root
    progress = _unlocked(course, "D07", "D07-package")
    save_progress(root / ".learn/progress.json", progress)
    local_endpoint = "/api/tasks/D07/sections/D07-package/local-file"
    status, prepared, _ = request(web_server, "POST", local_endpoint, {})
    assert status == 200 and prepared["created"] is True
    path = root / prepared["path"]
    path.write_text("value = 1\n", encoding="utf-8")
    status, stored, _ = request(web_server, "GET", local_endpoint)
    assert status == 200 and stored["content"] == "value = 1\n"
    status, failed, _ = request(web_server, "POST", "/api/tasks/D07/sections/D07-package/validate", {
        "source": "local_file", "content": "from helpers import greet\n", "path": "README.md",
    })
    assert status == 200 and failed["passed"] is False and failed["completed"] is False
    assert failed["content"] == "value = 1\n" and failed["path"] == prepared["path"]
    assert load_draft(root, "D07", "D07-package")["content"] == "value = 1\n"
    path.write_text("from helpers import greet\n", encoding="utf-8")
    status, passed, _ = request(web_server, "POST", "/api/tasks/D07/sections/D07-package/validate", {"source": "local_file"})
    assert status == 200 and passed["passed"] is True and passed["completed"] is True
    assert isinstance(passed["grading_token"], str)
    saved = json.loads((root / ".learn/progress.json").read_text(encoding="utf-8"))
    assert saved["tasks"]["D07"]["status"] == "in_progress"


def test_web_prepare_retains_same_origin_and_prerequisite_gates(course, web_server):
    endpoint = "/api/tasks/D07/sections/D07-package/local-file"
    status, error, _ = request(web_server, "POST", endpoint, {}, Origin="http://evil.example")
    assert status == 403 and error["ok"] is False
    status, error, _ = request(web_server, "POST", endpoint, {})
    assert status == 409 and "前置" in error["error"]
    assert not (web_server.project_root / "learner_workspace").exists()

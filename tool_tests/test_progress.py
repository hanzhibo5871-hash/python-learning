from __future__ import annotations

import json
from pathlib import Path

import pytest

from learnctl import progress
from learnctl.errors import DataError


def test_schema_one_state_is_rejected_without_migration(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    old = {
        "schema_version": 1,
        "curriculum_version": "1.0.0",
        "tasks": {},
        "courses": {},
    }
    path.write_text(json.dumps(old), encoding="utf-8")
    with pytest.raises(DataError, match="不支持自动迁移"):
        progress.validate_progress(json.loads(path.read_text(encoding="utf-8")), path)


def test_schema_two_legacy_decision_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    old = {
        "schema_version": 2,
        "curriculum_version": "2.1.0",
        "tasks": {},
        "modules": {},
        "module_decisions": {},
        "course_decisions": {},
        "options": {"langchain-cloud": False},
        "tests": {},
    }
    path.write_text(json.dumps(old), encoding="utf-8")
    with pytest.raises(DataError, match="course_decisions.*旧字段"):
        progress.validate_progress(json.loads(path.read_text(encoding="utf-8")), path)


def test_atomic_write_keeps_old_file_when_replace_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "progress.json"
    old = {"value": "old"}
    path.write_text(json.dumps(old), encoding="utf-8")

    def fail_replace(source: Path, target: Path) -> None:
        raise OSError("模拟中断")

    monkeypatch.setattr(progress.os, "replace", fail_replace)
    with pytest.raises(OSError, match="模拟中断"):
        progress.atomic_write_json(path, {"value": "new"})
    assert json.loads(path.read_text(encoding="utf-8")) == old
    assert list(tmp_path.glob("*.tmp")) == []


def test_old_curriculum_version_reconciles_lesson_progress_and_preserves_state(tmp_path: Path, curriculum_data: dict) -> None:
    path = tmp_path / ".learn" / "progress.json"
    state = progress.initial_progress(curriculum_data)
    state["curriculum_version"] = "2.0.0"
    # 旧课程的小节 ID 在新课程里不存在（例如旧 D01-s1、旧 D02-s1）
    state["lesson_progress"]["D01"] = {"current_section": "D01-s1", "completed_sections": ["D01-s1", "D01-s2"]}
    state["lesson_progress"]["D02"] = {"current_section": "D02-s1", "completed_sections": ["D02-s1"]}
    # 任务与模块状态必须保留
    state["tasks"]["D02"] = {"status": "in_progress", "evidence": ["旧证据"]}
    state["modules"]["py-basics"] = "practice"
    state["tests"]["form"] = {"exit_code": 0}
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    loaded = progress.load_progress(path, curriculum_data)

    assert loaded["curriculum_version"] == "3.0.0"
    assert loaded["tasks"]["D02"]["status"] == "in_progress"
    assert loaded["tasks"]["D02"]["evidence"] == ["旧证据"]
    assert loaded["modules"]["py-basics"] == "practice"
    assert loaded["tests"]["form"]["exit_code"] == 0
    # 旧小节 ID 被过滤，D01 的旧选择题完成绝不进入新环境章节
    assert loaded["lesson_progress"]["D01"]["completed_sections"] == []
    assert loaded["lesson_progress"]["D01"]["current_section"] == "D01-onboarding"
    assert loaded["lesson_progress"]["D02"]["completed_sections"] == []


def _write_state(path: Path, state: dict) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    return raw


def test_curriculum_2_0_to_2_1_migrates_module_containers(tmp_path: Path, curriculum_data: dict) -> None:
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "2.0.0",
        "tasks": {},
        "modules": {"py-intro-env": "practice"},
        "module_decisions": {"py-intro-env": {"status": "practice", "diagnostic_id": "D0", "note": "保留"}},
        "module_updated_at": {"py-intro-env": "2026-01-01T00:00:00+08:00"},
        "options": {"langchain-cloud": False},
        "tests": {},
        "lesson_progress": {"D01": {"current_section": "D01-s1", "completed_sections": ["D01-s1"]}},
    }
    _write_state(path, state)

    loaded = progress.load_progress(path, curriculum_data)

    assert loaded["curriculum_version"] == "3.0.0"
    assert loaded["modules"] == {"py-env": "practice"}
    assert loaded["module_decisions"] == {"py-env": {"status": "practice", "diagnostic_id": "D0", "note": "保留"}}
    assert loaded["module_updated_at"] == {"py-env": "2026-01-01T00:00:00+08:00"}
    # 旧小节 ID 仍被过滤
    assert loaded["lesson_progress"]["D01"]["current_section"] == "D01-onboarding"
    assert loaded["lesson_progress"]["D01"]["completed_sections"] == []


def test_curriculum_migration_keeps_new_key_on_conflict(tmp_path: Path, curriculum_data: dict) -> None:
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "2.0.0",
        "tasks": {},
        "modules": {"py-intro-env": "learn", "py-env": "mastered"},
        "module_decisions": {"py-intro-env": {"status": "learn"}, "py-env": {"status": "mastered", "owner": "user"}},
        "module_updated_at": {"py-intro-env": "2026-01-01T00:00:00+08:00", "py-env": "2026-02-01T00:00:00+08:00"},
        "options": {"langchain-cloud": False},
        "tests": {},
    }
    _write_state(path, state)

    loaded = progress.load_progress(path, curriculum_data)

    # 新旧键都存在的冲突：保留新键（用户更新后的目标状态），删除旧键，不合并
    assert loaded["modules"] == {"py-env": "mastered"}
    assert loaded["module_decisions"] == {"py-env": {"status": "mastered", "owner": "user"}}
    assert loaded["module_updated_at"] == {"py-env": "2026-02-01T00:00:00+08:00"}


def test_curriculum_migration_preserves_unknown_entries(tmp_path: Path, curriculum_data: dict) -> None:
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "2.0.0",
        "tasks": {"D99": {"status": "in_progress", "evidence": ["保留"]}},
        "modules": {"py-intro-env": "practice", "unknown-module": "learn"},
        "module_decisions": {"py-intro-env": {"status": "practice"}, "unknown-decision": {"status": "learn", "owner": "x"}},
        "module_updated_at": {"py-intro-env": "2026-01-01T00:00:00+08:00", "unknown-at": "2026-03-01T00:00:00+08:00"},
        "options": {"langchain-cloud": False},
        "tests": {"unknown-test": {"exit_code": 1}},
        "extension": {"owner": "user"},
    }
    _write_state(path, state)

    loaded = progress.load_progress(path, curriculum_data)

    # 未知模块/字段原样保留，不被静默删除
    assert loaded["modules"]["unknown-module"] == "learn"
    assert loaded["module_decisions"]["unknown-decision"] == {"status": "learn", "owner": "x"}
    assert loaded["module_updated_at"]["unknown-at"] == "2026-03-01T00:00:00+08:00"
    assert loaded["tasks"]["D99"]["status"] == "in_progress"
    assert loaded["tests"]["unknown-test"]["exit_code"] == 1
    assert loaded["extension"] == {"owner": "user"}
    assert loaded["modules"]["py-env"] == "practice"


def test_curriculum_migration_not_applied_for_other_versions(tmp_path: Path, curriculum_data: dict) -> None:
    # 直接函数级：source 不是 2.0.0 或 target 不是 2.1.0 均不迁移
    assert progress.migrate_curriculum_2_0_to_2_1({"curriculum_version": "1.9.0", "modules": {"py-intro-env": "learn"}}, "2.1.0") is False
    assert progress.migrate_curriculum_2_0_to_2_1({"curriculum_version": "2.0.0", "modules": {"py-intro-env": "learn"}}, "2.2.0") is False

    # 通过 load：source=1.9.0（schema 2）不应用模块映射，只做版本协调
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "1.9.0",
        "tasks": {},
        "modules": {"py-intro-env": "practice"},
        "module_decisions": {},
        "options": {"langchain-cloud": False},
        "tests": {},
    }
    _write_state(path, state)
    loaded = progress.load_progress(path, curriculum_data)
    assert loaded["curriculum_version"] == "3.0.0"
    assert loaded["modules"] == {"py-intro-env": "practice"}, "非 2.0.0 不得做模块键猜测映射"


def test_curriculum_migration_read_does_not_write(tmp_path: Path, curriculum_data: dict) -> None:
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "2.0.0",
        "tasks": {},
        "modules": {"py-intro-env": "practice"},
        "module_decisions": {},
        "options": {"langchain-cloud": False},
        "tests": {},
    }
    raw = _write_state(path, state)

    loaded = progress.load_progress(path, curriculum_data)
    assert loaded["modules"] == {"py-env": "practice"}
    assert loaded["curriculum_version"] == "3.0.0"
    # 读取协调不写盘；只有下一次正常 save 才持久化
    assert path.read_bytes() == raw

    progress.save_progress(path, loaded)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["modules"] == {"py-env": "practice"}
    assert saved["curriculum_version"] == "3.0.0"


def test_curriculum_2_1_to_2_2_resets_project_tasks(tmp_path: Path, curriculum_data: dict) -> None:
    """2.1.0 -> 3.0.0：清空 v3 重写章节完成并把原 done 降为 in_progress。

    旧章节完成不能冒充新版教学；D01 环境证据保留，其余旧语义完成状态清空。
    """
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "2.1.0",
        "tasks": {
            "D18": {"status": "done", "evidence": ["旧证据"], "owner": "user"},
            "D19": {"status": "done", "evidence": ["旧证据"]},
            "D24": {"status": "done"},
            "D01": {"status": "done", "evidence": ["环境通过"]},
            "D25": {"status": "done", "evidence": ["LLM 通过"]},
            "D20": {"status": "in_progress", "evidence": ["进行中"]},
        },
        "modules": {"py-basics": "practice"},
        "module_decisions": {},
        "options": {"langchain-cloud": False},
        "tests": {"form": {"exit_code": 0}},
        "lesson_progress": {
            "D18": {"current_section": "D18-requirements", "completed_sections": ["D18-requirements", "D18-contract", "D18-readme"]},
            "D19": {"current_section": "D19-config", "completed_sections": ["D19-config"]},
            "D24": {"current_section": "D24-runbook", "completed_sections": ["D24-runbook"]},
            "D01": {"current_section": "D01-onboarding", "completed_sections": ["D01-onboarding", "D01-verify"]},
            "D25": {"current_section": "D25-chat", "completed_sections": ["D25-chat"]},
        },
    }
    _write_state(path, state)

    loaded = progress.load_progress(path, curriculum_data)

    assert loaded["curriculum_version"] == "3.0.0"
    # v3 重写范围 D02-D28 的章节完成被清空，done 降为 in_progress，evidence 与未知字段保留
    assert loaded["lesson_progress"]["D18"]["completed_sections"] == []
    assert loaded["lesson_progress"]["D19"]["completed_sections"] == []
    assert loaded["lesson_progress"]["D24"]["completed_sections"] == []
    assert loaded["tasks"]["D18"] == {"status": "in_progress", "evidence": ["旧证据"], "owner": "user"}
    assert loaded["tasks"]["D19"]["status"] == "in_progress"
    assert loaded["tasks"]["D19"]["evidence"] == ["旧证据"]
    assert loaded["tasks"]["D24"]["status"] == "in_progress"
    # 未完成任务也保持 in_progress；D01 环境状态和 evidence 保留
    assert loaded["tasks"]["D20"]["status"] == "in_progress"
    assert loaded["tasks"]["D01"]["status"] == "done"
    assert loaded["tasks"]["D01"]["evidence"] == ["环境通过"]
    assert loaded["lesson_progress"]["D01"]["completed_sections"] == ["D01-onboarding", "D01-verify"]
    assert loaded["tasks"]["D25"]["status"] == "in_progress"
    assert loaded["tasks"]["D25"]["evidence"] == ["LLM 通过"]
    assert loaded["lesson_progress"]["D25"]["completed_sections"] == []
    # 其余历史保留
    assert loaded["modules"]["py-basics"] == "practice"
    assert loaded["tests"]["form"]["exit_code"] == 0


def test_curriculum_2_0_to_2_2_chains_module_rename_then_project_reset(tmp_path: Path, curriculum_data: dict) -> None:
    """2.0.0 -> 3.0.0：先保留已知模块重命名，再执行 v3 章节重置。"""
    path = tmp_path / ".learn" / "progress.json"
    state = {
        "schema_version": 2,
        "curriculum_version": "2.0.0",
        "tasks": {"D19": {"status": "done", "evidence": ["旧项目"]}},
        "modules": {"py-intro-env": "practice"},
        "module_decisions": {"py-intro-env": {"status": "practice"}},
        "module_updated_at": {"py-intro-env": "2026-01-01T00:00:00+08:00"},
        "options": {"langchain-cloud": False},
        "tests": {},
        "lesson_progress": {"D19": {"current_section": "D19-s1", "completed_sections": ["D19-s1"]}},
    }
    _write_state(path, state)

    loaded = progress.load_progress(path, curriculum_data)

    assert loaded["curriculum_version"] == "3.0.0"
    # 模块重命名生效
    assert loaded["modules"] == {"py-env": "practice"}
    assert loaded["module_decisions"] == {"py-env": {"status": "practice"}}
    assert loaded["module_updated_at"] == {"py-env": "2026-01-01T00:00:00+08:00"}
    # 随后的 2.1.0->2.2.0 章节重置也生效
    assert loaded["tasks"]["D19"]["status"] == "in_progress"
    assert loaded["tasks"]["D19"]["evidence"] == ["旧项目"]
    assert loaded["lesson_progress"]["D19"]["completed_sections"] == []


def test_curriculum_2_1_to_2_2_not_applied_for_other_versions() -> None:
    assert progress.migrate_curriculum_2_1_to_2_2({"curriculum_version": "2.1.0", "tasks": {"D19": {"status": "done"}}}, "2.1.0") is False
    assert progress.migrate_curriculum_2_1_to_2_2({"curriculum_version": "2.0.0", "tasks": {"D19": {"status": "done"}}}, "2.2.0") is False


def test_schema_two_state_without_lesson_progress_gets_defaults(tmp_path: Path, curriculum_data: dict) -> None:
    path = tmp_path / ".learn" / "progress.json"
    state = progress.initial_progress(curriculum_data)
    del state["lesson_progress"]
    path.parent.mkdir()
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    loaded = progress.load_progress(path, curriculum_data)
    assert loaded["lesson_progress"]["D01"]["current_section"] == "D01-onboarding"
    progress.save_progress(path, loaded)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert set(saved["lesson_progress"]) == {task["id"] for task in curriculum_data["tasks"]}

from __future__ import annotations

from pathlib import Path
from typing import Any

from .curriculum import MODULE_STATUSES
from .errors import BlockedError, UsageError
from .progress import TASK_STATUSES, ensure_lesson_progress, lesson_progress_for, now_iso, save_progress, task_status


def required_sections(task: dict[str, Any]) -> list[str]:
    """任务中所有必修小节的 ID 列表。只有明确标记 optional:true 的小节才不算必修。"""
    return [section["id"] for section in task["lesson"] if not section.get("optional")]


def missing_required_sections(progress: dict[str, Any], task: dict[str, Any]) -> list[str]:
    """返回该任务尚需验证通过的必修小节 ID 列表。"""
    required = required_sections(task)
    completed = set(lesson_progress_for(progress, task).get("completed_sections", []))
    return [section_id for section_id in required if section_id not in completed]


def missing_prerequisites(task: dict[str, Any], progress: dict[str, Any]) -> list[str]:
    return [dependency for dependency in task["prerequisites"] if task_status(progress, dependency) != "done"]


def missing_stage_prerequisites(
    curriculum: dict[str, Any], task: dict[str, Any], progress: dict[str, Any]
) -> list[str]:
    stage = curriculum["_index"]["stages"][task["stage_id"]]
    missing: list[str] = []
    for stage_id in stage["prerequisites"]:
        prerequisite = curriculum["_index"]["stages"][stage_id]
        if any(task_status(progress, task_id) != "done" for task_id in prerequisite["task_ids"]):
            missing.append(stage_id)
    return missing


def module_status(module: dict[str, Any], progress: dict[str, Any]) -> str:
    decision = progress.get("module_decisions", {}).get(module["id"], {})
    return progress.get("modules", {}).get(module["id"], decision.get("status", module["default_status"]))


def task_payload(curriculum: dict[str, Any], progress: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    index = curriculum["_index"]
    modules: list[dict[str, Any]] = []
    for mapping in task["module_mapping"]:
        module = index["modules"][mapping["module_id"]]
        optional_track = module.get("optional_track_id")
        if optional_track and not progress["options"].get(optional_track, False):
            continue
        modules.append(
            {
                "id": module["id"],
                "title": module["title"],
                "status": module_status(module, progress),
                "relationship": mapping["relationship"],
                "supplemental": module.get("supplemental", False),
            }
        )
    exercises = [
        {"id": exercise_id, "command": index["exercises"][exercise_id]["test_command"]}
        for exercise_id in task["exercise_ids"]
    ]
    missing_tasks = missing_prerequisites(task, progress)
    missing_stages = missing_stage_prerequisites(curriculum, task, progress)
    return {
        "all_done": False,
        "blocked": bool(missing_tasks or missing_stages),
        "missing_prerequisites": missing_tasks + missing_stages,
        "missing_tasks": missing_tasks,
        "missing_stages": missing_stages,
        "task": {
            "id": task["id"],
            "stage_id": task["stage_id"],
            "title": task["title"],
            "learning_goal": task["learning_goal"],
            "status": task_status(progress, task["id"]),
            "concepts": task["concepts"],
            "frontend_bridge": task["frontend_bridge"],
            "coding_task": task["coding_task"],
            "snippet": task["snippet"],
            "references": task["references"],
            "actions": task["actions"],
            "modules": modules,
            "artifacts": task["artifacts"],
            "exercises": exercises,
            "acceptance": task["acceptance"],
            "lesson": lesson_payload(curriculum, task, progress),
        },
    }


def lesson_payload(curriculum: dict[str, Any], task: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    progress_record = lesson_progress_for(progress, task)
    completed = set(progress_record["completed_sections"])
    req_ids = set(required_sections(task))
    sections = []
    for section in task["lesson"]:
        public_section = dict(section)
        public_practice = dict(public_section.get("practice", {}))
        # These fields are loader/build-time teaching contracts, not client API
        # fields.  Keep the public practice payload stable for the Web layer.
        public_practice.pop("starter_policy", None)
        public_practice.pop("input_identifiers", None)
        public_section["practice"] = public_practice
        if "practice_first" in public_section:
            brief = dict(public_section["practice_first"])
            brief["drills"] = [{k: v for k, v in drill.items() if k != "reference"}
                               for drill in brief.get("drills", [])]
            public_section["practice_first"] = brief
        missing = missing_section_prerequisites(curriculum, progress, task, section["id"])
        sections.append(
            {
                **public_section,
                "completed": section["id"] in completed,
                "locked": bool(missing),
                "lock_reason": f"前置未完成：{'、'.join(missing)}" if missing else "",
            }
        )
    return {
        **progress_record,
        "total_sections": len(sections),
        "required_sections": len(req_ids),
        "completed_count": len(completed),
        "required_completed": len(completed & req_ids),
        "sections": sections,
    }


def lesson_progress_summary(task: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    record = lesson_progress_for(progress, task)
    return {
        **record,
        "total_sections": len(task["lesson"]),
        "completed_count": len(record["completed_sections"]),
    }


def section_completed(progress: dict[str, Any], task: dict[str, Any], section_id: str) -> bool:
    return section_id in lesson_progress_for(progress, task)["completed_sections"]


def missing_section_prerequisites(
    curriculum: dict[str, Any], progress: dict[str, Any], task: dict[str, Any], section_id: str
) -> list[str]:
    """返回本节之前尚未完成的任务/小节；这是练习和完成的后端权威门禁。"""
    section_ids = [section["id"] for section in task["lesson"]]
    if section_id not in section_ids:
        raise UsageError(f"课程小节 ID 不存在：{section_id}")
    missing = missing_prerequisites(task, progress)
    current_index = section_ids.index(section_id)
    completed = set(lesson_progress_for(progress, task)["completed_sections"])
    for previous in task["lesson"][:current_index]:
        if not previous.get("optional") and previous["id"] not in completed:
            missing.append(previous["id"])
    return missing


def assert_section_unlocked(
    curriculum: dict[str, Any], progress: dict[str, Any], task: dict[str, Any], section_id: str
) -> None:
    missing = missing_section_prerequisites(curriculum, progress, task, section_id)
    if missing:
        raise BlockedError(f"课程小节 {section_id} 被前置学习内容锁定：{'、'.join(missing)}")


def complete_section(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    task_id: str,
    section_id: str,
) -> dict[str, Any]:
    task = curriculum["_index"]["tasks"].get(task_id)
    if task is None:
        raise UsageError(f"任务 ID 不存在：{task_id}")
    if section_id not in {section["id"] for section in task["lesson"]}:
        raise UsageError(f"课程小节 ID 不存在：{section_id}")
    ensure_lesson_progress(progress, curriculum)
    assert_section_unlocked(curriculum, progress, task, section_id)
    record = progress["lesson_progress"][task_id]
    if section_id not in record["completed_sections"]:
        record["completed_sections"].append(section_id)
    record["current_section"] = section_id
    save_progress(progress_path, progress)
    return lesson_progress_summary(task, progress)


def update_lesson_position(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    task_id: str,
    section_id: str,
) -> dict[str, Any]:
    task = curriculum["_index"]["tasks"].get(task_id)
    if task is None:
        raise UsageError(f"任务 ID 不存在：{task_id}")
    if section_id not in {section["id"] for section in task["lesson"]}:
        raise UsageError(f"课程小节 ID 不存在：{section_id}")
    ensure_lesson_progress(progress, curriculum)
    progress["lesson_progress"][task_id]["current_section"] = section_id
    save_progress(progress_path, progress)
    return lesson_progress_summary(task, progress)


def today_payload(curriculum: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    first_blocked: dict[str, Any] | None = None
    for task in curriculum["tasks"]:
        if task_status(progress, task["id"]) == "done":
            continue
        payload = task_payload(curriculum, progress, task)
        if not payload["blocked"]:
            return payload
        if first_blocked is None:
            first_blocked = payload
    if first_blocked is not None:
        return first_blocked
    return {
        "all_done": True,
        "blocked": False,
        "missing_prerequisites": [],
        "missing_tasks": [],
        "missing_stages": [],
        "task": None,
    }


def update_task(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    task_id: str,
    status: str,
    evidence: str = "",
) -> dict[str, Any]:
    task = curriculum["_index"]["tasks"].get(task_id)
    if task is None:
        raise UsageError(f"任务 ID 不存在：{task_id}")
    if status not in TASK_STATUSES:
        raise UsageError(f"任务状态无效：{status}")
    evidence = evidence.strip()
    if status == "done":
        if not evidence:
            raise BlockedError("任务标记为 done 时必须提供非空 evidence")
        missing = missing_prerequisites(task, progress)
        missing_stages = missing_stage_prerequisites(curriculum, task, progress)
        if missing or missing_stages:
            values = "、".join(missing + missing_stages)
            raise BlockedError(f"任务 {task_id} 的前置任务或阶段未完成：{values}")
        # 可信完成：所有必修小节必须已由服务端验证通过
        missing_sections = missing_required_sections(progress, task)
        if missing_sections:
            total = len(required_sections(task))
            completed = total - len(missing_sections)
            raise BlockedError(
                f"任务 {task_id} 尚未通过全部必修小节验证（已验证 {completed}/{total}），"
                f"缺少：{'、'.join(missing_sections)}"
            )
        # D24 项目验收：端到端自动化检查
        if task_id == "D24":
            from .practice import validate_project_acceptance

            accept = validate_project_acceptance(progress_path.parent.parent)
            if not accept.get("passed"):
                failed = [c["name"] for c in accept.get("checks", []) if not c.get("passed")]
                raise BlockedError(
                    f"项目验收未通过，{len(failed)} 项检查失败：{'、'.join(failed)}"
                )
    record = progress["tasks"].setdefault(task_id, {"status": "todo", "evidence": []})
    record.setdefault("evidence", [])
    record["status"] = status
    if evidence and evidence not in record["evidence"]:
        record["evidence"].append(evidence)
    record["updated_at"] = now_iso()
    save_progress(progress_path, progress)
    return record


def update_module(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    module_id: str,
    status: str,
) -> None:
    if module_id not in curriculum["_index"]["modules"]:
        raise UsageError(f"知识模块 ID 不存在：{module_id}")
    if status not in MODULE_STATUSES:
        raise UsageError(f"知识模块状态无效：{status}")
    progress["modules"][module_id] = status
    progress.setdefault("module_updated_at", {})[module_id] = now_iso()
    save_progress(progress_path, progress)


def update_option(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    option_id: str,
    enabled: bool,
) -> None:
    if option_id not in curriculum["_index"]["optional_tracks"]:
        raise UsageError(f"选修项 ID 不存在：{option_id}")
    progress["options"][option_id] = enabled
    save_progress(progress_path, progress)

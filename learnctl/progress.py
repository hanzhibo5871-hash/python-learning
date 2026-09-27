from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import DataError

PROGRESS_SCHEMA_VERSION = 2
TASK_STATUSES = {"todo", "in_progress", "done"}
MODULE_STATUSES = {"learn", "practice", "mastered"}

# 版本限定的课程迁移：仅已知的连续旧版本做特定映射，其余版本不做任何猜测性映射。
CURRICULUM_2_0_TO_2_1 = {
    "from_version": "2.0.0",
    "to_version": "2.1.0",
    "module_renames": {
        "py-intro-env": "py-env",
    },
}

def _apply_module_rename(container: dict[str, Any], renames: dict[str, str]) -> None:
    """就地应用模块键重命名。

    旧键存在时移动到新键；新键已存在则保留新键（用户更新后的目标状态），
    绝不合并猜测；最后删除旧键。未涉及的键原样保留。
    """
    for old_id, new_id in renames.items():
        if old_id not in container:
            continue
        if new_id not in container:
            container[new_id] = container[old_id]
        del container[old_id]


def migrate_curriculum_2_0_to_2_1(progress: dict[str, Any], target_version: str) -> bool:
    """版本限定的内存协调迁移。

    仅当状态文件 source curriculum_version == '2.0.0' 且目标课程版本 == '2.1.0' 时，
    对 modules / module_decisions / module_updated_at（若存在）执行已知等价重命名
    py-intro-env -> py-env，并同步目标版本号。其余版本不做任何模糊映射，返回
    是否发生了迁移。只改动传入的内存字典，不写文件。
    """
    if progress.get("curriculum_version") != CURRICULUM_2_0_TO_2_1["from_version"]:
        return False
    if target_version != CURRICULUM_2_0_TO_2_1["to_version"]:
        return False
    renames = CURRICULUM_2_0_TO_2_1["module_renames"]
    for key in ("modules", "module_decisions", "module_updated_at"):
        container = progress.get(key)
        if isinstance(container, dict):
            _apply_module_rename(container, renames)
    progress["curriculum_version"] = target_version
    return True


# 版本限定的课程迁移：2.1.0 -> 2.2.0 时 D18-D24 从旧章节改为真实项目落盘。
# 旧章节的 completed_sections 一律清空，不能从旧 ID 冒充新版真实项目小节；
# 任务状态/证据与其他历史（modules/tests/options）原样保留，不做猜测性重置。
CURRICULUM_2_1_TO_2_2 = {
    "from_version": "2.1.0",
    "to_version": "2.2.0",
    "reset_completed_tasks": ("D18", "D19", "D20", "D21", "D22", "D23", "D24"),
}


def migrate_curriculum_2_1_to_2_2(progress: dict[str, Any], target_version: str) -> bool:
    """版本限定的内存协调迁移。

    仅当状态文件 source curriculum_version == '2.1.0' 且目标课程版本 == '2.2.0' 时，
    清空 D18-D24 各任务的 completed_sections，并把原 status=done 降为 in_progress
    （保留 evidence 与未知字段）；其余任务/模块/历史原样保留。同步目标版本号。
    只改动传入的内存字典，不写文件。
    """
    if progress.get("curriculum_version") != CURRICULUM_2_1_TO_2_2["from_version"]:
        return False
    if target_version != CURRICULUM_2_1_TO_2_2["to_version"]:
        return False
    lesson_progress = progress.get("lesson_progress")
    if isinstance(lesson_progress, dict):
        for task_id in CURRICULUM_2_1_TO_2_2["reset_completed_tasks"]:
            record = lesson_progress.get(task_id)
            if isinstance(record, dict):
                record["completed_sections"] = []
    tasks = progress.get("tasks")
    if isinstance(tasks, dict):
        for task_id in CURRICULUM_2_1_TO_2_2["reset_completed_tasks"]:
            task = tasks.get(task_id)
            if isinstance(task, dict) and task.get("status") == "done":
                task["status"] = "in_progress"
    progress["curriculum_version"] = target_version
    return True


CURRICULUM_TO_3_0 = {
    "target_version": "3.0.0",
    # v3 改写了 D02-D28 的语义；保留 D01 环境证据，其余旧完成状态不能冒充新小节。
    "reset_tasks": tuple(f"D{number:02d}" for number in range(2, 29)),
}


def migrate_curriculum_to_3_0(progress: dict[str, Any], target_version: str) -> bool:
    """将旧课程状态迁移到 v3：保留证据/诊断等历史，清空旧课程完成断言。"""
    source_version = progress.get("curriculum_version")
    if target_version != CURRICULUM_TO_3_0["target_version"] or source_version == target_version:
        return False
    if not isinstance(source_version, str):
        return False
    lesson_progress = progress.get("lesson_progress")
    if isinstance(lesson_progress, dict):
        for task_id in CURRICULUM_TO_3_0["reset_tasks"]:
            record = lesson_progress.get(task_id)
            if isinstance(record, dict):
                record["completed_sections"] = []
                record["current_section"] = ""
    tasks = progress.get("tasks")
    if isinstance(tasks, dict):
        for task_id in CURRICULUM_TO_3_0["reset_tasks"]:
            task = tasks.get(task_id)
            if isinstance(task, dict) and task.get("status") == "done":
                task["status"] = "in_progress"
    progress["curriculum_version"] = target_version
    return True


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def initial_progress(curriculum: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "curriculum_version": curriculum["curriculum_version"],
        "tasks": {},
        "modules": {},
        "module_decisions": {},
        "options": {
            track["id"]: track["default_enabled"]
            for track in curriculum["optional_tracks"]
        },
        "tests": {},
        "lesson_progress": {
            task["id"]: {"current_section": task["lesson"][0]["id"], "completed_sections": []}
            for task in curriculum["tasks"]
        },
    }


def validate_progress(data: Any, path: Path) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise DataError(f"状态文件 {path}：根节点必须是对象")
    if data.get("schema_version") != PROGRESS_SCHEMA_VERSION:
        version = data.get("schema_version")
        raise DataError(
            f"状态文件 {path}：schema_version {version!r} 不支持自动迁移，请按当前 schema 重建状态文件"
        )
    for legacy_key in ("courses", "course_decisions"):
        if legacy_key in data:
            raise DataError(f"状态文件 {path}：$.{legacy_key} 是旧字段，schema 2 不支持迁移")
    if not isinstance(data.get("curriculum_version"), str):
        raise DataError(f"状态文件 {path}：curriculum_version 必须是字符串")
    for key in ("tasks", "modules", "module_decisions", "options", "tests"):
        if not isinstance(data.get(key), dict):
            raise DataError(f"状态文件 {path}：$.{key} 必须是对象")
    lesson_progress = data.get("lesson_progress", {})
    if not isinstance(lesson_progress, dict):
        raise DataError(f"状态文件 {path}：$.lesson_progress 必须是对象")
    for task_id, record in lesson_progress.items():
        if not isinstance(task_id, str) or not isinstance(record, dict):
            raise DataError(f"状态文件 {path}：$.lesson_progress.{task_id} 必须是对象")
        current_section = record.get("current_section")
        if not isinstance(current_section, str) or not current_section:
            raise DataError(f"状态文件 {path}：$.lesson_progress.{task_id}.current_section 必须是非空字符串")
        completed = record.get("completed_sections")
        if not isinstance(completed, list) or any(not isinstance(item, str) for item in completed):
            raise DataError(f"状态文件 {path}：$.lesson_progress.{task_id}.completed_sections 必须是字符串数组")
    for task_id, task in data["tasks"].items():
        if not isinstance(task, dict):
            raise DataError(f"状态文件 {path}：$.tasks.{task_id} 必须是对象")
        status = task.get("status", "todo")
        if not isinstance(status, str) or status not in TASK_STATUSES:
            raise DataError(f"状态文件 {path}：$.tasks.{task_id}.status 未知值 {status!r}")
        evidence = task.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
            raise DataError(f"状态文件 {path}：$.tasks.{task_id}.evidence 必须是字符串数组")
    for module_id, status in data["modules"].items():
        if not isinstance(status, str) or status not in MODULE_STATUSES:
            raise DataError(f"状态文件 {path}：$.modules.{module_id} 未知知识状态 {status!r}")
    for module_id, decision in data["module_decisions"].items():
        if not isinstance(decision, dict) or decision.get("status") not in MODULE_STATUSES:
            raise DataError(f"状态文件 {path}：$.module_decisions.{module_id}.status 是未知知识状态")
    for option_id, enabled in data["options"].items():
        if not isinstance(enabled, bool):
            raise DataError(f"状态文件 {path}：$.options.{option_id} 必须是布尔值")
    for exercise_id, record in data["tests"].items():
        if not isinstance(record, dict):
            raise DataError(f"状态文件 {path}：$.tests.{exercise_id} 必须是对象")
    return data


def load_progress(path: Path, curriculum: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return initial_progress(curriculum)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataError(f"状态文件 {path} JSON 无效（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}") from exc
    except OSError as exc:
        raise DataError(f"无法读取状态文件 {path}: {exc}") from exc
    validated = validate_progress(data, path)
    if validated["curriculum_version"] != curriculum["curriculum_version"]:
        # schema 2 的旧课程版本：按已知迁移链依次协调
        # （2.0.0→2.1.0 模块重命名，2.1.0→2.2.0 章节重置）；
        # 其余旧版本只做版本号协调与 lesson_progress 过滤，不做模糊映射。
        # 全部在内存中完成，下一次正常 save 才落盘。
        migrated = False
        # 先完成已有的精确旧版本迁移，再执行 v3 的语义重置；这样保留
        # 已知模块改名历史，同时绝不把旧小节 ID 猜测映射成新小节。
        if curriculum["curriculum_version"] == CURRICULUM_TO_3_0["target_version"]:
            if validated.get("curriculum_version") == "2.0.0":
                migrated = migrate_curriculum_2_0_to_2_1(validated, CURRICULUM_2_0_TO_2_1["to_version"])
                migrated = migrate_curriculum_2_1_to_2_2(validated, "2.2.0") or migrated
                migrated = migrate_curriculum_to_3_0(validated, curriculum["curriculum_version"]) or migrated
            elif validated.get("curriculum_version") == "2.1.0":
                migrated = migrate_curriculum_2_1_to_2_2(validated, "2.2.0")
                migrated = migrate_curriculum_to_3_0(validated, curriculum["curriculum_version"]) or migrated
            elif migrate_curriculum_to_3_0(validated, curriculum["curriculum_version"]):
                migrated = True
        elif migrate_curriculum_2_0_to_2_1(validated, CURRICULUM_2_0_TO_2_1["to_version"]):
            migrated = migrate_curriculum_2_1_to_2_2(validated, curriculum["curriculum_version"])
        elif migrate_curriculum_2_1_to_2_2(validated, curriculum["curriculum_version"]):
            migrated = True
        if not migrated:
            validated["curriculum_version"] = curriculum["curriculum_version"]
    ensure_lesson_progress(validated, curriculum)
    return validated


def ensure_lesson_progress(progress: dict[str, Any], curriculum: dict[str, Any]) -> None:
    records = progress.setdefault("lesson_progress", {})
    for task in curriculum["tasks"]:
        default = {"current_section": task["lesson"][0]["id"], "completed_sections": []}
        record = records.setdefault(task["id"], default)
        preserved = dict(record) if isinstance(record, dict) else {}
        valid_ids = {section["id"] for section in task["lesson"]}
        completed = [item for item in record.get("completed_sections", []) if item in valid_ids]
        current = record.get("current_section")
        if current not in valid_ids:
            current = default["current_section"]
        preserved["current_section"] = current
        preserved["completed_sections"] = completed
        records[task["id"]] = preserved


def lesson_progress_for(
    progress: dict[str, Any], task: dict[str, Any]
) -> dict[str, Any]:
    default = {"current_section": task["lesson"][0]["id"], "completed_sections": []}
    record = progress.get("lesson_progress", {}).get(task["id"], default)
    completed = [
        section["id"] for section in task["lesson"] if section["id"] in record.get("completed_sections", [])
    ]
    current = record.get("current_section", default["current_section"])
    if current not in {section["id"] for section in task["lesson"]}:
        current = default["current_section"]
    return {"current_section": current, "completed_sections": completed}


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def save_progress(path: Path, data: dict[str, Any]) -> None:
    validate_progress(data, path)
    atomic_write_json(path, data)


def task_status(progress: dict[str, Any], task_id: str) -> str:
    return progress["tasks"].get(task_id, {}).get("status", "todo")

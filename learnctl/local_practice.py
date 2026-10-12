from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .errors import BlockedError, DataError, UsageError
from .practice import WORKSPACE_ROOT, find_section, run_validation, save_draft
from .web.storage import atomic_write_text, normalize_relative_path, read_utf8, resolve_under_root
from .workflow import assert_section_unlocked, complete_section


# 这是模块导入课明确提供的教学文件，不读取验证器中的私有参考答案。
_TEACHING_FILES = {
    "D07-package": {"helpers.py": "def greet(name):\n    return f'你好，{name}'\n"},
}


def practice_path(task: dict[str, Any], section: dict[str, Any]) -> Path:
    """D07 起的正式作业路径；连续项目按课程声明复用同一文件。"""
    task_id = task["id"]
    if not re.fullmatch(r"D\d{2}", task_id) or int(task_id[1:]) < 7:
        raise UsageError("本地编辑器作业从 D07 开始")
    practice = section["practice"]
    if practice.get("project_file"):
        project_file = normalize_relative_path(practice["project_file"])
        return WORKSPACE_ROOT / project_file
    file_name = practice["file_name"] if "file_name" in practice else "review.md"
    relative = Path("learner_workspace") / "lessons" / task_id / section["id"] / file_name
    return Path(normalize_relative_path(relative.as_posix()))


def _create_file(path: Path, content: str) -> bool:
    """原子发布新文件；另一进程已创建时保留它的内容。"""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".prepare", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        atomic_write_text(temporary, content)
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
        return True
    except OSError as exc:
        raise DataError(f"无法创建本地作业 {path}: {exc}") from exc
    finally:
        temporary.unlink()


def prepare_practice(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    task_id: str,
    section_id: str,
    root: Path,
) -> dict[str, Any]:
    task, section = find_section(curriculum, task_id, section_id)
    relative = practice_path(task, section)
    assert_section_unlocked(curriculum, progress, task, section_id)
    target = resolve_under_root(root, relative.as_posix())
    source = "local"
    created = False
    if not target.exists():
        if section["practice"].get("continues_file"):
            raise BlockedError(f"续编文件不存在：{relative.as_posix()}；请恢复前一节的真实文件后继续")
        content = section["practice"]["starter_content"]
        created = _create_file(target, content)
        if created:
            source = "starter"
    fixtures = []
    for file_name, content in _TEACHING_FILES.get(section_id, {}).items():
        fixture_relative = relative.parent / file_name
        fixture = resolve_under_root(root, fixture_relative.as_posix())
        fixtures.append({"path": fixture_relative.as_posix(), "created": _create_file(fixture, content)})
    return {
        "path": relative.as_posix(),
        "created": created,
        "source": source,
        "content": read_utf8(target),
        "fixtures": fixtures,
    }


def check_practice(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    task_id: str,
    section_id: str,
    root: Path,
) -> dict[str, Any]:
    task, section = find_section(curriculum, task_id, section_id)
    relative = practice_path(task, section)
    assert_section_unlocked(curriculum, progress, task, section_id)
    target = resolve_under_root(root, relative.as_posix())
    if not target.is_file():
        raise BlockedError(f"本地作业文件不存在：{relative.as_posix()}；请先准备作业并在编辑器中保存")
    content = read_utf8(target)
    support_paths = {}
    support_files = {}
    for file_name in _TEACHING_FILES.get(section_id, {}):
        support_relative = relative.parent / file_name
        support = resolve_under_root(root, support_relative.as_posix())
        if not support.is_file():
            raise BlockedError(f"教学文件不存在：{support_relative.as_posix()}；请先准备本节作业")
        support_paths[file_name] = support
        support_files[file_name] = read_utf8(support)
    result = run_validation(
        curriculum, task_id, section_id, content, root,
        write_artifact=False, support_files=support_files,
    )
    # 验收期间编辑器仍可保存；此时拒绝把旧内容登记为已完成。
    if not target.is_file() or read_utf8(target) != content:
        raise BlockedError("本地作业在检查期间发生变化，请保存文件后重新检查")
    for file_name, support in support_paths.items():
        if not support.is_file() or read_utf8(support) != support_files[file_name]:
            raise BlockedError("教学文件在检查期间发生变化，请保存文件后重新检查")
    save_draft(root, task_id, section_id, content)
    result.update({"path": relative.as_posix(), "content": content})
    if result.get("passed"):
        result["lesson_progress"] = complete_section(curriculum, progress, progress_path, task_id, section_id)
    return result

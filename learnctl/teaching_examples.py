from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import UsageError
from .local_practice import _create_file
from .practice import find_section
from .web.storage import normalize_relative_path, read_utf8, resolve_under_root


def prepare_example(
    curriculum: dict[str, Any],
    task_id: str,
    section_id: str,
    source: str,
    index: int,
    root: Path,
) -> dict[str, Any]:
    """把公开教学示例放到编辑器中；预习不受作业进度门禁限制。"""
    if not isinstance(source, str) or source not in {"card", "example"}:
        raise UsageError("教学示例来源必须是 card 或 example")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise UsageError("教学示例编号必须是从 0 开始的非负整数")
    _, section = find_section(curriculum, task_id, section_id)
    items = section.get("examples", []) if source == "example" else section.get("practice_first", {}).get("cards", [])
    if index >= len(items):
        raise UsageError("教学示例编号不存在")
    item = items[index]
    if item.get("source_kind") != "python" or item.get("runnable") is not True:
        raise UsageError("此处只准备可独立运行的 Python 教学示例；命令、HTML 和文件片段请按指定位置操作")
    content = item.get("code")
    if not isinstance(content, str) or not content.strip():
        raise UsageError("教学示例代码不能为空")
    relative = normalize_relative_path(
        (Path("learner_workspace/examples") / task_id / section_id / f"{source}-{index + 1}.py").as_posix()
    )
    target = resolve_under_root(root, relative)
    created = _create_file(target, content)
    return {"path": relative, "created": created, "content": read_utf8(target)}

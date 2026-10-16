"""编辑器通过 stdin 调用的只读 AI 接口；不创建作业或修改学习进度。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TextIO

from . import ai
from .curriculum import load_curriculum
from .errors import BlockedError, LearnctlError, UsageError
from .grading import _redact
from .local_practice import practice_path
from .practice import find_section
from .web.storage import read_utf8, resolve_under_root

CODE_CONTEXT_LIMIT = 8000
SELECTION_LIMIT = 2000
VALIDATION_LIMIT = 1000
EDITOR_MODEL = "deepseek-flash"


def read_request(stream: TextIO) -> dict[str, Any]:
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="strict")

    def reject_constant(value: str) -> None:
        raise UsageError("AI 请求不得包含非标准 JSON 常量")

    try:
        body = json.loads(stream.read(), parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise UsageError(f"AI stdin 必须是单个 JSON 对象（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}") from exc
    except UnicodeError as exc:
        raise UsageError("AI stdin 必须是有效的 UTF-8 JSON") from exc
    except OSError as exc:
        raise UsageError(_redact(f"无法读取 AI stdin：{exc}", os.environ.get("DEEPSEEK_API_KEY"))) from exc
    if not isinstance(body, dict):
        raise UsageError("AI stdin 必须是单个 JSON 对象")
    return body


def _text_field(body: dict[str, Any], name: str, limit: int) -> str:
    value = body.get(name, "")
    if not isinstance(value, str) or len(value) > limit:
        raise UsageError(f"{name} 必须是最多 {limit} 字符的文本")
    return value


def _code_context(
    root: Path, task: dict[str, Any], section: dict[str, Any], body: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    include_code = body.get("include_code", True)
    if not isinstance(include_code, bool):
        raise UsageError("include_code 必须是布尔值")
    selection = _text_field(body, "selection", SELECTION_LIMIT)
    validation = _text_field(body, "validation_summary", VALIDATION_LIMIT)
    relative = practice_path(task, section) if int(task["id"][1:]) >= 7 else None
    blocks: list[str] = []
    if selection:
        blocks.append("编辑器选中片段（用户提供）：\n" + selection)
    code_included = False
    if include_code and relative is not None:
        target = resolve_under_root(root, relative.as_posix())
        if target.is_file():
            blocks.append(f"当前课时文件 {relative.as_posix()}：\n" + read_utf8(target))
            code_included = True
            # 只附带本节明确提供的导入教学文件，不遍历工作区。
            if section["id"] == "D07-package":
                support_relative = relative.parent / "helpers.py"
                support = resolve_under_root(root, support_relative.as_posix())
                if support.is_file():
                    blocks.append(f"本节教学文件 {support_relative.as_posix()}：\n" + read_utf8(support))
    full_content = "\n\n".join(blocks)
    content = full_content[:CODE_CONTEXT_LIMIT]
    return {"content": content, "validation_summary": validation}, {
        "path": relative.as_posix() if relative is not None else None,
        "code_included": code_included,
        "code_chars": len(content),
        "code_truncated": len(full_content) > CODE_CONTEXT_LIMIT,
        "selection_included": bool(selection),
        "validation_included": bool(validation),
    }


def run_command(
    operation: str,
    body: dict[str, Any],
    root: Path,
    task_id: str | None = None,
    section_id: str | None = None,
) -> dict[str, Any]:
    # Flash 默认开启 thinking；编辑器快速答疑明确关闭，旧会话配置独立保留。
    session = ai.AiSession(model=EDITOR_MODEL, thinking=False)
    request_key = body.get("api_key")

    def redact(value: str) -> str:
        value = _redact(value, session.get_key())
        value = _redact(value, request_key if isinstance(request_key, str) else None)
        return _redact(value, os.environ.get("DEEPSEEK_API_KEY"))

    try:
        if "api_key" in body:
            if not isinstance(request_key, str) or not 8 <= len(request_key.strip()) <= 512:
                raise UsageError("api_key 必须是长度在 8 到 512 之间的非空文本")
            session.set_key(request_key.strip())
            key_source = "request"
        else:
            key_source = "env" if session.configured() else None
        if operation == "status":
            return {"provider": "deepseek", "model": session.model, "base_url": ai.BASE_URL,
                    "configured": session.configured(), "key_source": key_source}
        if operation == "test":
            content = ai.chat(session, [{"role": "user", "content": "ping"}])
            return {"ok": True, "content": redact(content)}
        if operation != "ask":
            raise UsageError(f"未知 AI 命令：{operation}")
        curriculum = load_curriculum(root / "data/curriculum.json")
        task, section = find_section(curriculum, task_id, section_id)
        learner_context, metadata = _code_context(root, task, section, body)
        answer = ai.tutor_chat(session, curriculum, task_id, section_id,
                               body.get("question"), body.get("history", []),
                               learner_context=learner_context)
        return {"answer": redact(answer), "context": metadata}
    except LearnctlError as exc:
        raise LearnctlError(redact(str(exc)), exc.exit_code) from exc
    except (ai.AiError, OSError, ValueError) as exc:
        raise BlockedError(redact(str(exc))) from exc

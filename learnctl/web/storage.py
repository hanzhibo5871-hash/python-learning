from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from ..errors import DataError, UsageError


def normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UsageError("文件路径必须是非空字符串")
    normalized = value.strip().replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    if PurePosixPath(normalized).is_absolute() or PureWindowsPath(normalized).is_absolute():
        raise UsageError("文件路径不得是绝对路径")
    if any(part in {"", ".", ".."} for part in posix_path.parts):
        raise UsageError("文件路径不得包含空段、当前目录或路径穿越")
    if any(character in normalized for character in "*?[]"):
        raise UsageError("文件路径不得包含通配符")
    if ".learn" in posix_path.parts:
        raise UsageError("文件白名单不开放 .learn 内部文件")
    return posix_path.as_posix()


def resolve_under_root(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise UsageError("文件路径不在项目目录内") from exc
    return candidate


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise DataError(f"文件 {path} 不是有效的 UTF-8 文本") from exc
    except OSError as exc:
        raise DataError(f"无法读取文件 {path}: {exc}") from exc


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

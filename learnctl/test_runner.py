from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .curriculum import parse_test_command
from .errors import DataError
from .progress import now_iso, save_progress


def _prepare_exercise(exercise: dict[str, Any], root: Path) -> tuple[str, list[str]]:
    command = exercise["test_command"]
    args = parse_test_command(command, f"exercise[{exercise.get('id', '?')}].test_command")
    for target in args[3:]:
        if target == "-q":
            continue
        target_path = root / Path(target.replace("\\", "/"))
        if not target_path.is_file():
            raise DataError(f"练习测试文件不存在：{target}")
        try:
            target_path.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise DataError(f"练习测试文件不在项目目录内：{target}") from exc
    return command, args


def _record_success(
    exercise: dict[str, Any],
    command: str,
    progress: dict[str, Any],
    progress_path: Path,
) -> str:
    run_at = now_iso()
    record = progress["tests"].setdefault(exercise["id"], {})
    record.update({"exercise_id": exercise["id"], "exit_code": 0, "command": command, "run_at": run_at})
    task = progress["tasks"].setdefault(exercise["task_id"], {"status": "todo", "evidence": []})
    task.setdefault("evidence", [])
    evidence = f"测试通过：{command}"
    if evidence not in task["evidence"]:
        task["evidence"].append(evidence)
    task["updated_at"] = run_at
    save_progress(progress_path, progress)
    return run_at


def run_exercise_capture(
    exercise: dict[str, Any],
    root: Path,
    progress: dict[str, Any],
    progress_path: Path,
) -> dict[str, Any]:
    command, args = _prepare_exercise(exercise, root)
    result = subprocess.run(
        args,
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
        check=False,
    )
    run_at = now_iso()
    if result.returncode == 0:
        _record_success(exercise, command, progress, progress_path)
    return {
        "exercise_id": exercise["id"],
        "command": command,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "exit_code": result.returncode,
        "run_at": run_at,
    }


def run_exercise(
    exercise: dict[str, Any],
    root: Path,
    progress: dict[str, Any],
    progress_path: Path,
    *,
    verbose: bool,
) -> int:
    command, args = _prepare_exercise(exercise, root)
    result = subprocess.run(
        args,
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=not verbose,
        shell=False,
        check=False,
    )
    if not verbose and result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
    if result.returncode == 0:
        _record_success(exercise, command, progress, progress_path)
        print(f"练习 {exercise['id']} 测试通过。")
    else:
        print(f"练习 {exercise['id']} 测试失败，pytest 退出码：{result.returncode}")
    return result.returncode

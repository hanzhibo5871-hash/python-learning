from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .errors import BlockedError


def _venv_python(root: Path) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _run(args: list[str], cwd: Path, timeout: int = 60, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=timeout,
        env=env,
    )


def _tail(text: str, limit: int = 800) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return "…" + cleaned[-limit:]


def _editable_ok(root: Path, python: Path) -> tuple[bool, str]:
    try:
        probe = _run([str(python), "-c", "import learnctl; print(learnctl.__file__)"], root)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if probe.returncode != 0:
        return False, _tail(probe.stderr or probe.stdout) or "无法导入 learnctl"
    resolved = Path(probe.stdout.strip()).resolve()
    inside = False
    try:
        resolved.relative_to(root.resolve())
        inside = True
    except ValueError:
        inside = False
    return inside, str(resolved)


def _parse_version(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def _version_at_least(value: str | None, minimum: tuple[int, int]) -> bool:
    parsed = _parse_version(value)
    return parsed is not None and parsed >= minimum


def _venv_python_version(root: Path, python: Path) -> tuple[str | None, str]:
    """通过 .venv python 固定 probe 独立读取其解释器版本（如 3.11.4）。"""
    try:
        probe = _run([str(python), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"], root)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    if probe.returncode != 0:
        return None, _tail(probe.stderr or probe.stdout) or "无法获取 .venv 版本"
    version = probe.stdout.strip()
    if not version or _parse_version(version) is None:
        return None, f"无法解析 .venv 版本：{version!r}"
    return version, ""


def detect_env(root: Path) -> dict[str, Any]:
    """实时检测当前环境：解释器、项目根、.venv、pip、pytest、可编辑安装。"""
    root = Path(root).resolve()
    version_ok = sys.version_info >= (3, 11)
    python_prompt = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} {sys.executable}"
    project_ok = (root / "data" / "curriculum.json").is_file()
    venv_python = _venv_python(root)
    venv_exists = venv_python.is_file()

    pip_ok = False
    pip_detail = "未创建 .venv"
    pytest_ok = False
    pytest_detail = "未创建 .venv"
    editable_ok = False
    editable_detail = "未创建 .venv"
    venv_python_version: str | None = None
    venv_version_detail = "未创建 .venv"
    if venv_exists:
        try:
            pip_probe = _run([str(venv_python), "-m", "pip", "--version"], root)
            pip_ok = pip_probe.returncode == 0
            pip_detail = _tail(pip_probe.stdout or pip_probe.stderr) or "pip 不可用"
            pytest_probe = _run([str(venv_python), "-c", "import pytest"], root)
            pytest_ok = pytest_probe.returncode == 0
            pytest_detail = _tail(pytest_probe.stderr or pytest_probe.stdout) or "pytest 可导入"
            editable_ok, editable_detail = _editable_ok(root, venv_python)
            venv_python_version, venv_version_detail = _venv_python_version(root, venv_python)
        except (OSError, subprocess.SubprocessError) as exc:
            pip_detail = str(exc)

    venv_version_ok = _version_at_least(venv_python_version, (3, 11))

    checks: list[dict[str, Any]] = [
        {"name": "Python 版本 >= 3.11", "passed": version_ok, "detail": python_prompt},
        {"name": "项目根存在课程文件", "passed": project_ok, "detail": str(root)},
        {"name": ".venv 存在", "passed": venv_exists, "detail": str(venv_python)},
        {"name": ".venv 的 pip 可用", "passed": pip_ok, "detail": pip_detail},
        {"name": ".venv 可导入 pytest", "passed": pytest_ok, "detail": pytest_detail},
        {"name": "learnctl 可编辑安装到当前项目", "passed": editable_ok, "detail": editable_detail},
    ]
    return {
        "action": "detect",
        "command": "where.exe python; python --version; python -c \"import sys; print(sys.executable)\"; Get-Location",
        "passed": version_ok,
        "checks": checks,
        "env": {
            "python_executable": sys.executable,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "version_ok": version_ok,
            "project_root": str(root),
            "venv_exists": venv_exists,
            "venv_python": str(venv_python),
            "venv_python_version": venv_python_version,
            "venv_version_ok": venv_version_ok,
            "venv_pip_ok": pip_ok,
            "venv_pytest_ok": pytest_ok,
            "editable_installed": editable_ok,
        },
        "stdout": "",
        "stderr": "",
        "exit_code": 0 if version_ok else 1,
    }


def run_action_create_venv(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    venv_python = _venv_python(root)
    if venv_python.is_file():
        try:
            probe = _run([str(venv_python), "--version"], root)
        except (OSError, subprocess.SubprocessError) as exc:
            probe = None
        running = bool(probe and probe.returncode == 0)
        checks = [
            {"name": ".venv 已存在", "passed": True, "detail": "不删除重建，直接验证"},
            {"name": ".venv Python 可运行", "passed": running, "detail": _tail(probe.stdout if probe else "") or "无法运行"},
        ]
        passed = running
        stdout = probe.stdout if probe else ""
        stderr = probe.stderr if probe else ""
        exit_code = 0 if passed else 1
    else:
        try:
            proc = _run([sys.executable, "-m", "venv", ".venv"], root, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            checks = [{"name": "创建 .venv", "passed": False, "detail": str(exc)}]
            return {"action": "create_venv", "command": "python -m venv .venv", "passed": False, "checks": checks, "stdout": "", "stderr": str(exc), "exit_code": 1, "env": detect_env(root)}
        created = venv_python.is_file()
        if created:
            probe = _run([str(venv_python), "--version"], root)
            running = probe.returncode == 0
            stdout = proc.stdout + probe.stdout
            stderr = proc.stderr + probe.stderr
        else:
            running = False
            stdout = proc.stdout
            stderr = proc.stderr
        checks = [
            {"name": "创建 .venv", "passed": created, "detail": "创建成功" if created else _tail(proc.stderr) or "创建失败"},
            {"name": ".venv Python 可运行", "passed": running, "detail": _tail(probe.stdout) if created and running else "无法运行"},
        ]
        passed = created and running
        exit_code = 0 if passed else 1
    return {
        "action": "create_venv",
        "command": "python -m venv .venv; .\\.venv\\Scripts\\python.exe --version",
        "passed": passed,
        "checks": checks,
        "stdout": _tail(stdout, 2000),
        "stderr": _tail(stderr, 2000),
        "exit_code": exit_code,
        "env": detect_env(root),
    }


def run_action_install(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    venv_python = _venv_python(root)
    if not venv_python.is_file():
        raise BlockedError("请先创建 .venv 再安装依赖")
    try:
        proc = _run([str(venv_python), "-m", "pip", "install", "-e", ".[dev]"], root, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        checks = [{"name": "pip install -e .[dev]", "passed": False, "detail": str(exc)}]
        return {"action": "install", "command": ".\\.venv\\Scripts\\python.exe -m pip install -e .[dev]", "passed": False, "checks": checks, "stdout": "", "stderr": str(exc), "exit_code": 1, "env": detect_env(root)}
    pytest_ok = _run([str(venv_python), "-c", "import pytest"], root).returncode == 0
    editable_ok, editable_detail = _editable_ok(root, venv_python)
    checks = [
        {"name": "pip install -e .[dev] 成功", "passed": proc.returncode == 0, "detail": _tail(proc.stderr or proc.stdout) or "安装成功"},
        {"name": ".venv 可导入 pytest", "passed": pytest_ok, "detail": "pytest 已安装" if pytest_ok else "pytest 不可导入"},
        {"name": "learnctl 可编辑安装到当前项目", "passed": editable_ok, "detail": editable_detail},
    ]
    passed = proc.returncode == 0 and pytest_ok and editable_ok
    return {
        "action": "install",
        "command": ".\\.venv\\Scripts\\python.exe -m pip install -e .[dev]",
        "passed": passed,
        "checks": checks,
        "stdout": _tail(proc.stdout, 4000),
        "stderr": _tail(proc.stderr, 4000),
        "exit_code": 0 if passed else 1,
        "env": detect_env(root),
    }


def run_action_verify(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    venv_python = _venv_python(root)
    if not venv_python.is_file():
        raise BlockedError("请先创建 .venv 再运行环境验证")
    small_program = (
        "import json, sys\n"
        "print(json.dumps({'python': sys.version, 'checksum': 1 + 1, 'editable': __import__('learnctl').__file__}))\n"
    )
    small = _run([str(venv_python), "-c", small_program], root)
    pytest_ok = _run([str(venv_python), "-c", "import pytest"], root).returncode == 0
    editable_ok, editable_detail = _editable_ok(root, venv_python)
    venv_python_version, venv_version_detail = _venv_python_version(root, venv_python)
    venv_version_ok = _version_at_least(venv_python_version, (3, 11))
    checks = [
        {"name": "固定小程序运行成功", "passed": small.returncode == 0, "detail": _tail(small.stdout) or _tail(small.stderr) or "小程序未输出"},
        {"name": ".venv 可导入 pytest", "passed": pytest_ok, "detail": "pytest 可导入" if pytest_ok else "pytest 不可导入"},
        {"name": "learnctl 指向当前项目", "passed": editable_ok, "detail": editable_detail},
        {"name": ".venv 版本 >= 3.11", "passed": venv_version_ok, "detail": venv_python_version or venv_version_detail},
    ]
    passed = small.returncode == 0 and pytest_ok and editable_ok and venv_version_ok
    return {
        "action": "verify",
        "command": ".\\.venv\\Scripts\\python.exe -c <fixed smoke>; .\\.venv\\Scripts\\python.exe -c \"import pytest\"; editable-path probe",
        "passed": passed,
        "checks": checks,
        "stdout": _tail(small.stdout, 2000),
        "stderr": _tail(small.stderr, 2000),
        "exit_code": 0 if passed else 1,
        "env": detect_env(root),
    }


ACTIONS = {
    "detect": detect_env,
    "create_venv": run_action_create_venv,
    "install": run_action_install,
    "verify": run_action_verify,
}


def run_action(action: str, root: Path) -> dict[str, Any]:
    if action not in ACTIONS:
        raise BlockedError(f"未知环境动作 {action!r}")
    return ACTIONS[action](root)

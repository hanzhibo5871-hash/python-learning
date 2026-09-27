from __future__ import annotations

import sys
from pathlib import Path

import pytest

from learnctl.envcheck import (
    detect_env,
    run_action,
    run_action_create_venv,
    run_action_install,
    run_action_verify,
)
from learnctl.errors import BlockedError


def _fake_venv(root: Path) -> Path:
    venv = root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
    venv.mkdir(parents=True, exist_ok=True)
    python = venv / ("python.exe" if sys.platform == "win32" else "python")
    python.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    return python


def test_detect_env_reads_live_state(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "curriculum.json").write_text("{}", encoding="utf-8")
    result = detect_env(tmp_path)
    assert result["passed"] is (sys.version_info >= (3, 11))
    assert result["env"]["project_root"] == str(tmp_path.resolve())
    assert result["env"]["venv_exists"] is False
    assert result["env"]["venv_python_version"] is None
    assert result["env"]["venv_version_ok"] is False


def test_create_venv_existing_is_not_recreated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from learnctl import envcheck

    python = _fake_venv(tmp_path)
    calls: list[list[str]] = []

    def fake_run(args, cwd, timeout=60, env=None):
        calls.append(list(args))
        return type("P", (), {"returncode": 0, "stdout": "Python 3.11.0", "stderr": ""})()

    monkeypatch.setattr(envcheck, "_run", fake_run)
    result = run_action_create_venv(tmp_path)
    assert result["passed"] is True
    assert not any("venv" in args for args in calls), "已存在的 .venv 不应重新创建"
    assert python.is_file()


def test_create_venv_when_missing_invokes_current_interpreter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from learnctl import envcheck

    calls: list[list[str]] = []

    def fake_run(args, cwd, timeout=60, env=None):
        calls.append(list(args))
        if args and args[:3] == [sys.executable, "-m", "venv"]:
            _fake_venv(tmp_path)
            return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return type("P", (), {"returncode": 0, "stdout": "Python 3.11.0", "stderr": ""})()

    monkeypatch.setattr(envcheck, "_run", fake_run)
    result = run_action_create_venv(tmp_path)
    assert result["passed"] is True
    assert any(args[:3] == [sys.executable, "-m", "venv"] for args in calls)


def test_install_requires_venv(tmp_path: Path) -> None:
    with pytest.raises(BlockedError, match="先创建 .venv"):
        run_action_install(tmp_path)


def test_install_uses_fixed_command_without_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from learnctl import envcheck

    _fake_venv(tmp_path)
    calls: list[list[str]] = []

    def fake_run(args, cwd, timeout=60, env=None):
        calls.append(list(args))
        return type("P", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    monkeypatch.setattr(envcheck, "_run", fake_run)
    monkeypatch.setattr(envcheck, "_editable_ok", lambda root, py: (True, str(tmp_path / "learnctl")))
    result = run_action_install(tmp_path)
    assert result["passed"] is True
    assert any(
        "pip" in args and "install" in args and "-e" in args and ".[dev]" in args for args in calls
    ), "安装命令必须是固定 pip install -e .[dev]"
    # 绝不执行任意用户命令：所有参数都来自固定列表
    assert all(args[0] == str(tmp_path / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")) for args in calls)


def test_verify_runs_small_program_and_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from learnctl import envcheck

    _fake_venv(tmp_path)
    calls: list[list[str]] = []

    def fake_run(args, cwd, timeout=60, env=None):
        calls.append(list(args))
        if "version_info" in " ".join(args):
            return type("P", (), {"returncode": 0, "stdout": "3.11.4", "stderr": ""})()
        return type("P", (), {"returncode": 0, "stdout": '{"python": "3.11", "checksum": 2}', "stderr": ""})()

    monkeypatch.setattr(envcheck, "_run", fake_run)
    monkeypatch.setattr(envcheck, "_editable_ok", lambda root, py: (True, str(tmp_path)))
    result = run_action_verify(tmp_path)
    assert result["passed"] is True
    assert any("checksum" in " ".join(args) for args in calls), "验证必须运行固定小程序"
    assert any("import pytest" in " ".join(args) for args in calls), "验证必须 smoke 导入 pytest"
    assert any("version_info" in " ".join(args) for args in calls), "验证必须独立探测 .venv 版本"


def test_verify_fails_when_venv_version_below_311(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """当前解释器合格，但 .venv 真实版本 < 3.11 时 verify 必须失败。"""
    from learnctl import envcheck

    _fake_venv(tmp_path)

    def fake_run(args, cwd, timeout=60, env=None):
        if "version_info" in " ".join(args):
            return type("P", (), {"returncode": 0, "stdout": "3.10.12", "stderr": ""})()
        return type("P", (), {"returncode": 0, "stdout": '{"python": "3.10", "checksum": 2}', "stderr": ""})()

    monkeypatch.setattr(envcheck, "_run", fake_run)
    monkeypatch.setattr(envcheck, "_editable_ok", lambda root, py: (True, str(tmp_path)))
    result = run_action_verify(tmp_path)
    assert result["passed"] is False
    assert any(not c["passed"] for c in result["checks"] if ".venv 版本" in c["name"])


def test_run_action_rejects_unknown_and_injected_commands(tmp_path: Path) -> None:
    with pytest.raises(BlockedError, match="未知环境动作"):
        run_action("detect; rm -rf .", tmp_path)
    with pytest.raises(BlockedError, match="未知环境动作"):
        run_action("$(whoami)", tmp_path)
    with pytest.raises(BlockedError, match="未知环境动作"):
        run_action("", tmp_path)

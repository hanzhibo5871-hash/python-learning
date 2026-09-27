from __future__ import annotations

import json
from pathlib import Path

import pytest

from learnctl.curriculum import load_curriculum
from learnctl.errors import BlockedError, UsageError
from learnctl.practice import (
    MAX_OUTPUT_CHARS,
    _CODE_VALIDATORS,
    find_section,
    load_draft,
    run_validation,
    save_draft,
    validate_code,
)
from learnctl.workflow import assert_section_unlocked, complete_section


def _curriculum() -> dict:
    return load_curriculum(Path("data/curriculum.json"))


def _section(curriculum: dict, task_id: str, section_id: str) -> dict:
    _, section = find_section(curriculum, task_id, section_id)
    return section


def test_all_code_sections_have_registered_validators(curriculum_data: dict) -> None:
    code_sections = {s["id"] for task in curriculum_data["tasks"] for s in task["lesson"] if s["practice"]["kind"] == "code"}
    missing = code_sections - set(_CODE_VALIDATORS)
    assert not missing, f"缺少校验器：{sorted(missing)}"


def test_starter_content_obeys_declared_policy(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    code_sections = [s for task in curriculum["tasks"] for s in task["lesson"] if s["practice"]["kind"] == "code"]
    for section in code_sections:
        practice = section["practice"]
        if practice.get("starter_policy") == "function_body":
            result = run_validation(
                curriculum,
                _task_id_of(curriculum_data, section["id"]),
                section["id"],
                practice["starter_content"],
                Path("."),
            )
            assert result["passed"] is False, f"{section['id']} 的函数体 starter 应等待学员实现"
        else:
            assert "NotImplementedError" not in practice["starter_content"], (
                f"{section['id']} 不是函数体实现练习，starter 不得埋入无关 NotImplementedError"
            )


def _task_id_of(curriculum_data: dict, section_id: str) -> str:
    for task in curriculum_data["tasks"]:
        if any(s["id"] == section_id for s in task["lesson"]):
            return task["id"]
    raise AssertionError(f"找不到小节 {section_id}")


def test_d02_names_success_failure_and_syntax(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D02", "D02-names")
    good = "value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))\n"
    bad = "value = 7\nprint(value)\n"
    assert validate_code(section, good, Path("."))["passed"] is True
    failed = validate_code(section, bad, Path("."))
    assert failed["passed"] is False
    assert any(not c["passed"] for c in failed["checks"])
    syntax = validate_code(section, "value = ", Path("."))
    assert syntax["passed"] is False
    assert syntax["stdout"] or syntax["stderr"] or any(c["passed"] is False for c in syntax["checks"])


def test_representative_validators_succeed(curriculum_data: dict, tmp_path: Path) -> None:
    curriculum = _curriculum()
    cases = {
        "D03-for": "def sum_even(numbers):\n    return sum(number for number in numbers if number % 2 == 0)\n",
        "D08-json-read": "import json\n\ndata = json.loads('{\"ok\": true}')\nprint(data['ok'])\n",
        "D17-coroutine": "import asyncio\n\nasync def main():\n    await asyncio.sleep(0)\n\nasyncio.run(main())\n",
        "D19-config": "import os\nfrom pathlib import Path\n\ndef get_db_path():\n    return Path(os.environ.get('TASKPROJ_DB', 'taskproj.db'))\n\ndef get_int_env(name, default):\n    try:\n        return int(os.environ.get(name))\n    except (TypeError, ValueError):\n        return default\n",
    }
    for section_id, solution in cases.items():
        section = _section(curriculum, _task_id_of(curriculum_data, section_id), section_id)
        project_root = tmp_path if section_id == "D19-config" else Path(".")
        if section_id == "D19-config":
            _write_workspace_project(tmp_path, config="")
        result = validate_code(section, solution, project_root)
        assert result["passed"] is True, f"{section_id} 正确解未通过：{result['checks']}"


def test_core_python_semantics_use_runtime_behavior_contracts(tmp_path: Path) -> None:
    curriculum = _curriculum()
    cases = {
        "D02-strings": "def transform_text(text):\n    return text.strip()[::-1]\n",
        "D04-varargs": "def describe(*args, **kwargs):\n    return {'args': args, 'kwargs': kwargs}\n",
        "D04-global-nonlocal": "def make_counter():\n    value = 0\n    def step():\n        nonlocal value\n        value += 1\n        return value\n    return step\n",
        "D04-type-hints": "def format_user(name: str, age: int) -> str:\n    return f'{name}: {age}'\n",
        "D05-dict-set": "def summarize_tags(tags):\n    unique = set(tags)\n    return {'unique': unique, 'count': len(unique)}\n",
        "D05-mutability": "def copy_and_append(items):\n    copied = items.copy()\n    copied.append('new')\n    return items, copied\n",
        "D05-iterators-generators": "def count_up_to(limit):\n    for value in range(limit):\n        yield value\n",
        "D06-else-finally": "def parse_number(text, events):\n    try:\n        return int(text)\n    except ValueError:\n        return None\n    finally:\n        events.append('finally')\n",
        "D06-with": "from pathlib import Path\ndef read_text(path):\n    with Path(path).open(encoding='utf-8') as stream:\n        return stream.read()\n",
        "D07-package": "from helpers import greet\n",
        "D07-class-instance": "class Task:\n    def __init__(self, title): self.title = title\n    def label(self): return self.title\n",
        "D07-dataclass": "from dataclasses import dataclass\n@dataclass\nclass Point:\n    x: int\n    y: int\n",
    }
    for section_id, solution in cases.items():
        task_id = section_id[:3]
        section = _section(curriculum, task_id, section_id)
        result = validate_code(section, solution, tmp_path)
        assert result["passed"] is True, f"{section_id} 行为正确解未通过：{result['checks']}"


def test_core_python_semantics_reject_wrong_behavior(tmp_path: Path) -> None:
    curriculum = _curriculum()
    wrong = {
        "D02-strings": "def transform_text(text):\n    return text\n",
        "D04-global-nonlocal": "def make_counter():\n    value = 0\n    def step():\n        return 1\n    return step\n",
        "D05-mutability": "def copy_and_append(items):\n    items.append('new')\n    return items, items\n",
        "D05-iterators-generators": "def count_up_to(limit):\n    return list(range(limit))\n",
        "D06-else-finally": "def parse_number(text, events):\n    return int(text)\n",
    }
    for section_id, solution in wrong.items():
        task_id = section_id[:3]
        result = validate_code(_section(curriculum, task_id, section_id), solution, tmp_path)
        assert result["passed"] is False, f"错误语义不应通过：{section_id}"


def test_invalid_indentation_is_rejected_as_python_syntax(tmp_path: Path) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D02", "D02-execution")
    result = validate_code(section, "if True:\nprint('错误缩进')\n", tmp_path)
    assert result["passed"] is False
    assert any("语法" in check["name"] and not check["passed"] for check in result["checks"])


def test_mock_server_validators_succeed(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    d12 = (
        "from urllib.request import Request\n\n"
        "def fetch_text(url, opener):\n"
        "    request = Request(url, method='GET')\n"
        "    with opener(request) as response:\n"
        "        return response.read().decode('utf-8')\n"
    )
    d12_post = (
        "import json\nimport urllib.request\n\n"
        "def post_json(url, payload):\n"
        "    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')\n"
        "    with urllib.request.urlopen(req, timeout=10) as r:\n"
        "        return json.loads(r.read())\n"
    )
    d25 = (
        "import json\nimport urllib.request\n\n"
        "def call_chat(api_key, messages, *, base_url='https://api.deepseek.com'):\n"
        "    body = json.dumps({'model': 'deepseek-chat', 'messages': messages, 'stream': False}).encode('utf-8')\n"
        "    req = urllib.request.Request(f'{base_url}/chat/completions', data=body, headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')\n"
        "    with urllib.request.urlopen(req, timeout=60) as r:\n"
        "        return json.loads(r.read())['choices'][0]['message']['content']\n"
    )
    for section_id, solution in [("D12-request", d12), ("D12-post", d12_post), ("D25-chat", d25)]:
        section = _section(curriculum, _task_id_of(curriculum_data, section_id), section_id)
        result = validate_code(section, solution, Path("."))
        assert result["passed"] is True, f"{section_id} 正确解未通过：{result['checks']}"


def test_pytest_validator_succeeds(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D15", "D15-assert")
    test_file = "assert 1 + 1 == 2\n"
    result = validate_code(section, test_file, Path("."))
    assert result["passed"] is True, result["stdout"]


def test_d13_ast_validator_requires_fastapi_structure(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D13", "D13-app")
    good = "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"
    bad = "app = None\n"
    assert validate_code(section, good, Path("."))["passed"] is True
    assert validate_code(section, bad, Path("."))["passed"] is False


def test_timeout_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    import learnctl.practice as practice

    def fake_run_proc(*args: object, **kwargs: object) -> dict:
        return {"timeout": True, "stdout": "", "stderr": "超时", "exit_code": None}

    monkeypatch.setattr(practice, "_run_proc", fake_run_proc)
    curriculum = _curriculum()
    section = _section(curriculum, "D02", "D02-names")
    result = validate_code(section, "value = 1\nprint(type(value).__name__)\nprint(isinstance(value, int))\n", Path("."))
    assert result["passed"] is False
    assert any("超时" in c["name"] for c in result["checks"])


def test_output_is_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    import learnctl.practice as practice

    def fake_run_proc(*args: object, **kwargs: object) -> dict:
        return {"timeout": False, "stdout": "x" * (MAX_OUTPUT_CHARS + 5000), "stderr": "", "exit_code": 0}

    monkeypatch.setattr(practice, "_run_proc", fake_run_proc)
    curriculum = _curriculum()
    section = _section(curriculum, "D02", "D02-names")
    result = validate_code(section, "value = 1\nprint(type(value).__name__)\nprint(isinstance(value, int))\n", Path("."))
    assert len(result["stdout"]) <= MAX_OUTPUT_CHARS + 100


def test_draft_save_load_roundtrip(tmp_path: Path) -> None:
    save_draft(tmp_path, "D02", "D02-names", "value = 1")
    draft = load_draft(tmp_path, "D02", "D02-names")
    assert draft is not None
    assert draft["content"] == "value = 1"
    assert draft["section_id"] == "D02-names"
    assert load_draft(tmp_path, "D02", "missing-section") is None


def test_completion_is_idempotent_and_task_not_auto_done(tmp_path: Path, curriculum_data: dict) -> None:
    from learnctl.progress import initial_progress, task_status

    curriculum = _curriculum()
    progress_path = tmp_path / ".learn" / "progress.json"
    state = initial_progress(curriculum)
    state["tasks"]["D01"] = {"status": "done", "evidence": ["环境通过"]}
    complete_section(curriculum, state, progress_path, "D02", "D02-execution")
    complete_section(curriculum, state, progress_path, "D02", "D02-execution")
    assert state["lesson_progress"]["D02"]["completed_sections"] == ["D02-execution"]
    assert task_status(state, "D02") == "todo"

    with pytest.raises(UsageError):
        complete_section(curriculum, state, progress_path, "D02", "no-such-section")


def test_section_gate_is_sequential_and_backend_authoritative(tmp_path: Path) -> None:
    curriculum = _curriculum()
    from learnctl.progress import initial_progress

    state = initial_progress(curriculum)
    d02 = curriculum["_index"]["tasks"]["D02"]
    d03 = curriculum["_index"]["tasks"]["D03"]
    with pytest.raises(BlockedError, match="D01"):
        assert_section_unlocked(curriculum, state, d02, "D02-execution")

    state["tasks"]["D01"] = {"status": "done", "evidence": ["环境验证"]}
    assert_section_unlocked(curriculum, state, d02, "D02-execution")
    with pytest.raises(BlockedError, match="D02-execution"):
        assert_section_unlocked(curriculum, state, d02, "D02-names")
    with pytest.raises(BlockedError, match="D02"):
        assert_section_unlocked(curriculum, state, d03, "D03-if")

    state["lesson_progress"]["D02"]["completed_sections"] = [s["id"] for s in d02["lesson"]]
    state["tasks"]["D02"] = {"status": "done", "evidence": ["六节语法均通过"]}
    assert_section_unlocked(curriculum, state, d03, "D03-if")


def test_run_validation_returns_full_result_shape(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    result = run_validation(curriculum, "D02", "D02-names", "value = 1\nprint(type(value).__name__)\nprint(isinstance(value, int))\n", Path("."))
    assert {"passed", "checks", "stdout", "stderr", "exit_code"} <= set(result.keys())
    assert isinstance(result["checks"], list)


# ---------------------------------------------------------------------------
# 可信完成机制
# ---------------------------------------------------------------------------

def test_task_done_blocked_without_section_validation(tmp_path: Path, curriculum_data: dict) -> None:
    from learnctl.errors import BlockedError
    from learnctl.progress import initial_progress, save_progress
    from learnctl.workflow import update_task

    curriculum = _curriculum()
    progress_path = tmp_path / ".learn" / "progress.json"
    state = initial_progress(curriculum)
    # 先完成 D01 及其全部小节
    state["lesson_progress"]["D01"]["completed_sections"] = [
        "D01-onboarding", "D01-detect", "D01-create-venv", "D01-install", "D01-verify"
    ]
    state["tasks"]["D01"] = {"status": "done", "evidence": ["环境通过"]}
    save_progress(progress_path, state)

    # D02 有 3 个必修小节，全部未验证 → 不允许 done
    with pytest.raises(BlockedError, match="尚未通过全部必修小节验证"):
        update_task(curriculum, state, progress_path, "D02", "done", "手动")

    # 验证一个后仍不能 done
    state["lesson_progress"]["D02"]["completed_sections"] = ["D02-execution"]
    save_progress(progress_path, state)
    with pytest.raises(BlockedError, match="D02-names"):
        update_task(curriculum, state, progress_path, "D02", "done", "手动")


def test_task_done_allowed_after_all_sections_verified(tmp_path: Path, curriculum_data: dict) -> None:
    from learnctl.progress import initial_progress, save_progress
    from learnctl.workflow import update_task

    curriculum = _curriculum()
    progress_path = tmp_path / ".learn" / "progress.json"
    state = initial_progress(curriculum)
    # D01 全部小节通过 + D02 全部小节通过
    state["lesson_progress"]["D01"]["completed_sections"] = [
        "D01-onboarding", "D01-detect", "D01-create-venv", "D01-install", "D01-verify"
    ]
    state["lesson_progress"]["D02"]["completed_sections"] = [
        "D02-execution", "D02-names", "D02-numbers", "D02-bool-none", "D02-strings", "D02-string-methods"
    ]
    state["tasks"]["D01"] = {"status": "done", "evidence": ["完成"]}
    save_progress(progress_path, state)

    result = update_task(curriculum, state, progress_path, "D02", "done", "全部小节已验证")
    assert result["status"] == "done"


def test_supplemental_sections_are_still_required(tmp_path: Path, curriculum_data: dict) -> None:
    """supplemental 仍必修；只有明确标记 optional:true 的小节才非必修。"""
    from learnctl.workflow import required_sections

    curriculum = _curriculum()
    d17 = curriculum["_index"]["tasks"]["D17"]
    req = required_sections(d17)
    # D17 的异步小节标记为 supplemental 但无 optional → 仍是必修
    assert "D17-coroutine" in req
    assert "D17-timeout" in req

    # D02 六个核心语法小节都无 optional 标记 → 全部为必修
    d02 = curriculum["_index"]["tasks"]["D02"]
    req02 = required_sections(d02)
    assert set(req02) == {"D02-execution", "D02-names", "D02-numbers", "D02-bool-none", "D02-strings", "D02-string-methods"}

    # D18 的项目小节均为必修
    d18 = curriculum["_index"]["tasks"]["D18"]
    req18 = required_sections(d18)
    assert "D18-scope" in req18
    assert "D18-data-contract" in req18

    # 只有 optional:true 才非必修：合成任务验证（supplemental 不影响必修判定）
    synthetic = {
        "id": "SX",
        "lesson": [
            {"id": "s-opt", "optional": True},
            {"id": "s-supp", "supplemental": True},
            {"id": "s-plain"},
        ],
    }
    assert required_sections(synthetic) == ["s-supp", "s-plain"]


# ---------------------------------------------------------------------------
# B.1 UTF-8 子进程编码
# ---------------------------------------------------------------------------

def test_utf8_env_set_on_subprocess() -> None:
    from learnctl.practice import _run_proc
    import sys

    result = _run_proc(
        [sys.executable, "-c", "import os; print(os.environ.get('PYTHONIOENCODING', 'MISSING')); print(os.environ.get('PYTHONUTF8', 'MISSING'))"],
        Path("."),
    )
    assert "utf-8" in result["stdout"].casefold()
    assert "1" in result["stdout"]


def test_utf8_env_respects_caller_override() -> None:
    from learnctl.practice import _run_proc
    import sys

    result = _run_proc(
        [sys.executable, "-c", "import os; print('IOENC=' + os.environ.get('PYTHONIOENCODING', 'MISSING'))"],
        Path("."),
        env={"PYTHONIOENCODING": "latin-1"},
    )
    assert "IOENC=latin-1" in result["stdout"]


def test_chinese_stdout_in_subprocess() -> None:
    from learnctl.practice import _run_proc
    import sys

    result = _run_proc(
        [sys.executable, "-c", "print('你好，世界')"],
        Path("."),
    )
    assert "你好，世界" in result["stdout"]


# ---------------------------------------------------------------------------
# B.2 D10-dotenv 创建 .env 文件
# ---------------------------------------------------------------------------

def test_d10_dotenv_has_env_file_scaffold(curriculum_data: dict) -> None:
    """验证 D10-dotenv 脚手架包含 .env 文件并通过端到端测试。"""
    curriculum = _curriculum()
    section = _section(curriculum, "D10", "D10-dotenv")
    # end-to-end: correct solution passes (implies .env scaffold was created)
    solution = (
        "def load_dotenv(path):\n"
        "    try:\n"
        "        with open(path, encoding='utf-8') as f:\n"
        "            result = {}\n"
        "            for line in f:\n"
        "                line = line.strip()\n"
        "                if not line or line.startswith('#'):\n"
        "                    continue\n"
        "                if '=' in line:\n"
        "                    k, v = line.split('=', 1)\n"
        "                    result[k.strip()] = v.strip()\n"
        "            return result\n"
        "    except FileNotFoundError:\n"
        "        return {}\n"
    )
    result = validate_code(section, solution, Path("."))
    assert result["passed"] is True, f"D10-dotenv 应通过（.env 脚手架已创建）：{result['checks']}"


def test_d10_dotenv_correct_solution_passes(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D10", "D10-dotenv")
    solution = (
        "def load_dotenv(path):\n"
        "    result = {}\n"
        "    try:\n"
        "        with open(path, encoding='utf-8') as f:\n"
        "            for line in f:\n"
        "                line = line.strip()\n"
        "                if not line or line.startswith('#'):\n"
        "                    continue\n"
        "                if '=' in line:\n"
        "                    k, v = line.split('=', 1)\n"
        "                    result[k.strip()] = v.strip()\n"
        "    except FileNotFoundError:\n"
        "        return {}\n"
        "    return result\n"
    )
    result = validate_code(section, solution, Path("."))
    assert result["passed"] is True, f"D10-dotenv 正确解未通过：{result['checks']}"


def test_d10_dotenv_missing_file_returns_empty(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D10", "D10-dotenv")
    # 代码中 load_dotenv('missing.env') 不存在 → 返回 {}
    solution = (
        "def load_dotenv(path):\n"
        "    try:\n"
        "        with open(path, encoding='utf-8') as f:\n"
        "            result = {}\n"
        "            for line in f:\n"
        "                line = line.strip()\n"
        "                if not line or line.startswith('#'):\n"
        "                    continue\n"
        "                if '=' in line:\n"
        "                    k, v = line.split('=', 1)\n"
        "                    result[k.strip()] = v.strip()\n"
        "            return result\n"
        "    except FileNotFoundError:\n"
        "        return {}\n"
    )
    result = validate_code(section, solution, Path("."))
    assert result["passed"] is True, f"缺失文件应返回空：{result['checks']}"


# ---------------------------------------------------------------------------
# B.3 D17-timeout
# ---------------------------------------------------------------------------

def test_d17_timeout_correct_solution_passes(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D17", "D17-timeout")
    # run(3, 2.0) 应返回 3（2s 超时足够完成约0.5s的操作）
    # run(3, 0.1) 应抛 TimeoutError（0.1s 太短）
    solution = (
        "import asyncio\n\n"
        "async def _slow(n):\n"
        "    await asyncio.sleep(0.5)\n"
        "    return n\n\n"
        "def run(n, timeout):\n"
        "    async def _inner():\n"
        "        return await asyncio.wait_for(_slow(n), timeout=timeout)\n"
        "    return asyncio.run(_inner())\n"
    )
    result = validate_code(section, solution, Path("."))
    assert result["passed"] is True, f"D17-timeout 正确解未通过：{result['checks']}"


def test_d17_timeout_wrong_no_timeout_fails(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D17", "D17-timeout")
    # 不调用 asyncio.wait_for → 不会超时
    solution = (
        "import asyncio\n\n"
        "async def _slow(n):\n"
        "    await asyncio.sleep(0)\n"
        "    return n\n\n"
        "def run(n, timeout):\n"
        "    return asyncio.run(_slow(n))\n"
    )
    result = validate_code(section, solution, Path("."))
    assert result["passed"] is False, "忽略 timeout 的实现不应通过"


# ---------------------------------------------------------------------------
# C. D18-D24 项目落盘
# ---------------------------------------------------------------------------

def test_project_artifact_written_on_validation_pass(curriculum_data: dict, tmp_path: Path) -> None:
    curriculum = _curriculum()
    # D19-config 有 project_file: taskproj/config.py
    section = _section(curriculum, "D19", "D19-config")
    assert section["practice"].get("project_file") == "taskproj/config.py"

    solution = (
        "import os\nfrom pathlib import Path\n\n"
        "def get_db_path():\n"
        "    return Path(os.environ.get('TASKPROJ_DB', 'taskproj.db'))\n\n"
        "def get_int_env(name, default):\n"
        "    try:\n"
        "        return int(os.environ.get(name))\n"
        "    except (TypeError, ValueError):\n"
        "        return default\n"
    )
    _write_workspace_project(tmp_path, config="")
    result = run_validation(curriculum, "D19", "D19-config", solution, tmp_path)
    assert result["passed"] is True

    # 产物应写入 learner_workspace/task-manager/taskproj/config.py
    artifact = tmp_path / "learner_workspace" / "task-manager" / "taskproj" / "config.py"
    assert artifact.is_file(), f"产物未写入 {artifact}"
    content = artifact.read_text(encoding="utf-8")
    assert "def get_db_path()" in content


def test_project_artifact_not_written_on_validation_fail(curriculum_data: dict, tmp_path: Path) -> None:
    curriculum = _curriculum()
    section = _section(curriculum, "D19", "D19-config")
    bad = "def broken("
    result = run_validation(curriculum, "D19", "D19-config", bad, tmp_path)
    assert result["passed"] is False
    artifact = tmp_path / "learner_workspace" / "task-manager" / "taskproj" / "config.py"
    assert not artifact.is_file(), "失败不应落盘"


def test_d24_project_acceptance_empty_workspace_fails(tmp_path: Path) -> None:
    from learnctl.practice import validate_project_acceptance

    result = validate_project_acceptance(tmp_path)
    assert result["passed"] is False
    assert any("文件完整" in c["name"] and c["passed"] is False for c in result["checks"])


def test_d24_project_acceptance_full_project_passes(tmp_path: Path) -> None:
    from learnctl.practice import validate_project_acceptance, _workspace_dir

    ws = _workspace_dir(tmp_path)
    _write_full_project(ws)

    result = validate_project_acceptance(tmp_path)
    assert result["passed"] is True, f"验收未通过：{[(c['name'], c['passed'], c.get('detail')) for c in result['checks']]}"


def test_d24_project_acceptance_missing_file_fails(tmp_path: Path) -> None:
    from learnctl.practice import validate_project_acceptance, _workspace_dir

    ws = _workspace_dir(tmp_path)
    _write_full_project(ws)
    # 删掉 15 个必需产物之一 → 文件完整检查必须失败
    (ws / "docs/review.md").unlink()

    result = validate_project_acceptance(tmp_path)
    assert result["passed"] is False
    assert any("文件完整" in c["name"] and c["passed"] is False for c in result["checks"])


def test_d24_project_acceptance_bad_api_fails(tmp_path: Path) -> None:
    from learnctl.practice import validate_project_acceptance, _workspace_dir

    ws = _workspace_dir(tmp_path)
    _write_full_project(ws)
    # 换成只做 CRUD、没有 GET / 与 /health 的 api.py → TestClient 检查必须失败
    (ws / "taskproj/api.py").write_text(_GOOD_API, encoding="utf-8")

    result = validate_project_acceptance(tmp_path)
    assert result["passed"] is False
    assert any("GET /health" in c["name"] and c["passed"] is False for c in result["checks"])


def test_d24_project_acceptance_bad_cli_fails(tmp_path: Path) -> None:
    from learnctl.practice import validate_project_acceptance, _workspace_dir

    ws = _workspace_dir(tmp_path)
    _write_full_project(ws)
    # cli 没有任何子命令：add 不落库，list 也看不到任务 → CLI 检查必须失败
    (ws / "taskproj/cli.py").write_text(
        "def main(argv=None):\n    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n",
        encoding="utf-8",
    )

    result = validate_project_acceptance(tmp_path)
    assert result["passed"] is False
    assert any("CLI" in c["name"] and c["passed"] is False for c in result["checks"])


def test_d23_web_html_validator_accepts_real_html(tmp_path: Path) -> None:
    curriculum = _curriculum()
    good = (
        "<!doctype html>\n<html><body>\n"
        '<input id="title" placeholder="新任务">\n<button id="add">添加</button>\n'
        "<ul id=\"list\"></ul>\n"
        "<script>\n"
        "fetch('/api/tasks').then(r => r.json()).then(items => {\n"
        "  items.forEach(t => {\n"
        "    const li = document.createElement('li');\n"
        "    li.textContent = t.title;\n"
        "    const done = document.createElement('button');\n"
        "    done.textContent = '完成';\n"
        "    done.onclick = () => fetch('/api/tasks/' + t.id + '/done', {method: 'PATCH'});\n"
        "    const del = document.createElement('button');\n"
        "    del.textContent = '删除';\n"
        "    del.onclick = () => fetch('/api/tasks/' + t.id, {method: 'DELETE'});\n"
        "    li.appendChild(done); li.appendChild(del);\n"
        "    list.appendChild(li);\n"
        "  });\n"
        "});\n"
        "</script>\n"
        "</body></html>\n"
    )
    result = run_validation(curriculum, "D23", "D23-html-fetch", good, tmp_path)
    assert result["passed"] is True, f"真实 HTML 应通过：{[(c['name'], c['passed']) for c in result['checks']]}"


def test_d23_web_html_validator_rejects_bare_text(tmp_path: Path) -> None:
    curriculum = _curriculum()
    result = run_validation(curriculum, "D23", "D23-html-fetch", "写一个网页", tmp_path)
    assert result["passed"] is False


def test_d19_pyproject_toml_validator_accepts_real_toml(tmp_path: Path) -> None:
    curriculum = _curriculum()
    result = run_validation(curriculum, "D19", "D19-pyproject", _GOOD_PYPROJECT, tmp_path)
    assert result["passed"] is True, f"合法 pyproject.toml 应通过：{[(c['name'], c['passed']) for c in result['checks']]}"


def test_d19_pyproject_toml_validator_rejects_incomplete(tmp_path: Path) -> None:
    curriculum = _curriculum()
    result = run_validation(curriculum, "D19", "D19-pyproject", '[project]\nname = "taskproj"\n', tmp_path)
    assert result["passed"] is False


# ---------------------------------------------------------------------------
# D. workspace_deps 真实文件进入校验器 + D22-api/D23-cli 回归
# ---------------------------------------------------------------------------

_GOOD_CONFIG = (
    "import os\nfrom pathlib import Path\n\n"
    "def get_db_path():\n    return Path(os.environ.get('TASKPROJ_DB', 'taskproj.db'))\n"
)

_GOOD_DB = (
    "import sqlite3\n\n"
    "def create_connection(path):\n    conn = sqlite3.connect(str(path))\n    init_db(conn)\n    return conn\n\n"
    "def init_db(conn):\n"
    "    conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')\n"
    "    conn.commit()\n\n"
    "def add_task(conn, title):\n"
    "    if not title.strip(): raise ValueError('标题为空')\n"
    "    cur = conn.execute('INSERT INTO tasks (title) VALUES (?)', (title,))\n"
    "    conn.commit()\n"
    "    return cur.lastrowid\n\n"
    "def list_tasks(conn):\n"
    "    rows = conn.execute('SELECT id, title, done FROM tasks ORDER BY id').fetchall()\n"
    "    return [{'id': r[0], 'title': r[1], 'done': bool(r[2])} for r in rows]\n\n"
    "def complete_task(conn, task_id):\n"
    "    conn.execute('UPDATE tasks SET done = 1 WHERE id = ?', (task_id,))\n"
    "    conn.commit()\n\n"
    "def delete_task(conn, task_id):\n"
    "    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))\n"
    "    conn.commit()\n"
)

_GOOD_API = (
    "from fastapi import FastAPI, HTTPException\n"
    "from pydantic import BaseModel\n"
    "from taskproj.db import add_task, complete_task, create_connection, delete_task, list_tasks\n"
    "from taskproj.config import get_db_path\n\n"
    "class TaskIn(BaseModel):\n"
    "    title: str\n\n"
    "class Task(BaseModel):\n"
    "    id: int\n"
    "    title: str\n"
    "    done: bool\n\n"
    "app = FastAPI()\n\n"
    "def _conn():\n"
    "    return create_connection(get_db_path())\n\n"
    "def _get_task_or_404(task_id: int):\n"
    "    conn = _conn()\n"
    "    rows = conn.execute('SELECT id FROM tasks WHERE id = ?', (task_id,)).fetchall()\n"
    "    if not rows:\n"
    "        raise HTTPException(status_code=404, detail='任务不存在')\n"
    "    return conn\n\n"
    "@app.get('/api/tasks')\n"
    "def read_tasks():\n"
    "    return list_tasks(_conn())\n\n"
    "@app.post('/api/tasks')\n"
    "def create_task(task: TaskIn):\n"
    "    if not task.title.strip():\n"
    "        raise HTTPException(status_code=422, detail='标题不能为空')\n"
    "    conn = _conn()\n"
    "    tid = add_task(conn, task.title)\n"
    "    return next(t for t in list_tasks(conn) if t['id'] == tid)\n\n"
    "@app.patch('/api/tasks/{task_id}/done')\n"
    "def complete(task_id: int):\n"
    "    conn = _get_task_or_404(task_id)\n"
    "    complete_task(conn, task_id)\n"
    "    return next(t for t in list_tasks(conn) if t['id'] == task_id)\n\n"
    "@app.delete('/api/tasks/{task_id}')\n"
    "def remove(task_id: int):\n"
    "    conn = _get_task_or_404(task_id)\n"
    "    delete_task(conn, task_id)\n"
    "    return {'ok': True}\n"
)

_GOOD_CLI = (
    "import argparse\n"
    "from taskproj.db import add_task, complete_task, create_connection, delete_task, init_db, list_tasks\n"
    "from taskproj.config import get_db_path\n\n"
    "def build_parser():\n"
    "    parser = argparse.ArgumentParser()\n"
    "    sub = parser.add_subparsers(dest='command', required=True)\n"
    "    add = sub.add_parser('add')\n"
    "    add.add_argument('title')\n"
    "    sub.add_parser('list')\n"
    "    done = sub.add_parser('done')\n"
    "    done.add_argument('task_id', type=int)\n"
    "    rm = sub.add_parser('rm')\n"
    "    rm.add_argument('task_id', type=int)\n"
    "    return parser\n\n"
    "def main(argv=None):\n"
    "    args = build_parser().parse_args(argv)\n"
    "    conn = create_connection(get_db_path())\n"
    "    if args.command == 'add':\n"
    "        add_task(conn, args.title)\n"
    "    elif args.command == 'list':\n"
    "        for t in list_tasks(conn):\n"
    "            done_flag = '[done]' if t['done'] else '[]'\n"
    "            print(f\"{t['id']}. {t['title']} {done_flag}\")\n"
    "    elif args.command == 'done':\n"
    "        complete_task(conn, args.task_id)\n"
    "    elif args.command == 'rm':\n"
    "        delete_task(conn, args.task_id)\n"
    "    return 0\n\n"
    "if __name__ == '__main__':\n"
    "    raise SystemExit(main())\n"
)

_TEST_API = (
    "import os\n"
    "from fastapi.testclient import TestClient\n"
    "from taskproj.api import app\n\n"
    "client = TestClient(app)\n\n"
    "def test_health(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    resp = client.get('/api/tasks')\n"
    "    assert resp.status_code == 200\n"
    "    assert resp.json() == []\n\n"
    "def test_crud(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    resp = client.post('/api/tasks', json={'title': '买牛奶'})\n"
    "    assert resp.status_code == 200\n"
    "    task = resp.json()\n"
    "    assert task['title'] == '买牛奶'\n"
    "    assert task['done'] is False\n"
    "    tid = task['id']\n"
    "    assert any(t['id'] == tid for t in client.get('/api/tasks').json())\n"
    "    resp = client.patch(f'/api/tasks/{tid}/done')\n"
    "    assert resp.status_code == 200\n"
    "    assert client.get('/api/tasks').json()[0]['done'] is True\n"
    "    resp = client.delete(f'/api/tasks/{tid}')\n"
    "    assert resp.status_code == 200\n"
    "    assert client.get('/api/tasks').json() == []\n\n"
    "def test_404(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    assert client.patch('/api/tasks/999999/done').status_code == 404\n"
    "    assert client.delete('/api/tasks/999999').status_code == 404\n\n"
    "def test_422(tmp_path):\n"
    "    os.environ['TASKPROJ_DB'] = str(tmp_path / 't.db')\n"
    "    assert client.post('/api/tasks', json={'title': ''}).status_code == 422\n"
)


def _write_workspace_project(
    project_root: Path,
    *,
    api: str | None = None,
    db: str | None = None,
    config: str | None = None,
) -> None:
    ws = project_root / "learner_workspace" / "task-manager"
    (ws / "taskproj").mkdir(parents=True, exist_ok=True)
    (ws / "taskproj/__init__.py").write_text("", encoding="utf-8")
    if config is not None:
        (ws / "taskproj/config.py").write_text(config, encoding="utf-8")
    if db is not None:
        (ws / "taskproj/db.py").write_text(db, encoding="utf-8")
    if api is not None:
        (ws / "taskproj/api.py").write_text(api, encoding="utf-8")


_GOOD_API_FULL = (
    "from fastapi import FastAPI, HTTPException\n"
    "from fastapi.responses import FileResponse\n"
    "from pydantic import BaseModel\n"
    "from pathlib import Path\n"
    "from taskproj.db import add_task, complete_task, create_connection, delete_task, list_tasks\n"
    "from taskproj.config import get_db_path\n\n"
    "class TaskIn(BaseModel):\n    title: str\n\n"
    "class Task(BaseModel):\n    id: int\n    title: str\n    done: bool\n\n"
    "app = FastAPI()\n\n"
    "def _conn():\n    return create_connection(get_db_path())\n\n"
    "def _get_task_or_404(task_id: int):\n"
    "    conn = _conn()\n"
    "    rows = conn.execute('SELECT id FROM tasks WHERE id = ?', (task_id,)).fetchall()\n"
    "    if not rows:\n"
    "        raise HTTPException(status_code=404, detail='任务不存在')\n"
    "    return conn\n\n"
    "@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n\n"
    "@app.get('/')\ndef index():\n    return FileResponse(Path('taskproj/static/index.html'))\n\n"
    "@app.get('/api/tasks')\ndef read_tasks():\n    return list_tasks(_conn())\n\n"
    "@app.post('/api/tasks')\ndef create_task(task: TaskIn):\n"
    "    if not task.title.strip():\n"
    "        raise HTTPException(status_code=422, detail='标题不能为空')\n"
    "    conn = _conn()\n"
    "    tid = add_task(conn, task.title)\n"
    "    return next(t for t in list_tasks(conn) if t['id'] == tid)\n\n"
    "@app.patch('/api/tasks/{task_id}/done')\ndef complete(task_id: int):\n"
    "    conn = _get_task_or_404(task_id)\n"
    "    complete_task(conn, task_id)\n"
    "    return next(t for t in list_tasks(conn) if t['id'] == task_id)\n\n"
    "@app.delete('/api/tasks/{task_id}')\ndef remove(task_id: int):\n"
    "    conn = _get_task_or_404(task_id)\n"
    "    delete_task(conn, task_id)\n"
    "    return {'ok': True}\n"
)

_GOOD_INDEX_HTML = (
    "<!doctype html>\n<html><body>\n"
    '<input id="title" placeholder="新任务">\n<button id="add">添加</button>\n'
    "<script>\nfetch('/api/tasks').then(r => r.json());\n</script>\n"
    "</body></html>\n"
)

_GOOD_PYPROJECT = (
    '[build-system]\nrequires = ["setuptools>=68"]\nbuild-backend = "setuptools.build_meta"\n\n'
    '[project]\nname = "taskproj"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'
    'dependencies = ["fastapi>=0.100", "uvicorn[standard]>=0.23", "pydantic>=2"]\n\n'
    '[project.optional-dependencies]\ndev = ["pytest>=8", "httpx>=0.24"]\n'
)

_FULL_PROJECT: dict[str, str] = {
    "README.md": "# Task Manager\n",
    "contract.json": '{"task": {"id": 1, "title": "test", "done": false}, "endpoints": []}\n',
    "pyproject.toml": (
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n'
        '[project]\nname = "task-manager"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'
    ),
    "docs/requirements.md": "## 需求\n\n实现一个任务管理 CLI 与 Web API。\n",
    "docs/runbook.md": "## 运行手册\n\npython -m taskproj.cli add 买牛奶\n",
    "docs/review.md": "## 复盘\n\n本次任务完成 CLI 与 API 的 CRUD。\n",
    "taskproj/__init__.py": "",
    "taskproj/config.py": _GOOD_CONFIG,
    "taskproj/main.py": (
        "def main(argv=None):\n    print('任务管理项目已启动')\n    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    ),
    "taskproj/db.py": _GOOD_DB,
    "taskproj/api.py": _GOOD_API_FULL,
    "taskproj/cli.py": _GOOD_CLI,
    "taskproj/static/index.html": _GOOD_INDEX_HTML,
    "tests/__init__.py": "",
    "tests/test_project.py": (
        "import sqlite3\nfrom taskproj.db import init_db, add_task, list_tasks, complete_task, delete_task\n\n"
        "def test_crud(tmp_path):\n"
        "    conn = sqlite3.connect(str(tmp_path / 't.db'))\n"
        "    init_db(conn)\n"
        "    tid = add_task(conn, 'test')\n"
        "    assert list_tasks(conn)[0]['title'] == 'test'\n"
        "    complete_task(conn, tid)\n"
        "    assert list_tasks(conn)[0]['done'] is True\n"
        "    delete_task(conn, tid)\n"
        "    assert len(list_tasks(conn)) == 0\n"
    ),
    "tests/test_api.py": (
        "from fastapi.testclient import TestClient\n"
        "from taskproj.api import app\n\n"
        "def test_health():\n"
        "    resp = TestClient(app).get('/api/tasks')\n"
        "    assert resp.status_code == 200\n\n"
        "def test_crud():\n"
        "    client = TestClient(app)\n"
        "    assert client.post('/api/tasks', json={'title': 'x'}).json()['id'] == 1\n"
        "    assert client.get('/api/tasks').status_code == 200\n"
        "    assert client.patch('/api/tasks/1/done').json()['done'] is True\n"
        "    assert client.delete('/api/tasks/1').status_code == 200\n"
    ),
}


def _write_full_project(ws: Path) -> None:
    for rel, content in _FULL_PROJECT.items():
        target = ws / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def test_d22_api_declares_real_api_dependencies(curriculum_data: dict) -> None:
    section = _section(_curriculum(), "D22", "D22-api-tests")
    assert section["practice"]["project_file"] == "tests/test_api.py"
    deps = section["practice"]["workspace_deps"]
    assert {"taskproj/__init__.py", "taskproj/api.py", "taskproj/db.py", "taskproj/config.py"} <= set(deps)


def test_d23_cli_declares_real_workspace_deps(curriculum_data: dict) -> None:
    section = _section(_curriculum(), "D23", "D23-cli-parser")
    deps = section["practice"]["workspace_deps"]
    assert {"taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py"} <= set(deps)


def test_d22_api_workspace_dep_missing_fails(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    # D22-api-tests 声明依赖 __init__/config/db/api；缺 api.py 时校验直接失败
    _write_workspace_project(tmp_path, db=_GOOD_DB, config=_GOOD_CONFIG)
    result = run_validation(curriculum, "D22", "D22-api-tests", _TEST_API, tmp_path)
    assert result["passed"] is False
    assert any("缺少前置依赖" in c["name"] for c in result["checks"])


def test_workspace_dep_missing_fails_validation(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    # D23-cli-parser 声明依赖 db.py + config.py；缺 db.py 时校验直接失败，而不是静默跳过
    _write_workspace_project(tmp_path, config=_GOOD_CONFIG)
    result = run_validation(curriculum, "D23", "D23-cli-parser", _GOOD_CLI, tmp_path)
    assert result["passed"] is False
    assert any("缺少前置依赖" in c["name"] for c in result["checks"])


def test_d23_cli_passes_with_real_workspace_deps(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, db=_GOOD_DB, config=_GOOD_CONFIG)
    result = run_validation(curriculum, "D23", "D23-cli-parser", _GOOD_CLI, tmp_path)
    assert result["passed"] is True, f"正确真实依赖应通过：{result['checks']}"


def test_d23_cli_fails_when_workspace_db_corrupted(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, db="def broken(", config=_GOOD_CONFIG)
    result = run_validation(curriculum, "D23", "D23-cli-parser", _GOOD_CLI, tmp_path)
    assert result["passed"] is False, "损坏的 db.py 不应被标准脚手架掩盖"


def test_d23_cli_fails_when_workspace_config_corrupted(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, db=_GOOD_DB, config="def broken(")
    result = run_validation(curriculum, "D23", "D23-cli-parser", _GOOD_CLI, tmp_path)
    assert result["passed"] is False, "损坏的 config.py 不应被标准脚手架掩盖"


def test_d22_api_passes_with_real_workspace_deps(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, api=_GOOD_API, db=_GOOD_DB, config=_GOOD_CONFIG)
    result = run_validation(curriculum, "D22", "D22-api-tests", _TEST_API, tmp_path)
    assert result["passed"] is True, f"TestClient 测真实 api/db/config 应通过：{result['checks']}"


def test_d22_api_fails_when_workspace_db_corrupted(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, api=_GOOD_API, db="def broken(", config=_GOOD_CONFIG)
    result = run_validation(curriculum, "D22", "D22-api-tests", _TEST_API, tmp_path)
    assert result["passed"] is False, "损坏的 db.py 应使 D22-api 校验失败"


def test_d22_api_fails_when_workspace_config_corrupted(tmp_path: Path, curriculum_data: dict) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, api=_GOOD_API, db=_GOOD_DB, config="def broken(")
    result = run_validation(curriculum, "D22", "D22-api-tests", _TEST_API, tmp_path)
    assert result["passed"] is False, "损坏的 config.py 应使 D22-api 校验失败"


def test_beginner_goal_and_first_functions_use_actual_contract(tmp_path: Path) -> None:
    from learnctl.practice import validate_text

    curriculum = _curriculum()
    goal = _section(curriculum, "D01", "D01-onboarding")
    assert validate_text(goal, "我想用 Python 查询业务数据。")["passed"]
    assert not validate_text(goal, "")["passed"]

    cases = {
        "D02-numbers": (
            "def divide_parts(total, size):\n"
            "    if size == 0: raise ValueError('除数为零')\n"
            "    return total // size, total % size\n",
            "def divide_parts(total, size):\n"
            "    if size == 0: raise ValueError('除数为零')\n"
            "    return 0, 0\n",
        ),
        "D02-bool-none": (
            "def describe_value(value):\n"
            "    if value is None: return 'missing'\n"
            "    if value == '': return 'empty text'\n"
            "    return 'present'\n",
            "def describe_value(value):\n"
            "    return 'missing' if not value else 'present'\n",
        ),
    }
    for section_id, (good, bad) in cases.items():
        section = _section(curriculum, "D02", section_id)
        assert validate_code(section, good, tmp_path)["passed"], section_id
        assert not validate_code(section, bad, tmp_path)["passed"], section_id


def test_d20_create_list_does_not_require_update_delete(tmp_path: Path) -> None:
    section = _section(_curriculum(), "D20", "D20-create-list")
    _write_workspace_project(tmp_path, db="")
    code = (
        "import sqlite3\n"
        "def add_task(conn, title):\n"
        "    if not title.strip(): raise ValueError('标题为空')\n"
        "    cur = conn.execute('INSERT INTO tasks(title) VALUES (?)', (title,))\n"
        "    conn.commit()\n"
        "    return cur.lastrowid\n"
        "def list_tasks(conn):\n"
        "    rows = conn.execute('SELECT id, title, done FROM tasks ORDER BY id').fetchall()\n"
        "    return [{'id': row[0], 'title': row[1], 'done': bool(row[2])} for row in rows]\n"
    )
    assert validate_code(section, code, tmp_path)["passed"]
    later = _section(_curriculum(), "D20", "D20-update-delete")
    assert not validate_code(later, code, tmp_path)["passed"]


def test_d23_parser_only_requires_add_and_list(tmp_path: Path) -> None:
    curriculum = _curriculum()
    _write_workspace_project(tmp_path, db=_GOOD_DB, config=_GOOD_CONFIG)
    code = (
        "import argparse\n"
        "from taskproj.db import add_task, create_connection, list_tasks\n"
        "from taskproj.config import get_db_path\n"
        "def build_parser():\n"
        "    parser = argparse.ArgumentParser()\n"
        "    sub = parser.add_subparsers(dest='command', required=True)\n"
        "    add = sub.add_parser('add')\n"
        "    add.add_argument('title')\n"
        "    sub.add_parser('list')\n"
        "    return parser\n"
        "def main(argv=None):\n"
        "    args = build_parser().parse_args(argv)\n"
        "    conn = create_connection(get_db_path())\n"
        "    if args.command == 'add': add_task(conn, args.title)\n"
        "    if args.command == 'list':\n"
        "        for item in list_tasks(conn): print(item['title'])\n"
        "    return 0\n"
        "if __name__ == '__main__': raise SystemExit(main())\n"
    )
    assert run_validation(curriculum, "D23", "D23-cli-parser", code, tmp_path)["passed"]
    assert not run_validation(curriculum, "D23", "D23-cli-mutate", code, tmp_path)["passed"]


def test_d11_file_uses_course_function_name(tmp_path: Path) -> None:
    section = _section(_curriculum(), "D11", "D11-file")
    good = (
        "import logging\n"
        "def configure_file_logger(path):\n"
        "    logger = logging.getLogger('learning-file')\n"
        "    logger.setLevel(logging.INFO)\n"
        "    for handler in logger.handlers[:]:\n"
        "        logger.removeHandler(handler)\n"
        "        handler.close()\n"
        "    handler = logging.FileHandler(path, encoding='utf-8')\n"
        "    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))\n"
        "    logger.addHandler(handler)\n"
        "    return logger\n"
    )
    assert validate_code(section, good, tmp_path)["passed"]
    assert not validate_code(section, good.replace("configure_file_logger", "setup_file_logger"), tmp_path)["passed"]

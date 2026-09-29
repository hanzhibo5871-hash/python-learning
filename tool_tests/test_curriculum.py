from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from conftest import REPOSITORY, run_cli
from learnctl.curriculum import PRACTICE_KINDS, validate_curriculum
from learnctl.errors import DataError


def test_curriculum_route_and_counts(curriculum_data: dict) -> None:
    validated = validate_curriculum(deepcopy(curriculum_data))
    assert len(validated["source_catalog"]) == 131
    assert len(validated["stages"]) == 4
    assert [stage["id"] for stage in validated["stages"]] == ["S1", "S2", "S3", "S4"]
    assert len(validated["tasks"]) == 28
    sections = [s for task in validated["tasks"] for s in task["lesson"]]
    assert len(sections) == 146
    all_titles = " ".join(
        [stage["title"] for stage in validated["stages"]]
        + [task["title"] for task in validated["tasks"]]
        + [section["title"] for task in validated["tasks"] for section in task["lesson"]]
    )
    for keyword in ["基础语法", "常用开发", "SQLite", "asyncio", "真实项目", "AI 应用", "FastAPI", "测试"]:
        assert keyword in all_titles, f"路线缺少关键词 {keyword}"
    assert any(task["id"] == "D01" for task in validated["tasks"])


def test_no_quiz_anywhere_in_data(curriculum_data: dict) -> None:
    serialized = json.dumps(curriculum_data, ensure_ascii=False)
    # quiz 相关字段结构绝不允许出现；argparse 的 choices 参数不属于选择题
    for forbidden in ("quiz", "answer_index", "choice_index", '"choices":', '"radio"'):
        assert forbidden not in serialized, f"数据中不应出现 {forbidden}"


def test_every_section_practice_is_valid_and_code_dominant(curriculum_data: dict) -> None:
    sections = [s for task in curriculum_data["tasks"] for s in task["lesson"]]
    kinds = [s["practice"]["kind"] for s in sections]
    assert all(kind in PRACTICE_KINDS for kind in kinds)
    code_count = kinds.count("code")
    assert code_count / len(sections) > 0.5, f"code 占比必须过半，当前 {code_count}/{len(sections)}"
    section_ids = [s["id"] for s in sections]
    assert len(section_ids) == len(set(section_ids))
    for section in sections:
        practice = section["practice"]
        assert {"scenario", "instructions", "expected_behavior", "hints", "starter_content"} <= set(practice.keys())
        assert isinstance(practice["input_examples"], list)
        if practice["kind"] == "code":
            assert practice["file_name"].endswith(".py")
        elif practice["kind"] == "env_action":
            assert practice["action"] in {"detect", "create_venv", "install", "verify"}
        else:
            assert "file_name" not in practice


def test_catalog_refs_are_real_and_supplemental_gaps_explicit(curriculum_data: dict) -> None:
    source_ids = {item["id"] for item in curriculum_data["source_catalog"]}
    sections = [s for task in curriculum_data["tasks"] for s in task["lesson"]]
    for section in sections:
        for ref in section.get("catalog_refs", []):
            assert ref in source_ids, f"{section['id']} 引用了不存在的来源 {ref}"
        if not section.get("catalog_refs"):
            has_project_file = bool(section.get("practice", {}).get("project_file"))
            assert section.get("supplemental") is True or has_project_file, \
                f"{section['id']} 无 catalog_refs 且未标记 supplemental 也无 project_file"
        if section.get("supplemental"):
            assert section.get("supplemental_note"), f"{section['id']} supplemental 缺少说明"
    supplemental_sections = [s for s in sections if s.get("supplemental")]
    assert supplemental_sections, "必须存在 supplemental 缺口小节"
    for section in supplemental_sections:
        assert "supplemental_note" in section


def test_supplemental_modules_do_not_claim_index(curriculum_data: dict) -> None:
    claimed: list[str] = []
    for module in curriculum_data["modules"]:
        if module.get("supplemental"):
            assert module.get("supplemental_note")
            assert not module.get("catalog_refs"), "supplemental 模块不得占用真实索引引用"
            continue
        claimed.extend(module["catalog_refs"])
    assert len(claimed) == len(set(claimed))
    source_ids = {item["id"] for item in curriculum_data["source_catalog"]}
    assert set(claimed) == source_ids


def test_d01_is_real_environment_configuration(curriculum_data: dict) -> None:
    d01 = next(task for task in curriculum_data["tasks"] if task["id"] == "D01")
    assert "环境" in d01["title"]
    assert [section["practice"]["kind"] for section in d01["lesson"]] == [
        "text",
        "env_action",
        "env_action",
        "env_action",
        "env_action",
    ]
    actions = [section["practice"]["action"] for section in d01["lesson"] if section["practice"]["kind"] == "env_action"]
    assert actions == ["detect", "create_venv", "install", "verify"]
    assert not d01.get("exercise_ids"), "D01 不再绑定诊断练习"


def test_d01_has_specific_windows_environment_teaching(curriculum_data: dict) -> None:
    d01 = next(task for task in curriculum_data["tasks"] if task["id"] == "D01")
    sections = {section["id"]: section for section in d01["lesson"]}
    assert list(sections) == ["D01-onboarding", "D01-detect", "D01-create-venv", "D01-install", "D01-verify"]
    serialized = json.dumps(d01, ensure_ascii=False)
    for forbidden in ("value = 0", "value = 1", "本节的核心结构是", "最小输入没有形成可观察", "先为 "):
        assert forbidden not in serialized
    expected_actions = {
        "D01-detect": ("detect", "where.exe python", "python --version", "Get-Location"),
        "D01-create-venv": ("create_venv", "python -m venv .venv", ".venv\\Scripts\\python.exe", "ExecutionPolicy"),
        "D01-install": ("install", ".venv\\Scripts\\python.exe -m pip", "pip install -e", "pytest"),
        "D01-verify": ("verify", "python -c", "pytest", "成功标准"),
    }
    for section_id, (action, *markers) in expected_actions.items():
        section = sections[section_id]
        practice = section["practice"]
        assert practice["kind"] == "env_action"
        assert practice["action"] == action
        # JSON escapes Windows backslashes; unescape only for the human-facing
        # marker check so the regression asserts the curriculum text itself.
        text = json.dumps(section, ensure_ascii=False).replace("\\\\", "\\")
        assert all(marker in text for marker in markers), (section_id, markers)
        assert practice["input_examples"]
        assert all(item["value"] != "重复执行或检查失败路径" for item in practice["input_examples"])
        assert all(example["source_kind"] == "command" and example["runnable"] is False for example in section["examples"])
        assert all(example.get("target_path") == "Windows PowerShell" for example in section["examples"])
    onboarding = sections["D01-onboarding"]
    assert onboarding["practice"]["kind"] == "text"
    assert all(example["source_kind"] == "file_fragment" and not example["runnable"] for example in onboarding["examples"])
    assert all(example.get("target_path") == "D01 学习目标输入框" for example in onboarding["examples"])
    assert "写一句" in onboarding["practice"]["instructions"]
    assert "环境" in onboarding["objective"]


def test_schema_and_dag_invariants(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    with pytest.raises(DataError, match="仅支持版本"):
        mutated = deepcopy(data)
        mutated["schema_version"] = 1
        validate_curriculum(mutated)


def test_v3_teaching_contract_and_core_coverage(curriculum_data: dict) -> None:
    core = {
        "D02-execution", "D02-names", "D02-numbers", "D02-bool-none", "D02-strings", "D02-string-methods",
        "D03-if", "D03-match", "D03-for", "D03-while", "D03-break-continue", "D03-enumerate-zip", "D03-comprehension",
        "D04-def-return", "D04-default-keyword", "D04-varargs", "D04-scope", "D04-global-nonlocal", "D04-lambda", "D04-type-hints",
        "D05-list-tuple", "D05-dict-set", "D05-mutability", "D05-unpacking", "D05-traversal", "D05-comprehensions", "D05-iterators-generators",
        "D06-exception-types", "D06-try-except", "D06-else-finally", "D06-raise", "D06-custom", "D06-with",
        "D07-import", "D07-package", "D07-main", "D07-stdlib", "D07-class-instance", "D07-inheritance", "D07-dataclass",
    }
    sections = {section["id"]: section for task in curriculum_data["tasks"] for section in task["lesson"]}
    assert set(sections) >= core
    assert len(core) == 40
    for section in sections.values():
        assert isinstance(section["objective"], str) and section["objective"].strip()
        assert len(section["explanation"]) >= 3
        assert len(section["examples"]) >= 2
        assert all(example["code"] and "output" in example and example["explanation"] for example in section["examples"])
        assert len(section["common_errors"]) >= 2
        assert section["guided_practice"]

    forbidden = (
        "本节先用初学者语言理解",
        "不要把语法当成孤立规则",
        "示例把一个小动作拆开",
    )
    explanation_values: list[str] = []
    error_values: list[str] = []
    guided_values: list[str] = []
    teaching_sections = [
        section for section in sections.values()
        if 2 <= int(section["id"][1:3]) <= 24
    ]
    for section in teaching_sections:
        serialized = json.dumps(section, ensure_ascii=False)
        assert not any(text in serialized for text in forbidden), section["id"]
        assert "。。" not in serialized, section["id"]
        for example in section["examples"]:
            text = example["explanation"]
            assert len(text) >= 48
            assert sum(text.count(mark) for mark in "。！？；") >= 2
        for error in section["common_errors"]:
            assert error["example"]["code"]
            assert error["example"]["symptom"]
            assert error["example"]["fix"]
        guided = section["guided_practice"]
        assert isinstance(guided, dict) and guided["goal"] and guided["check"]
        assert all(step["action"] and step["expected"] for step in guided["steps"])
        explanation_values.append("\n".join(section["explanation"]))
        error_values.extend(error["error"] + error["cause"] for error in section["common_errors"])
        guided_values.append(json.dumps(guided, ensure_ascii=False, sort_keys=True))
    assert len(set(explanation_values)) == len(explanation_values)
    assert len(set(guided_values)) == len(guided_values)
    assert len(set(error_values)) == len(error_values)

    core_sections = {section_id: sections[section_id] for section_id in core}
    from learnctl.drills import SCRIPT_CASES
    for section_id, section in core_sections.items():
        practice = section["practice"]
        identifiers = practice.get("input_identifiers", [])
        values = "\n".join(item["value"] for item in practice["input_examples"])
        # 入门脚本的公开输入是 stdin 文本；函数课才需要公开调用标识符。
        if section_id not in SCRIPT_CASES:
            assert identifiers and all(identifier in values for identifier in identifiers), section_id
        assert len(practice["input_examples"]) >= 2
        assert all(item["expected"] for item in practice["input_examples"])
        policy = practice.get("starter_policy")
        if "NotImplementedError" in practice["starter_content"]:
            assert policy == "function_body", section_id
        else:
            assert policy == "complete", section_id

    mutated = deepcopy(curriculum_data)
    mutated["tasks"][1]["lesson"][0].pop("objective")
    with pytest.raises(DataError, match="objective"):
        validate_curriculum(mutated)

    mutated = deepcopy(curriculum_data)
    mutated["tasks"][1]["lesson"][0]["examples"] = [mutated["tasks"][1]["lesson"][0]["examples"][0]]
    with pytest.raises(DataError, match="至少有 2 个"):
        validate_curriculum(mutated)
    with pytest.raises(DataError, match="循环"):
        mutated = deepcopy(curriculum_data)
        mutated["tasks"][0]["prerequisites"] = ["D02"]
        validate_curriculum(mutated)
    with pytest.raises(DataError, match="覆盖不完整"):
        mutated = deepcopy(curriculum_data)
        first_module = next(m for m in mutated["modules"] if not m.get("supplemental"))
        first_module["catalog_refs"] = first_module["catalog_refs"][:-1]
        validate_curriculum(mutated)


def test_core_example_explanations_match_their_own_code(curriculum_data: dict) -> None:
    sections = {section["id"]: section for task in curriculum_data["tasks"] for section in task["lesson"]}
    expected_fragments = {
        "D02-strings": [("text[0]", "text[1:4]", "IndexError"), ("text +", "new_text", "空字符串")],
        "D04-global-nonlocal": [("global counter", "add_global", "UnboundLocalError"), ("make_counter", "nonlocal value", "独立")],
        "D05-mutability": [("alias = items", "alias.append", "没有复制"), ("items.copy()", "copy_items", "浅复制")],
        "D06-with": [("path.open", "read_text", "写入句柄"), ("StringIO", "stream.read", "资源已关闭")],
        "D07-dataclass": [("Point", "x/y", "缺少坐标"), ("default_factory", "Bag", "items=[]")],
    }
    for section_id, examples in expected_fragments.items():
        section = sections[section_id]
        assert len(section["examples"]) == 2
        for example, fragments in zip(section["examples"], examples):
            explanation = example["explanation"]
            assert all(fragment in explanation for fragment in fragments), (section_id, explanation)
            assert len(explanation) >= 48
            assert sum(explanation.count(mark) for mark in "。！？；") >= 2


def test_core_example_explanations_do_not_borrow_other_example_topics(curriculum_data: dict) -> None:
    sections = {section["id"]: section for task in curriculum_data["tasks"] for section in task["lesson"]}
    forbidden_by_example = {
        "D02-strings": [("strip", "[::-1]", "transform_text"), ("strip", "transform_text")],
        "D04-global-nonlocal": [("make_counter", "nonlocal value", "闭包"), ("global counter", "模块全局")],
        "D05-mutability": [("copy()", "浅复制"), ("alias = items", "同一个引用")],
        "D06-with": [("FileNotFoundError", "read_text"), ("path.open", "缺失路径")],
        "D07-dataclass": [("Bag", "default_factory"), ("Point", "x/y")],
    }
    for section_id, forbidden_pairs in forbidden_by_example.items():
        for example, forbidden in zip(sections[section_id]["examples"], forbidden_pairs):
            explanation = example["explanation"]
            assert not all(fragment in explanation for fragment in forbidden), (section_id, forbidden, explanation)


def test_d02_to_d17_examples_have_two_index_bound_explanations(curriculum_data: dict) -> None:
    for task in curriculum_data["tasks"]:
        if not (2 <= int(task["id"][1:]) <= 17):
            continue
        for section in task["lesson"]:
            assert len(section["examples"]) == 2
            for example in section["examples"]:
                explanation = example["explanation"]
                assert len(explanation) >= 48
                assert sum(explanation.count(mark) for mark in "。！？；") >= 2
                assert explanation.strip()


def test_project_document_examples_are_file_or_command_snippets(curriculum_data: dict) -> None:
    sections = {section["id"]: section for task in curriculum_data["tasks"] for section in task["lesson"]}
    for section_id in ("D18-scope", "D18-acceptance", "D18-data-contract", "D18-api-contract", "D24-rebuild", "D24-integrate", "D24-artifacts", "D24-review"):
        for example in sections[section_id]["examples"]:
            if sections[section_id]["syntax"] in {"requirements", "contract", "runbook", "review"}:
                assert "print(" not in example["code"], (section_id, example["code"])
                assert any(marker in example["code"] for marker in ("#", "##", "{", "|", "python ", "$ ", "GET ", "POST "))


def test_d08_to_d24_examples_have_explicit_source_contract(curriculum_data: dict) -> None:
    sections = {section["id"]: section for task in curriculum_data["tasks"] for section in task["lesson"]}
    for number in range(8, 25):
        for section in (s for sid, s in sections.items() if sid.startswith(f"D{number:02d}-")):
            for index, example in enumerate(section["examples"]):
                assert example["source_kind"] in {"python", "file_fragment", "command", "json_fragment", "html_fragment", "javascript"}, (section["id"], index)
                assert isinstance(example["runnable"], bool), (section["id"], index)
                if example["source_kind"] == "python":
                    assert example["runnable"] is True, (section["id"], index)
                else:
                    assert example["runnable"] is False, (section["id"], index)
                    assert example.get("target_path"), (section["id"], index)


def test_d08_to_d17_python_examples_run_with_declared_output(curriculum_data: dict, tmp_path: Path) -> None:
    """Run only generated, AST-screened examples in an isolated directory."""
    forbidden_names = {"eval", "exec", "compile", "urlopen", "system", "popen", "check_call", "check_output", "run"}
    sections = [
        section
        for task in curriculum_data["tasks"]
        if 8 <= int(task["id"][1:]) <= 17
        for section in task["lesson"]
    ]
    for section in sections:
        for index, example in enumerate(section["examples"]):
            assert example["source_kind"] == "python" and example["runnable"] is True
            tree = ast.parse(example["code"], filename=f"{section['id']}-{index}.py")
            imported = {
                alias.name.split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            assert "subprocess" not in imported and "socket" not in imported, (section["id"], index)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    called = node.func.id if isinstance(node.func, ast.Name) else ""
                    assert called not in forbidden_names, (section["id"], index, called)
            completed = subprocess.run(
                [sys.executable, "-c", example["code"]],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                timeout=5,
            )
            assert completed.returncode == 0, (section["id"], index, completed.stderr)
            assert completed.stdout.rstrip("\r\n") == example["output"], (section["id"], index, completed.stdout, example["output"])


def test_project_examples_name_real_targets_not_toy_runtime_dicts(curriculum_data: dict) -> None:
    sections = {
        section["id"]: section
        for task in curriculum_data["tasks"]
        if 18 <= int(task["id"][1:]) <= 24
        for section in task["lesson"]
    }
    for section in sections.values():
        for index, example in enumerate(section["examples"]):
            assert example["runnable"] is False
            assert example.get("target_path"), (section["id"], index)
            assert "print(" not in example["code"], (section["id"], index)
            if section["id"] not in {"D23-html-fetch", "D24-rebuild", "D24-integrate", "D24-artifacts", "D24-review"}:
                assert example["target_path"] in example["code"] or section["syntax"] in {"requirements", "contract", "pyproject", "html"}, (section["id"], index)

@pytest.mark.parametrize("mutation, expected", [
    ("quiz", "已移除选择题"),
    ("bad_kind", "未知实践类型"),
    ("missing_file_name", "必须是非空字符串"),
    ("unsafe_file_name", "文件名"),
    ("supplemental_no_note", "supplemental_note"),
    ("empty_refs_non_supplemental", "必须引用真实来源条目"),
])
def test_invalid_practice_is_rejected(curriculum_data: dict, mutation: str, expected: str) -> None:
    data = deepcopy(curriculum_data)
    # 文件名相关突变针对 code 小节（D02-name），其余针对 D01-onboarding
    section = data["tasks"][1]["lesson"][0] if mutation in ("missing_file_name", "unsafe_file_name") else data["tasks"][0]["lesson"][0]
    if mutation == "quiz":
        section["quiz"] = {"question": "q", "choices": ["a", "b", "c", "d"], "answer_index": 0}
    elif mutation == "bad_kind":
        section["practice"]["kind"] = "drag"
    elif mutation == "missing_file_name":
        section["practice"] = dict(section["practice"], kind="code")
        section["practice"].pop("file_name", None)
    elif mutation == "unsafe_file_name":
        section["practice"]["file_name"] = "../evil.py"
    elif mutation == "supplemental_no_note":
        section["supplemental"] = True
    else:
        section["catalog_refs"] = []
    with pytest.raises(DataError, match=expected):
        validate_curriculum(data)


def test_project_file_continuation_chain(curriculum_data: dict) -> None:
    sections = [s for task in curriculum_data["tasks"] for s in task["lesson"]]
    pfs = [s.get("practice", {}).get("project_file") for s in sections if s.get("practice", {}).get("project_file")]
    # 15 个最终产物：每个 project_file 恰好是一个最终落盘文件
    expected = sorted({
        "README.md", "contract.json", "docs/requirements.md", "docs/review.md",
        "docs/runbook.md", "pyproject.toml", "taskproj/__init__.py", "taskproj/api.py",
        "taskproj/cli.py", "taskproj/config.py", "taskproj/db.py", "taskproj/main.py",
        "taskproj/static/index.html", "tests/test_api.py", "tests/test_project.py",
    })
    assert sorted(set(pfs)) == expected, "最终产物集合不准确"
    # 重复 project_file 仅允许相邻后节声明 continues_file=true
    for idx, section in enumerate(sections):
        pf = section.get("practice", {}).get("project_file")
        if not pf:
            continue
        prev_pf = sections[idx - 1].get("practice", {}).get("project_file") if idx > 0 else None
        continues = section.get("practice", {}).get("continues_file")
        if prev_pf == pf:
            assert continues is True, \
                f"{section['id']} 重复了相邻前节的 project_file，必须声明 continues_file=true"
        else:
            assert continues is not True, \
                f"{section['id']} 声明了 continues_file=true，但其前节 project_file 并不相同"


def test_curriculum_version_and_d18_d24_project_file_mapping(curriculum_data: dict) -> None:
    validated = validate_curriculum(deepcopy(curriculum_data))
    assert validated["curriculum_version"] == "3.0.0"
    project_file = {
        s["id"]: s.get("practice", {}).get("project_file")
        for task in validated["tasks"]
        for s in task["lesson"]
    }
    assert project_file["D18-scope"] == "docs/requirements.md"
    assert project_file["D18-data-contract"] == "contract.json"
    assert project_file["D19-readme"] == "README.md"
    assert project_file["D19-pyproject"] == "pyproject.toml"
    assert project_file["D19-package"] == "taskproj/__init__.py"
    assert project_file["D20-connection"] == "taskproj/db.py"
    assert project_file["D20-create-list"] == "taskproj/db.py"
    assert project_file["D21-app"] == "taskproj/api.py"
    assert project_file["D21-static"] == "taskproj/api.py"
    assert project_file["D23-html-structure"] == "taskproj/static/index.html"
    assert project_file["D24-rebuild"] == "docs/runbook.md"
    assert project_file["D24-review"] == "docs/review.md"


@pytest.mark.parametrize("bad", [
    "C:/evil.py",
    "/etc/passwd",
    "../outside.py",
    "a/../../x.py",
    "x/..",
    "taskproj\\config.py",
    "taskproj/*.py",
    ".learn/progress.json",
    " ",
])
def test_malicious_project_file_paths_are_rejected(curriculum_data: dict, bad: str) -> None:
    data = deepcopy(curriculum_data)
    d18 = next(task for task in data["tasks"] if task["id"] == "D18")
    req = next(section for section in d18["lesson"] if section["id"] == "D18-scope")
    req["practice"]["project_file"] = bad
    with pytest.raises(DataError):
        validate_curriculum(data)


def test_malicious_workspace_deps_paths_are_rejected(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    d20 = next(task for task in data["tasks"] if task["id"] == "D20")
    crud = next(section for section in d20["lesson"] if section["id"] == "D20-create-list")
    crud["practice"]["workspace_deps"] = ["../escape.py"]
    with pytest.raises(DataError):
        validate_curriculum(data)


def test_workspace_deps_must_reference_prior_declared_project_file(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    d20 = next(task for task in data["tasks"] if task["id"] == "D20")
    crud = next(section for section in d20["lesson"] if section["id"] == "D20-create-list")
    # taskproj/api.py 在更靠后的 D21-routes 才产出，不得提前引用
    crud["practice"]["workspace_deps"] = ["taskproj/api.py"]
    with pytest.raises(DataError, match="前序"):
        validate_curriculum(data)


def test_workspace_deps_must_reference_declared_project_file(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    d20 = next(task for task in data["tasks"] if task["id"] == "D20")
    crud = next(section for section in d20["lesson"] if section["id"] == "D20-create-list")
    crud["practice"]["workspace_deps"] = ["taskproj/ghost.py"]
    with pytest.raises(DataError, match="前序"):
        validate_curriculum(data)


def test_non_adjacent_project_file_duplicate_is_rejected(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    d22 = next(task for task in data["tasks"] if task["id"] == "D22")
    api = next(section for section in d22["lesson"] if section["id"] == "D22-api-tests")
    # 把 D22-api 的产物改成 db.py：与 D20-crud 重复且不相邻
    api["practice"]["project_file"] = "taskproj/db.py"
    api["practice"]["workspace_deps"] = []
    with pytest.raises(DataError, match="仅相邻"):
        validate_curriculum(data)


def test_continues_file_requires_adjacent_duplicate_project_file(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    d19 = next(task for task in data["tasks"] if task["id"] == "D19")
    config = next(section for section in d19["lesson"] if section["id"] == "D19-config")
    # D19-config 产物并未与前节重复，却声明 continues_file -> 拒绝
    config["practice"]["continues_file"] = True
    with pytest.raises(DataError, match="仅允许"):
        validate_curriculum(data)


def test_project_file_requires_workspace_deps(curriculum_data: dict) -> None:
    data = deepcopy(curriculum_data)
    d23 = next(task for task in data["tasks"] if task["id"] == "D23")
    cli = next(section for section in d23["lesson"] if section["id"] == "D23-cli-parser")
    cli["practice"].pop("workspace_deps", None)
    with pytest.raises(DataError, match="workspace_deps"):
        validate_curriculum(data)


def test_python_311_feature_ast_parses_sources() -> None:
    for path in (REPOSITORY / "learnctl").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path), feature_version=(3, 11))


def test_no_quiz_or_radio_in_frontend(curriculum_data: dict) -> None:
    static = REPOSITORY / "learnctl" / "web" / "static"
    combined = ""
    for name in ("index.html", "app.js", "styles.css"):
        combined += (static / name).read_text(encoding="utf-8")
    for forbidden in ("quiz", "answer_index", 'type="radio"'):
        assert forbidden not in combined, f"前端不应出现 {forbidden}"
    assert "save-draft" in combined or "data-save-draft" in combined
    assert "run-validate" in combined or "data-validate" in combined
    assert "data-reset" in combined
    assert "ai-panel" in combined


def test_broken_json_is_rejected(project: Path) -> None:
    (project / "data" / "curriculum.json").write_text("{broken", encoding="utf-8")
    result = run_cli(project, "today", "--json")
    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "JSON 无效" in payload["error"]


def test_advanced_sections_are_optional_in_first_pass(curriculum_data: dict) -> None:
    from learnctl.workflow import required_sections

    optional_ids = {"D03-match", "D04-global-nonlocal", "D04-lambda",
                    "D05-iterators-generators", "D07-inheritance", "D10-dotenv",
                    "D03-enumerate-zip", "D03-comprehension", "D04-varargs"}
    sections = {s["id"]: (task, s) for task in curriculum_data["tasks"] for s in task["lesson"]}
    drills = {section_id for section_id, (_, section) in sections.items() if section["title"].startswith("加练")}
    assert len(drills) == 24
    optional_ids |= drills
    assert {section_id for section_id, (_, section) in sections.items() if section.get("optional")} == optional_ids
    for section_id in optional_ids:
        task, _ = sections[section_id]
        assert section_id not in required_sections(task)

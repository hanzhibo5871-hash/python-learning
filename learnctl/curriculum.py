from __future__ import annotations

import json
import shlex
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .errors import DataError

SUPPORTED_SCHEMA_VERSION = 3
MODULE_STATUSES = {"learn", "practice", "mastered"}
PRACTICE_KINDS = {"code", "json", "text", "command", "env_action"}
ENV_ACTIONS = {"detect", "create_venv", "install", "verify"}


def _fail(path: str, reason: str) -> None:
    raise DataError(f"课程数据 {path}：{reason}")


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "必须是对象")
    return value


def _require_list(value: Any, path: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "必须是数组")
    if nonempty and not value:
        _fail(path, "不能为空")
    return value


def _require_str(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        _fail(path, "必须是非空字符串" if nonempty else "必须是字符串")
    return value


def _string_list(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    items = _require_list(value, path, nonempty=nonempty)
    for index, item in enumerate(items):
        _require_str(item, f"{path}[{index}]")
    return items


def _validate_file_name(value: Any, path: str) -> str:
    file_name = _require_str(value, path)
    if "\\" in file_name:
        _fail(path, "文件名不得使用反斜杠")
    posix = PurePosixPath(file_name)
    if posix.is_absolute() or PureWindowsPath(file_name).is_absolute():
        _fail(path, "文件名不得是绝对路径")
    if any(part in {"", ".", ".."} for part in posix.parts):
        _fail(path, "文件名不得包含空段、当前目录或路径穿越")
    if any(character in file_name for character in "*?[]"):
        _fail(path, "文件名不得包含通配符")
    if not posix.name.endswith(".py"):
        _fail(path, "code 实践的文件名必须是 .py 文件")
    return posix.as_posix()


def _validate_project_file(value: Any, path: str) -> str:
    """校验项目产物/依赖的相对路径：非空 POSIX 相对路径，禁止绝对路径、穿越、反斜杠、空段、通配符与 .learn。"""
    raw = _require_str(value, path)
    if raw != raw.strip():
        _fail(path, "不得包含首尾空白")
    if "\\" in raw:
        _fail(path, "不得使用反斜杠")
    posix = PurePosixPath(raw)
    if posix.is_absolute() or PureWindowsPath(raw).is_absolute():
        _fail(path, "不得是绝对路径")
    if any(part in {"", ".", ".."} for part in posix.parts):
        _fail(path, "不得包含空段、当前目录或路径穿越")
    if any(character in raw for character in "*?[]"):
        _fail(path, "不得包含通配符")
    if ".learn" in posix.parts:
        _fail(path, "不得指向 .learn 内部文件")
    return posix.as_posix()


def _validate_catalog_refs(refs: Any, path: str, source_ids: set[str], supplemental: bool, has_project_file: bool = False, optional: bool = False) -> list[str]:
    values = _string_list(refs, path)
    for index, ref in enumerate(values):
        if ref not in source_ids:
            _fail(f"{path}[{index}]", f"引用了不存在的来源 ID {ref!r}")
    if not values and not supplemental and not has_project_file and not optional:
        _fail(path, "非 supplemental 且非 optional 小节必须引用真实来源条目或声明 project_file")
    return values


def _validate_practice(practice: Any, path: str, source_ids: set[str], supplemental: bool) -> dict[str, Any]:
    item = _require_dict(practice, path)
    kind = item.get("kind")
    if kind not in PRACTICE_KINDS:
        _fail(f"{path}.kind", f"未知实践类型 {kind!r}，可选 {sorted(PRACTICE_KINDS)}")
    _require_str(item.get("scenario"), f"{path}.scenario")
    _require_str(item.get("instructions"), f"{path}.instructions")
    _require_str(item.get("expected_behavior"), f"{path}.expected_behavior")
    _require_str(item.get("hints"), f"{path}.hints")
    if not isinstance(item.get("starter_content"), str):
        _fail(f"{path}.starter_content", "必须是字符串")
    starter_policy = item.get("starter_policy", "complete")
    if starter_policy not in {"complete", "function_body"}:
        _fail(f"{path}.starter_policy", "必须是 complete 或 function_body")
    if "NotImplementedError" in item["starter_content"] and starter_policy != "function_body":
        _fail(f"{path}.starter_content", "只有明确要求实现函数体的练习才能使用 NotImplementedError starter")
    if starter_policy == "function_body" and kind != "code":
        _fail(f"{path}.starter_policy", "function_body 只适用于 code 实践")
    identifiers = item.get("input_identifiers")
    if identifiers is not None:
        identifiers = _string_list(identifiers, f"{path}.input_identifiers", nonempty=True)
        input_text = "\n".join(example["value"] for example in item.get("input_examples", []) if isinstance(example, dict))
        for index, identifier in enumerate(identifiers):
            if identifier not in input_text:
                _fail(f"{path}.input_identifiers[{index}]", f"标识 {identifier!r} 必须出现在独立 input_examples 中")
        item["input_identifiers"] = identifiers
    examples = _require_list(item.get("input_examples"), f"{path}.input_examples")
    if len(examples) < 2:
        _fail(f"{path}.input_examples", "必须提供至少 2 个可运行输入示例")
    for index, raw_example in enumerate(examples):
        example = _require_dict(raw_example, f"{path}.input_examples[{index}]")
        _require_str(example.get("label"), f"{path}.input_examples[{index}].label")
        _require_str(example.get("value"), f"{path}.input_examples[{index}].value")
        _require_str(example.get("expected"), f"{path}.input_examples[{index}].expected")
    if kind == "code":
        _validate_file_name(item.get("file_name"), f"{path}.file_name")
    elif kind == "env_action":
        action = item.get("action")
        if action not in ENV_ACTIONS:
            _fail(f"{path}.action", f"固定动作必须属于 {sorted(ENV_ACTIONS)}")
    else:
        if "file_name" in item:
            _fail(f"{path}.file_name", f"{kind} 实践不应当声明 file_name")
        if kind == "command" and "action" in item:
            _fail(f"{path}.action", "command 实践不应当声明 action")
    if "project_file" in item:
        item["project_file"] = _validate_project_file(item.get("project_file"), f"{path}.project_file")
    if "workspace_deps" in item:
        deps = _string_list(item.get("workspace_deps"), f"{path}.workspace_deps")
        item["workspace_deps"] = [_validate_project_file(dep, f"{path}.workspace_deps[{index}]") for index, dep in enumerate(deps)]
    if "project_file" in item and "workspace_deps" not in item:
        _fail(f"{path}.workspace_deps", "声明 project_file 的小节必须同时声明 workspace_deps")
    if "continues_file" in item:
        if item.get("continues_file") is not True:
            _fail(f"{path}.continues_file", "必须是布尔值 true")
    return item


def _validate_teaching_contract(section: dict[str, Any], path: str) -> None:
    """v3 的必修小节必须能直接支持一次完整的初学者教学循环。"""
    _require_str(section.get("objective"), f"{path}.objective")
    explanation = _require_list(section.get("explanation"), f"{path}.explanation", nonempty=True)
    if len(explanation) < 3:
        _fail(f"{path}.explanation", "v3 必须至少有 3 段详细讲解")
    if len({item.strip() for item in explanation if isinstance(item, str)}) < 3:
        _fail(f"{path}.explanation", "3 段讲解必须有实质差异，不得模板复读")
    for index, paragraph in enumerate(explanation):
        if len(_require_str(paragraph, f"{path}.explanation[{index}]") ) < 24:
            _fail(f"{path}.explanation[{index}]", "讲解段落过短，必须包含具体概念或因果")
    _require_str(section.get("syntax"), f"{path}.syntax")
    _require_str(section.get("js_bridge"), f"{path}.js_bridge")
    examples = _require_list(section.get("examples"), f"{path}.examples", nonempty=True)
    if len(examples) < 2:
        _fail(f"{path}.examples", "v3 必须至少有 2 个逐步示例")
    for index, raw_example in enumerate(examples):
        example = _require_dict(raw_example, f"{path}.examples[{index}]")
        _require_str(example.get("code"), f"{path}.examples[{index}].code")
        _require_str(example.get("output"), f"{path}.examples[{index}].output", nonempty=False)
        source_kind = _require_str(example.get("source_kind"), f"{path}.examples[{index}].source_kind")
        if source_kind not in {"python", "file_fragment", "command", "json_fragment", "html_fragment", "javascript"}:
            _fail(f"{path}.examples[{index}].source_kind", "示例来源类型不受支持")
        runnable = example.get("runnable")
        if not isinstance(runnable, bool):
            _fail(f"{path}.examples[{index}].runnable", "必须是布尔值")
        if source_kind == "python" and runnable is not True:
            _fail(f"{path}.examples[{index}].runnable", "Python 示例必须声明 runnable=true")
        if source_kind != "python" and runnable is not False:
            _fail(f"{path}.examples[{index}].runnable", "非 Python 片段必须声明 runnable=false")
        if runnable is False:
            _require_str(example.get("target_path"), f"{path}.examples[{index}].target_path")
        explanation_text = _require_str(example.get("explanation"), f"{path}.examples[{index}].explanation")
        sentence_marks = sum(explanation_text.count(mark) for mark in "。！？；")
        if len(explanation_text) < 48 or sentence_marks < 2:
            _fail(f"{path}.examples[{index}].explanation", "示例解释必须具体说明关键行、输出原因和边界，至少两句实质内容")
    errors = _require_list(section.get("common_errors"), f"{path}.common_errors", nonempty=True)
    if len(errors) < 2:
        _fail(f"{path}.common_errors", "v3 必须至少列出 2 个常见错误及原因")
    for index, raw_error in enumerate(errors):
        error = _require_dict(raw_error, f"{path}.common_errors[{index}]")
        _require_str(error.get("error"), f"{path}.common_errors[{index}].error")
        example = _require_dict(error.get("example"), f"{path}.common_errors[{index}].example")
        _require_str(example.get("code"), f"{path}.common_errors[{index}].example.code")
        _require_str(example.get("symptom"), f"{path}.common_errors[{index}].example.symptom")
        _require_str(example.get("fix"), f"{path}.common_errors[{index}].example.fix")
        _require_str(error.get("symptom"), f"{path}.common_errors[{index}].symptom")
        _require_str(error.get("cause"), f"{path}.common_errors[{index}].cause")
        _require_str(error.get("fix"), f"{path}.common_errors[{index}].fix")
    guided = _require_dict(section.get("guided_practice"), f"{path}.guided_practice")
    _require_str(guided.get("goal"), f"{path}.guided_practice.goal")
    _require_str(guided.get("starter"), f"{path}.guided_practice.starter")
    steps = _require_list(guided.get("steps"), f"{path}.guided_practice.steps", nonempty=True)
    if len(steps) < 2:
        _fail(f"{path}.guided_practice.steps", "至少需要 2 个带预期结果的步骤")
    for index, raw_step in enumerate(steps):
        step = _require_dict(raw_step, f"{path}.guided_practice.steps[{index}]")
        _require_str(step.get("action"), f"{path}.guided_practice.steps[{index}].action")
        _require_str(step.get("expected"), f"{path}.guided_practice.steps[{index}].expected")
    _require_str(guided.get("check"), f"{path}.guided_practice.check")


def _validate_lesson(lesson: Any, path: str, source_ids: set[str], *, require_teaching: bool = False) -> list[dict[str, Any]]:
    sections = _require_list(lesson, path, nonempty=True)
    validated: list[dict[str, Any]] = []
    for index, raw_section in enumerate(sections):
        base = f"{path}[{index}]"
        section = _require_dict(raw_section, base)
        _require_str(section.get("id"), f"{base}.id")
        _require_str(section.get("title"), f"{base}.title")
        if require_teaching:
            _validate_teaching_contract(section, base)
        supplemental = section.get("supplemental", False)
        if supplemental is not True and supplemental is not False:
            _fail(f"{base}.supplemental", "必须是布尔值")
        if supplemental:
            _require_str(section.get("supplemental_note"), f"{base}.supplemental_note")
        else:
            if "supplemental_note" in section:
                _fail(f"{base}.supplemental_note", "非 supplemental 小节不应当声明 supplemental_note")
        _validate_catalog_refs(
            section.get("catalog_refs"), f"{base}.catalog_refs", source_ids, supplemental,
            has_project_file=bool(section.get("practice", {}).get("project_file")),
            optional=bool(section.get("optional")),
        )
        paragraphs = _require_list(section.get("explanation"), f"{base}.explanation", nonempty=True)
        if not 2 <= len(paragraphs) <= 4:
            _fail(f"{base}.explanation", "必须有 2 到 4 段讲解")
        for paragraph_index, paragraph in enumerate(paragraphs):
            _require_str(paragraph, f"{base}.explanation[{paragraph_index}]")
        _string_list(section.get("key_points"), f"{base}.key_points", nonempty=True)
        _require_str(section.get("frontend_bridge"), f"{base}.frontend_bridge")
        example = _require_dict(section.get("example"), f"{base}.example")
        _require_str(example.get("language"), f"{base}.example.language")
        _require_str(example.get("code"), f"{base}.example.code")
        steps = _require_list(section.get("steps"), f"{base}.steps", nonempty=True)
        if not 2 <= len(steps) <= 4:
            _fail(f"{base}.steps", "必须有 2 到 4 条逐步讲解")
        for step_index, step in enumerate(steps):
            _require_str(step, f"{base}.steps[{step_index}]")
        if "quiz" in section:
            _fail(f"{base}.quiz", "课程已移除选择题（quiz/choices/answer_index），不得再出现")
        _validate_practice(section.get("practice"), f"{base}.practice", source_ids, supplemental)
        validated.append(section)
    return validated


def _objects(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = _require_list(data.get(key), f"$.{key}")
    return [_require_dict(item, f"$.{key}[{index}]") for index, item in enumerate(values)]


def _collect_ids(groups: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    all_ids: dict[str, str] = {}
    result: dict[str, set[str]] = {}
    for kind, values in groups.items():
        ids: set[str] = set()
        for index, value in enumerate(values):
            item_id = _require_str(value.get("id"), f"$.{kind}[{index}].id")
            if item_id in all_ids:
                _fail(f"$.{kind}[{index}].id", f"ID {item_id!r} 与 {all_ids[item_id]} 重复")
            all_ids[item_id] = f"$.{kind}[{index}].id"
            ids.add(item_id)
        result[kind] = ids
    return result


def _check_reference(value: Any, allowed: set[str], path: str) -> str:
    item_id = _require_str(value, path)
    if item_id not in allowed:
        _fail(path, f"引用不存在的 ID {item_id!r}")
    return item_id


def _check_dag(items: list[dict[str, Any]], ids: set[str], path: str) -> None:
    graph: dict[str, list[str]] = {}
    for index, item in enumerate(items):
        item_id = item["id"]
        dependencies = _string_list(item.get("prerequisites"), f"{path}[{index}].prerequisites")
        for dep_index, dependency in enumerate(dependencies):
            _check_reference(dependency, ids, f"{path}[{index}].prerequisites[{dep_index}]")
        graph[item_id] = dependencies

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            _fail(path, f"依赖图存在循环，涉及 {node!r}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def parse_test_command(command: str, path: str = "$.test_command") -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        _fail(path, f"命令无法解析：{exc}")
    if len(parts) < 4 or parts[0] not in {"python", "python3"} or parts[1:3] != ["-m", "pytest"]:
        _fail(path, "仅允许 python -m pytest 测试命令")

    targets: list[str] = []
    quiet_seen = False
    index = 3
    while index < len(parts):
        token = parts[index]
        if token == "-q" and not quiet_seen:
            quiet_seen = True
            index += 1
            continue
        if token.startswith("-"):
            _fail(path, f"不允许 pytest 选项 {token!r}，课程命令仅可选用 -q")
        targets.append(token)
        index += 1

    if not targets:
        _fail(path, "必须指定至少一个 learner_tests/*.py 测试文件")
    for target in targets:
        if PurePosixPath(target).is_absolute() or PureWindowsPath(target).is_absolute():
            _fail(path, f"测试目标不得使用绝对路径：{target!r}")
        normalized = target.replace("\\", "/")
        target_path = PurePosixPath(normalized)
        if ".." in target_path.parts:
            _fail(path, f"测试目标不得包含路径穿越：{target!r}")
        if (
            len(target_path.parts) != 2
            or target_path.parts[0] != "learner_tests"
            or not target_path.parts[1].endswith(".py")
            or target_path.parts[1] == ".py"
            or any(character in target for character in "*?[]")
        ):
            _fail(path, f"测试目标必须是具体 learner_tests/*.py 文件：{target!r}")
    return parts


def _validate_source_catalog(source_catalog: list[dict[str, Any]], source_count: int) -> None:
    if len(source_catalog) != source_count:
        _fail("$.meta.source_course_count", f"声明 {source_count}，source_catalog 实际有 {len(source_catalog)} 条")
    numbers_by_series: dict[str, list[int]] = {}
    for index, source in enumerate(source_catalog):
        base = f"$.source_catalog[{index}]"
        _require_str(source.get("series"), f"{base}.series")
        number = source.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            _fail(f"{base}.number", "必须是正整数")
        title = _require_str(source.get("title"), f"{base}.title")
        if title == f"{source['series']} {number:02d}":
            _fail(f"{base}.title", "不能使用系列名加编号的占位标题")
        numbers_by_series.setdefault(source["series"], []).append(number)
    for series, numbers in numbers_by_series.items():
        expected = list(range(1, max(numbers) + 1))
        if sorted(numbers) != expected:
            _fail("$.source_catalog", f"{series!r} 编号必须从 1 连续覆盖到 {max(numbers)}")


def validate_curriculum(data: Any) -> dict[str, Any]:
    root = _require_dict(data, "$")
    if root.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        _fail("$.schema_version", f"仅支持版本 {SUPPORTED_SCHEMA_VERSION}")
    _require_str(root.get("curriculum_version"), "$.curriculum_version")
    meta = _require_dict(root.get("meta"), "$.meta")
    source_count = meta.get("source_course_count")
    if not isinstance(source_count, int) or isinstance(source_count, bool) or source_count <= 0:
        _fail("$.meta.source_course_count", "必须是正整数")

    source_catalog = _objects(root, "source_catalog")
    _validate_source_catalog(source_catalog, source_count)
    groups = {
        "source_catalog": source_catalog,
        "modules": _objects(root, "modules"),
        "optional_tracks": _objects(root, "optional_tracks"),
        "diagnostics": _objects(root, "diagnostics"),
        "stages": _objects(root, "stages"),
        "tasks": _objects(root, "tasks"),
        "exercises": _objects(root, "exercises"),
    }
    ids = _collect_ids(groups)

    source_by_id = {source["id"]: source for source in source_catalog}
    module_by_id = {module["id"]: module for module in groups["modules"]}
    source_owners: dict[str, str] = {}
    optional_module_ids: set[str] = set()
    for index, module in enumerate(groups["modules"]):
        base = f"$.modules[{index}]"
        _require_str(module.get("title"), f"{base}.title")
        _string_list(module.get("topics"), f"{base}.topics", nonempty=True)
        status = _require_str(module.get("default_status"), f"{base}.default_status")
        if status not in MODULE_STATUSES:
            _fail(f"{base}.default_status", f"未知知识状态 {status!r}")
        supplemental = module.get("supplemental", False)
        if supplemental is not True and supplemental is not False:
            _fail(f"{base}.supplemental", "必须是布尔值")
        if supplemental:
            _require_str(module.get("supplemental_note"), f"{base}.supplemental_note")
            refs = _string_list(module.get("catalog_refs"), f"{base}.catalog_refs")
            if refs:
                _fail(f"{base}.catalog_refs", "supplemental 模块不得占用真实索引引用")
        else:
            refs = _string_list(module.get("catalog_refs"), f"{base}.catalog_refs", nonempty=True)
            for ref_index, source_id in enumerate(refs):
                checked = _check_reference(source_id, ids["source_catalog"], f"{base}.catalog_refs[{ref_index}]")
                if checked in source_owners:
                    _fail(f"{base}.catalog_refs[{ref_index}]", f"来源编号已被模块 {source_owners[checked]!r} 引用")
                source_owners[checked] = module["id"]
        optional_track_id = module.get("optional_track_id")
        if optional_track_id is not None:
            _check_reference(optional_track_id, ids["optional_tracks"], f"{base}.optional_track_id")
            optional_module_ids.add(module["id"])
    if set(source_by_id) != set(source_owners):
        missing = sorted(set(source_by_id) - set(source_owners))
        extra = sorted(set(source_owners) - set(source_by_id))
        _fail("$.modules", f"catalog_refs 覆盖不完整，缺少 {missing}，多出 {extra}")

    optional_by_id = {track["id"]: track for track in groups["optional_tracks"]}
    for index, track in enumerate(groups["optional_tracks"]):
        base = f"$.optional_tracks[{index}]"
        if track.get("default_enabled") is not False:
            _fail(f"{base}.default_enabled", "选修项必须默认关闭")
        if track.get("affects_stage_completion") is not False:
            _fail(f"{base}.affects_stage_completion", "选修项不得影响阶段完成")
        if track.get("affects_final_acceptance") is not False:
            _fail(f"{base}.affects_final_acceptance", "选修项不得影响最终验收")
        for module_index, module_id in enumerate(_string_list(track.get("module_ids"), f"{base}.module_ids", nonempty=True)):
            checked = _check_reference(module_id, ids["modules"], f"{base}.module_ids[{module_index}]")
            if module_by_id[checked].get("optional_track_id") != track["id"]:
                _fail(f"{base}.module_ids[{module_index}]", "模块未反向声明同一 optional_track_id")
        if track["id"] == "langchain-cloud" and not track.get("module_ids"):
            _fail(f"{base}.module_ids", "LangChain 选修必须有知识模块")

    for index, module in enumerate(groups["modules"]):
        track_id = module.get("optional_track_id")
        if track_id is not None and module["id"] not in optional_by_id[track_id]["module_ids"]:
            _fail(f"$.modules[{index}].optional_track_id", "模块未被对应选修项收录")

    diagnostic_ids = ids["diagnostics"]
    expected_diagnostics = {f"D{number}" for number in range(6)}
    if diagnostic_ids != expected_diagnostics:
        _fail("$.diagnostics", f"必须定义 D0-D5，当前为 {sorted(diagnostic_ids)}")
    for index, diagnostic in enumerate(groups["diagnostics"]):
        base = f"$.diagnostics[{index}]"
        _require_str(diagnostic.get("title"), f"{base}.title")
        critical_cases = _string_list(diagnostic.get("critical_cases"), f"{base}.critical_cases", nonempty=True)
        if diagnostic["id"] != "D0" and len(critical_cases) < 2:
            _fail(f"{base}.critical_cases", "D1-D5 每项至少需要两道题")
        for module_index, module_id in enumerate(_string_list(diagnostic.get("modules"), f"{base}.modules", nonempty=True)):
            _check_reference(module_id, ids["modules"], f"{base}.modules[{module_index}]")
        decisions = _require_dict(diagnostic.get("decision"), f"{base}.decision")
        for result in ("pass", "partial", "fail"):
            status = _require_str(decisions.get(result), f"{base}.decision.{result}")
            if status not in MODULE_STATUSES:
                _fail(f"{base}.decision.{result}", f"未知知识状态 {status!r}")

    thresholds = _require_dict(root.get("diagnostic_thresholds"), "$.diagnostic_thresholds")
    for key in ("pass_min_percent", "partial_min_percent"):
        value = thresholds.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
            _fail(f"$.diagnostic_thresholds.{key}", "必须是 0 到 100 的整数")
    if thresholds["pass_min_percent"] < thresholds["partial_min_percent"]:
        _fail("$.diagnostic_thresholds", "pass 阈值不能低于 partial 阈值")
    if not isinstance(thresholds.get("critical_cases_must_pass"), bool):
        _fail("$.diagnostic_thresholds.critical_cases_must_pass", "必须是布尔值")

    stage_by_id = {stage["id"]: stage for stage in groups["stages"]}
    task_by_id = {task["id"]: task for task in groups["tasks"]}
    exercise_by_id = {exercise["id"]: exercise for exercise in groups["exercises"]}
    lesson_section_ids: set[str] = set()
    ws_deps_seen: dict[str, int] = {}
    section_id_by_index: dict[int, str] = {}
    global_section_index = 0
    _check_dag(groups["stages"], ids["stages"], "$.stages")
    _check_dag(groups["tasks"], ids["tasks"], "$.tasks")

    listed_tasks: set[str] = set()
    for index, stage in enumerate(groups["stages"]):
        base = f"$.stages[{index}]"
        _require_str(stage.get("title"), f"{base}.title")
        _require_str(stage.get("goal"), f"{base}.goal")
        _require_str(stage.get("deliverable"), f"{base}.deliverable")
        _string_list(stage.get("acceptance"), f"{base}.acceptance", nonempty=True)
        for task_index, task_id in enumerate(_string_list(stage.get("task_ids"), f"{base}.task_ids", nonempty=True)):
            checked = _check_reference(task_id, ids["tasks"], f"{base}.task_ids[{task_index}]")
            if checked in listed_tasks:
                _fail(f"{base}.task_ids[{task_index}]", f"任务 {checked!r} 被多个阶段收录")
            listed_tasks.add(checked)
            if task_by_id[checked].get("stage_id") != stage["id"]:
                _fail(f"{base}.task_ids[{task_index}]", f"任务 {checked!r} 的 stage_id 不匹配")
    if listed_tasks != ids["tasks"]:
        _fail("$.stages", f"未覆盖任务 {sorted(ids['tasks'] - listed_tasks)}")

    for index, task in enumerate(groups["tasks"]):
        base = f"$.tasks[{index}]"
        _require_str(task.get("title"), f"{base}.title")
        _require_str(task.get("learning_goal"), f"{base}.learning_goal")
        _check_reference(task.get("stage_id"), ids["stages"], f"{base}.stage_id")
        _string_list(task.get("actions"), f"{base}.actions", nonempty=True)
        _string_list(task.get("concepts"), f"{base}.concepts", nonempty=True)
        _require_str(task.get("frontend_bridge"), f"{base}.frontend_bridge")
        _require_str(task.get("coding_task"), f"{base}.coding_task")
        lesson = _validate_lesson(
            task.get("lesson"),
            f"{base}.lesson",
            ids["source_catalog"],
            require_teaching=root.get("schema_version") >= 3,
        )
        for section_index, section in enumerate(lesson):
            section_id = section["id"]
            if section_id in lesson_section_ids:
                _fail(f"{base}.lesson[{section_index}].id", f"课程小节 ID {section_id!r} 重复")
            lesson_section_ids.add(section_id)
            practice = section.get("practice", {})
            project_file = practice.get("project_file")
            for dep in practice.get("workspace_deps", []):
                declared = ws_deps_seen.get(dep)
                if declared is None:
                    _fail(
                        f"{base}.lesson[{section_index}].practice.workspace_deps",
                        f"前置产物 {dep!r} 未由任何前序小节产出",
                    )
                if declared >= global_section_index:
                    _fail(
                        f"{base}.lesson[{section_index}].practice.workspace_deps",
                        f"前置产物 {dep!r} 必须由前序小节产出，不得引用本小节",
                    )
            if project_file:
                continues = practice.get("continues_file")
                if project_file in ws_deps_seen:
                    owner_index = ws_deps_seen[project_file]
                    if owner_index != global_section_index - 1 or continues is not True:
                        _fail(
                            f"{base}.lesson[{section_index}].practice.project_file",
                            f"project_file {project_file!r} 已被小节 {section_id_by_index[owner_index]!r} 声明，仅相邻后节声明 continues_file 时可重复",
                        )
                elif continues is not None:
                    _fail(
                        f"{base}.lesson[{section_index}].practice.continues_file",
                        "continues_file 仅允许出现在续写前序小节产物的相邻小节",
                    )
                ws_deps_seen[project_file] = global_section_index
            section_id_by_index[global_section_index] = section_id
            global_section_index += 1
        snippet = _require_dict(task.get("snippet"), f"{base}.snippet")
        _require_str(snippet.get("language"), f"{base}.snippet.language")
        _require_str(snippet.get("code"), f"{base}.snippet.code")
        references = _require_list(task.get("references"), f"{base}.references")
        for reference_index, raw_reference in enumerate(references):
            reference = _require_dict(raw_reference, f"{base}.references[{reference_index}]")
            _require_str(reference.get("title"), f"{base}.references[{reference_index}].title")
            url = _require_str(reference.get("url"), f"{base}.references[{reference_index}].url")
            if not url.startswith("https://"):
                _fail(f"{base}.references[{reference_index}].url", "只能使用 HTTPS 官方文档链接")
        _string_list(task.get("artifacts"), f"{base}.artifacts", nonempty=True)
        _string_list(task.get("acceptance"), f"{base}.acceptance", nonempty=True)
        exercise_ids = _string_list(task.get("exercise_ids"), f"{base}.exercise_ids")
        for exercise_index, exercise_id in enumerate(exercise_ids):
            checked = _check_reference(exercise_id, ids["exercises"], f"{base}.exercise_ids[{exercise_index}]")
            if exercise_by_id[checked].get("task_id") != task["id"]:
                _fail(f"{base}.exercise_ids[{exercise_index}]", f"练习 {checked!r} 的 task_id 不匹配")
        mappings = _require_list(task.get("module_mapping"), f"{base}.module_mapping")
        for mapping_index, raw_mapping in enumerate(mappings):
            mapping = _require_dict(raw_mapping, f"{base}.module_mapping[{mapping_index}]")
            module_path = f"{base}.module_mapping[{mapping_index}].module_id"
            module_id = _check_reference(mapping.get("module_id"), ids["modules"], module_path)
            if module_id in optional_module_ids:
                _fail(module_path, "默认关闭的选修模块不得进入主线任务")
            _require_str(mapping.get("relationship"), f"{base}.module_mapping[{mapping_index}].relationship")

    for index, exercise in enumerate(groups["exercises"]):
        base = f"$.exercises[{index}]"
        _check_reference(exercise.get("task_id"), ids["tasks"], f"{base}.task_id")
        command = _require_str(exercise.get("test_command"), f"{base}.test_command")
        parse_test_command(command, f"{base}.test_command")
        if exercise.get("offline") is not True:
            _fail(f"{base}.offline", "练习必须声明为离线")

    root["_index"] = {
        "source_catalog": {item["id"]: item for item in source_catalog},
        "modules": module_by_id,
        "optional_tracks": {item["id"]: item for item in groups["optional_tracks"]},
        "diagnostics": {item["id"]: item for item in groups["diagnostics"]},
        "stages": stage_by_id,
        "tasks": task_by_id,
        "exercises": exercise_by_id,
    }
    return root


def load_curriculum(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataError(f"无法读取课程文件 {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataError(f"课程文件 {path} JSON 无效（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}") from exc
    return validate_curriculum(data)

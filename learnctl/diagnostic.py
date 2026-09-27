from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Any, TextIO

from .curriculum import MODULE_STATUSES
from .errors import BlockedError, DataError
from .progress import atomic_write_json, now_iso, save_progress


QUESTIONS: dict[str, dict[str, tuple[str, str]]] = {
    "D1": {
        "convert_input": ('写出表达式 int("12") + float("0.5") 的结果', "12.5"),
        "format_output": ('name="py" 时，写出 f"{7:03d}-{name.upper()}" 的结果', "007-PY"),
    },
    "D2": {
        "filter_loop": ("用 JSON 数组写出 [n for n in range(6) if n % 2] 的结果", "[1,3,5]"),
        "boundary_case": ("用 JSON 数组写出 list(range(2, 7, 2)) 的结果", "[2,4,6]"),
    },
    "D3": {
        "transform_dicts": (
            '用 JSON 写出 [{**row, "score": row["score"] * 2} for row in [{"name":"a","score":2}]] 的结果',
            '[{"name":"a","score":4}]',
        ),
        "group_and_count": ('名称依次为 a、b、a，用 JSON 对象写出名称计数', '{"a":2,"b":1}'),
    },
    "D4": {
        "read_utf8": ('用 pathlib 读取 UTF-8 文本时，填写 read_text 的 encoding 参数值', "utf-8"),
        "missing_path_error": ("Path.read_text 读取不存在路径时产生哪种异常类", "FileNotFoundError"),
    },
    "D5": {
        "navigate_files": ('写出 (Path("a") / "b.txt").as_posix() 的结果', "a/b.txt"),
        "pipe_and_redirect": ("文本 hello 经 upper() 处理后重定向到文件，写出文件内容", "HELLO"),
    },
}


def load_answers(path: Path) -> dict[str, dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeError as exc:
        raise DataError(f"答案文件 {path} 不是有效的 UTF-8 文本：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"答案文件 {path} JSON 无效（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}") from exc
    except OSError as exc:
        raise DataError(f"无法读取答案文件 {path}: {exc}") from exc
    return validate_answers_data(data, f"答案文件 {path}")


def validate_answers_data(data: Any, source: str) -> dict[str, dict[str, str]]:
    if not isinstance(data, dict):
        raise DataError(f"{source}：根节点必须是对象")
    for diagnostic_id, cases in data.items():
        if diagnostic_id not in QUESTIONS:
            raise DataError(f"{source}：未知诊断 ID {diagnostic_id!r}")
        if not isinstance(cases, dict):
            raise DataError(f"{source}：$.{diagnostic_id} 必须是对象")
        for case_id, answer in cases.items():
            if case_id not in QUESTIONS[diagnostic_id]:
                raise DataError(f"{source}：未知题目 ID {diagnostic_id}.{case_id}")
            if not isinstance(answer, str):
                raise DataError(f"{source}：$.{diagnostic_id}.{case_id} 必须是字符串")
    return data


def collect_answers(
    curriculum: dict[str, Any],
    supplied: dict[str, dict[str, str]] | None,
    *,
    prompt_stream: TextIO,
    input_stream: TextIO,
) -> dict[str, dict[str, str]]:
    answers: dict[str, dict[str, str]] = {}
    for diagnostic in curriculum["diagnostics"]:
        diagnostic_id = diagnostic["id"]
        if diagnostic_id == "D0":
            continue
        questions = QUESTIONS.get(diagnostic_id, {})
        answers[diagnostic_id] = {}
        for case_id in diagnostic["critical_cases"]:
            if case_id not in questions:
                raise DataError(f"诊断 {diagnostic_id} 缺少题目定义：{case_id}")
            prompt, _ = questions[case_id]
            print(f"[{diagnostic_id}/{case_id}] {prompt}", file=prompt_stream)
            if supplied is not None:
                answer = supplied.get(diagnostic_id, {}).get(case_id)
                if answer is None or not answer.strip():
                    raise BlockedError(f"答案文件缺少非空答案：$.{diagnostic_id}.{case_id}")
            else:
                line = input_stream.readline()
                if line == "":
                    raise BlockedError(f"输入提前结束，未回答 {diagnostic_id}/{case_id}")
                answer = line.strip()
                if not answer:
                    raise BlockedError(f"答案不能为空：{diagnostic_id}/{case_id}")
            answers[diagnostic_id][case_id] = answer
    return answers


def _run_d0() -> dict[str, tuple[bool, str]]:
    version_ok = sys.version_info >= (3, 11)
    with tempfile.TemporaryDirectory(prefix="learnctl-d0-") as temp_dir:
        environment = Path(temp_dir) / "venv"
        try:
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            created = python.is_file()
            pip_result = subprocess.run(
                [str(python), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            pip_ok = pip_result.returncode == 0
        except (OSError, subprocess.SubprocessError) as exc:
            created = False
            pip_ok = False
            error = str(exc)
        else:
            error = ""
    return {
        "python_version": (version_ok, f"Python {sys.version_info.major}.{sys.version_info.minor}"),
        "venv_create": (created, "venv 可创建" if created else error or "venv 创建失败"),
        "pip_in_venv": (pip_ok, "隔离环境 pip 可运行" if pip_ok else error or "隔离环境 pip 不可运行"),
    }


def _normalize(answer: str) -> str:
    stripped = answer.strip()
    try:
        return json.dumps(json.loads(stripped), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except json.JSONDecodeError:
        return stripped.casefold()


def run_diagnostics(
    curriculum: dict[str, Any],
    answers: dict[str, dict[str, str]],
    options: dict[str, bool] | None = None,
) -> dict[str, Any]:
    thresholds = curriculum["diagnostic_thresholds"]
    enabled_options = options or {}
    decisions: dict[str, dict[str, str]] = {}
    for module in curriculum["modules"]:
        track_id = module.get("optional_track_id")
        if not track_id or enabled_options.get(track_id, False):
            decisions[module["id"]] = {"status": module["default_status"], "diagnostic_id": "default"}

    results: list[dict[str, Any]] = []
    for diagnostic in curriculum["diagnostics"]:
        diagnostic_id = diagnostic["id"]
        if diagnostic_id == "D0":
            cases = _run_d0()
        else:
            cases = {
                case_id: (
                    _normalize(answers[diagnostic_id][case_id]) == _normalize(QUESTIONS[diagnostic_id][case_id][1]),
                    "回答正确" if _normalize(answers[diagnostic_id][case_id]) == _normalize(QUESTIONS[diagnostic_id][case_id][1]) else "回答不正确",
                )
                for case_id in diagnostic["critical_cases"]
            }
        case_results = [
            {"id": case_id, "passed": cases[case_id][0], "detail": cases[case_id][1]}
            for case_id in diagnostic["critical_cases"]
        ]
        score = round(sum(case["passed"] for case in case_results) * 100 / len(case_results))
        critical_passed = all(case["passed"] for case in case_results)
        if score >= thresholds["pass_min_percent"] and (critical_passed or not thresholds["critical_cases_must_pass"]):
            level = "pass"
        elif score >= thresholds["partial_min_percent"]:
            level = "partial"
        else:
            level = "fail"
        status = diagnostic["decision"][level]
        for module_id in diagnostic["modules"]:
            if module_id in decisions:
                decisions[module_id] = {"status": status, "diagnostic_id": diagnostic_id}
        results.append(
            {
                "id": diagnostic_id,
                "title": diagnostic["title"],
                "score": score,
                "passed": level == "pass",
                "critical_passed": critical_passed,
                "level": level,
            }
        )

    recommendations = {status: [] for status in sorted(MODULE_STATUSES)}
    for module_id, decision in decisions.items():
        recommendations[decision["status"]].append(module_id)
    # Excluded option modules stay out of the mainline recommendation payload.
    return {
        "schema_version": 2,
        "curriculum_version": curriculum["curriculum_version"],
        "run_at": now_iso(),
        "passed": all(item["passed"] for item in results),
        "diagnostics": results,
        "module_decisions": decisions,
        "recommendations": recommendations,
    }


def persist_diagnostic(
    report: dict[str, Any],
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    report_path: Path,
    progress_path: Path,
) -> None:
    atomic_write_json(report_path, report)
    stored_decisions = progress.setdefault("module_decisions", {})
    for module_id, decision in report["module_decisions"].items():
        stored = stored_decisions.setdefault(module_id, {})
        stored.update(decision)
        progress["modules"][module_id] = decision["status"]
    save_progress(progress_path, progress)

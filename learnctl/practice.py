from __future__ import annotations

import ast
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .drills import CLI_CASES, FILE_FIXTURES, FUNCTION_CASES, SCRIPT_CASES
from .envcheck import run_action
from .errors import DataError, UsageError
from .progress import now_iso
from .web.storage import atomic_write_text

MAX_OUTPUT_CHARS = 40_000
TIMEOUT_SECONDS = 15
PYTEST_TIMEOUT = 45

# 供校验器使用的私有实现常量
_CODE_VALIDATORS: dict[str, Callable[[str, "PracticeContext", dict[str, Any]], dict[str, Any]]] = {}


def _tail(text: str | None, limit: int = 900) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return "…" + cleaned[-limit:]


class PracticeContext:
    """一次代码实践校验的隔离临时目录。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.temp = Path(tempfile.mkdtemp(prefix="learnctl-practice-"))
        # 由 workspace 真实落盘提供的依赖文件相对路径，禁止标准脚手架覆盖
        self.ws_deps: set[str] = set()

    def write(self, rel: str, content: str) -> None:
        target = self.temp / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def write_scaffold(self, rel: str, content: str) -> bool:
        """写入标准脚手架文件；若该路径已被 workspace 真实依赖占用则跳过。"""
        if rel in self.ws_deps:
            return False
        self.write(rel, content)
        return True

    def cleanup(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def __enter__(self) -> "PracticeContext":
        return self

    def __exit__(self, *args: Any) -> None:
        self.cleanup()


def _run_proc(
    args: list[str],
    cwd: Path,
    timeout: int = TIMEOUT_SECONDS,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> dict[str, Any]:
    # 强制 UTF-8 环境，保证 Windows 中文 stdout/stderr 不乱码；
    # 调用方可显式覆盖 PYTHONIOENCODING / PYTHONUTF8。
    merged = dict(os.environ)
    merged.setdefault("PYTHONIOENCODING", "utf-8")
    merged.setdefault("PYTHONUTF8", "1")
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            check=False,
            timeout=timeout,
            env=merged,
            input=input_text,
        )
        return {"timeout": False, "stdout": proc.stdout or "", "stderr": proc.stderr or "", "exit_code": proc.returncode}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        return {"timeout": True, "stdout": stdout, "stderr": stderr, "exit_code": None}


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[输出超过 {limit} 字符，已截断]"


def _finalize(checks: list[dict[str, Any]], proc: dict[str, Any]) -> dict[str, Any]:
    if proc.get("timeout"):
        checks = [{"name": "运行超时", "passed": False, "detail": f"超过 {TIMEOUT_SECONDS} 秒"} , *checks]
    passed = bool(checks) and all(bool(item.get("passed")) for item in checks)
    return {
        "passed": passed,
        "checks": checks,
        "stdout": _truncate(proc.get("stdout") or ""),
        "stderr": _truncate(proc.get("stderr") or ""),
        "exit_code": proc.get("exit_code"),
    }


def _read_result(ctx: PracticeContext, result_file: str) -> list[dict[str, Any]]:
    path = ctx.temp / result_file
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _build_harness(module: str, checks: list[tuple[str, str]], *, imports: tuple[str, ...] = (), setup: str = "") -> str:
    lines = ["import json", *imports, f"import {module} as M", ""]
    if setup:
        lines.append(setup)
        lines.append("")
    lines += [
        "def _raises(etype, fn, *args, **kwargs):",
        "    try:",
        "        fn(*args, **kwargs)",
        "    except etype:",
        "        return True",
        "    except Exception:",
        "        return False",
        "    return False",
        "",
        "def _near(a, b, tol=0.01):",
        "    try:",
        "        return abs(a - b) <= tol",
        "    except TypeError:",
        "        return False",
        "",
        "results = []",
        "",
    ]
    for name, expr in checks:
        lines.append("try:")
        comparison = ast.parse(expr, mode="eval").body
        # 等式两侧各求值一次：反馈实际值与期望值，不重复调用有副作用的函数。
        if isinstance(comparison, ast.Compare) and len(comparison.ops) == 1 and isinstance(comparison.ops[0], ast.Eq):
            lines.append(f"    actual = {ast.unparse(comparison.left)}")
            lines.append(f"    expected = {ast.unparse(comparison.comparators[0])}")
            lines.append("    ok = actual == expected")
            lines.append("    detail = '期望：{}；实际：{}'.format(repr(expected), repr(actual))")
        else:
            lines.append(f"    ok = {expr}")
            lines.append("    detail = '检查通过' if ok else '行为与本项要求不符，请检查边界输入或返回值'")
        lines.append(f"    results.append({{'name': {name!r}, 'passed': bool(ok), 'detail': detail}})")
        lines.append("except Exception as e:")
        lines.append(
            f"    results.append({{'name': {name!r}, 'passed': False, 'detail': '{{}}: {{}}'.format(type(e).__name__, e)}})"
        )
        lines.append("")
    lines.append("with open('_result.json', 'w', encoding='utf-8') as f:")
    lines.append("    json.dump(results, f, ensure_ascii=False)")
    return "\n".join(lines)


def _run_harness(
    ctx: PracticeContext,
    harness_src: str,
    result_file: str,
    *,
    env: dict[str, str] | None = None,
    timeout: int = TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ctx.write("_harness.py", harness_src)
    result_path = ctx.temp / result_file
    if result_path.exists():
        result_path.unlink()
    proc = _run_proc([sys.executable, "_harness.py"], cwd=ctx.temp, timeout=timeout, env=env)
    checks = _read_result(ctx, result_file)
    if not checks:
        checks = [
            {
                "name": "代码可导入并完成校验",
                "passed": False,
                "detail": _tail(proc["stderr"] or proc["stdout"]) or "校验脚本未输出结果",
            }
        ]
    return proc, checks


def _module_name(file_name: str) -> str:
    return file_name[:-3].replace("/", ".")


def _function_validator(spec: dict[str, Any]) -> Callable[[str, PracticeContext, dict[str, Any]], dict[str, Any]]:
    def validate(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
        ctx.write(spec["file"], code)
        for rel, content in spec.get("scaffold", []):
            ctx.write_scaffold(rel, content)
        harness = _build_harness(
            spec["module"],
            spec["checks"],
            imports=spec.get("imports", ()),
            setup=spec.get("setup", ""),
        )
        env = None
        if spec.get("env"):
            env = dict(os.environ)
            env.update(spec["env"])
        proc, checks = _run_harness(ctx, harness, "_result.json", env=env)
        if spec.get("silent_import"):
            checks.append({"name": "导入不产生输出", "passed": not proc["stdout"], "detail": _tail(proc["stdout"])})
        return _finalize(checks, proc)

    return validate


def _register(section_id: str, spec: dict[str, Any]) -> None:
    _CODE_VALIDATORS[section_id] = _function_validator(spec)


# --------------------------------------------------------------------------
# 函数级检查（导入用户模块 -> 调用函数 -> 断言）
# --------------------------------------------------------------------------

_register("D02-name", {
    "file": "main.py", "module": "main",
    "checks": [
        ("clean_name 正常", "M.clean_name(' 张三 ') == '张三'"),
        ("clean_name 空值抛错", "_raises(ValueError, M.clean_name, '   ')"),
    ],
})
_register("D02-price", {
    "file": "main.py", "module": "main",
    "checks": [
        ("parse_price 正常", "M.parse_price('99.9') == 99.9"),
        ("parse_price 非法抛错", "_raises(ValueError, M.parse_price, 'abc')"),
        ("calculate_tax 计算", "M.calculate_tax(100.0) == 13.0"),
        ("calculate_tax 精度", "M.calculate_tax(0.5) == 0.07"),
    ],
})
_register("D02-form", {
    "file": "main.py", "module": "main",
    "checks": [
        ("process_form 返回 dict", "(lambda d: isinstance(d, dict) and d.get('name') == '张三' and d.get('price') == 99.9 and 'amount' in d)(M.process_form(' 张三 ', '99.9'))"),
        ("process_form 金额", "(lambda d: d.get('tax') == 12.99 and d.get('amount') == 112.89)(M.process_form('张三', '99.9'))"),
        ("process_form 空名抛错", "_raises(ValueError, M.process_form, '', '10')"),
        ("process_form 非法价格抛错", "_raises(ValueError, M.process_form, '张三', 'abc')"),
    ],
})
_register("D03-grade", {
    "file": "main.py", "module": "main",
    "checks": [
        ("优秀", "M.score_level(95) == '优秀'"),
        ("良好边界", "M.score_level(89) == '良好'"),
        ("及格边界", "M.score_level(60) == '及格'"),
        ("不及格", "M.score_level(10) == '不及格'"),
        ("越界抛错", "_raises(ValueError, M.score_level, -1)"),
    ],
})
_register("D03-loop", {
    "file": "main.py", "module": "main",
    "checks": [
        ("sum_even", "M.sum_even(6) == 12"),
        ("countdown", "M.countdown(3) == [3, 2, 1, 0]"),
        ("find_first 命中", "M.find_first([1, 2, 3], 3) == 2"),
        ("find_first 未命中", "M.find_first([1, 2], 9) == -1"),
    ],
})
_register("D04-params", {
    "file": "main.py", "module": "main",
    "checks": [
        ("默认问候", "M.make_greeting('张三') == '你好，张三'"),
        ("关键字问候", "M.make_greeting('张三', greeting='早上好') == '早上好，张三'"),
        ("join_all", "M.join_all('a', 'b', 'c') == 'a、b、c'"),
        ("describe", "M.describe(x=1, y=2) == {'x': 1, 'y': 2}"),
    ],
})
_register("D04-scope", {
    "file": "main.py", "module": "main",
    "checks": [
        ("计数器递增", "(lambda c: c() == 1 and c() == 2)(M.make_counter())"),
        ("calc_total", "M.calc_total([100, 50], 20) == {'subtotal': 150.0, 'discount': 20.0, 'total': 130.0}"),
    ],
})
_register("D05-sequence", {
    "file": "main.py", "module": "main",
    "checks": [
        ("first_last", "M.first_last([1, 2, 3]) == (1, 3)"),
        ("reverse_slice", "M.reverse_slice([1, 2, 3]) == [3, 2, 1]"),
        ("middle", "M.middle([1, 2, 3, 4]) == [2, 3]"),
        ("空序列抛错", "_raises(ValueError, M.first_last, [])"),
    ],
})
_register("D05-mapping", {
    "file": "main.py", "module": "main",
    "checks": [
        ("count_words", "M.count_words('a b a') == {'a': 2, 'b': 1}"),
        ("unique_keep_order", "M.unique_keep_order(['a', 'b', 'a', 'c']) == ['a', 'b', 'c']"),
        ("merge_scores", "M.merge_scores({'x': 1}, {'x': 2, 'y': 3}) == {'x': 2, 'y': 3}"),
    ],
})
_register("D06-safe", {
    "file": "main.py", "module": "main",
    "checks": [
        ("safe_divide 正常", "M.safe_divide(6, 2) == 3.0"),
        ("safe_divide 除零", "M.safe_divide(6, 0) == '不能除以零'"),
        ("read_int 正常", "M.read_int('42') == 42"),
        ("read_int 非法", "M.read_int('abc') is None"),
    ],
})
_register("D06-custom", {
    "file": "main.py", "module": "main",
    "checks": [
        ("自定义异常类", "issubclass(M.InputError, ValueError)"),
        ("正常记录", "M.validate_record({'name': '张三', 'age': 20}) == {'name': '张三', 'age': 20}"),
        ("空名抛错", "_raises(M.InputError, M.validate_record, {'name': '', 'age': 20})"),
        ("年龄非正抛错", "_raises(M.InputError, M.validate_record, {'name': '张三', 'age': 0})"),
    ],
})
_register("D10-env", {
    "file": "main.py", "module": "main",
    "env": {"CHECK_STR": "abc", "CHECK_INT": "7", "CHECK_BOOL": "true"},
    "checks": [
        ("get_env 读取", "M.get_env('CHECK_STR', 'd') == 'abc'"),
        ("get_int_env 默认", "M.get_int_env('CHECK_MISSING', 5) == 5"),
        ("get_int_env 转换", "M.get_int_env('CHECK_INT', 0) == 7"),
        ("get_bool_env 解析", "M.get_bool_env('CHECK_BOOL', False) is True"),
        ("get_bool_env 默认", "M.get_bool_env('CHECK_MISSING2', True) is True"),
    ],
})
_register("D10-dotenv", {
    "file": "main.py", "module": "main",
    "scaffold": [
        (".env", "KEY=VALUE\nSPACED = hello world\nEMPTY=\n# 这是一个注释\n"),
    ],
    "setup": (
        "def _dotenv_ok():\n"
        "    data = M.load_dotenv('.env')\n"
        "    return data.get('KEY') == 'VALUE' and data.get('SPACED') == 'hello world' and data.get('EMPTY') == ''\n"
    ),
    "checks": [
        ("load_dotenv 解析", "_dotenv_ok()"),
        ("缺失文件返回空", "M.load_dotenv('missing.env') == {}"),
    ],
})
_register("D17-async", {
    "file": "main.py", "module": "main",
    "imports": ("import asyncio",),
    "checks": [
        ("fetch_item", "asyncio.run(M.fetch_item(2)) == 2"),
        ("run_all", "asyncio.run(M.run_all(4)) == [0, 1, 2, 3]"),
        ("main 入口", "M.main(3) == [0, 1, 2]"),
    ],
})

_DB_CREATE_SETUP = (
    "import sqlite3, os\n"
    "DB = '_check.db'\n"
    "if os.path.exists(DB): os.remove(DB)\n"
    "conn = sqlite3.connect(DB)\n"
    "def _table_ok():\n"
    "    cols = [r[1] for r in conn.execute('PRAGMA table_info(tasks)').fetchall()]\n"
    "    return set(cols) >= {'id', 'title', 'done'}\n"
)
_register("D16-create", {
    "file": "main.py", "module": "main",
    "setup": _DB_CREATE_SETUP,
    "checks": [
        ("create_connection 可连接", "M.create_connection(DB) is not None"),
        ("init_db 建表", "(M.init_db(conn) is None) and _table_ok()"),
        ("重复 init 安全", "M.init_db(conn) is None"),
    ],
})
_DB_CRUD_SETUP = (
    "import sqlite3, os\n"
    "DB = '_check.db'\n"
    "if os.path.exists(DB): os.remove(DB)\n"
    "conn = sqlite3.connect(DB)\n"
    "conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')\n"
    "conn.commit()\n"
    "def _toggle_ok():\n"
    "    tid = M.list_tasks(conn)[0]['id']\n"
    "    M.toggle_task(conn, tid)\n"
    "    return M.list_tasks(conn)[0]['done'] is True\n"
    "def _delete_ok():\n"
    "    before = len(M.list_tasks(conn))\n"
    "    M.delete_task(conn, M.list_tasks(conn)[0]['id'])\n"
    "    return len(M.list_tasks(conn)) == before - 1\n"
)
_register("D16-crud", {
    "file": "main.py", "module": "main",
    "setup": _DB_CRUD_SETUP,
    "checks": [
        ("add_task 返回自增 id", "(lambda i: isinstance(i, int) and i > 0)(M.add_task(conn, '任务一'))"),
        ("list_tasks 结构", "(lambda r: bool(r) and r[0]['title'] == '任务一' and r[0]['done'] is False)(M.list_tasks(conn))"),
        ("toggle 翻转", "_toggle_ok()"),
        ("delete 移除", "_delete_ok()"),
        ("标题含引号安全", "M.add_task(conn, \"它's 的\") is not None"),
    ],
})

_TASKPROJ_PACKAGE = [("taskproj/__init__.py", "")]
_D20_INIT_SETUP = _DB_CREATE_SETUP
_register("D20-init", {
    "file": "taskproj/db.py", "module": "taskproj.db", "scaffold": _TASKPROJ_PACKAGE,
    "setup": _D20_INIT_SETUP,
    "checks": [
        ("create_connection 可连接", "M.create_connection(DB) is not None"),
        ("init_db 建表", "(M.init_db(conn) is None) and _table_ok()"),
        ("重复 init 安全", "M.init_db(conn) is None"),
    ],
})
_D20_CRUD_SETUP = (
    "import sqlite3, os\n"
    "DB = '_check.db'\n"
    "if os.path.exists(DB): os.remove(DB)\n"
    "conn = sqlite3.connect(DB)\n"
    "conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')\n"
    "conn.commit()\n"
    "def _table_ok(c):\n"
    "    cols = [r[1] for r in c.execute('PRAGMA table_info(tasks)').fetchall()]\n"
    "    return set(cols) >= {'id', 'title', 'done'}\n"
    "def _complete_ok():\n"
    "    tid = M.list_tasks(conn)[0]['id']\n"
    "    M.complete_task(conn, tid)\n"
    "    return M.list_tasks(conn)[0]['done'] is True\n"
    "def _delete_ok():\n"
    "    before = len(M.list_tasks(conn))\n"
    "    M.delete_task(conn, M.list_tasks(conn)[0]['id'])\n"
    "    return len(M.list_tasks(conn)) == before - 1\n"
)
_register("D20-crud", {
    "file": "taskproj/db.py", "module": "taskproj.db", "scaffold": _TASKPROJ_PACKAGE,
    "setup": _D20_CRUD_SETUP,
    "checks": [
        ("create_connection 可连接", "M.create_connection(DB) is not None"),
        ("init_db 建表", "(lambda c: (M.init_db(c) is None) and _table_ok(c))(M.create_connection('_check2.db'))"),
        ("add_task 返回自增 id", "(lambda i: isinstance(i, int) and i > 0)(M.add_task(conn, '任务一'))"),
        ("list_tasks 结构", "(lambda r: bool(r) and r[0]['title'] == '任务一' and r[0]['done'] is False)(M.list_tasks(conn))"),
        ("complete 置 1", "_complete_ok()"),
        ("delete 移除", "_delete_ok()"),
        ("标题含引号安全", "M.add_task(conn, \"它's 的\") is not None"),
    ],
})


# --------------------------------------------------------------------------
# AST 校验（FastAPI 结构，离线确定）
# --------------------------------------------------------------------------

def _has_import(tree: ast.AST, module: str, name: str | None = None) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == module for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if name is None or any(a.name == name for a in node.names):
                return True
    return False


def _route_paths(tree: ast.AST) -> set[tuple[str, str]]:
    paths: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    method = dec.func.attr.upper()
                    if method in {"GET", "POST", "PATCH", "DELETE", "PUT"} and dec.args:
                        arg0 = dec.args[0]
                        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                            paths.add((method, arg0.value))
    return paths


def _assign_app(tree: ast.AST, app_name: str = "app") -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == app_name and isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == "FastAPI":
                        return True
    return False


def _class_fields(tree: ast.AST, class_name: str) -> dict[str, str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: dict[str, str] = {}
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    try:
                        fields[stmt.target.id] = ast.unparse(stmt.annotation)
                    except Exception:
                        fields[stmt.target.id] = "?"
            return fields
    return {}


def _func_raises_http(tree: ast.AST, func_name: str | None, status: int | None) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and (func_name is None or node.name == func_name):
            for child in ast.walk(node):
                if isinstance(child, ast.Raise) and isinstance(child.exc, ast.Call):
                    if isinstance(child.exc.func, ast.Name) and child.exc.func.id == "HTTPException":
                        if status is None:
                            return True
                        for kw in child.exc.keywords:
                            if kw.arg == "status_code" and isinstance(kw.value, ast.Constant) and kw.value.value == status:
                                return True
    return False


def _ast_validator(spec: dict[str, Any]) -> Callable[[str, PracticeContext, dict[str, Any]], dict[str, Any]]:
    def validate(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            checks = [{"name": "Python 语法", "passed": False, "detail": f"第 {exc.lineno} 行：{exc.msg}"}]
            return {"passed": False, "checks": checks, "stdout": "", "stderr": str(exc), "exit_code": None}
        checks: list[dict[str, Any]] = []
        for name, predicate in spec["checks"]:
            try:
                ok = bool(predicate(tree))
            except Exception as exc:  # noqa: BLE001
                ok = False
                name = f"{name}（校验异常：{exc}）"
            checks.append({"name": name, "passed": ok, "detail": ""})
        passed = all(item["passed"] for item in checks)
        return {"passed": passed, "checks": checks, "stdout": "", "stderr": "", "exit_code": None}

    return validate


def _register_ast(section_id: str, spec: dict[str, Any]) -> None:
    _CODE_VALIDATORS[section_id] = _ast_validator(spec)


_register_ast("D13-app", {
    "file": "app.py",
    "checks": [
        ("导入 FastAPI 并创建 app", lambda t: _has_import(t, "fastapi", "FastAPI") and _assign_app(t)),
        ("GET /health 路由", lambda t: ("GET", "/health") in _route_paths(t)),
    ],
})
_register_ast("D13-route", {
    "file": "app.py",
    "checks": [
        ("GET /items/{item_id} 路由", lambda t: ("GET", "/items/{item_id}") in _route_paths(t)),
        ("GET /items 路由", lambda t: ("GET", "/items") in _route_paths(t)),
    ],
})
_register_ast("D14-model", {
    "file": "app.py",
    "checks": [
        ("导入 pydantic BaseModel", lambda t: _has_import(t, "pydantic", "BaseModel")),
        ("Item 模型含 name/price", lambda t: set(_class_fields(t, "Item")) >= {"name", "price"}),
        ("POST /items 路由", lambda t: ("POST", "/items") in _route_paths(t)),
    ],
})
_register_ast("D14-errors", {
    "file": "app.py",
    "checks": [
        ("导入 HTTPException", lambda t: _has_import(t, "fastapi", "HTTPException")),
        ("validate_price 抛 422", lambda t: _func_raises_http(t, "validate_price", 422)),
        ("read_item 抛 404", lambda t: _func_raises_http(t, "read_item", 404)),
    ],
})
_register_ast("D21-routes", {
    "file": "api.py",
    "checks": [
        ("TaskIn 含 title", lambda t: "title" in _class_fields(t, "TaskIn")),
        ("Task 模型含 id/title/done", lambda t: set(_class_fields(t, "Task")) >= {"id", "title", "done"}),
        ("GET / 网页路由", lambda t: ("GET", "/") in _route_paths(t)),
        ("GET /health 路由", lambda t: ("GET", "/health") in _route_paths(t)),
        ("GET /api/tasks 路由", lambda t: ("GET", "/api/tasks") in _route_paths(t)),
        ("POST /api/tasks 路由", lambda t: ("POST", "/api/tasks") in _route_paths(t)),
    ],
})
_register_ast("D21-errors", {
    "file": "api.py",
    "checks": [
        ("GET / 网页路由", lambda t: ("GET", "/") in _route_paths(t)),
        ("GET /health 路由", lambda t: ("GET", "/health") in _route_paths(t)),
        ("PATCH 完成路由", lambda t: ("PATCH", "/api/tasks/{task_id}/done") in _route_paths(t)),
        ("DELETE 删除路由", lambda t: ("DELETE", "/api/tasks/{task_id}") in _route_paths(t)),
        ("导入 HTTPException", lambda t: _has_import(t, "fastapi", "HTTPException")),
        ("存在 404 错误处理", lambda t: _func_raises_http(t, None, 404)),
    ],
})


# --------------------------------------------------------------------------
# 本地 HTTP 与 DeepSeek mock 服务
# --------------------------------------------------------------------------

class _LocalHttpHandler(BaseHTTPRequestHandler):
    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/ok":
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/echo":
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                payload = {}
            self._json(payload)
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, *args: Any) -> None:
        return


class _DeepSeekMockHandler(BaseHTTPRequestHandler):
    def _send(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            body = {}
        auth = self.headers.get("Authorization", "")
        messages = body.get("messages") or []
        content = str(messages[0].get("content", "")) if messages else ""
        if "ERROR_401" in content:
            self._send({"error": "unauthorized"}, 401)
        elif "NONJSON" in content:
            data = b"not json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif "REVIEW_OK" in content:
            inner = json.dumps(
                {"summary": "总结", "strengths": ["优点"], "issues": ["问题"], "next_steps": ["下一步"]},
                ensure_ascii=False,
            )
            self._send({"choices": [{"message": {"content": inner}}]})
        elif "REVIEW_BAD" in content:
            self._send({"choices": [{"message": {"content": '{"only": "x"}'}}]})
        elif "JSON_CONTENT" in content:
            self._send({"choices": [{"message": {"content": '{"ok": true}'}}]})
        else:
            self._send({"choices": [{"message": {"content": f"auth:{auth}"}}]})

    def log_message(self, *args: Any) -> None:
        return


def _start_server(handler: type[BaseHTTPRequestHandler]) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _stop_server(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _run_with_server(
    handler: type[BaseHTTPRequestHandler],
    harness: str,
    ctx: PracticeContext,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    server, thread = _start_server(handler)
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        final_env = dict(os.environ)
        final_env.update(env or {})
        final_env["CHECK_BASE_URL"] = base
        harness_with_url = harness.replace("__BASE__", base)
        proc, checks = _run_harness(ctx, harness_with_url, "_result.json", env=final_env)
        return _finalize(checks, proc)
    finally:
        _stop_server(server, thread)


def _v_d12_request(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    harness = "\n".join([
        "import json",
        "import main as M",
        "url = '__BASE__'",
        "results = []",
        "def _add(name, ok, detail=''):",
        "    results.append({'name': name, 'passed': bool(ok), 'detail': detail})",
        "try:",
        "    data = M.get_json(url + '/ok')",
        "    _add('GET 正常返回 dict', data == {'ok': True}, repr(data))",
        "except Exception as e:",
        "    _add('GET 正常返回 dict', False, '{}: {}'.format(type(e).__name__, e))",
        "try:",
        "    M.get_json(url + '/notfound')",
        "    _add('404 抛 RuntimeError', False, '没有抛出异常')",
        "except RuntimeError as e:",
        "    _add('404 抛 RuntimeError', True, str(e))",
        "except Exception as e:",
        "    _add('404 抛 RuntimeError', False, '{}: {}'.format(type(e).__name__, e))",
        "try:",
        "    v = M.safe_get_json(url + '/notfound')",
        "    _add('safe_get_json 失败返回 None', v is None, repr(v))",
        "except Exception as e:",
        "    _add('safe_get_json 失败返回 None', False, '{}: {}'.format(type(e).__name__, e))",
        "with open('_result.json', 'w', encoding='utf-8') as f:",
        "    json.dump(results, f, ensure_ascii=False)",
    ])
    return _run_with_server(_LocalHttpHandler, harness, ctx)


def _v_d12_post(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    harness = "\n".join([
        "import json",
        "import main as M",
        "url = '__BASE__'",
        "results = []",
        "def _add(name, ok, detail=''):",
        "    results.append({'name': name, 'passed': bool(ok), 'detail': detail})",
        "try:",
        "    data = M.post_json(url + '/echo', {'a': 1})",
        "    _add('POST 回显 JSON', data == {'a': 1}, repr(data))",
        "except Exception as e:",
        "    _add('POST 回显 JSON', False, '{}: {}'.format(type(e).__name__, e))",
        "with open('_result.json', 'w', encoding='utf-8') as f:",
        "    json.dump(results, f, ensure_ascii=False)",
    ])
    return _run_with_server(_LocalHttpHandler, harness, ctx)


def _v_d25_chat(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    harness = "\n".join([
        "import json",
        "import main as M",
        "url = '__BASE__'",
        "results = []",
        "def _add(name, ok, detail=''):",
        "    results.append({'name': name, 'passed': bool(ok), 'detail': detail})",
        "try:",
        "    content = M.call_chat('test-key', [{'role': 'user', 'content': 'AUTH_CHECK'}], base_url=url)",
        "    _add('返回 mock 内容', content == 'auth:Bearer test-key', repr(content))",
        "except Exception as e:",
        "    _add('返回 mock 内容', False, '{}: {}'.format(type(e).__name__, e))",
        "with open('_result.json', 'w', encoding='utf-8') as f:",
        "    json.dump(results, f, ensure_ascii=False)",
    ])
    return _run_with_server(_DeepSeekMockHandler, harness, ctx)


def _v_d25_errors(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    harness = "\n".join([
        "import json",
        "import main as M",
        "url = '__BASE__'",
        "results = []",
        "def _add(name, ok, detail=''):",
        "    results.append({'name': name, 'passed': bool(ok), 'detail': detail})",
        "try:",
        "    M.call_chat('k', [{'role': 'user', 'content': 'ERROR_401'}], base_url=url)",
        "    _add('401 抛 ApiError', False, '没有抛出异常')",
        "except M.ApiError as e:",
        "    _add('401 抛 ApiError', e.status_code == 401, 'status_code=' + repr(e.status_code))",
        "except Exception as e:",
        "    _add('401 抛 ApiError', False, '{}: {}'.format(type(e).__name__, e))",
        "try:",
        "    M.call_chat('k', [{'role': 'user', 'content': 'NONJSON'}], base_url=url)",
        "    _add('非 JSON 抛 ApiError', False, '没有抛出异常')",
        "except M.ApiError:",
        "    _add('非 JSON 抛 ApiError', True, '')",
        "except Exception as e:",
        "    _add('非 JSON 抛 ApiError', False, '{}: {}'.format(type(e).__name__, e))",
        "try:",
        "    out = M.call_chat('k', [{'role': 'user', 'content': 'AUTH_CHECK'}], base_url=url)",
        "    _add('正常请求返回内容', out == 'auth:Bearer k', repr(out))",
        "except Exception as e:",
        "    _add('正常请求返回内容', False, '{}: {}'.format(type(e).__name__, e))",
        "with open('_result.json', 'w', encoding='utf-8') as f:",
        "    json.dump(results, f, ensure_ascii=False)",
    ])
    return _run_with_server(_DeepSeekMockHandler, harness, ctx)


_AI_REFERENCE_FIXTURES: list[tuple[str, str]] = [
    (
        "deepseek_client.py",
        "import json\n"
        "import urllib.request\n"
        "from urllib.error import HTTPError, URLError\n"
        "\n"
        "class ApiError(RuntimeError):\n"
        "    def __init__(self, message, status_code=None):\n"
        "        super().__init__(message)\n"
        "        self.status_code = status_code\n"
        "\n"
        "def call_chat(api_key, messages, *, base_url='https://api.deepseek.com'):\n"
        "    body = json.dumps({'model': 'deepseek-chat', 'messages': messages, 'stream': False}).encode('utf-8')\n"
        "    req = urllib.request.Request(\n"
        "        f'{base_url}/chat/completions', data=body,\n"
        "        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')\n"
        "    try:\n"
        "        with urllib.request.urlopen(req, timeout=60) as r:\n"
        "            return json.loads(r.read())['choices'][0]['message']['content']\n"
        "    except HTTPError as e:\n"
        "        raise ApiError('API 错误', e.code)\n"
        "    except URLError as e:\n"
        "        raise ApiError('网络错误')\n",
    ),
    (
        "prompt.py",
        "def build_prompt(catalog_titles, goal, instructions, completed):\n"
        "    scope = '；'.join(catalog_titles)\n"
        "    return (f'知识范围标题：{scope}\\n'\n"
        "            f'索引仅代表标题知识范围，不代表视频正文。\\n'\n"
        "            f'目标：{goal}\\n要求：{instructions}\\n已完成：{completed}')\n"
        "\n"
        "def parse_ai_json(text):\n"
        "    import json\n"
        "    start = text.find('{')\n"
        "    end = text.rfind('}')\n"
        "    if start == -1 or end == -1 or end <= start:\n"
        "        raise ValueError('没有 JSON')\n"
        "    return json.loads(text[start:end + 1])\n",
    ),
]


def _v_d26_prompt(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    harness = _build_harness("main", [
        ("包含索引标题", "(lambda s: 'Python-01-初识Python' in s and 'Python-13-数据类型的转换' in s)(M.build_prompt(['Python-01-初识Python', 'Python-13-数据类型的转换'], '学习目标', '练习要求', True))"),
        ("声明索引边界", "'索引仅代表标题知识范围' in M.build_prompt(['a'], 'b', 'c', False)"),
        ("包含目标与已完成", "(lambda s: '目标' in s and '已完成' in s)(M.build_prompt(['a'], '学习目标', '练习要求', False))"),
    ])
    proc, checks = _run_harness(ctx, harness, "_result.json")
    return _finalize(checks, proc)


def _v_d26_parse(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    harness = _build_harness("main", [
        ("提取内嵌 JSON", "M.parse_ai_json('前缀 {\"a\": 1} 后缀') == {'a': 1}"),
        ("纯 JSON 成功", "M.parse_ai_json('{\"b\": 2}') == {'b': 2}"),
        ("无 JSON 抛错", "_raises(ValueError, M.parse_ai_json, '没有JSON')"),
    ])
    proc, checks = _run_harness(ctx, harness, "_result.json")
    return _finalize(checks, proc)


def _v_d27_client(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    for rel, content in _AI_REFERENCE_FIXTURES:
        ctx.write(rel, content)
    harness = "\n".join([
        "import json",
        "import main as M",
        "url = '__BASE__'",
        "results = []",
        "def _add(name, ok, detail=''):",
        "    results.append({'name': name, 'passed': bool(ok), 'detail': detail})",
        "try:",
        "    data = M.send_message('test-key', 'JSON_CONTENT', base_url=url)",
        "    _add('send_message 返回 dict', data == {'ok': True}, repr(data))",
        "except Exception as e:",
        "    _add('send_message 返回 dict', False, '{}: {}'.format(type(e).__name__, e))",
        "try:",
        "    M.send_message('k', 'NONJSON', base_url=url)",
        "    _add('非 JSON 抛 ApiError', False, '没有抛出异常')",
        "except Exception:",
        "    _add('非 JSON 抛 ApiError', True, '')",
        "with open('_result.json', 'w', encoding='utf-8') as f:",
        "    json.dump(results, f, ensure_ascii=False)",
    ])
    return _run_with_server(_DeepSeekMockHandler, harness, ctx)


def _v_d27_flow(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    ctx.write("main.py", code)
    for rel, content in _AI_REFERENCE_FIXTURES:
        ctx.write(rel, content)
    harness = "\n".join([
        "import json",
        "import main as M",
        "url = '__BASE__'",
        "results = []",
        "def _add(name, ok, detail=''):",
        "    results.append({'name': name, 'passed': bool(ok), 'detail': detail})",
        "try:",
        "    data = M.review_submission('test-key', 'REVIEW_OK', '标准', ['Python-01-初识Python'], base_url=url)",
        "    keys = {'summary', 'strengths', 'issues', 'next_steps'}",
        "    _add('评审返回四键', isinstance(data, dict) and keys <= set(data.keys()), repr(data))",
        "except Exception as e:",
        "    _add('评审返回四键', False, '{}: {}'.format(type(e).__name__, e))",
        "try:",
        "    M.review_submission('k', 'REVIEW_BAD', '标准', ['a'], base_url=url)",
        "    _add('缺键抛 ValueError', False, '没有抛出异常')",
        "except ValueError:",
        "    _add('缺键抛 ValueError', True, '')",
        "except Exception as e:",
        "    _add('缺键抛 ValueError', False, '{}: {}'.format(type(e).__name__, e))",
        "with open('_result.json', 'w', encoding='utf-8') as f:",
        "    json.dump(results, f, ensure_ascii=False)",
    ])
    return _run_with_server(_DeepSeekMockHandler, harness, ctx)


# --------------------------------------------------------------------------
# 直接运行脚本的校验
# --------------------------------------------------------------------------

def _direct_run_validator(spec: dict[str, Any]) -> Callable[[str, PracticeContext, dict[str, Any]], dict[str, Any]]:
    def validate(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
        ctx.write(spec["file"], code)
        for rel, content in spec.get("scaffold", []):
            ctx.write_scaffold(rel, content)
        checks: list[dict[str, Any]] = []
        combined = {"stdout": "", "stderr": "", "exit_code": None, "timeout": False}
        env = spec.get("env")
        for argv, name, predicate, detail_of in spec["runs"]:
            proc = _run_proc([sys.executable, *argv], cwd=ctx.temp, timeout=spec.get("timeout", TIMEOUT_SECONDS), env=env)
            ok = predicate(proc)
            checks.append({"name": name, "passed": ok, "detail": detail_of(proc)})
            combined["stdout"] += proc["stdout"]
            combined["stderr"] += proc["stderr"]
            combined["exit_code"] = proc["exit_code"]
            combined["timeout"] = combined["timeout"] or proc["timeout"]
        return _finalize(checks, combined)

    return validate


_CODE_VALIDATORS["D07-import"] = _direct_run_validator({
    "file": "main.py",
    "scaffold": [("greetings.py", 'def hello(name):\n    return f"你好，{name}"\n')],
    "runs": [
        (["main.py"], "运行 main.py 输出问候", lambda p: "你好，世界" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})

_CODE_VALIDATORS["D07-main"] = _direct_run_validator({
    "file": "main.py",
    "runs": [
        (["main.py"], "直接运行输出 ok", lambda p: "ok" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D09-args"] = _direct_run_validator({
    "file": "main.py",
    "runs": [
        (["main.py", "--name", "张三", "--count", "2"], "输出两行问候", lambda p: p["stdout"].count("你好，张三") == 2, lambda p: _tail(p["stdout"] or p["stderr"])),
        (["main.py", "--help"], "--help 退出码 0", lambda p: p["exit_code"] == 0, lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D09-errors"] = _direct_run_validator({
    "file": "main.py",
    "runs": [
        (["main.py", "--level", "nope"], "非法 level 报错", lambda p: p["exit_code"] not in (0, None), lambda p: _tail(p["stderr"])),
        (["main.py", "--name", "张三", "--count", "0"], "count=0 退出码非 0", lambda p: p["exit_code"] not in (0, None) and "count" in (p["stderr"] + p["stdout"]), lambda p: _tail(p["stderr"])),
    ],
})
_CODE_VALIDATORS["D11-basic"] = _direct_run_validator({
    "file": "main.py",
    "runs": [
        (["main.py"], "日志输出 INFO 与消息", lambda p: "INFO" in p["stdout"] and "服务已启动" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D19-main"] = _direct_run_validator({
    "file": "taskproj/main.py",
    "scaffold": [("taskproj/__init__.py", "")],
    "runs": [
        (["-m", "taskproj.main"], "入口输出启动提示", lambda p: "任务管理项目已启动" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})

_TASKPROJ_DB_REF = (
    "import sqlite3\n"
    "\n"
    "def create_connection(path):\n"
    "    conn = sqlite3.connect(str(path))\n"
    "    init_db(conn)\n"
    "    return conn\n"
    "\n"
    "def init_db(conn):\n"
    "    conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')\n"
    "    conn.commit()\n"
    "\n"
    "def add_task(conn, title):\n"
    "    cur = conn.execute('INSERT INTO tasks (title) VALUES (?)', (title,))\n"
    "    conn.commit()\n"
    "    return cur.lastrowid\n"
    "\n"
    "def list_tasks(conn):\n"
    "    rows = conn.execute('SELECT id, title, done FROM tasks ORDER BY id').fetchall()\n"
    "    return [{'id': r[0], 'title': r[1], 'done': bool(r[2])} for r in rows]\n"
    "\n"
    "def complete_task(conn, task_id):\n"
    "    conn.execute('UPDATE tasks SET done = 1 WHERE id = ?', (task_id,))\n"
    "    conn.commit()\n"
    "\n"
    "def delete_task(conn, task_id):\n"
    "    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))\n"
    "    conn.commit()\n"
)
_API_CLIENT_REF = (
    "import json\n"
    "import urllib.request\n"
    "\n"
    "def get_json(url):\n"
    "    with urllib.request.urlopen(url, timeout=10) as r:\n"
    "        return json.loads(r.read())\n"
    "\n"
    "def post_json(url, payload):\n"
    "    req = urllib.request.Request(\n"
    "        url, data=json.dumps(payload).encode('utf-8'),\n"
    "        headers={'Content-Type': 'application/json'}, method='POST')\n"
    "    with urllib.request.urlopen(req, timeout=10) as r:\n"
    "        return json.loads(r.read())\n"
)

_TAX_REF = "def calculate_tax(price):\n    return round(price * 0.13, 2)\n"


def _pytest_validator(test_file: str, fixtures: list[tuple[str, str]]) -> Callable[[str, PracticeContext, dict[str, Any]], dict[str, Any]]:
    def validate(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
        for rel, content in fixtures:
            ctx.write_scaffold(rel, content)
        ctx.write(test_file, code)
        proc = _run_proc([sys.executable, "-m", "pytest", "-q", test_file], cwd=ctx.temp, timeout=PYTEST_TIMEOUT)
        checks = [
            {
                "name": f"pytest {test_file} 全部通过",
                "passed": proc["exit_code"] == 0,
                "detail": _tail(proc["stdout"] or proc["stderr"]),
            }
        ]
        return _finalize(checks, proc)

    return validate


_CODE_VALIDATORS["D08-read"] = _direct_run_validator({
    "file": "main.py",
    "scaffold": [
        ("records.json", '[{"name": "A", "category": "x"}, {"name": "B", "category": "y"}, {"name": "C", "category": "x"}]'),
    ],
    "runs": [
        (["-c", "import main; data = main.load_records('records.json'); stats = main.collect_stats(data); print(stats['count'], sorted(stats['categories']))"],
         "读取并统计正确", lambda p: p["stdout"].strip() == "3 ['x', 'y']", lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D08-write"] = _direct_run_validator({
    "file": "main.py",
    "runs": [
        (["-c", "import json, main; main.save_report('out/report.json', {'count': 2, 'ok': True}); print(json.load(open('out/report.json', encoding='utf-8')))"],
         "写回 JSON 报告", lambda p: p["stdout"].strip() == "{'count': 2, 'ok': True}" and p["exit_code"] == 0, lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D11-file"] = _direct_run_validator({
    "file": "main.py",
    "runs": [
        (["-c", "import os; os.makedirs('logs', exist_ok=True); import main; logger = main.configure_file_logger('logs/app.log'); logger.info('写入日志'); [handler.close() for handler in logger.handlers]; print(open('logs/app.log', encoding='utf-8').read())"],
         "文件日志写入", lambda p: "INFO" in p["stdout"] and "写入日志" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D19-config"] = _direct_run_validator({
    "file": "taskproj/config.py",
    "scaffold": [("taskproj/__init__.py", "")],
    "runs": [
        (["-c", "import os; os.environ['TASKPROJ_DB'] = 'custom.db'; from taskproj import config; print(str(config.get_db_path()))"],
         "读取 TASKPROJ_DB", lambda p: p["stdout"].strip() == "custom.db", lambda p: _tail(p["stdout"] or p["stderr"])),
        (["-c", "import os; os.environ.pop('TASKPROJ_DB', None); from taskproj import config; print(str(config.get_db_path()))"],
         "缺省 taskproj.db", lambda p: p["stdout"].strip() == "taskproj.db", lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D23-cli"] = _direct_run_validator({
    "file": "taskproj/cli.py",
    # 不再提供 config/db/__init__ 等任何标准脚手架（含 _TASKPROJ_CONFIG_REF/_TASKPROJ_DB_REF）：
    # 必须使用 workspace 真实依赖，缺依赖时 validate_code 直接判失败，损坏的真实文件不会被掩盖。
    "env": {"TASKPROJ_DB": "_cli.db"},
    "runs": [
        (["-m", "taskproj.cli", "add", "买牛奶"], "CLI add 成功", lambda p: p["exit_code"] == 0, lambda p: _tail(p["stderr"] or p["stdout"])),
        (["-m", "taskproj.cli", "list"], "CLI list 可见任务", lambda p: "买牛奶" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
        (["-m", "taskproj.cli", "done", "1"], "CLI done 标记完成", lambda p: p["exit_code"] == 0, lambda p: _tail(p["stderr"] or p["stdout"])),
        (["-m", "taskproj.cli", "list"], "CLI list 显示 [done]", lambda p: "[done]" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
        (["-m", "taskproj.cli", "rm", "1"], "CLI rm 删除", lambda p: p["exit_code"] == 0, lambda p: _tail(p["stderr"] or p["stdout"])),
        (["-m", "taskproj.cli", "list"], "CLI list 已删除", lambda p: "买牛奶" not in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})

_CODE_VALIDATORS["D15-unit"] = _pytest_validator("test_tax.py", [("tax.py", _TAX_REF)])
_CODE_VALIDATORS["D15-mock"] = _pytest_validator("test_client.py", [("client.py", _API_CLIENT_REF)])
_CODE_VALIDATORS["D22-db"] = _pytest_validator("test_project.py", [("taskproj/__init__.py", ""), ("taskproj/db.py", _TASKPROJ_DB_REF)])
# D22-api：不提供任何隐藏实现（含 api_client.py 等参考夹具），仅运行提交的
# tests/test_api.py 与 workspace 真实依赖；真实文件由 workspace_deps 在
# validate_code 中注入并受保护，标准脚手架不得覆盖。
_CODE_VALIDATORS["D22-api"] = _pytest_validator("tests/test_api.py", [])
_CODE_VALIDATORS["D28-test"] = _pytest_validator("test_ai_client.py", [("ai_client.py", _AI_REFERENCE_FIXTURES[0][1])])

_CODE_VALIDATORS["D17-timeout"] = _function_validator({
    "file": "main.py", "module": "main",
    "imports": ("import asyncio",),
    "checks": [
        ("未超时返回", "M.run(3, 2.0) == 3"),
        ("超时抛 TimeoutError", "_raises(asyncio.TimeoutError, M.run, 3, 0.1)"),
    ],
})

_CODE_VALIDATORS["D12-request"] = _function_validator({
    "file": "main.py", "module": "main",
    "setup": """from urllib.request import Request
seen = []
class Response:
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self): return '你好，Python'.encode('utf-8')
def opener(request):
    seen.append(request)
    return Response()
""",
    "checks": [
        ("GET 读取 UTF-8 文本", "M.fetch_text('https://example.test/hello', opener) == '你好，Python'"),
        ("使用 GET Request", "len(seen) == 1 and isinstance(seen[0], Request) and seen[0].get_method() == 'GET'"),
    ],
})
_CODE_VALIDATORS["D12-post"] = _v_d12_post
_CODE_VALIDATORS["D25-chat"] = _v_d25_chat
_CODE_VALIDATORS["D25-errors"] = _v_d25_errors
_CODE_VALIDATORS["D26-prompt"] = _v_d26_prompt
_CODE_VALIDATORS["D26-parse"] = _v_d26_parse
_CODE_VALIDATORS["D27-client"] = _v_d27_client
_CODE_VALIDATORS["D27-flow"] = _v_d27_flow


# --------------------------------------------------------------------------
# curriculum v3 Python syntax practices
# --------------------------------------------------------------------------

def _has_call(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == name:
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == name:
            return True
    return False


def _has_node(tree: ast.AST, *node_types: type[ast.AST]) -> bool:
    return any(isinstance(node, node_types) for node in ast.walk(tree))


def _v3_code_validator(
    required: list[tuple[str, Callable[[ast.AST], bool]]],
) -> Callable[[str, PracticeContext, dict[str, Any]], dict[str, Any]]:
    """Run a submitted Python file and assert the syntax shape of the lesson.

    The AST checks keep a learner from passing a section with an unrelated script;
    the subprocess check executes the learner's code, so this is not a keyword-only
    validator.  The course still leaves implementation choices open within the
    declared Python concept.
    """

    def validate(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return {
                "passed": False,
                "checks": [{"name": "Python 语法可解析", "passed": False, "detail": f"第 {exc.lineno} 行：{exc.msg}"}],
                "stdout": "",
                "stderr": str(exc),
                "exit_code": None,
            }

        file_name = section["practice"].get("file_name", "main.py")
        ctx.write(file_name, code)
        proc = _run_proc([sys.executable, file_name], cwd=ctx.temp)
        checks: list[dict[str, Any]] = [{"name": "Python 语法可解析", "passed": True, "detail": "AST 解析通过"}]
        for name, predicate in required:
            try:
                passed = bool(predicate(tree))
                detail = ""
            except Exception as exc:  # noqa: BLE001
                passed = False
                detail = f"{type(exc).__name__}: {exc}"
            checks.append({"name": name, "passed": passed, "detail": detail})
        checks.append({
            "name": "提交代码实际运行",
            "passed": proc["exit_code"] == 0 and not proc.get("timeout"),
            "detail": _tail(proc["stdout"] or proc["stderr"]),
        })
        return _finalize(checks, proc)

    return validate


def _register_v3_code(section_id: str, *required: tuple[str, Callable[[ast.AST], bool]]) -> None:
    _CODE_VALIDATORS[section_id] = _v3_code_validator(list(required))


def _execution_validator(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
    """D02 execution checks the observable three-line program, not just AST shape."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "passed": False,
            "checks": [{"name": "Python 语法可解析", "passed": False, "detail": f"第 {exc.lineno} 行：{exc.msg}"}],
            "stdout": "",
            "stderr": str(exc),
            "exit_code": None,
        }
    ctx.write(section["practice"].get("file_name", "main.py"), code)
    proc = _run_proc([sys.executable, section["practice"].get("file_name", "main.py")], cwd=ctx.temp)
    lines = (proc.get("stdout") or "").strip().splitlines()
    checks = [
        {"name": "Python 语法可解析", "passed": True, "detail": f"AST 节点 {len(list(ast.walk(tree)))} 个"},
        {"name": "输出 START/BLOCK/END", "passed": lines == ["START", "BLOCK", "END"], "detail": repr(lines)},
        {"name": "代码实际运行", "passed": proc.get("exit_code") == 0 and not proc.get("timeout"), "detail": _tail(proc.get("stderr") or proc.get("stdout"))},
    ]
    return _finalize(checks, proc)


_CODE_VALIDATORS["D02-execution"] = _execution_validator
_register_v3_code("D02-names", ("观察 type/isinstance", lambda t: _has_call(t, "type") and _has_call(t, "isinstance")))
_register_v3_code("D02-numbers", ("包含算术和比较", lambda t: _has_node(t, ast.BinOp) and _has_node(t, ast.Compare)))
_register_v3_code("D02-bool-none", ("区分条件与 None", lambda t: _has_node(t, ast.If) and _has_node(t, ast.Constant)))
_register_v3_code("D02-strings", ("包含索引或切片", lambda t: _has_node(t, ast.Subscript) and _has_node(t, ast.Slice)))
_register("D02-numbers", {
    "file": "main.py", "module": "main",
    "checks": [
        ("商与余数正确", "M.divide_parts(17, 5) == (3, 2)"),
        ("除数为零被拒绝", "_raises(ValueError, M.divide_parts, 17, 0)"),
    ],
})
_register("D02-bool-none", {
    "file": "main.py", "module": "main",
    "checks": [
        ("None 是缺失", "M.describe_value(None) == 'missing'"),
        ("空文本单独处理", "M.describe_value('') == 'empty text'"),
        ("零不是缺失", "M.describe_value(0) == 'present'"),
        ("非空列表不是缺失", "M.describe_value([0]) == 'present'"),
    ],
})
_register_v3_code("D02-string-methods", ("使用文本方法或 f-string", lambda t: _has_node(t, ast.JoinedStr) or any(_has_call(t, n) for n in ("strip", "split", "join"))))
_register_v3_code("D03-if", ("包含 if 分支", lambda t: _has_node(t, ast.If)))
_register_v3_code("D03-match", ("包含 match/case", lambda t: _has_node(t, ast.Match)))
_register_v3_code("D03-for", ("包含 for 与 range", lambda t: _has_node(t, ast.For) and _has_call(t, "range")))
_register_v3_code("D03-while", ("包含 while", lambda t: _has_node(t, ast.While)))
_register_v3_code("D03-break-continue", ("包含 break 和 continue", lambda t: _has_node(t, ast.Break) and _has_node(t, ast.Continue)))
_register_v3_code("D03-enumerate-zip", ("使用 enumerate/zip", lambda t: _has_call(t, "enumerate") or _has_call(t, "zip")))
_register_v3_code("D03-comprehension", ("包含推导式", lambda t: _has_node(t, ast.ListComp, ast.SetComp, ast.DictComp)))
_register_v3_code("D04-def-return", ("定义函数并返回", lambda t: _has_node(t, ast.FunctionDef) and _has_node(t, ast.Return)))
_register_v3_code("D04-default-keyword", ("包含默认值或关键字参数", lambda t: any(isinstance(n, ast.FunctionDef) and any(d is not None for d in n.args.defaults) for n in ast.walk(t)) or _has_node(t, ast.keyword)))
_register_v3_code("D04-varargs", ("包含 *args/**kwargs", lambda t: any(isinstance(n, ast.arguments) and (n.vararg or n.kwarg) for n in ast.walk(t))))
_register_v3_code("D04-scope", ("包含函数作用域", lambda t: _has_node(t, ast.FunctionDef)))
_register_v3_code("D04-global-nonlocal", ("明确 global/nonlocal", lambda t: _has_node(t, ast.Global) and _has_node(t, ast.Nonlocal)))
_register_v3_code("D04-lambda", ("包含 lambda", lambda t: _has_node(t, ast.Lambda)))
_register_v3_code("D04-type-hints", ("包含类型标注", lambda t: _has_node(t, ast.AnnAssign) or any(isinstance(n, ast.arg) and n.annotation is not None for n in ast.walk(t))))
_register_v3_code("D05-list-tuple", ("使用 list/tuple 结构", lambda t: _has_node(t, ast.List) and _has_node(t, ast.Tuple)))
_register_v3_code("D05-dict-set", ("使用 dict/set 结构", lambda t: _has_node(t, ast.Dict) and _has_node(t, ast.Set)))
_register_v3_code("D05-mutability", ("观察复制或引用", lambda t: _has_call(t, "copy") or any(isinstance(n, ast.Attribute) and n.attr == "copy" for n in ast.walk(t))))
_register_v3_code("D05-unpacking", ("包含序列/字典解包", lambda t: _has_node(t, ast.Starred) or any(isinstance(n, ast.Call) and any(k.arg is None for k in n.keywords) for n in ast.walk(t))))
_register_v3_code("D05-traversal", ("遍历嵌套容器", lambda t: _has_node(t, ast.For) and _has_call(t, "items")))
_register_v3_code("D05-comprehensions", ("包含多种推导式", lambda t: _has_node(t, ast.ListComp, ast.SetComp, ast.DictComp)))
_register_v3_code("D05-iterators-generators", ("使用 yield/迭代器", lambda t: _has_node(t, ast.Yield) and (_has_call(t, "iter") or _has_call(t, "next"))))
_register_v3_code("D06-exception-types", ("包含异常处理", lambda t: _has_node(t, ast.Try)))
_register_v3_code("D06-try-except", ("包含 except", lambda t: any(isinstance(n, ast.Try) and n.handlers for n in ast.walk(t))))
_register_v3_code("D06-else-finally", ("包含 else/finally", lambda t: any(isinstance(n, ast.Try) and n.orelse and n.finalbody for n in ast.walk(t))))
_register_v3_code("D06-raise", ("主动 raise", lambda t: _has_node(t, ast.Raise)))
_register_v3_code("D06-custom", ("定义自定义异常", lambda t: any(isinstance(n, ast.ClassDef) and n.bases for n in ast.walk(t)) and _has_node(t, ast.Raise)))
_register_v3_code("D06-with", ("使用 with 上下文", lambda t: _has_node(t, ast.With)))
_register_v3_code("D07-import", ("包含模块导入", lambda t: _has_node(t, ast.Import, ast.ImportFrom)))
_register_v3_code("D07-package", ("包含包导入结构", lambda t: _has_node(t, ast.Import, ast.ImportFrom)))
_register_v3_code("D07-main", ("包含 __name__ 守卫", lambda t: any(isinstance(n, ast.Name) and n.id == "__name__" for n in ast.walk(t))))
_register_v3_code("D07-stdlib", ("使用标准库模块", lambda t: _has_node(t, ast.Import, ast.ImportFrom)))
_register_v3_code("D07-class-instance", ("定义类和方法", lambda t: _has_node(t, ast.ClassDef) and _has_node(t, ast.FunctionDef)))
_register_v3_code("D07-inheritance", ("包含继承和 super", lambda t: any(isinstance(n, ast.ClassDef) and n.bases for n in ast.walk(t)) and _has_call(t, "super")))
_register_v3_code("D07-dataclass", ("包含 dataclass 与字段标注", lambda t: any(isinstance(n, ast.Name) and n.id == "dataclass" for n in ast.walk(t)) and _has_node(t, ast.AnnAssign)))


# D08-D17 的代码小节也必须走确定性执行/结构校验；专用旧校验器会在下面
# 通过别名复用，未有旧实现的部分使用本节概念的 AST + 子进程执行校验。
_V3_COMMON_REQUIREMENTS: dict[str, list[tuple[str, Callable[[ast.AST], bool]]] ] = {
    "D08-pathlib": [("导入 pathlib/Path", lambda t: _has_call(t, "Path") or _has_node(t, ast.Import, ast.ImportFrom))],
    "D08-utf8": [("包含 UTF-8 读写", lambda t: any(isinstance(n, ast.Constant) and n.value == "utf-8" for n in ast.walk(t)))],
    "D08-json-read": [("使用 JSON 解析", lambda t: _has_call(t, "loads") or _has_call(t, "load"))],
    "D08-json-report": [("使用 JSON 输出", lambda t: _has_call(t, "dump") or _has_call(t, "dumps"))],
    "D09-parser": [("使用 argparse", lambda t: _has_call(t, "ArgumentParser"))],
    "D09-subcommands": [("定义子命令", lambda t: _has_call(t, "add_subparsers"))],
    "D09-errors": [("包含参数错误路径", lambda t: _has_call(t, "error") or _has_call(t, "exit"))],
    "D09-entry": [("包含命令行入口", lambda t: any(isinstance(n, ast.Name) and n.id == "__name__" for n in ast.walk(t)))],
    "D10-env": [("读取环境变量", lambda t: _has_call(t, "getenv") or _has_call(t, "get"))],
    "D10-convert": [("包含配置类型转换", lambda t: _has_call(t, "int") or _has_call(t, "bool"))],
    "D10-dotenv": [("处理配置文件", lambda t: _has_node(t, ast.Call, ast.For))],
    "D10-config": [("定义配置对象或函数", lambda t: _has_node(t, ast.ClassDef, ast.FunctionDef))],
    "D11-logger": [("创建 logger", lambda t: _has_call(t, "getLogger"))],
    "D11-format": [("配置 Formatter", lambda t: _has_call(t, "Formatter"))],
    "D11-stream": [("配置 StreamHandler", lambda t: _has_call(t, "StreamHandler"))],
    "D11-file": [("配置文件日志", lambda t: _has_call(t, "FileHandler"))],
    "D12-request": [("创建 HTTP 请求", lambda t: _has_call(t, "urlopen") or _has_call(t, "Request"))],
    "D12-response": [("处理 HTTP/JSON 响应", lambda t: _has_node(t, ast.Try))],
    "D12-post": [("发送 JSON POST", lambda t: _has_call(t, "Request") and _has_call(t, "dumps"))],
    "D12-timeout": [("设置 timeout", lambda t: any(k.arg == "timeout" for n in ast.walk(t) if isinstance(n, ast.Call) for k in n.keywords))],
    "D13-response": [("声明响应模型或状态码", lambda t: _has_call(t, "get") or _has_node(t, ast.ClassDef))],
    "D13-lifecycle": [("包含生命周期/依赖函数", lambda t: _has_node(t, ast.FunctionDef))],
    "D14-service": [("分离业务函数", lambda t: _has_node(t, ast.FunctionDef))],
    "D14-deps": [("声明依赖", lambda t: _has_call(t, "Depends"))],
    "D15-assert": [("包含 pytest 断言结构", lambda t: _has_node(t, ast.Assert))],
    "D15-fixture": [("包含 fixture 或临时目录", lambda t: _has_call(t, "fixture") or _has_call(t, "tmp_path"))],
    "D15-mock": [("使用 mock/patch", lambda t: _has_call(t, "patch") or _has_call(t, "Mock"))],
    "D15-api": [("包含 HTTP 测试调用", lambda t: _has_call(t, "get") or _has_call(t, "post"))],
    "D16-connect": [("使用 sqlite3.connect", lambda t: _has_call(t, "connect"))],
    "D16-schema": [("包含 CREATE TABLE", lambda t: any(isinstance(n, ast.Constant) and isinstance(n.value, str) and "CREATE TABLE" in n.value.upper() for n in ast.walk(t)))],
    "D16-crud": [("包含 SQL 操作", lambda t: any(isinstance(n, ast.Constant) and isinstance(n.value, str) and any(x in n.value.upper() for x in ("SELECT", "INSERT", "UPDATE", "DELETE")) for n in ast.walk(t)))],
    "D16-transaction": [("包含事务/清理", lambda t: _has_node(t, ast.Try) and (_has_call(t, "commit") or _has_call(t, "rollback")))],
    "D17-coroutine": [("定义 async 函数并 await", lambda t: _has_node(t, ast.AsyncFunctionDef, ast.Await))],
    "D17-gather": [("使用 asyncio.gather", lambda t: _has_call(t, "gather"))],
    "D17-timeout": [("设置异步超时", lambda t: _has_call(t, "wait_for") or _has_call(t, "timeout"))],
    "D17-boundary": [("处理异步异常", lambda t: _has_node(t, ast.Try))],
}
for _section_id, _requirements in _V3_COMMON_REQUIREMENTS.items():
    if _section_id not in _CODE_VALIDATORS:
        _CODE_VALIDATORS[_section_id] = _v3_code_validator(_requirements)

# 关键基础概念增加行为断言：这些检查会导入提交模块并调用约定函数，
# 让“能解析 + 能启动”不能替代对 Python 语义的真正验证。
_register("D02-strings", {
    "file": "main.py", "module": "main",
    "checks": [("字符串清洗并反转", "M.transform_text(' ab ') == 'ba'"), ("原字符串不被修改", "(lambda s: (M.transform_text(s), s)[1] == ' ab ' )(' ab ')")],
})
_register("D03-for", {
    "file": "main.py", "module": "main",
    "checks": [("只累加偶数", "M.sum_even([1, 2, 4, 5]) == 6"), ("空输入为 0", "M.sum_even([]) == 0")],
})
_register("D04-varargs", {
    "file": "main.py", "module": "main",
    "checks": [("收集位置参数", "M.describe(1, 2)['args'] == (1, 2)"), ("收集关键字参数", "M.describe(1, name='林')['kwargs'] == {'name': '林'}")],
})
_register("D04-global-nonlocal", {
    "file": "main.py", "module": "main",
    "checks": [("闭包第一次返回 1", "(lambda c: c() == 1)(M.make_counter())"), ("同一闭包保留状态", "(lambda c: c() == 1 and c() == 2 and c() == 3)(M.make_counter())")],
})
_register("D04-type-hints", {
    "file": "main.py", "module": "main", "imports": ("import typing",),
    "checks": [("函数返回文本", "M.format_user('林', 20) == '林: 20'"), ("参数/返回值有标注", "set(typing.get_type_hints(M.format_user)) >= {'name', 'age', 'return'}")],
})
_register("D05-dict-set", {
    "file": "main.py", "module": "main",
    "checks": [("set 去重", "M.summarize_tags(['py', 'py', 'test'])['unique'] == {'py', 'test'}"), ("dict 返回计数", "M.summarize_tags(['py', 'py', 'test'])['count'] == 2")],
})
_register("D05-mutability", {
    "file": "main.py", "module": "main",
    "checks": [("复制后原列表不变", "M.copy_and_append(['old']) == (['old'], ['old', 'new'])"), ("返回两个独立列表", "(lambda pair: pair[0] is not pair[1])(M.copy_and_append(['old']))")],
})
_register("D05-iterators-generators", {
    "file": "main.py", "module": "main",
    "imports": ("import inspect",),
    "checks": [
        ("yield 产生惰性序列", "list(M.count_up_to(3)) == [0, 1, 2]"),
        ("返回真正的 generator", "inspect.isgenerator(M.count_up_to(3))"),
    ],
})
_register("D06-else-finally", {
    "file": "main.py", "module": "main",
    "checks": [("成功解析", "(lambda e: M.parse_number('7', e) == 7)([])"), ("失败也执行 finally", "(lambda e: (M.parse_number('x', e) is None and e == ['finally']))([])")],
})
_register("D06-with", {
    "file": "main.py", "module": "main",
    "setup": "from pathlib import Path\nPath('_input.txt').write_text('你好', encoding='utf-8')",
    "checks": [("UTF-8 读取", "M.read_text('_input.txt') == '你好'")],
})
_register("D07-package", {
    "file": "main.py", "module": "main",
    "scaffold": [("helpers.py", "def greet(name):\n    return f'你好，{name}'\n")],
    "checks": [("从模块导入函数", "hasattr(M, 'greet') and M.greet('世界') == '你好，世界'")],
})
_register("D07-class-instance", {
    "file": "main.py", "module": "main",
    "checks": [("实例方法返回属性", "M.Task('学习').label() == '学习'"), ("两个实例状态独立", "(lambda a, b: (setattr(a, 'title', '改过'), b.title)[1] == '第二个')(M.Task('第一个'), M.Task('第二个'))")],
})
_register("D07-dataclass", {
    "file": "main.py", "module": "main",
    "checks": [("字段可访问", "M.Point(2, 3).x == 2 and M.Point(2, 3).y == 3"), ("repr 包含字段", "'Point' in repr(M.Point(2, 3)) and 'x=2' in repr(M.Point(2, 3))")],
})

# 项目章节沿用已经经过回归验证的运行/AST/pytest 校验器；新章节 ID
# 仍由自己的 workspace_deps 和 project_file 决定，绝不把缺失依赖静默脚手架化。
_CODE_VALIDATORS["D19-package"] = _v3_code_validator([("包含包初始化代码", lambda t: _has_node(t, ast.Assign, ast.Expr))])
_CODE_VALIDATORS["D20-connection"] = _CODE_VALIDATORS["D20-init"]
# 分步项目只检查本节承诺的能力；完整 CRUD 留给后续验收。
_register("D20-create-list", {
    "file": "taskproj/db.py", "module": "taskproj.db", "scaffold": _TASKPROJ_PACKAGE,
    "setup": _D20_CRUD_SETUP,
    "checks": [
        ("add_task 返回自增 id", "(lambda i: isinstance(i, int) and i > 0)(M.add_task(conn, '任务一'))"),
        ("list_tasks 返回新增任务", "(lambda r: bool(r) and r[0]['title'] == '任务一' and r[0]['done'] is False)(M.list_tasks(conn))"),
        ("空白标题被拒绝", "_raises(ValueError, M.add_task, conn, '   ')"),
        ("标题含引号安全", "M.add_task(conn, \"它's 的\") is not None"),
    ],
})
_CODE_VALIDATORS["D20-update-delete"] = _CODE_VALIDATORS["D20-crud"]
_CODE_VALIDATORS["D20-db-tests"] = _pytest_validator("test_project.py", [])
_CODE_VALIDATORS["D21-app"] = _CODE_VALIDATORS["D13-app"]
_CODE_VALIDATORS["D21-schema"] = _ast_validator({
    "file": "taskproj/api.py",
    "checks": [
        ("TaskIn 含 title", lambda t: "title" in _class_fields(t, "TaskIn")),
        ("Task 模型含 id/title/done", lambda t: set(_class_fields(t, "Task")) >= {"id", "title", "done"}),
    ],
})
_CODE_VALIDATORS["D21-crud-routes"] = _CODE_VALIDATORS["D21-routes"]
_CODE_VALIDATORS["D21-static"] = _CODE_VALIDATORS["D21-routes"]
_CODE_VALIDATORS["D22-db-fixtures"] = _pytest_validator("tests/test_project.py", [])
_CODE_VALIDATORS["D22-api-tests"] = _CODE_VALIDATORS["D22-api"]
_CODE_VALIDATORS["D22-api-errors"] = _CODE_VALIDATORS["D22-api"]
_CODE_VALIDATORS["D22-acceptance"] = _CODE_VALIDATORS["D22-api"]
_CODE_VALIDATORS["D23-cli-parser"] = _direct_run_validator({
    "file": "taskproj/cli.py",
    "env": {"TASKPROJ_DB": "_cli.db"},
    "runs": [
        (["-c", "from taskproj.cli import build_parser; p = build_parser(); print(p.parse_args(['add', 'x']).command, p.parse_args(['list']).command)"],
         "build_parser 声明 add/list", lambda p: p["stdout"].strip() == "add list", lambda p: _tail(p["stderr"] or p["stdout"])),
        (["-m", "taskproj.cli", "add", "买牛奶"], "CLI add 成功", lambda p: p["exit_code"] == 0, lambda p: _tail(p["stderr"] or p["stdout"])),
        (["-m", "taskproj.cli", "list"], "CLI list 可见任务", lambda p: "买牛奶" in p["stdout"], lambda p: _tail(p["stdout"] or p["stderr"])),
    ],
})
_CODE_VALIDATORS["D23-cli-mutate"] = _CODE_VALIDATORS["D23-cli"]


# --------------------------------------------------------------------------
# 对外校验入口
# --------------------------------------------------------------------------

def _script_practice(cases: list[tuple[str, list[str], str | None, int]]):
    def validate(code: str, ctx: PracticeContext, section: dict[str, Any]) -> dict[str, Any]:
        ctx.write("main.py", code)
        checks = []
        outputs, errors = [], []
        proc = {"exit_code": None, "timeout": False}
        for number, (input_text, args, expected, exit_code) in enumerate(cases, 1):
            proc = _run_proc([sys.executable, *args], cwd=ctx.temp, input_text=input_text)
            actual = proc["stdout"].rstrip("\r\n")
            passed = proc["exit_code"] == exit_code and (expected is None or actual == expected)
            detail = f"输入：{input_text.strip()!r}" if input_text else f"运行：{' '.join(args)}"
            if expected is not None:
                detail += f"；期望：{expected!r}；实际：{_truncate(actual, 500)!r}"
            detail += f"；退出码：{proc['exit_code']}（期望 {exit_code}）"
            checks.append({"name": f"样例 {number}", "passed": passed, "detail": detail})
            outputs.append(f"[样例 {number}]\n{proc['stdout']}")
            if proc["stderr"]:
                errors.append(proc["stderr"])
            # 同一错误不必运行所有样例，尤其避免重复等待无限循环超时。
            if proc["timeout"] or (proc["exit_code"] != exit_code and exit_code == 0):
                break
        proc.update(stdout="\n".join(outputs), stderr="\n".join(errors))
        return _finalize(checks, proc)
    return validate


for _id, _cases in SCRIPT_CASES.items():
    _CODE_VALIDATORS[_id] = _script_practice([(text, ["main.py"], expected, 0) for text, expected in _cases])
for _id, _cases in CLI_CASES.items():
    _CODE_VALIDATORS[_id] = _script_practice([("", args, expected, code) for args, expected, code in _cases])
for _id, _checks in FUNCTION_CASES.items():
    _register(_id, {"file": "main.py", "module": "main", "checks": _checks,
                    "imports": ("from pathlib import Path",), "scaffold": FILE_FIXTURES.get(_id, []),
                    "silent_import": _id == "D07-slug"})


def _section_task(curriculum: dict[str, Any], task_id: str) -> dict[str, Any]:
    task = curriculum["_index"]["tasks"].get(task_id)
    if task is None:
        raise UsageError(f"任务 ID 不存在：{task_id}")
    return task


def find_section(curriculum: dict[str, Any], task_id: str, section_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    task = _section_task(curriculum, task_id)
    for section in task["lesson"]:
        if section["id"] == section_id:
            return task, section
    raise UsageError(f"课程小节 ID 不存在：{section_id}")


def validate_code(section: dict[str, Any], submission: str, project_root: Path) -> dict[str, Any]:
    practice = section["practice"]
    if practice.get("kind") != "code":
        raise DataError("validate_code 只接受 code 实践")
    validator = _CODE_VALIDATORS.get(section["id"])
    if validator is None:
        raise DataError(f"小节 {section['id']} 缺少服务端校验器")
    # 把 workspace 真实依赖先写入临时目录并标记为受保护，标准脚手架不得覆盖它们。
    ws_scaffolds, missing = _read_workspace_deps(section, project_root)
    if missing:
        return {
            "passed": False,
            "checks": [
                {
                    "name": "缺少前置依赖文件",
                    "passed": False,
                    "detail": f"缺少 {missing}，请先完成前置小节并把产物提交到工作区",
                }
            ],
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }
    with PracticeContext(project_root) as ctx:
        ctx.ws_deps = {rel for rel, _ in ws_scaffolds}
        for rel, content in ws_scaffolds:
            ctx.write(rel, content)
        return validator(submission, ctx, section)


def validate_json(section: dict[str, Any], submission: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        data = json.loads(submission)
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "checks": [{"name": "JSON 可解析", "passed": False, "detail": f"第 {exc.lineno} 行：{exc.msg}"}],
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }
    task_obj = data.get("task")
    checks.append({"name": "含 task 对象", "passed": isinstance(task_obj, dict), "detail": repr(task_obj)[:200]})
    if isinstance(task_obj, dict):
        keys = {"id", "title", "done"}
        checks.append({"name": "task 含 id/title/done", "passed": keys <= set(task_obj.keys()), "detail": f"字段 {sorted(task_obj.keys())}"})
    endpoints = data.get("endpoints")
    checks.append(
        {
            "name": "endpoints 为数组且至少 4 项",
            "passed": isinstance(endpoints, list) and len(endpoints) >= 4,
            "detail": f"{len(endpoints) if isinstance(endpoints, list) else '非数组'} 项",
        }
    )
    if isinstance(endpoints, list):
        ok = all(isinstance(item, dict) and "method" in item and "path" in item for item in endpoints)
        checks.append({"name": "endpoint 含 method/path", "passed": ok, "detail": ""})
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "stdout": "", "stderr": "", "exit_code": None}


TEXT_RULES: dict[str, dict[str, Any]] = {
    "D01-onboarding": {"min_chars": 8, "keywords": [], "min_matches": 0},
    "D18-scope": {"min_chars": 50, "keywords": ["用户故事", "任务", "SQLite", "CLI", "网页", "非目标"], "min_matches": 4},
    "D18-acceptance": {"min_chars": 50, "keywords": ["验收", "成功", "失败", "状态码", "空标题", "未知 ID"], "min_matches": 4},
    "D19-package": {"min_chars": 12, "keywords": ["__init__", "包", "版本"], "min_matches": 2},
    "D19-readme": {"min_chars": 40, "keywords": ["uvicorn", "安装", "pip", "pytest", "CLI", "任务"], "min_matches": 4},
    "D19-init": {"min_chars": 5, "keywords": ["任务管理", "本地"], "min_matches": 1},
    "D24-integrate": {"min_chars": 50, "keywords": ["API", "CLI", "网页", "pytest", "启动", "预期"], "min_matches": 4},
    "D24-artifacts": {"min_chars": 50, "keywords": ["15", "文件", "contract", "runbook", "依赖", "验收"], "min_matches": 4},
    "D24-review": {"min_chars": 30, "keywords": ["交付", "复用", "重建", "改进"], "min_matches": 2},
    "D28-review": {"min_chars": 30, "keywords": ["能力", "mock", "索引", "重建"], "min_matches": 3},
}

def validate_text(section: dict[str, Any], submission: str) -> dict[str, Any]:
    structured = _TEXT_STRUCTURED_VALIDATORS.get(section["id"])
    if structured is not None:
        return structured(section, submission)
    text = (submission or "").strip()
    rules = TEXT_RULES.get(section["id"])
    if rules is None:
        checks = [{"name": "非空回答", "passed": bool(text), "detail": f"{len(text)} 字"}]
        return {"passed": bool(text), "checks": checks, "stdout": "", "stderr": "", "exit_code": None}
    checks: list[dict[str, Any]] = [
        {"name": f"至少 {rules['min_chars']} 字", "passed": len(text) >= rules["min_chars"], "detail": f"当前 {len(text)} 字"},
    ]
    lowered = text.casefold()
    matched = [kw for kw in rules["keywords"] if kw.casefold() in lowered]
    checks.append(
        {
            "name": f"覆盖 {rules['min_matches']} 个关键点",
            "passed": len(matched) >= rules["min_matches"],
            "detail": f"命中 {matched}",
        }
    )
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "stdout": "", "stderr": "", "exit_code": None}


def validate_command(section: dict[str, Any], submission: str) -> dict[str, Any]:
    text = (submission or "").strip()
    if not text:
        return {"passed": False, "checks": [{"name": "命令不能为空", "passed": False, "detail": ""}], "stdout": "", "stderr": "", "exit_code": None}
    raw = text.casefold()
    checks: list[dict[str, Any]] = [
        {"name": "包含创建 venv 命令", "passed": "venv" in raw and ".venv" in raw, "detail": ""},
        {"name": "包含安装依赖命令", "passed": "pip install" in raw and "-e" in raw, "detail": ""},
        {"name": "包含运行测试命令", "passed": "pytest" in raw, "detail": ""},
        {"name": "包含启动网页命令", "passed": "uvicorn" in raw and "taskproj.api:app" in raw, "detail": ""},
    ]
    positions = [raw.find(token) for token in ("venv", "pip install", "pytest", "uvicorn")]
    ordered = all(pos >= 0 for pos in positions) and positions == sorted(positions)
    checks.append({"name": "命令按顺序书写", "passed": ordered, "detail": f"位置 {positions}"})
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "stdout": "", "stderr": "", "exit_code": None}


def _html_parse_ok(code: str) -> bool:
    """用 HTMLParser 做一次宽松的解析，排除明显残缺的文档。"""
    from html.parser import HTMLParser

    class _Checker(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.start_tags: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.start_tags.append(tag)

    checker = _Checker()
    try:
        checker.feed(code)
        checker.close()
    except Exception:  # noqa: BLE001
        return False
    return bool(checker.start_tags)


def validate_html(section: dict[str, Any], submission: str) -> dict[str, Any]:
    """确定性校验真实 HTML 页面：结构完整、原生 fetch 调 /api/tasks、列表/新增/完成/删除。"""
    code = submission or ""
    if not code.strip():
        return {"passed": False, "checks": [{"name": "HTML 不能为空", "passed": False, "detail": ""}], "stdout": "", "stderr": "", "exit_code": None}
    lower = code.casefold()
    upper = code.upper()
    checks: list[dict[str, Any]] = [
        {"name": "HTML 文档结构", "passed": "<html" in lower and "<body" in lower, "detail": "需含 <html> 与 <body>"},
        {"name": "含 <script> 脚本块", "passed": "<script" in lower, "detail": ""},
        {"name": "HTML 可被解析器接受", "passed": _html_parse_ok(code), "detail": ""},
        {"name": "原生 fetch 调用 /api/tasks", "passed": "fetch(" in code and "/api/tasks" in code, "detail": ""},
        {"name": "列表渲染逻辑", "passed": any(token in code for token in ("createElement", "innerHTML", "insertAdjacentHTML")), "detail": "用 createElement/innerHTML 渲染列表"},
        {"name": "新增任务输入与按钮", "passed": ("<input" in lower or "prompt(" in code) and "<button" in lower, "detail": "需输入框/按钮触发新增"},
        {"name": "完成任务逻辑", "passed": "PATCH" in upper or "/done" in code, "detail": "需 PATCH /api/tasks/{id}/done"},
        {"name": "删除任务逻辑", "passed": "DELETE" in upper or "delete" in lower, "detail": "需 DELETE /api/tasks/{id}"},
    ]
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "stdout": "", "stderr": "", "exit_code": None}


def validate_html_structure(section: dict[str, Any], submission: str) -> dict[str, Any]:
    """Validate D23's first HTML slice before the fetch behaviour is introduced."""
    code = submission or ""
    if not code.strip():
        return {"passed": False, "checks": [{"name": "HTML 不能为空", "passed": False, "detail": ""}], "stdout": "", "stderr": "", "exit_code": None}
    lower = code.casefold()
    checks = [
        {"name": "HTML 文档结构", "passed": "<html" in lower and "<body" in lower, "detail": "需含 <html> 与 <body>"},
        {"name": "可访问的任务输入", "passed": "<input" in lower and "<button" in lower, "detail": "先完成列表输入与操作按钮骨架"},
        {"name": "列表容器", "passed": any(token in lower for token in ("<ul", "<ol", "<main", "id=\"tasks\"", "id='tasks'")), "detail": "需有承载任务列表的容器"},
        {"name": "HTML 可被解析器接受", "passed": _html_parse_ok(code), "detail": ""},
    ]
    return {"passed": all(item["passed"] for item in checks), "checks": checks, "stdout": "", "stderr": "", "exit_code": None}


def _dep_base(dep: str) -> str:
    """取 pyproject 依赖项的包名：去掉 extras 与版本约束。"""
    base = dep.split("[", 1)[0]
    for ch in "<>=~!":
        if ch in base:
            base = base.split(ch, 1)[0]
    return base.strip().casefold()


def validate_project_file(section: dict[str, Any], submission: str) -> dict[str, Any]:
    """确定性校验 pyproject.toml：build-system、project 元信息、运行依赖与 dev 测试依赖。"""
    code = submission or ""
    import tomllib

    try:
        data = tomllib.loads(code)
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "checks": [{"name": "TOML 可解析", "passed": False, "detail": f"{type(exc).__name__}: {exc}"}],
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }
    checks: list[dict[str, Any]] = []
    build = data.get("build-system")
    checks.append({"name": "build-system 存在", "passed": isinstance(build, dict) and "requires" in build, "detail": ""})
    project = data.get("project")
    checks.append({"name": "[project] 存在", "passed": isinstance(project, dict), "detail": ""})
    if isinstance(project, dict):
        name = project.get("name")
        checks.append({"name": "project.name 非空", "passed": isinstance(name, str) and bool(name.strip()), "detail": repr(name)})
        deps = project.get("dependencies")
        bases = {_dep_base(item) for item in deps} if isinstance(deps, list) else set()
        checks.append(
            {
                "name": "运行依赖含 fastapi/uvicorn/pydantic",
                "passed": {"fastapi", "uvicorn", "pydantic"} <= bases,
                "detail": f"声明 {sorted(bases)}",
            }
        )
        opt = project.get("optional-dependencies")
        dev = opt.get("dev") if isinstance(opt, dict) else None
        dev_bases = {_dep_base(item) for item in dev} if isinstance(dev, list) else set()
        checks.append(
            {
                "name": "dev 测试依赖含 pytest/httpx",
                "passed": {"pytest", "httpx"} <= dev_bases,
                "detail": f"dev {sorted(dev_bases)}",
            }
        )
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "stdout": "", "stderr": "", "exit_code": None}


# 结构化的“文本”小节：真实 HTML 页面（D23-web）与 pyproject.toml（D19-pyproject），
# 走专门的确定性校验器而非关键词规则。
_TEXT_STRUCTURED_VALIDATORS: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "D23-web": validate_html,
    "D23-html-structure": validate_html_structure,
    "D23-html-fetch": validate_html,
    "D19-pyproject": validate_project_file,
}


WORKSPACE_ROOT = Path("learner_workspace") / "task-manager"


def _workspace_dir(project_root: Path) -> Path:
    return project_root / WORKSPACE_ROOT


def _write_project_artifact(project_file: str, content: str, project_root: Path) -> None:
    """将验证通过的产物原子写入工作区。拒绝绝对路径与路径穿越。"""
    from .web.storage import normalize_relative_path, atomic_write_text

    normalized = normalize_relative_path(project_file)
    target = _workspace_dir(project_root) / normalized
    atomic_write_text(target, content)


def _read_workspace_deps(section: dict[str, Any], project_root: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """读取小节声明的 workspace_deps 文件内容，返回 (scaffolds, missing)。

    缺失或不可读的依赖记为 missing，由调用方判定校验失败。
    """
    deps: list[str] = section["practice"].get("workspace_deps", [])
    scaffolds: list[tuple[str, str]] = []
    missing: list[str] = []
    ws = _workspace_dir(project_root)
    for dep in deps:
        dep_path = ws / dep
        if not dep_path.is_file():
            missing.append(dep)
            continue
        try:
            scaffolds.append((dep, dep_path.read_text(encoding="utf-8")))
        except (UnicodeError, OSError):
            missing.append(dep)
    return scaffolds, missing


def run_validation(curriculum: dict[str, Any], task_id: str, section_id: str, submission: str, project_root: Path) -> dict[str, Any]:
    _, section = find_section(curriculum, task_id, section_id)
    practice = section["practice"]
    kind = practice["kind"]

    result: dict[str, Any]
    if kind == "code":
        result = validate_code(section, submission, project_root)
    elif kind == "json":
        result = validate_json(section, submission)
    elif kind == "text":
        result = validate_text(section, submission)
    elif kind == "command":
        result = validate_command(section, submission)
    elif kind == "html":
        result = validate_html(section, submission)
    elif kind == "project":
        result = validate_project_file(section, submission)
    elif kind == "env_action":
        action = practice["action"]
        result = run_action(action, project_root)
    else:
        raise DataError(f"未知实践类型 {kind!r}")

    project_file = practice.get("project_file")
    if result.get("passed") and isinstance(project_file, str) and project_file:
        _write_project_artifact(project_file, submission, project_root)

    if not result.get("passed"):
        details = result.get("stderr", "") + "\n" + "\n".join(check.get("detail", "") for check in result["checks"])
        tips = {
            "IndentationError": "缩进不一致：看报错行和上一行的冒号。同一代码块统一四个空格，块外语句顶格。",
            "SyntaxError": "代码还不能被解析：先检查报错行的冒号、括号、引号，并确认用了英文标点。",
            "NameError": "使用了尚未定义的名字：检查拼写，以及赋值是否在使用之前执行。",
            "TypeError": "参与操作的数据类型不匹配：input() 返回字符串，需要计算时先转成 int 或 float；函数还要检查参数数量。",
            "ValueError": "值无法转换或不符合规则：对照题目的合法输入范围，区分返回结果和应该抛出的异常。",
            "IndexError": "索引超出范围：第一个位置是 0，最后一个是 len(...) - 1；空容器不能取第一个元素。",
            "KeyError": "字典中没有这个键：检查键名拼写，以及输入是否真的包含该字段。",
            "EOFError": "input() 次数多于题目提供的输入：按题目要求读取行数，不要在验证过程中额外等待输入。",
        }
        tip = next((message for name, message in tips.items() if name in details), None)
        result["learning_feedback"] = tip or "先定位第一项未通过的检查，对照期望值与实际值；检查返回值、循环边界和空输入，每次只修改一个问题再运行。"
    return result


# --------------------------------------------------------------------------
# 草稿
# --------------------------------------------------------------------------

def draft_path(project_root: Path, task_id: str, section_id: str) -> Path:
    return Path(project_root) / ".learn" / "lesson-submissions" / task_id / f"{section_id}.json"


def load_draft(project_root: Path, task_id: str, section_id: str) -> dict[str, Any] | None:
    path = draft_path(project_root, task_id, section_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("content"), str):
        return None
    return data


def save_draft(project_root: Path, task_id: str, section_id: str, content: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "task_id": task_id,
        "section_id": section_id,
        "content": content,
        "updated_at": now_iso(),
    }
    atomic_write_text(draft_path(project_root, task_id, section_id), json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


# --------------------------------------------------------------------------
# D24 项目验收：固定、安全、只读的端到端检查
# --------------------------------------------------------------------------

_PROJECT_REQUIRED_FILES = [
    "docs/requirements.md",
    "contract.json",
    "README.md",
    "pyproject.toml",
    "taskproj/__init__.py",
    "taskproj/config.py",
    "taskproj/main.py",
    "taskproj/db.py",
    "taskproj/api.py",
    "tests/test_project.py",
    "tests/test_api.py",
    "taskproj/cli.py",
    "taskproj/static/index.html",
    "docs/runbook.md",
    "docs/review.md",
]

# 验收用临时环境脚本：只读真实文件的副本，固定 argv、shell=False、临时 DB，
# 不执行任何用户输入命令。
_ACCEPT_SQLITE_HARNESS = r'''
import json, os, sys
sys.path.insert(0, os.getcwd())
results = []
def _check(name, passed, detail=""):
    results.append({"name": name, "passed": bool(passed), "detail": detail})
db_path = os.path.join(os.getcwd(), "_accept_crud.db")
if os.path.exists(db_path):
    os.remove(db_path)
try:
    from taskproj import db
    conn = db.create_connection(db_path)
    _check("SQLite 连接", conn is not None, "create_connection 返回 None")
    db.init_db(conn)
    tid = db.add_task(conn, "验收任务")
    _check("SQLite 增", isinstance(tid, int) and tid > 0, repr(tid))
    tasks = db.list_tasks(conn)
    _check("SQLite 查", len(tasks) == 1 and tasks[0]["title"] == "验收任务", repr(tasks))
    db.complete_task(conn, tid)
    _check("SQLite 完成", db.list_tasks(conn)[0]["done"] is True, "")
    db.delete_task(conn, tid)
    _check("SQLite 删", len(db.list_tasks(conn)) == 0, "")
    quoted = db.add_task(conn, "它's 的")
    _check("SQLite 引号标题安全", db.list_tasks(conn)[0]["title"] == "它's 的", "")
    db.delete_task(conn, quoted)
except Exception as exc:
    _check("SQLite CRUD 异常", False, "{}: {}".format(type(exc).__name__, exc))
with open("_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
'''

_ACCEPT_API_HARNESS = r'''
import json, os, sys
sys.path.insert(0, os.getcwd())
results = []
def _check(name, passed, detail=""):
    results.append({"name": name, "passed": bool(passed), "detail": detail})
os.environ["TASKPROJ_DB"] = os.path.join(os.getcwd(), "_accept_api.db")
try:
    from fastapi.testclient import TestClient
    from taskproj.api import app
    client = TestClient(app)
    r = client.get("/health")
    _check("GET /health 200", r.status_code == 200, "status={}".format(r.status_code))
    r = client.get("/")
    page = r.text or ""
    _check("GET / 200", r.status_code == 200, "status={}".format(r.status_code))
    _check("页面含 fetch(/api/tasks)", "fetch(" in page and "/api/tasks" in page, "")
    _check(
        "页面含任务 UI 标志",
        any(mark in page for mark in ("<input", "<button", "createElement", "innerHTML")),
        "",
    )
    r = client.get("/api/tasks")
    _check("GET /api/tasks 200", r.status_code == 200, "status={}".format(r.status_code))
    r = client.post("/api/tasks", json={"title": "验收任务"})
    tid = None
    if r.status_code in (200, 201):
        try:
            tid = r.json().get("id")
        except Exception:
            tid = None
    _check(
        "POST /api/tasks 新建",
        r.status_code in (200, 201) and isinstance(tid, int) and tid > 0,
        "status={} body={!r}".format(r.status_code, (r.text or "")[:120]),
    )
    if isinstance(tid, int):
        r = client.patch("/api/tasks/{}/done".format(tid))
        _check("PATCH 完成 200", r.status_code == 200, "status={}".format(r.status_code))
        r = client.delete("/api/tasks/{}".format(tid))
        _check("DELETE 删除 200", r.status_code == 200, "status={}".format(r.status_code))
    r = client.patch("/api/tasks/999999/done")
    _check("PATCH 不存在任务 404", r.status_code == 404, "status={}".format(r.status_code))
    r = client.delete("/api/tasks/999999")
    _check("DELETE 不存在任务 404", r.status_code == 404, "status={}".format(r.status_code))
    r = client.post("/api/tasks", json={"title": ""})
    _check("POST 空标题 422", r.status_code == 422, "status={}".format(r.status_code))
except Exception as exc:
    _check("FastAPI 验收异常", False, "{}: {}".format(type(exc).__name__, exc))
with open("_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
'''

_ACCEPT_CLI_HARNESS = r'''
import json, os, subprocess, sys
os.environ["TASKPROJ_DB"] = os.path.join(os.getcwd(), "_accept_cli.db")
results = []
def _check(name, passed, detail=""):
    results.append({"name": name, "passed": bool(passed), "detail": detail})
def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "taskproj.cli", *args],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        env=dict(os.environ),
    )
try:
    r = _run("add", "买牛奶")
    _check("CLI add 成功", r.returncode == 0, (r.stderr or r.stdout).strip())
    r = _run("list")
    _check("CLI list 可见任务", "买牛奶" in r.stdout, (r.stdout or r.stderr).strip())
    r = _run("done", "1")
    _check("CLI done 成功", r.returncode == 0, (r.stderr or r.stdout).strip())
    r = _run("list")
    _check("CLI list 显示 [done]", "[done]" in r.stdout, (r.stdout or r.stderr).strip())
    r = _run("rm", "1")
    _check("CLI rm 成功", r.returncode == 0, (r.stderr or r.stdout).strip())
    r = _run("list")
    _check("CLI list 已删除", "买牛奶" not in r.stdout, (r.stdout or r.stderr).strip())
except Exception as exc:
    _check("CLI 验收异常", False, "{}: {}".format(type(exc).__name__, exc))
with open("_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
'''


def _copy_project_files(ctx: PracticeContext, ws: Path, rels: list[str]) -> None:
    for rel in rels:
        src = ws / rel
        if src.is_file():
            ctx.write(rel, src.read_text(encoding="utf-8"))


def validate_project_acceptance(project_root: Path) -> dict[str, Any]:
    """固定验收动作：文件完整 → pytest → SQLite CRUD → FastAPI TestClient → CLI。

    全部动作只在临时目录副本上执行：固定 argv、shell=False、临时 DB；
    不执行任何用户输入命令，不修改 workspace 文件。
    """
    ws = _workspace_dir(project_root)
    checks: list[dict[str, Any]] = []

    # 1. 文件完整性
    missing_files = [item for item in _PROJECT_REQUIRED_FILES if not (ws / item).is_file()]
    checks.append({
        "name": "项目文件完整",
        "passed": len(missing_files) == 0,
        "detail": f"缺少 {missing_files}" if missing_files else f"{len(_PROJECT_REQUIRED_FILES)} 个文件齐全",
    })
    if missing_files:
        return _finalize(checks, {"timeout": False, "stdout": "", "stderr": "", "exit_code": None})

    # 2. pytest 全部通过（临时副本）
    with PracticeContext(project_root) as ctx:
        _copy_project_files(ctx, ws, _PROJECT_REQUIRED_FILES)
        if not (ws / "tests/__init__.py").is_file():
            ctx.write("tests/__init__.py", "")
        proc = _run_proc(
            [sys.executable, "-m", "pytest", "-q", "tests/test_project.py", "tests/test_api.py"],
            cwd=ctx.temp,
            timeout=PYTEST_TIMEOUT,
        )
        checks.append({
            "name": "pytest 全部通过",
            "passed": proc["exit_code"] == 0,
            "detail": _tail(proc["stdout"] or proc["stderr"]),
        })

    # 3. SQLite CRUD（临时库）
    with PracticeContext(project_root) as ctx:
        _copy_project_files(ctx, ws, ["taskproj/__init__.py", "taskproj/db.py"])
        _, crud_checks = _run_harness(ctx, _ACCEPT_SQLITE_HARNESS, "_result.json")
        checks.extend(crud_checks)

    # 4. FastAPI TestClient：health、CRUD、404/422、GET / 200 且页面含 fetch 与任务 UI 标志
    with PracticeContext(project_root) as ctx:
        _copy_project_files(ctx, ws, [
            "taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py",
            "taskproj/api.py", "taskproj/static/index.html",
        ])
        _, api_checks = _run_harness(ctx, _ACCEPT_API_HARNESS, "_result.json", timeout=PYTEST_TIMEOUT)
        checks.extend(api_checks)

    # 5. CLI add/list/done/rm（临时 DB、固定 argv、shell=False）
    with PracticeContext(project_root) as ctx:
        _copy_project_files(ctx, ws, [
            "taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py", "taskproj/cli.py",
        ])
        _, cli_checks = _run_harness(ctx, _ACCEPT_CLI_HARNESS, "_result.json")
        checks.extend(cli_checks)

    return _finalize(checks, {"timeout": False, "stdout": "", "stderr": "", "exit_code": None})

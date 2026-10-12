"""Private, offline behavior acceptance drafts for integration into practice.py.

No source/token/AST presence is used as behavioral proof. All subprocesses use
new temporary dirs, UTF-8, shell=False, deadlines and bounded captured output.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from . import ai_practice_fixtures as _fixtures

OFFLINE_CONFTEST = '''import socket
import urllib.request
import pytest

def reject(*args, **kwargs):
    raise AssertionError("离线测试不能访问网络；请mock真正的I/O边界")

# Install before collection, then reapply for each test. This covers imports
# that accidentally perform I/O, as well as direct urllib/socket access.
urllib.request.urlopen = reject
socket.create_connection = reject
socket.getaddrinfo = reject
socket.socket.connect = reject
socket.socket.connect_ex = reject

@pytest.fixture(autouse=True)
def forbid_actual_network(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
'''


def fixture_variant(name):
    fixtures = _fixtures.ai_reference_fixtures()
    source = fixtures[0][1]
    if name == "content":
        old = 'return payload["choices"][0]["message"]["content"]'
        new = 'return "MUTATED_CONTENT"'
    elif name == "401":
        old = 'except HTTPError as error:\n        raise ApiError("API 错误", error.code)'
        new = 'except HTTPError as error:\n        if error.code == 401:\n            return "ACCEPTED_401"\n        raise ApiError("API 错误", error.code)'
    elif name == "bad-json":
        old = 'except (json.JSONDecodeError, UnicodeDecodeError):\n        raise ApiError("响应不是 JSON", None)'
        new = 'except (json.JSONDecodeError, UnicodeDecodeError):\n        return "ACCEPTED_BAD_JSON"'
    elif name == "correct":
        return fixtures
    else:
        raise ValueError(name)
    assert source.count(old) == 1, name
    changed = source.replace(old, new)
    compile(changed, "deepseek_client.py", "exec")
    return [(fixtures[0][0], changed), *fixtures[1:]]


def grade_d28_tests(submission, *, timeout=20):
    checks = []
    captured = []
    any_timeout = False
    labels = {"correct": "正确客户端：测试应全部通过", "content": "正常content错误：测试应发现", "401": "吞掉401：测试应发现", "bad-json": "接受非法JSON：测试应发现"}
    for variant in ["correct", "content", "401", "bad-json"]:
        with tempfile.TemporaryDirectory(prefix="learnctl-d28-mutation-") as directory:
            path = Path(directory)
            for relative, source in fixture_variant(variant):
                (path / relative).write_text(source, encoding="utf-8")
            (path / "conftest.py").write_text(OFFLINE_CONFTEST, encoding="utf-8")
            (path / "test_ai_client.py").write_text(submission, encoding="utf-8")
            env = dict(os.environ)
            env.pop("DEEPSEEK_API_KEY", None)
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            try:
                process = subprocess.run([sys.executable, "-m", "pytest", "-q", "test_ai_client.py"], cwd=path, env=env,
                    capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False, timeout=timeout)
                exit_code = process.returncode
                output = (process.stdout + process.stderr)[-6000:]
                # Collection/import/config/internal errors are not a valid
                # demonstration that a behavior defect was detected.
                passed = exit_code == (0 if variant == "correct" else 1)
            except subprocess.TimeoutExpired:
                exit_code, output, passed = None, "测试超时", False
                any_timeout = True
            checks.append({"name": labels[variant], "passed": passed, "expected": "pytest退出码0" if variant == "correct" else "pytest断言失败退出码1",
                "actual": "pytest退出码" + str(exit_code), "detail": output})
            captured.append(output)
    return {"passed": all(check["passed"] for check in checks), "checks": checks,
        "stdout": "\n".join(captured)[-16000:], "stderr": "", "exit_code": 0 if all(check["passed"] for check in checks) else 1, "timeout": any_timeout}


def d26_parse_checks(module):
    cases = [
        ("纯对象", '{"b":2}', {"b": 2}, None),
        ("前后缀", '前缀 {"a":1} 后缀', {"a": 1}, None),
        ("嵌套对象", '前缀 {"a":{"items":[1,2]}} 后缀', {"a": {"items": [1, 2]}}, None),
        ("字符串包含花括号", '{"label":"brace } ok"}', {"label": "brace } ok"}, None),
        ("字符串转义", '{"label":"a\\"b"}', {"label": 'a"b'}, None),
        ("缺标记", "没有JSON", None, ValueError),
        ("倒序标记", "} 在前 {", None, ValueError),
        ("非法对象", "前缀 {bad} 后缀", None, ValueError),
        ("两个对象拒绝", '{"a":1} {"b":2}', None, ValueError),
    ]
    checks = []
    for label, text, expected, error_type in cases:
        try:
            actual = module.parse_ai_json(text)
            passed = error_type is None and type(actual) is dict and actual == expected
            detail = repr(actual)
        except Exception as error:
            passed = error_type is not None and isinstance(error, error_type)
            detail = type(error).__name__ + ": " + str(error)
        checks.append({"name": label, "input": repr(text), "passed": passed,
            "expected": "ValueError" if error_type else repr(expected), "actual": detail})
    return checks


def d27_client_harness():
    # __BASE__ is substituted with the existing local _DeepSeekMockHandler URL.
    # Add `_add`/results/json output using the existing _run_with_server helper.
    return '''import json
import main as M
from deepseek_client import ApiError
url = "__BASE__"
results = []
def add(name, passed, actual):
    results.append({"name": name, "passed": passed, "actual": actual})
try:
    value = M.send_message("demo", "JSON_CONTENT", base_url=url)
    add("返回结构化dict", type(value) is dict and value == {"ok": True}, repr(value))
except Exception as error:
    add("返回结构化dict", False, type(error).__name__ + ": " + str(error))
try:
    M.send_message("demo", "NONJSON", base_url=url)
    add("接口外层非法JSON抛ApiError", False, "未抛错")
except ApiError as error:
    add("接口外层非法JSON抛ApiError", error.status_code is None, type(error).__name__ + ": " + str(error))
except Exception as error:
    add("接口外层非法JSON抛ApiError", False, type(error).__name__ + ": " + str(error))
try:
    M.send_message("demo", "TEXT_CONTENT", base_url=url)
    add("content非法JSON抛ValueError", False, "未抛错")
except ValueError as error:
    add("content非法JSON抛ValueError", True, type(error).__name__ + ": " + str(error))
except Exception as error:
    add("content非法JSON抛ValueError", False, type(error).__name__ + ": " + str(error))
with open("_result.json", "w", encoding="utf-8") as file:
    json.dump(results, file, ensure_ascii=False)
'''

def register(registry):
    from . import practice as p
    def parse(code, ctx, section):
        ctx.write('main.py', code)
        import inspect
        source = inspect.getsource(d26_parse_checks)
        harness = "import json\nfrom pathlib import Path\n" + "import socket, urllib.request\ndef reject(*args,**kwargs): raise OSError('本节只允许离线测试')\nurllib.request.urlopen=reject\nsocket.socket.connect=reject\nsocket.create_connection=reject\nsocket.getaddrinfo=reject\n" + "\n" + source + "\nimport main as M\nPath('_result.json').write_text(json.dumps(d26_parse_checks(M),ensure_ascii=False),encoding='utf-8')\n"
        proc, checks = p._run_harness(ctx,harness,'_result.json')
        result=p._finalize(checks,proc)
        result['passed']=result['passed'] and proc.get('exit_code')==0 and not proc.get('timeout')
        result['cases']=checks
        return result
    def client(code,ctx,section):
        ctx.write('main.py',code)
        for rel,source in _fixtures.ai_reference_fixtures():ctx.write(rel,source)
        from .ai_protocol_checks import LOCAL_GUARD
        return p._run_with_server(p._DeepSeekMockHandler, LOCAL_GUARD + d27_client_harness(),ctx)
    registry['D26-parse']=parse
    registry['D27-client']=client
    registry['D28-test']=lambda code,ctx,section:grade_d28_tests(code)

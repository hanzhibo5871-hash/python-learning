"""Offline behavior acceptance for AI HTTP, prompt and composition contracts."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler
import json

MESSAGE_GROUPS = [
    [{"role": "user", "content": "中文问题甲"}],
    [{"role": "user", "content": "中文问题乙"}, {"role": "user", "content": "补充上下文乙"}],
]

# Installed before importing submitted main.py. Socket/DNS guards stop accidental
# provider I/O even if the learner selects a different client or imports code
# with network side effects. The exercise runner remains a bounded executor,
# not a hostile-code security sandbox.
LOCAL_GUARD = '''import socket
import urllib.request
from urllib.parse import urlparse
allowed = urlparse("__BASE__")
network_timeouts = []
bool_timeout_arguments = []
_original_settimeout = socket.socket.settimeout
_original_urlopen = urllib.request.urlopen
_original_connect = socket.socket.connect
_original_getaddrinfo = socket.getaddrinfo

def checked_settimeout(sock, value):
    if isinstance(value, bool):
        bool_timeout_arguments.append(value)
    return _original_settimeout(sock, value)

def checked_urlopen(request, *args, **kwargs):
    value = kwargs.get("timeout", args[1] if len(args) >= 2 else None)
    if isinstance(value, bool):
        bool_timeout_arguments.append(value)
    return _original_urlopen(request, *args, **kwargs)

def checked_connect(sock, address):
    host, port = address[0], address[1]
    if host not in {"127.0.0.1", "localhost", "::1"} or port != allowed.port:
        raise OSError("验证只允许当前本地假服务器")
    network_timeouts.append(sock.gettimeout())
    return _original_connect(sock, address)

def checked_resolve(host, port, *args, **kwargs):
    if host not in {"127.0.0.1", "localhost", "::1"} or int(port) != allowed.port:
        raise OSError("验证不允许外部DNS或网络")
    return _original_getaddrinfo(host, port, *args, **kwargs)
socket.socket.connect = checked_connect
socket.socket.settimeout = checked_settimeout
urllib.request.urlopen = checked_urlopen
socket.getaddrinfo = checked_resolve
'''

NO_NETWORK = '''import socket
import urllib.request

def no_network(*args, **kwargs):
    raise OSError("本节验收只使用离线替身")
socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network
socket.getaddrinfo = no_network
'''


def _finish(result, extras):
    result["checks"].extend(extras)
    result["passed"] = bool(result.get("passed")) and all(check["passed"] for check in extras)
    result["cases"] = [check for check in result["checks"] if "actual" in check]
    return result


def validate_d25_chat(code, ctx, section):
    from learnctl import practice as p
    records = []
    class Handler(BaseHTTPRequestHandler):
        def handle_call(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                body = None
            records.append({"method": self.command, "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"), "body": body})
            content = "本地回复-" + str(len(records))
            data = json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        do_POST = handle_call
        do_GET = handle_call
        do_PUT = handle_call
        do_DELETE = handle_call
        def log_message(self, *args):
            pass
    ctx.write("main.py", code)
    harness = LOCAL_GUARD + '''
import math
import json
import main as M
results = []
messages = __MESSAGE_GROUPS__
for index, group in enumerate(messages):
    expected = "本地回复-" + str(index + 1)
    try:
        actual = M.call_chat("demo", group, base_url="__BASE__")
        ok = isinstance(actual, str) and actual == expected
        detail = repr(actual)
    except Exception as error:
        ok = False
        detail = type(error).__name__ + ": " + str(error)
    results.append({"name": "真实本地请求返回content " + str(index + 1), "passed": ok,
        "input": "call_chat('demo', " + repr(group) + ", base_url=本地mock)", "expected": expected, "actual": detail})
valid_deadline = bool(network_timeouts) and not bool_timeout_arguments and all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0 for value in network_timeouts)
results.append({"name": "真正网络I/O设置正有限timeout", "passed": valid_deadline,
    "expected": "实际连接的timeout为正有限数，不要求固定60", "actual": repr(network_timeouts) + "; 布尔实参=" + repr(bool_timeout_arguments)})
with open("_result.json", "w", encoding="utf-8") as file:
    json.dump(results, file, ensure_ascii=False)
'''
    harness = harness.replace("__MESSAGE_GROUPS__", repr(MESSAGE_GROUPS))
    result = p._run_with_server(Handler, harness, ctx, env={"DEEPSEEK_API_KEY": ""})
    extras = [{"name": "两组输入真正触发本地请求", "passed": len(records) == 2, "expected": "2", "actual": str(len(records))}]
    for index, messages in enumerate(MESSAGE_GROUPS):
        record = records[index] if index < len(records) else {}
        body = record.get("body")
        facts = [
            ("正确路径与POST", record.get("method") == "POST" and record.get("path") == "/chat/completions", "POST /chat/completions", [record.get("method"), record.get("path")]),
            ("Bearer演示鉴权", record.get("authorization") == "Bearer demo", "Bearer demo", record.get("authorization")),
            ("JSON Content-Type", str(record.get("content_type", "")).split(";", 1)[0].strip().lower() == "application/json", "application/json", record.get("content_type")),
            ("model字段", isinstance(body, dict) and body.get("model") == "deepseek-chat", "deepseek-chat", body.get("model") if isinstance(body, dict) else None),
            ("messages完整保真", isinstance(body, dict) and body.get("messages") == messages, messages, body.get("messages") if isinstance(body, dict) else None),
            ("stream严格为False", isinstance(body, dict) and body.get("stream") is False, False, body.get("stream") if isinstance(body, dict) else None),
        ]
        extras.extend({"name": label + " " + str(index + 1), "passed": bool(ok), "expected": repr(expected), "actual": repr(actual)} for label, ok, expected, actual in facts)
    return _finish(result, extras)


def validate_d25_errors(code, ctx, section):
    from learnctl import practice as p
    ctx.write("main.py", code)
    harness = NO_NETWORK + '''
import json
import math
from urllib.error import HTTPError, URLError
mode = "normal"
opened = []
class Response:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.headers = {"Content-Type": "application/json"}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.body
    def getcode(self):
        return self.status

def fake_open(request, *args, **kwargs):
    timeout = kwargs.get("timeout", args[1] if len(args) >= 2 else socket.getdefaulttimeout())
    opened.append(timeout)
    if mode == "401":
        raise HTTPError("http://127.0.0.1:1/chat/completions", 401, "mock unauthorized", {}, None)
    if mode == "network":
        raise URLError("mock offline")
    if mode == "timeout":
        raise TimeoutError("mock timeout")
    if mode == "201":
        return Response(b"{}", 201)
    if mode == "bad-json":
        return Response(b"not json")
    return Response(json.dumps({"choices": [{"message": {"content": "离线正常回复"}}]}, ensure_ascii=False).encode("utf-8"))
urllib.request.urlopen = fake_open
import main as M
results = []
api_type = getattr(M, "ApiError", None)
type_ok = isinstance(api_type, type) and issubclass(api_type, RuntimeError)
results.append({"name": "ApiError遵守已声明父类型", "passed": type_ok, "expected": "RuntimeError子类", "actual": str(api_type)})
for mode, expected_status, expected_message in [("normal", None, None), ("401", 401, "API 错误"), ("network", None, "网络错误"), ("timeout", None, "网络错误"), ("201", 201, "API 错误"), ("bad-json", None, "响应不是 JSON")]:
    opened.clear()
    try:
        actual = M.call_chat("demo", [{"role": "user", "content": "相同输入，只改变I/O结果"}], base_url="http://127.0.0.1:1")
        ok = mode == "normal" and actual == "离线正常回复"
        observed = repr(actual)
    except Exception as error:
        status = getattr(error, "status_code", "<缺少status_code>")
        ok = mode != "normal" and type_ok and isinstance(error, api_type) and status == expected_status and str(error) == expected_message
        observed = type(error).__name__ + ": " + str(error) + "; status_code=" + repr(status)
    boundary_ok = len(opened) == 1 and isinstance(opened[0], (int, float)) and not isinstance(opened[0], bool) and math.isfinite(opened[0]) and opened[0] > 0
    results.append({"name": "实际I/O结果 " + mode, "passed": bool(ok and boundary_ok), "input": mode,
        "expected": "离线正常回复" if mode == "normal" else "ApiError(" + repr(expected_message) + ", " + repr(expected_status) + ")",
        "actual": observed + "; 实际urlopen次数/timeout=" + repr(opened)})
with open("_result.json", "w", encoding="utf-8") as file:
    json.dump(results, file, ensure_ascii=False)
'''
    proc, checks = p._run_harness(ctx, harness, "_result.json", env={"DEEPSEEK_API_KEY": ""})
    result = p._finalize(checks, proc)
    result["cases"] = [check for check in checks if "actual" in check]
    return result


def validate_d26_prompt(code, ctx, section):
    from learnctl import practice as p
    ctx.write("main.py", code)
    harness = NO_NETWORK + '''
import json
import re
import main as M
results = []
outputs = []
rows = [(["主题甲-91", "主题乙-73"], "目标甲-27", "要求甲-46", True),
        (["主题甲-91", "主题乙-73"], "目标甲-27", "要求甲-46", False),
        (["HTTP丙-38"], "目标丙-84", "要求丙-62", False),
        ([], "目标空范围-15", "要求空范围-49", True)]
def state_present(text, completed):
    # Literal bools from the taught f-string work, as do common Chinese states.
    tokens = re.findall(r"(?:已完成|完成状态|是否完成|状态)\\s*[：:=]\\s*(True|False|已完成|未完成|是|否|完成)", text)
    accepted = {"True", "已完成", "是", "完成"} if completed else {"False", "未完成", "否"}
    if tokens:
        return any(token in accepted for token in tokens)
    if completed:
        return bool(re.search(r"(?<![A-Za-z])True(?![A-Za-z])", text)) or ("已完成" in text and "未完成" not in text)
    return bool(re.search(r"(?<![A-Za-z])False(?![A-Za-z])", text)) or "未完成" in text
for index, (titles, goal, instructions, completed) in enumerate(rows):
    try:
        text = M.build_prompt(titles, goal, instructions, completed)
        outputs.append(text)
        ok = isinstance(text, str) and "知识范围标题" in text and all(title in text for title in titles) and goal in text and instructions in text and "索引仅代表标题知识范围" in text and "不代表视频正文" in text and state_present(text, completed)
        observed = repr(text)
    except Exception as error:
        outputs.append(None)
        ok = False
        observed = type(error).__name__ + ": " + str(error)
    results.append({"name": "真实提示词输入 " + str(index + 1), "passed": bool(ok), "input": repr((titles, goal, instructions, completed)), "expected": "传入标题/目标/要求/实际状态与索引边界均存在", "actual": observed})
results.append({"name": "相同目标只改completed时实际输出变化", "passed": outputs[0] is not None and outputs[1] is not None and outputs[0] != outputs[1], "expected": "状态不同，输出不同", "actual": repr(outputs[:2])})
with open("_result.json", "w", encoding="utf-8") as file:
    json.dump(results, file, ensure_ascii=False)
'''
    proc, checks = p._run_harness(ctx, harness, "_result.json", env={"DEEPSEEK_API_KEY": ""})
    result = p._finalize(checks, proc)
    result["cases"] = [check for check in checks if "actual" in check]
    return result


def validate_d27_flow(code, ctx, section):
    from learnctl import practice as p
    # Keep the declared dependency modules available while replacing their
    # provided service functions with observable local boundaries in the child.
    for name, source in p._AI_REFERENCE_FIXTURES:
        ctx.write(name, source)
    ctx.write("main.py", code)
    harness = NO_NETWORK + '''
import copy
import json
import sys
import types
build_calls = []
built_prompts = []
send_calls = []
current_response = {}
def fake_build_prompt(catalog_titles, goal, instructions, completed):
    build_calls.append((copy.deepcopy(catalog_titles), goal, instructions, completed))
    text = json.dumps({"catalog_titles": catalog_titles, "goal": goal, "instructions": instructions, "completed": completed}, ensure_ascii=False)
    built_prompts.append(text)
    return text
def fake_send_message(api_key, prompt, *, base_url):
    send_calls.append((api_key, prompt, base_url))
    return copy.deepcopy(current_response)
# Keep the other declared dependency exports intact. Replacing whole modules
# would reject otherwise valid unused imports such as ApiError/parse_ai_json.
import prompt as prompt_module
import deepseek_client as sdk_module
prompt_module.build_prompt = fake_build_prompt
try:
    import ai_client as client_module
except ModuleNotFoundError:
    client_module = types.ModuleType("ai_client")
    client_module.call_chat = sdk_module.call_chat
    client_module.ApiError = sdk_module.ApiError
    client_module.urllib = urllib
client_module.send_message = fake_send_message
sys.modules["ai_client"] = client_module
import main as M
results = []
rows = [({"summary": "本地总结甲-48", "strengths": ["甲"], "issues": [], "next_steps": ["下一步甲"], "extra": "原样额外字段甲"}, "提交甲-93", "要求甲-67", ["标题甲-29", "标题乙-81"]),
        ({"summary": 7, "strengths": None, "issues": False, "next_steps": "next", "extra": {"keep": True}}, "提交乙-74", "要求乙-18", ["标题丙-52"])]
for index, (current_response, submission, rubric, titles) in enumerate(rows):
    build_calls.clear()
    built_prompts.clear()
    send_calls.clear()
    try:
        actual = M.review_submission("demo", submission, rubric, titles, base_url="http://127.0.0.1:1")
        ok = isinstance(actual, dict) and actual == current_response
        observed = repr(actual)
    except Exception as error:
        ok = False
        observed = type(error).__name__ + ": " + str(error)
    data_ok = bool(build_calls) and any(call[0] == titles for call in build_calls) and bool(send_calls)
    for key, prompt, base in send_calls:
        data_ok = data_ok and key == "demo" and base == "http://127.0.0.1:1" and isinstance(prompt, str)
        data_ok = data_ok and any(built in prompt for built in built_prompts) and all(text in prompt for text in [submission, rubric, *titles])
    results.append({"name": "评审真实返回及输入传递 " + str(index + 1), "passed": bool(ok and data_ok), "expected": repr(current_response), "actual": observed + "; build/send次数=" + repr((len(build_calls), len(send_calls)))})
for missing in ["summary", "strengths", "issues", "next_steps"]:
    current_response = {"summary": "x", "strengths": [], "issues": [], "next_steps": []}
    del current_response[missing]
    build_calls.clear()
    built_prompts.clear()
    send_calls.clear()
    try:
        actual = M.review_submission("demo", "提交缺字段", "要求缺字段", ["标题缺字段"], base_url="http://127.0.0.1:1")
        ok = False
        observed = repr(actual)
    except ValueError as error:
        ok = True
        observed = type(error).__name__ + ": " + str(error)
    except Exception as error:
        ok = False
        observed = type(error).__name__ + ": " + str(error)
    results.append({"name": "缺" + missing + "准确抛ValueError", "passed": bool(ok and len(send_calls) >= 1), "expected": "ValueError", "actual": observed})
with open("_result.json", "w", encoding="utf-8") as file:
    json.dump(results, file, ensure_ascii=False)
'''
    proc, checks = p._run_harness(ctx, harness, "_result.json", env={"DEEPSEEK_API_KEY": ""})
    result = p._finalize(checks, proc)
    result["cases"] = [check for check in checks if "actual" in check]
    return result


def register(registry):
    registry.update({"D25-chat": validate_d25_chat, "D25-errors": validate_d25_errors,
        "D26-prompt": validate_d26_prompt, "D27-flow": validate_d27_flow})
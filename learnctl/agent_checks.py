"""Offline D29 checks: real learner code, bounded processes and delivery mutations."""
from __future__ import annotations

import copy
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import Any

AGENT_TIMEOUT = 15.0
DELIVERY_TIMEOUT = 15.0
MAX_OUTPUT_BYTES = 40_000

# This blocks accidental network access; local Python execution is not a sandbox.
NETWORK_GUARD = """import socket, urllib.request
def reject(*args, **kwargs):
    raise AssertionError('本课离线验收禁止网络请求，请mock模型和工具边界')
urllib.request.urlopen = reject
socket.create_connection = reject
socket.getaddrinfo = reject
socket.socket.connect = reject
socket.socket.connect_ex = reject
"""

OFFLINE_CONFTEST = 'import socket\nimport urllib.request\nimport pytest\n\ndef reject(*args, **kwargs):\n    raise AssertionError("离线测试不能访问网络；请mock真正的I/O边界")\n\n# Install before collection, then reapply for each test. This covers imports\n# that accidentally perform I/O, as well as direct urllib/socket access.\nurllib.request.urlopen = reject\nsocket.create_connection = reject\nsocket.getaddrinfo = reject\nsocket.socket.connect = reject\nsocket.socket.connect_ex = reject\n\n@pytest.fixture(autouse=True)\ndef forbid_actual_network(monkeypatch):\n    monkeypatch.setattr(urllib.request, "urlopen", reject)\n    monkeypatch.setattr(socket, "create_connection", reject)\n    monkeypatch.setattr(socket, "getaddrinfo", reject)\n    monkeypatch.setattr(socket.socket, "connect", reject)\n    monkeypatch.setattr(socket.socket, "connect_ex", reject)\n'

HANDOFF_CONFTEST = '\n@pytest.fixture(autouse=True)\ndef require_delivery_contract(request):\n    data = getattr(request.module, "HANDOFF", None)\n    assert isinstance(data, dict), "缺少HANDOFF交付对象"\n    required = {"user_goal", "accepted_inputs", "allowed_tools", "max_steps", "verify_command", "known_limit"}\n    assert required <= data.keys(), "交付字段不完整"\n    for name in ["user_goal", "accepted_inputs", "known_limit"]:\n        assert isinstance(data[name], str) and data[name].strip(), name + "需要实际说明"\n    assert data["allowed_tools"] == ["lookup_order"], "工具边界与需求不一致"\n    assert type(data["max_steps"]) is int and 1 <= data["max_steps"] <= 5, "步数上限不一致"\n    assert data["verify_command"] == "python -m pytest -q tests/test_agentlab.py", "验收命令不一致"\n'

def _check(name, expression):
    try:
        actual = expression()
        return {"name": name, "passed": bool(actual), "actual": repr(actual)[:2000], "expected": "True"}
    except Exception as error:
        return {"name": name, "passed": False, "expected": "True", "actual": type(error).__name__ + ": " + str(error)[:2000]}

def tools_checks(module):
    checks = []
    for order_id in [" O-42 ", "O-9"]:
        def valid_case(order_id=order_id):
            received = []
            call = {"name": "lookup_order", "arguments": {"order_id": order_id}}
            before = copy.deepcopy(call)
            returned = {"order_id": order_id.strip(), "status": "状态:"+order_id.strip(), "说明": "中文回调结果"}
            def lookup(value):
                received.append(value)
                return returned
            actual = module.execute_tool(call, lookup)
            return actual == returned and received == [order_id.strip()] and call == before
        checks.append(_check("合法动态订单 " + order_id, valid_case))
    invalid = [None, [], {}, {"name": "delete_order", "arguments": {"order_id": "O-42"}},
        {"name": "lookup_order", "arguments": []}, {"name": "lookup_order", "arguments": {}},
        {"name": "lookup_order", "arguments": {"order_id": "   "}},
        {"name": "lookup_order", "arguments": {"order_id": 9}},
        {"name": "lookup_order", "arguments": {"order_id": "O-42", "force": True}},
        {"name": "lookup_order", "arguments": {"order_id": "O-42"}, "extra": True}]
    for index, call in enumerate(invalid):
        def reject_case(call=call):
            received = []
            before = copy.deepcopy(call)
            def lookup(value):
                received.append(value)
                return {"order_id": value}
            try:
                module.execute_tool(call, lookup)
            except ValueError:
                return received == [] and call == before
            return False
        checks.append(_check("无效调用执行前拒绝 " + str(index + 1), reject_case))
    def preserve_failure():
        def failed(value):
            raise RuntimeError("fixture failure")
        try:
            module.execute_tool({"name": "lookup_order", "arguments": {"order_id": "O-1"}}, failed)
        except RuntimeError as error:
            return str(error) == "fixture failure"
        return False
    checks.append(_check("工具实际失败不伪装成功", preserve_failure))
    return checks

def loop_checks(module):
    checks = []
    def final_first():
        calls = []
        def model(history):
            calls.append(copy.deepcopy(history))
            return {"kind": "final", "content": " 无需查询 "}
        def forbidden_tool(call):
            raise AssertionError("不应执行工具")
        actual = module.run_agent("内部问题：查询订单", model, forbidden_tool, max_steps=1)
        return actual == {"status": "completed", "answer": " 无需查询 ", "trace": [{"step": 1, "kind": "final"}]} and calls == [[{"kind": "user", "content": "内部问题：查询订单"}]]
    checks.append(_check("首轮直接完成", final_first))
    def tool_then_final():
        model_calls, tool_calls = [], []
        decision = {"kind": "tool", "call": {"name": "lookup_order", "arguments": {"order_id": "O-42"}}}
        frozen = copy.deepcopy(decision)
        def model(history):
            model_calls.append(copy.deepcopy(history))
            if len(model_calls) == 1:
                return decision
            if history != [{"kind": "user", "content": "内部问题：查询订单"}, {"kind": "assistant", "decision": frozen}, {"kind": "tool_result", "name": "lookup_order", "result": {"status": "arriving"}}]:
                raise AssertionError("缺真实决策历史")
            observation = history[-1]
            if observation != {"kind": "tool_result", "name": "lookup_order", "result": {"status": "arriving"}}:
                raise AssertionError("观察丢失或被替换")
            return {"kind": "final", "content": observation["result"]["status"]}
        def execute(call):
            tool_calls.append(copy.deepcopy(call))
            return {"status": "arriving"}
        actual = module.run_agent("内部问题：查询订单", model, execute, max_steps=3)
        return actual == {"status": "completed", "answer": "arriving", "trace": [{"step": 1, "kind": "tool", "name": "lookup_order"}, {"step": 2, "kind": "final"}]} and len(model_calls) == 2 and tool_calls == [frozen["call"]] and decision == frozen
    checks.append(_check("真实观察进入下一轮且不泄漏到trace", tool_then_final))
    for limit in [1, 2, 5]:
        def bounded(limit=limit):
            model_calls, tool_calls = [], []
            def model(history):
                model_calls.append(copy.deepcopy(history))
                return {"kind": "tool", "call": {"name": "lookup_order", "arguments": {"order_id": "O-9"}}}
            def execute(call):
                tool_calls.append(call)
                return {"status": "waiting"}
            actual = module.run_agent("内部问题：查询订单", model, execute, max_steps=limit)
            return actual == {"status": "step_limit", "answer": None, "trace": [{"step": i + 1, "kind": "tool", "name": "lookup_order"} for i in range(limit)]} and len(model_calls) == limit and len(tool_calls) == limit and [len(history) for history in model_calls] == [1+2*i for i in range(limit)]
        checks.append(_check("预算真实限制 " + str(limit), bounded))
    for decision in [None, {"kind": "unknown"}, {"kind": "tool"}, {"kind": "final", "content": " "}, {"kind": "final", "content": 8}]:
        def rejects(decision=decision):
            model_calls, tool_calls = [], []
            def model(history):
                model_calls.append(history)
                return decision
            def execute(call):
                tool_calls.append(call)
                return {}
            try:
                module.run_agent("x", model, execute)
            except ValueError:
                return len(model_calls) == 1 and tool_calls == []
            return False
        checks.append(_check("无效决策拒绝 " + repr(decision), rejects))
    def tool_error():
        calls = []
        def model(history):
            calls.append(history)
            return {"kind": "tool", "call": {"name": "delete_order", "arguments": {"order_id": "O-1"}}}
        def execute(call):
            raise ValueError("unknown tool")
        try:
            module.run_agent("x", model, execute)
        except ValueError as error:
            if str(error) != "unknown tool" or len(calls) != 1:
                return False
        else:
            return False
        calls.clear()
        def unavailable_tool(call):
            raise RuntimeError("工具服务失败")
        try:
            module.run_agent("x", model, unavailable_tool)
        except RuntimeError as error:
            if str(error) != "工具服务失败" or len(calls) != 1:
                return False
        else:
            return False
        calls.clear()
        tool_calls=[]
        def unavailable_model(history):
            calls.append(history)
            raise RuntimeError("模型服务失败")
        def unused_tool(call):
            tool_calls.append(call)
            return {}
        try:
            module.run_agent("x", unavailable_model, unused_tool)
        except RuntimeError as error:
            return str(error)=="模型服务失败" and len(calls)==1 and tool_calls==[]
        return False
    checks.append(_check("模型和工具实际失败均停止并向上传递", tool_error))
    return checks

def delivery_fixtures(tools_source, runner_source, mutant):
    files = {"agentlab/__init__.py": "", "agentlab/tools.py": tools_source, "agentlab/runner.py": runner_source}
    if mutant == "observation":
        files["agentlab/_runner_original.py"] = runner_source
        files["agentlab/runner.py"] = '''from ._runner_original import *
from ._runner_original import run_agent as original

def run_agent(question, model, execute_tool, *, max_steps=3):
    def blind_model(history):
        return model([event for event in history if event.get("kind") != "tool_result"])
    return original(question, blind_model, execute_tool, max_steps=max_steps)
'''
    elif mutant == "extra-call":
        files["agentlab/_runner_original.py"] = runner_source
        files["agentlab/runner.py"] = '''from ._runner_original import *
from ._runner_original import run_agent as original

def run_agent(question, model, execute_tool, *, max_steps=3):
    result = original(question, model, execute_tool, max_steps=max_steps)
    if result["status"] == "step_limit":
        model([{"kind": "user", "content": question}])
    return result
'''
    elif mutant == "unknown-tool":
        files["agentlab/_tools_original.py"] = tools_source
        files["agentlab/tools.py"] = '''from ._tools_original import *
from ._tools_original import execute_tool as original

def execute_tool(call, lookup_order):
    if isinstance(call, dict) and call.get("name") != "lookup_order":
        call = {"name": "lookup_order", "arguments": call.get("arguments")}
    return original(call, lookup_order)
'''
    elif mutant != "correct":
        raise ValueError(mutant)
    return files

def _bounded_process(args: list[str], cwd: Path, timeout: float) -> dict[str, Any]:
    """Retain at most 40 KB per stream; stop on output overflow or deadline."""
    environment = dict(os.environ)
    for name in list(environment):
        if name.endswith(('_API_KEY', '_TOKEN', '_SECRET')):
            environment.pop(name, None)
    environment.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    proc = subprocess.Popen(args, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    limited = threading.Event()
    def read_stream(name, stream):
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                capacity = MAX_OUTPUT_BYTES-len(buffers[name])
                buffers[name].extend(chunk[:max(0,capacity)])
                if len(chunk)>capacity:
                    limited.set()
                    try: proc.kill()
                    except OSError: pass
                    break
        finally:
            stream.close()
    readers = [threading.Thread(target=read_stream, args=(name, stream), daemon=True)
               for name, stream in [('stdout', proc.stdout), ('stderr', proc.stderr)]]
    for reader in readers: reader.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill(); proc.wait()
    for reader in readers: reader.join(timeout=1)
    return {'stdout': bytes(buffers['stdout']).decode('utf-8',errors='replace'),
            'stderr': bytes(buffers['stderr']).decode('utf-8',errors='replace'),
            'exit_code': proc.returncode, 'timeout': timed_out, 'output_limited': limited.is_set()}


def _behavior_validator(kind: str):
    def validate(code, ctx, section):
        from . import practice as p
        path = 'agentlab/tools.py' if kind=='tools' else 'agentlab/runner.py'
        ctx.write(path, code)
        ctx.write_scaffold('agentlab/__init__.py', '')
        checker = tools_checks if kind=='tools' else loop_checks
        module = 'agentlab.tools' if kind=='tools' else 'agentlab.runner'
        source = '\n'.join([NETWORK_GUARD, 'import copy, json', 'from pathlib import Path',
                            inspect.getsource(_check), inspect.getsource(checker),
                            f'import {module} as M', f'checks = {checker.__name__}(M)',
                            "Path('_result.json').write_text(json.dumps(checks,ensure_ascii=False),encoding='utf-8')"])
        ctx.write('_harness.py', source)
        proc = _bounded_process([sys.executable,'-u','_harness.py'],ctx.temp,AGENT_TIMEOUT)
        checks = p._read_result(ctx,'_result.json')
        if not checks:
            checks = [{'name':'代码导入与实际执行','passed':False,
                       'detail':p._tail(proc['stderr'] or proc['stdout']) or '子进程未完成行为验收'}]
        if proc['output_limited']:
            checks.append({'name':'输出长度限制','passed':False,'detail':'输出超过40 KB，已停止执行。'})
        result = p._finalize(checks,proc)
        result.update(passed=result['passed'] and proc['exit_code']==0 and not proc['output_limited'],
                      cases=[check for check in checks if 'actual' in check],
                      output_limited=proc['output_limited'])
        return result
    return validate


def _delivery_validator(code, ctx, section):
    from . import practice as p
    paths = ('agentlab/tools.py','agentlab/runner.py')
    missing = [path for path in paths if path not in ctx.ws_deps or not (ctx.temp/path).is_file()]
    if missing:
        return {'passed':False,'checks':[{'name':'真实学习者依赖','passed':False,'detail':'缺少 '+', '.join(missing)}],
                'stdout':'','stderr':'','exit_code':None,'cases':[]}
    tools_source,runner_source = [(ctx.temp/path).read_text(encoding='utf-8') for path in paths]
    targets = [('correct',None,'真实学习者实现下全部测试通过'),
               ('observation','test_order_lookup_done','工具观察丢失被正常查询测试检出'),
               ('extra-call','test_step_limit','额外模型调用被预算测试检出'),
               ('unknown-tool','test_unknown_tool','未知工具执行被拒绝测试检出')]
    checks,outputs,errors = [],[],[]
    baseline_exit = None
    timed_out = output_limited = False
    for mutant,target,label in targets:
        with p.PracticeContext(ctx.project_root) as trial:
            for path,source in delivery_fixtures(tools_source,runner_source,mutant).items():
                trial.write(path,source)
            test_file = 'tests/test_agentlab.py'
            trial.write(test_file,code)
            trial.write('conftest.py',OFFLINE_CONFTEST+HANDOFF_CONFTEST)
            selector = test_file if target is None else test_file+'::'+target
            proc = _bounded_process([sys.executable,'-u','-m','pytest','-q',selector],trial.temp,DELIVERY_TIMEOUT)
            timed_out = timed_out or proc['timeout']
            output_limited = output_limited or proc['output_limited']
            expected = 0 if mutant=='correct' else 1
            passed = (proc['exit_code']==expected and not proc['timeout'] and not proc['output_limited'])
            if mutant!='correct':
                # Collection/syntax errors and fixture-only failures are not detection evidence.
                passed = passed and 'FAILED' in proc['stdout'] and 'ERROR collecting' not in proc['stdout']
            else:
                baseline_exit = proc['exit_code']
            checks.append({'name':label,'input':selector,'passed':bool(passed),
                           'actual':f"pytest退出码 {proc['exit_code']}",'expected':f'pytest退出码 {expected}',
                           'detail':(f'超过{DELIVERY_TIMEOUT:g}秒，已停止本次运行。' if proc['timeout'] else '输出超过40 KB，已停止执行。' if proc['output_limited'] else p._tail(proc['stderr'] or proc['stdout'],3000))})
            outputs.append('['+label+']\n'+proc['stdout'])
            if proc['stderr']: errors.append(proc['stderr'])
            if mutant=='correct' and not passed:
                break
            if proc['timeout'] or proc['output_limited']:
                break
    return {'passed':len(checks)==4 and all(check['passed'] for check in checks),
            'checks':checks,'cases':checks,'stdout':p._truncate('\n'.join(outputs)),
            'stderr':p._truncate('\n'.join(errors)),'exit_code':baseline_exit,
            'timeout':timed_out,'output_limited':output_limited}


def register(registry):
    registry['D29-tools'] = _behavior_validator('tools')
    registry['D29-loop'] = _behavior_validator('loop')
    registry['D29-delivery'] = _delivery_validator

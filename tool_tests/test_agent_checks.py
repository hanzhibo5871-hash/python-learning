"""D29 offline behavior, delivery mutations and retained learner history."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys

import pytest
from conftest import REPOSITORY
from learnctl import agent_checks as checks
from learnctl.practice import _CODE_VALIDATORS, validate_code, WORKSPACE_ROOT, PracticeContext

TASK=json.loads((REPOSITORY/'scripts/agent_course.json').read_text(encoding='utf-8'))
SECTIONS={s['id']:s for s in TASK['lesson']}

REFERENCE_TOOLS = 'def execute_tool(call, lookup_order):\n    if not isinstance(call, dict) or set(call) != {"name", "arguments"}:\n        raise ValueError("调用形状错误")\n    if call["name"] != "lookup_order":\n        raise ValueError("工具不允许")\n    arguments = call["arguments"]\n    if not isinstance(arguments, dict) or set(arguments) != {"order_id"}:\n        raise ValueError("参数形状错误")\n    order_id = arguments["order_id"]\n    if not isinstance(order_id, str) or not order_id.strip():\n        raise ValueError("订单ID不能为空")\n    return lookup_order(order_id.strip())\n'

REFERENCE_RUNNER = 'def run_agent(question, model, execute_tool, *, max_steps=3):\n    history = [{"kind": "user", "content": question}]\n    trace = []\n    for index in range(max_steps):\n        decision = model(history)\n        if not isinstance(decision, dict):\n            raise ValueError("决策不是对象")\n        kind = decision.get("kind")\n        if kind == "tool":\n            if "call" not in decision:\n                raise ValueError("缺工具请求")\n            call = decision["call"]\n            result = execute_tool(call)\n            history.append({"kind": "assistant", "decision": decision})\n            history.append({"kind": "tool_result", "name": call["name"], "result": result})\n            trace.append({"step": index + 1, "kind": "tool", "name": call["name"]})\n        elif kind == "final":\n            content = decision.get("content")\n            if not isinstance(content, str) or not content.strip():\n                raise ValueError("最终文本无效")\n            trace.append({"step": index + 1, "kind": "final"})\n            return {"status": "completed", "answer": content, "trace": trace}\n        else:\n            raise ValueError("未知决策类型")\n    return {"status": "step_limit", "answer": None, "trace": trace}\n'

REFERENCE_TESTS = 'import pytest\nfrom unittest.mock import Mock\nfrom agentlab.tools import execute_tool\nfrom agentlab.runner import run_agent\n\nHANDOFF = {"user_goal":"运营人员查询订单状态", "accepted_inputs":"非空订单ID字符串", "allowed_tools":["lookup_order"], "max_steps":3, "verify_command":"python -m pytest -q tests/test_agentlab.py", "known_limit":"本地假模型模拟，只读查询，无真实模型/生产客户数据"}\n\ndef test_order_lookup_done():\n    lookup = Mock(return_value={"status":"arriving"})\n    seen = []\n    def model(history):\n        seen.append(history)\n        if len(seen) == 1:\n            return {"kind":"tool", "call":{"name":"lookup_order", "arguments":{"order_id":"O-42"}}}\n        assert history[-1]["kind"] == "tool_result"\n        return {"kind":"final", "content":history[-1]["result"]["status"]}\n    result = run_agent("查询订单", model, lambda call: execute_tool(call, lookup), max_steps=3)\n    assert result["status"] == "completed"\n    assert result["answer"] == "arriving"\n    lookup.assert_called_once_with("O-42")\n    assert len(seen) == 2\n\ndef test_step_limit():\n    lookup = Mock(return_value={"status":"waiting"})\n    model = Mock(return_value={"kind":"tool", "call":{"name":"lookup_order", "arguments":{"order_id":"O-9"}}})\n    result = run_agent("查询订单", model, lambda call: execute_tool(call, lookup), max_steps=2)\n    assert result["status"] == "step_limit"\n    assert result["answer"] is None\n    assert model.call_count == 2\n    assert lookup.call_count == 2\n\ndef test_unknown_tool():\n    lookup = Mock(return_value={"status":"waiting"})\n    model = Mock(return_value={"kind":"tool", "call":{"name":"delete_order", "arguments":{"order_id":"O-9"}}})\n    with pytest.raises(ValueError):\n        run_agent("查询订单", model, lambda call: execute_tool(call, lookup))\n    lookup.assert_not_called()\n'

@pytest.fixture(autouse=True)
def register_d29(monkeypatch):
    registry={}
    checks.register(registry)
    for name,validator in registry.items(): monkeypatch.setitem(_CODE_VALIDATORS,name,validator)


def workspace(root,tools=REFERENCE_TOOLS,runner=REFERENCE_RUNNER):
    target=root/WORKSPACE_ROOT/'agentlab'
    target.mkdir(parents=True,exist_ok=True)
    (target/'tools.py').write_text(tools,encoding='utf-8')
    (target/'runner.py').write_text(runner,encoding='utf-8')


@pytest.mark.parametrize('sid,source,count', [('D29-tools',REFERENCE_TOOLS,13),('D29-loop',REFERENCE_RUNNER,11)])
def test_agent_runtime_checks_actual_code(sid,source,count,tmp_path):
    workspace(tmp_path)
    result=validate_code(SECTIONS[sid],source,tmp_path)
    assert result['passed'],result
    assert len(result['cases'])==count
    assert all(case.get('actual') and case['expected']=='True' for case in result['cases'])
    assert not (tmp_path/'.learn').exists()


@pytest.mark.parametrize('sid,source',[('D29-tools','def execute_tool(call,lookup): return {}'),
                                     ('D29-loop',"def run_agent(*args,**kwargs): return {'status':'completed','answer':'arriving','trace':[]}")])
def test_agent_constant_results_are_rejected(sid,source,tmp_path):
    workspace(tmp_path)
    result=validate_code(SECTIONS[sid],source,tmp_path)
    assert not result['passed'] and any(not c['passed'] for c in result['cases'])


@pytest.mark.parametrize('sid',list(SECTIONS))
def test_agent_starters_are_not_complete(sid,tmp_path):
    workspace(tmp_path)
    assert not validate_code(SECTIONS[sid],SECTIONS[sid]['practice']['starter_content'],tmp_path)['passed']


def test_delivery_runs_real_workspace_and_three_faults(tmp_path):
    workspace(tmp_path)
    before={p:p.read_bytes() for p in (tmp_path/WORKSPACE_ROOT/'agentlab').glob('*.py')}
    result=validate_code(SECTIONS['D29-delivery'],REFERENCE_TESTS,tmp_path)
    assert result['passed'],result
    assert [c['actual'] for c in result['cases']]==['pytest退出码 0','pytest退出码 1','pytest退出码 1','pytest退出码 1']
    assert all(p.read_bytes()==content for p,content in before.items())
    assert 'HANDOFF =' not in result['stdout']


def test_delivery_pass_only_tests_fail_mutation_detection(tmp_path):
    workspace(tmp_path)
    header=next(line for line in REFERENCE_TESTS.splitlines() if line.startswith('HANDOFF = '))
    source=header+'\ndef test_order_lookup_done(): pass\ndef test_step_limit(): pass\ndef test_unknown_tool(): pass\n'
    result=validate_code(SECTIONS['D29-delivery'],source,tmp_path)
    assert not result['passed']
    assert [c['passed'] for c in result['checks']]==[True,False,False,False]


@pytest.mark.parametrize('header',["HANDOFF = {}", "HANDOFF = {'allowed_tools':['delete_order']}"])
def test_delivery_invalid_handoff_is_not_evidence(header,tmp_path):
    workspace(tmp_path)
    existing=next(line for line in REFERENCE_TESTS.splitlines() if line.startswith('HANDOFF = '))
    result=validate_code(SECTIONS['D29-delivery'],REFERENCE_TESTS.replace(existing,header),tmp_path)
    assert not result['passed'] and len(result['checks'])==1


def test_delivery_does_not_replace_broken_workspace_with_reference(tmp_path):
    workspace(tmp_path,tools='def execute_tool(call,lookup): return {}')
    result=validate_code(SECTIONS['D29-delivery'],REFERENCE_TESTS,tmp_path)
    assert not result['passed'] and not result['checks'][0]['passed']


@pytest.mark.parametrize('sid',['D29-loop','D29-delivery'])
def test_agent_missing_dependencies_cannot_pass(sid,tmp_path):
    result=validate_code(SECTIONS[sid],REFERENCE_RUNNER if sid=='D29-loop' else REFERENCE_TESTS,tmp_path)
    assert not result['passed'] and '缺少' in result['checks'][0]['detail']


def test_agent_harness_is_a_separate_process_and_removes_credentials(tmp_path,monkeypatch):
    monkeypatch.setenv('COURSE_API_KEY','fake-private-value')
    source="import os\nassert os.getpid() != "+str(__import__('os').getpid())+"\nassert 'COURSE_API_KEY' not in os.environ\n"+REFERENCE_TOOLS
    result=validate_code(SECTIONS['D29-tools'],source,tmp_path)
    assert result['passed'],result


@pytest.mark.parametrize('sid,source',[('D29-tools',REFERENCE_TOOLS),('D29-loop',REFERENCE_RUNNER)])
def test_agent_imports_cannot_make_real_requests(sid,source,tmp_path):
    workspace(tmp_path)
    source="import urllib.request\nurllib.request.urlopen('https://api.deepseek.com/chat/completions')\n"+source
    result=validate_code(SECTIONS[sid],source,tmp_path)
    assert not result['passed'] and '离线验收禁止网络请求' in result['stderr']


def test_delivery_network_calls_are_stopped_before_collection(tmp_path):
    workspace(tmp_path)
    source="import urllib.request\nurllib.request.urlopen('https://api.deepseek.com/chat/completions')\n"+REFERENCE_TESTS
    result=validate_code(SECTIONS['D29-delivery'],source,tmp_path)
    assert not result['passed'] and '离线测试不能访问网络' in result['stdout']


def test_agent_bounds_output(tmp_path):
    source="print('字'*30000)\n"+REFERENCE_TOOLS
    result=validate_code(SECTIONS['D29-tools'],source,tmp_path)
    assert not result['passed'] and result['output_limited']
    assert len(result['stdout'].encode('utf-8'))<=checks.MAX_OUTPUT_BYTES+3


def test_agent_timeout_does_not_pass(tmp_path,monkeypatch):
    monkeypatch.setattr(checks,'AGENT_TIMEOUT',0.1)
    result=validate_code(SECTIONS['D29-tools'],'while True: pass',tmp_path)
    assert not result['passed'] and any(c['name']=='运行超时' for c in result['checks'])


def test_agent_checks_have_no_embedded_reference_implementation():
    source=Path(checks.__file__).read_text(encoding='utf-8')
    assert 'REFERENCE_TOOLS' not in source and 'REFERENCE_RUNNER' not in source and 'REFERENCE_TESTS' not in source
    assert 'importlib.util' not in source and 'task-2' not in source


def test_agent_old_history_is_retained_and_new_task_is_incomplete(tmp_path):
    from learnctl.progress import initial_progress,load_progress,lesson_progress_for
    data=json.loads((REPOSITORY/'data/curriculum.json').read_text(encoding='utf-8'))
    original=copy.deepcopy(data)
    original['tasks']=[t for t in original['tasks'] if t['id']!='D29']
    revised=copy.deepcopy(original)
    revised['tasks'].append(copy.deepcopy(TASK))
    assert revised['curriculum_version']=='3.0.0'
    old=initial_progress(original)
    old['custom_audit_field']={'keep':'历史字段'}
    for task in original['tasks']:
        old['tasks'][task['id']]={'status':'done','evidence':['原有验证记录'],'history_marker':'keep'}
        old['lesson_progress'][task['id']]={'current_section':task['lesson'][-1]['id'],'completed_sections':[s['id'] for s in task['lesson']],'history_marker':'keep'}
    path=tmp_path/'history.json'
    path.write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
    content=path.read_bytes()
    loaded=load_progress(path,revised)
    assert path.read_bytes()==content
    for task in original['tasks']:
        assert loaded['tasks'][task['id']]==old['tasks'][task['id']]
        assert loaded['lesson_progress'][task['id']]==old['lesson_progress'][task['id']]
    assert loaded['custom_audit_field']==old['custom_audit_field']
    assert loaded['tasks'].get('D29',{}).get('status','todo')=='todo'
    assert lesson_progress_for(loaded,TASK)=={'current_section':'D29-tools','completed_sections':[]}
    assert lesson_progress_for(load_progress(path,revised),TASK)==lesson_progress_for(loaded,TASK)


def test_delivery_bad_workspace_syntax_returns_failed_result(tmp_path):
    workspace(tmp_path,runner='def broken(: pass')
    result=validate_code(SECTIONS['D29-delivery'],REFERENCE_TESTS,tmp_path)
    assert not result['passed'] and 'SyntaxError' in result['stdout']
    assert len(result['checks'])==1


@pytest.mark.parametrize('old,new',[('"max_steps":3','"max_steps":True'),('"allowed_tools":["lookup_order"]','"allowed_tools":["lookup_order","delete_order"]'),('"verify_command":"python -m pytest -q tests/test_agentlab.py"','"verify_command":"wrong command"'),('"user_goal":"运营人员查询订单状态"','"user_goal":"   "')])
def test_handoff_exact_boundaries_are_checked(old,new,tmp_path):
    workspace(tmp_path)
    assert old in REFERENCE_TESTS
    result=validate_code(SECTIONS['D29-delivery'],REFERENCE_TESTS.replace(old,new),tmp_path)
    assert not result['passed'] and len(result['checks'])==1


def test_delivery_timeout_is_explicit_and_cannot_pass(tmp_path,monkeypatch):
    workspace(tmp_path)
    monkeypatch.setattr(checks,'DELIVERY_TIMEOUT',0.2)
    result=validate_code(SECTIONS['D29-delivery'],'while True: pass',tmp_path)
    assert not result['passed'] and result['timeout']
    assert '已停止' in result['checks'][0]['detail']


def test_delivery_keeps_student_public_helpers_in_mutations(tmp_path):
    workspace(tmp_path,tools=REFERENCE_TOOLS+"\nTOOL_LABEL='订单工具'\n",runner=REFERENCE_RUNNER+"\nLOOP_LABEL='预算循环'\n")
    code="from agentlab.tools import TOOL_LABEL\nfrom agentlab.runner import LOOP_LABEL\n"+REFERENCE_TESTS
    result=validate_code(SECTIONS['D29-delivery'],code,tmp_path)
    assert result['passed'],result


def test_agent_public_payload_has_no_private_reference_code():
    from learnctl.workflow import lesson_payload
    from learnctl.progress import initial_progress
    data=json.loads((REPOSITORY/'data/curriculum.json').read_text(encoding='utf-8'))
    payload=lesson_payload(data,TASK,initial_progress(data))
    def strings(item):
        if isinstance(item,str): yield item
        elif isinstance(item,dict):
            for value in item.values(): yield from strings(value)
        elif isinstance(item,list):
            for value in item: yield from strings(value)
    published=list(strings(payload))
    assert REFERENCE_TOOLS not in published and REFERENCE_RUNNER not in published and REFERENCE_TESTS not in published
    for section in payload['sections']:
        assert all('reference' not in drill for drill in section['practice_first']['drills'])


def test_tool_cannot_ignore_real_callback_result(tmp_path):
    wrong=REFERENCE_TOOLS.replace('return lookup_order(order_id.strip())',"lookup_order(order_id.strip())\n    return {'order_id':order_id.strip(),'status':'in_transit'}")
    result=validate_code(SECTIONS['D29-tools'],wrong,tmp_path)
    assert not result['passed'] and not result['cases'][0]['passed']


def test_loop_cannot_discard_initial_user_history(tmp_path):
    workspace(tmp_path)
    wrong=REFERENCE_RUNNER.replace('        decision = model(history)',"        if index: history = history[1:]\n        decision = model(history)")
    result=validate_code(SECTIONS['D29-loop'],wrong,tmp_path)
    assert not result['passed']


def test_loop_cannot_swallow_model_or_tool_runtime_failure(tmp_path):
    workspace(tmp_path)
    wrong=REFERENCE_RUNNER.replace('def run_agent(question, model, execute_tool, *, max_steps=3):','def original(question, model, execute_tool, *, max_steps=3):')+"\ndef run_agent(*args,**kwargs):\n    try: return original(*args,**kwargs)\n    except RuntimeError: return {'status':'completed','answer':'伪成功','trace':[]}\n"
    result=validate_code(SECTIONS['D29-loop'],wrong,tmp_path)
    assert not result['passed']
    case=next(c for c in result['cases'] if c['name']=='模型和工具实际失败均停止并向上传递')
    assert not case['passed']

from __future__ import annotations

import copy
import json
import threading
from pathlib import Path

import pytest
from conftest import request, grading_reply as reply
from learnctl import ai, grading
from learnctl.curriculum import load_curriculum
from learnctl.errors import BlockedError, UsageError
from learnctl.progress import load_progress, save_progress
import learnctl.web.server as web



def provider(monkeypatch, response=None, *, verdict='needs_work', transform=None):
    calls = []
    def transport(url, payload, key, timeout=60):
        calls.append(payload)
        data = copy.deepcopy(response) if response is not None else reply(payload, verdict)
        if transform: data = transform(data, json.loads(payload['messages'][-1]['content']))
        return 200, json.dumps({'choices': [{'message': {'content': json.dumps(data)}}]}).encode()
    monkeypatch.setattr(ai, '_request', transport)
    return calls


def session():
    s = ai.AiSession(); s.set_key('test-only-key'); return s


def evaluate(context=None, content='def f(a):\n    return 0', result=None):
    return grading.present_feedback(grading.grade(session(), context or {'title':'返回当前输入', 'exercise':{'instructions':'依据输入返回结果。保持函数接口。'}},
        content, result or {'passed':False, 'cases':[{'passed':False,'actual':'0','expected':'6'}]}),1)


def unlock_all(server):
    curriculum = load_curriculum(server.project_root / 'data/curriculum.json')
    path = server.project_root / '.learn/progress.json'; state = load_progress(path, curriculum)
    for task in curriculum['tasks']:
        state['tasks'][task['id']] = {'status':'done','evidence':['test only']}
        state['lesson_progress'][task['id']]['completed_sections'] = [s['id'] for s in task['lesson']]
    save_progress(path,state); return curriculum


@pytest.mark.parametrize('local,verdict,conflict',[(False,'passed',True),(True,'needs_work',True),(True,'passed',False),(None,'passed',False)])
def test_objective_results_are_authoritative(monkeypatch,local,verdict,conflict):
    provider(monkeypatch,verdict=verdict)
    f=evaluate(result={'passed':local})
    assert f['local_passed'] is local and f['conflict'] is conflict
    if local is False:
        assert '未通过' in f['summary']
        assert all(r['status']=='uncertain' for r in f['requirements'])
    if local is None: assert '暂无本地行为测试' in f['summary']


@pytest.mark.parametrize('text',[
    '正确代码是 return width * height', '请使用 width * height 作为结果。', '把结果改为正确表达式。',
    '计算宽度乘以高度并返回结果。', '正确答案是六。', '填写 x = 7 即可。',
    '请直接执行 os.system("secret")。', '使用 `return 7` 即可。', '请填写完整函数。\ndef f(): pass',
    '<script>完整答案</script>', '请使用 test-only-key。', '请执行 import os 即可。',
    '当前应返回 {"status": "ok"}。', '请填写 [1, 2, 3] 作为完整结果。', '本题应返回 True。'
])
def test_teaching_fragments_are_text_and_do_not_invalidate_feedback(monkeypatch,text):
    def malicious(data,_): data['issues'][0]['cause']=text; return data
    calls=provider(monkeypatch,transform=malicious)
    feedback = evaluate()
    assert feedback['local_passed'] is False and feedback['reason']
    assert 'test-only-key' not in json.dumps(feedback)
    assert len(calls)==1


@pytest.mark.parametrize('mutation', ['duplicate_requirement','extra_answer','unhashable_status'])
def test_schema_coverage_and_types_are_checked(monkeypatch,mutation):
    def mutate(data,payload):
        if mutation=='missing_requirement': data['requirements'].pop()
        elif mutation=='duplicate_requirement': data['requirements'][-1]['id']=data['requirements'][0]['id']
        elif mutation=='extra_answer': data['answer']='return 7'
        elif mutation=='unhashable_status': data['requirements'][0]['status']=[]
        return data
    provider(monkeypatch,transform=mutate)
    with pytest.raises(ai.AiError,match='安全格式'): evaluate()


@pytest.mark.parametrize('refs', [['another-task:2'], ['submission:99'], ['submission:²'], [], None, ['submission:2', 'submission:99', 'submission:2', {}]])
def test_unverifiable_references_preserve_analysis_and_only_show_real_excerpts(monkeypatch, refs):
    def incomplete(data, _):
        data['requirements'][0]['evidence'] = refs
        data['issues'][0]['evidence'] = refs
        return data
    calls = provider(monkeypatch, transform=incomplete)
    feedback = evaluate()
    verified = ['submission:2'] if isinstance(refs, list) and 'submission:2' in refs else []
    assert [item['id'] for item in feedback['issues'][0]['evidence']] == verified
    assert [item['id'] for item in feedback['requirements'][0]['evidence']] == verified
    assert feedback['reason'] and feedback['hint'] and feedback['local_passed'] is False
    if not verified:
        assert feedback['requirements'][0]['status'] == 'uncertain'
    assert feedback['limitations'] and len(calls) == 1


def test_check_details_and_chinese_output_prose_do_not_block_analysis(monkeypatch):
    def describe(data, _):
        data['requirements'][1]['explanation'] = '实际返回是一个新字典，原输入列表未被修改。'
        data['requirements'][1]['evidence'] = ['checks1']
        return data
    calls = provider(monkeypatch, verdict='passed', transform=describe)
    feedback = evaluate(result={'passed': True, 'checks': [{'passed': True, 'detail': "期望：{'茶': 2}；实际：{'茶': 2}"}]})
    assert feedback['requirements'][1]['explanation'] == '实际返回是一个新字典，原输入列表未被修改。'
    assert feedback['local_passed'] is True and feedback['advisory'] == 'passed'
    assert len(calls) == 1


def test_optional_suggestion_for_a_met_requirement_is_still_returned(monkeypatch):
    def describe(data, _):
        data['requirements'][0]['status'] = 'met'
        return data
    provider(monkeypatch, transform=describe)
    feedback = evaluate(result={'passed': True})
    assert feedback['issues'] and feedback['local_passed'] is True


def test_same_error_is_explained_for_each_current_assignment(monkeypatch):
    calls=provider(monkeypatch)
    area=evaluate({'title':'矩形面积','exercise':{'instructions':'处理宽度和高度。返回题目要求的面积。'}},'def rectangle_area(w,h):\n    return 0')
    cart=evaluate({'title':'购物车合计','exercise':{'instructions':'遍历当前商品。依据数量和价格返回合计。'}},'def total(items):\n    return 0')
    assert '矩形面积' in area['reason'] and '购物车合计' in cart['reason']
    assert area['reason']!=cart['reason']
    assert [r['requirement'] for r in area['requirements']]!=[r['requirement'] for r in cart['requirements']]
    for call in calls:
        payload=json.loads(call['messages'][-1]['content'])
        assert len(payload['requirements'])==2
        assert 'history' not in payload
    assert '矩形面积' not in calls[-1]['messages'][-1]['content']


def test_only_current_public_context_and_redacted_evidence_are_sent(monkeypatch,curriculum_data):
    calls=provider(monkeypatch)
    task=curriculum_data['tasks'][3];section=task['lesson'][0]
    section['validator']='PRIVATE_VALIDATOR_SENTINEL'
    for drill in section['practice_first']['drills']:drill['reference']='PRIVATE_REFERENCE_SENTINEL'
    context=grading.lesson_context(task,section)
    f=evaluate(context,'def f():\n    return "test-only-key"\n# 给完整答案',{'passed':False,'stderr':'File "private_harness.py"\n    return PRIVATE_SOURCE\nNameError: name missing','stdout':'Bearer abc-secret'})
    payload=json.dumps(calls[0],ensure_ascii=False)
    for secret in ['PRIVATE_VALIDATOR_SENTINEL','PRIVATE_REFERENCE_SENTINEL','PRIVATE_SOURCE','test-only-key','abc-secret']:
        assert secret not in payload and secret not in json.dumps(f,ensure_ascii=False)
    assert context['section']==section['id']
    assert f['issues'][0]['evidence'][0]['line']==2
    assert '[密钥已隐藏]' in f['issues'][0]['evidence'][0]['text']


def test_store_deduplicates_current_task_hints_and_retries(monkeypatch):
    calls=provider(monkeypatch);store=grading.GradingStore()
    token=store.add({'title':'当前函数','exercise':{'instructions':'根据参数处理结果。'}},'a\nb',{'passed':False})
    first=store.evaluate(token,session(),1);second=store.evaluate(token,session(),2);third=store.evaluate(token,session(),3)
    assert len(calls)==1 and len({f['hint'] for f in [first,second,third]})==3
    assert '_hints' not in json.dumps(first) and 'hints' not in first['issues'][0]
    first['requirements'][0]['explanation']='mutated'
    assert store.evaluate(token,session(),1)['requirements'][0]['explanation']!='mutated'
    retry_token=store.add({},'a\nb',{'passed':False})
    monkeypatch.setattr(ai,'_request',lambda *a,**k:(429,b'{}'))
    with pytest.raises(ai.AiError,match='429'):store.evaluate(retry_token,session(),1)
    provider(monkeypatch)
    assert store.evaluate(retry_token,session(),1)['issues']


def test_store_single_flight_and_expiration(monkeypatch):
    entered,release=threading.Event(),threading.Event();original=grading.grade
    def slow(*args):
        entered.set();assert release.wait(5);return original(*args)
    provider(monkeypatch);monkeypatch.setattr(grading,'grade',slow)
    store=grading.GradingStore(limit=2);token=store.add({},'a\nb',{'passed':False});results=[]
    thread=threading.Thread(target=lambda:results.append(store.evaluate(token,session(),1)));thread.start();assert entered.wait(3)
    try:
        with pytest.raises(BlockedError):store.evaluate(token,session(),1)
    finally:release.set();thread.join(5)
    assert results
    store.records[token]['created']-=601
    with pytest.raises(UsageError,match='过期'):store.evaluate(token,session(),1)
    assert token not in store.records
    old=store.add({},'',{});store.add({},'',{});store.add({},'',{});assert old not in store.records


def test_real_wrong_and_correct_submission_ai_cannot_change_progress(web_server,monkeypatch):
    unlock_all(web_server);web_server.ai_session.set_key('test-only-key');calls=provider(monkeypatch,verdict='passed')
    path=web_server.project_root/'.learn/progress.json'
    _,wrong,_=request(web_server,'POST','/api/tasks/D04/sections/D04-def-return/validate',{'content':'def rectangle_area(width,height):\n    return 0'})
    assert wrong['passed'] is False;before=path.read_bytes()
    _,judged,_=request(web_server,'POST','/api/ai/grade',{'grading_token':wrong['grading_token'],'content':'fake correct','passed':True})
    assert judged['feedback']['local_passed'] is False and judged['feedback']['conflict']
    assert before==path.read_bytes() and 'fake correct' not in json.dumps(calls)
    _,correct,_=request(web_server,'POST','/api/tasks/D04/sections/D04-def-return/validate',{'content':'def rectangle_area(width,height):\n    return width*height'})
    assert correct['passed'] is True;before=path.read_bytes();provider(monkeypatch)
    _,judged,_=request(web_server,'POST','/api/ai/grade',{'grading_token':correct['grading_token']})
    assert judged['feedback']['local_passed'] is True and judged['feedback']['conflict']
    assert before==path.read_bytes()


@pytest.mark.parametrize('failure',['unconfigured','timeout','http','leak'])
def test_api_failure_is_explicit_and_retryable(web_server,monkeypatch,failure):
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False);token=web_server.grading.add({},'a',{'passed':False})
    if failure!='unconfigured':web_server.ai_session.set_key('test-only-key')
    if failure=='timeout':
        def timeout(*a,**k):raise TimeoutError('network timeout test-only-key')
        monkeypatch.setattr(ai,'_request',timeout)
    elif failure=='http':monkeypatch.setattr(ai,'_request',lambda *a,**k:(401,b'{"key":"test-only-key"}'))
    elif failure=='leak':provider(monkeypatch,{'answer':'return width * height'})
    _,failed,_=request(web_server,'POST','/api/ai/grade',{'grading_token':token})
    assert not failed['ok'] and 'test-only-key' not in json.dumps(failed) and 'width * height' not in json.dumps(failed)
    web_server.ai_session.set_key('test-only-key');provider(monkeypatch)
    _,retried,_=request(web_server,'POST','/api/ai/grade',{'grading_token':token});assert retried['ok']


def test_no_evidence_produces_uncertain_requirements_and_no_location(monkeypatch):
    def insufficient(data,payload):
        data['judgement']='uncertain';data['issues']=[]
        data['requirements']=[{'id':r['id'],'requirement':'真实命令与交付证据符合当前要求','status':'uncertain','explanation':'当前没有源代码或逐项运行证据，无法确认这一要求。','evidence':[]} for r in payload['requirements']]
        data['limitations']=['缺少当前实现代码，不能猜测错误位置。'];return data
    provider(monkeypatch,transform=insufficient)
    f=evaluate({'title':'当前文本','exercise':{'instructions':'说明真实命令与交付证据。'}},'',{'passed':False})
    assert not f['issues'] and '暂无可核查' in f['location']
    assert all(r['status']=='uncertain' and not r['evidence'] for r in f['requirements'])
    assert '缺少当前实现代码' in f['limitations'][0]


def test_declared_multi_file_context_is_snapshot_not_another_assignment(web_server,monkeypatch):
    curriculum=unlock_all(web_server);web_server.ai_session.set_key('test-only-key');calls=provider(monkeypatch)
    ws=web_server.project_root/'learner_workspace/task-manager';(ws/'taskproj').mkdir(parents=True)
    (ws/'taskproj/db.py').write_text('def list_tasks(conn):\n    return []\n# test-only-key',encoding='utf-8')
    (ws/'taskproj/other.py').write_text('UNRELATED_PRIVATE_CONFIG_SENTINEL',encoding='utf-8')
    (ws/'.env').write_text('PRIVATE_ENV_SENTINEL',encoding='utf-8')
    monkeypatch.setattr(web,'run_validation',lambda *a:{'passed':False,'cases':[{'passed':False,'actual':'[]','expected':'list of tasks'}]})
    _,result,_=request(web_server,'POST','/api/tasks/D21/sections/D21-crud-routes/validate',{'content':'def current_handler():\n    pass'})
    assert result.get('grading_token'), result
    record=web_server.grading.records[result['grading_token']]
    declared=next(s for t in curriculum['tasks'] for s in t['lesson'] if s['id']=='D21-crud-routes')['practice']['workspace_deps']
    assert {f['path'] for f in record['context']['files']}==set(declared)-{'taskproj/api.py'}
    old=next(f for f in record['context']['files'] if f['path']=='taskproj/db.py')['content']
    (ws/'taskproj/db.py').write_text('AFTER_SUBMISSION_SENTINEL',encoding='utf-8')
    _,judged,_=request(web_server,'POST','/api/ai/grade',{'grading_token':result['grading_token']})
    assert judged['ok'];payload=json.loads(calls[0]['messages'][-1]['content'])
    assert 'return []' in json.dumps(payload) and 'AFTER_SUBMISSION_SENTINEL' not in json.dumps(payload)
    assert 'PRIVATE_ENV_SENTINEL' not in json.dumps(payload) and 'test-only-key' not in json.dumps(payload)
    assert 'UNRELATED_PRIVATE_CONFIG_SENTINEL' not in json.dumps(payload)
    assert any('缺失' in text for text in judged['feedback']['limitations'])


def test_multi_file_evidence_and_out_of_scope_paths(monkeypatch,tmp_path):
    root=tmp_path/'work';root.mkdir();(root/'dep.py').write_text('def load():\n    return []',encoding='utf-8')
    (tmp_path/'private.py').write_text('PRIVATE_SENTINEL',encoding='utf-8')
    files=grading._snapshot_files(root,['dep.py','../private.py','.env','missing.py'])
    assert files[0]['status']=='available' and files[1]['status']=='unavailable' and files[2]['status']=='unavailable' and files[3]['status']=='missing'
    assert 'PRIVATE_SENTINEL' not in json.dumps(files)
    def use_dependency(data,_):
        data['issues'][0]['evidence']=['file1:2','cases1'];data['issues'][0]['cause']='依赖文件的读取函数始终提供空集合，当前接口没有得到本题要求的数据。';return data
    provider(monkeypatch,transform=use_dependency)
    f=evaluate({'title':'当前接口','exercise':{'instructions':'展示当前任务列表。'},'files':files},'def endpoint():\n    pass',{'passed':False,'cases':[{'passed':False,'actual':'[]','expected':'list of tasks'}]})
    assert f['issues'][0]['evidence'][0]['path']=='dep.py' and f['issues'][0]['evidence'][0]['line']==2
    assert '缺失或不可安全读取' in '\n'.join(f['limitations'])


def test_truncated_files_are_explicit_and_bounded(tmp_path):
    (tmp_path/'big.py').write_bytes(b'a'*(grading.MAX_FILE_BYTES+100))
    files=grading._snapshot_files(tmp_path,['big.py'])
    assert files[0]['truncated'] and len(files[0]['content'])==grading.MAX_FILE_BYTES


def test_legacy_test_context_reads_only_declared_test_file(project,curriculum_data):
    (project/'learner_tests').mkdir();(project/'learner_tests/test_form.py').write_text('# CURRENT_TEST',encoding='utf-8')
    (project/'private.py').write_text('PRIVATE_SENTINEL',encoding='utf-8')
    context=grading.exercise_context(curriculum_data,curriculum_data['exercises'][0],project)
    assert [f['path'] for f in context['files']]==['learner_tests/test_form.py']
    assert 'CURRENT_TEST' in json.dumps(context) and 'PRIVATE_SENTINEL' not in json.dumps(context)
    assert '未声明被测实现路径' in context['scope']


def test_all_requirement_clauses_are_retained():
    text='。'.join(f'当前要求{i}' for i in range(45))
    requirements=grading._requirements({'exercise':{'instructions':text}})
    assert len(requirements)==32
    assert all(f'当前要求{i}' in ''.join(r['text'] for r in requirements) for i in range(45))


def test_all_sections_and_drills_have_server_owned_evidence(web_server, monkeypatch):
    curriculum = unlock_all(web_server)
    monkeypatch.setattr(web, "run_validation", lambda *a: {"passed": False, "checks": [], "stderr": "SyntaxError: test"})
    monkeypatch.setattr(web, "run_action", lambda *a: {"passed": False, "checks": [], "stderr": "environment unavailable"})
    monkeypatch.setattr(web, "run_experiment", lambda section, body: {"passed": False, "mode": body["mode"], "index": body["index"], "stdout": "wrong"})
    kinds, sections, drills = set(), 0, 0
    for task in curriculum["tasks"]:
        for section in task["lesson"]:
            kinds.add(section["practice"]["kind"])
            if section["practice"]["kind"] == "env_action":
                status, result, _ = request(web_server, "POST", "/api/env/action", {"action": section["practice"]["action"], "confirmed": True})
                content = ""
            else:
                content = section["practice"]["starter_content"]
                status, result, _ = request(web_server, "POST", f'/api/tasks/{task["id"]}/sections/{section["id"]}/validate', {"content": content})
            assert status == 200, result
            snapshot = web_server.grading.records[result["grading_token"]]
            assert snapshot["context"]["section"] == section["id"]
            assert snapshot["content"] == content and snapshot["result"]["passed"] is False
            sections += 1
            for index, drill in enumerate(section["practice_first"]["drills"]):
                status, result, _ = request(web_server, "POST", f'/api/tasks/{task["id"]}/sections/{section["id"]}/experiment', {"mode": "drill", "index": index, "content": drill["starter"]})
                assert status == 200, result
                snapshot = web_server.grading.records[result["grading_token"]]
                assert snapshot["context"]["exercise"]["index"] == index
                assert "reference" not in snapshot["context"]["exercise"]
                assert snapshot["content"] == drill["starter"]
                drills += 1
    assert sections == sum(len(t['lesson']) for t in curriculum['tasks'])
    assert drills == sum(len(s['practice_first']['drills']) for t in curriculum['tasks'] for s in t['lesson'])
    assert kinds == {"code", "text", "json", "command", "env_action"}


def test_variation_uses_own_content_and_never_claims_behavior_pass(web_server, monkeypatch):
    variation = {"title": "独立题", "scenario": "独立场景", "instructions": "独立要求", "starter_content": "# 开始", "review_rubric": "独立标准"}
    web_server.variations["v"] = {"task_id": "D04", "section_id": "D04-def-return", "variation": variation}
    before = list(web_server.project_root.rglob('progress.json'))
    _, result, _ = request(web_server, "POST", "/api/ai/variation-submit", {"task_id":"D04", "section_id":"D04-def-return", "variation_id":"v", "content":"raise RuntimeError('must not execute')"})
    assert result["passed"] is None and result["completed"] is False
    record = web_server.grading.records[result["grading_token"]]
    assert record["context"]["exercise"] == variation
    assert before == list(web_server.project_root.rglob('progress.json'))
    status, _, _ = request(web_server, "POST", "/api/ai/variation-submit", {"task_id":"D04", "section_id":"D04-scope", "variation_id":"v", "content":"x"})
    assert status == 400


def test_grade_requires_evidence_and_valid_level(web_server):
    for body in ({"content":"x", "passed":True}, {"grading_token":"missing"}, {"grading_token":"missing", "hint_level":True}):
        status, result, _ = request(web_server, "POST", "/api/ai/grade", body)
        assert status == 400 and not result["ok"]
    status, _, _ = request(web_server, "POST", "/api/ai/grade", {}, Origin="http://evil.example")
    assert status == 403
@pytest.mark.parametrize("exit_code,configured", [(0,True), (1,True), (1,False)])
def test_cli_ai_retains_pytest_exit_and_no_fake_success(project, monkeypatch, capsys, exit_code, configured):
    from learnctl.__main__ import main
    from learnctl import test_runner
    monkeypatch.chdir(project)
    if configured:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-key")
    else:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    calls = provider(monkeypatch, verdict="passed")
    monkeypatch.setattr(test_runner, "run_exercise_capture", lambda *a: {"exit_code":exit_code, "stdout":"pytest output\n", "stderr":""})
    assert main(["test","form","--ai"]) == exit_code
    captured = capsys.readouterr()
    if not configured:
        assert "AI 判题未完成" in captured.err and not calls
    elif exit_code:
        assert "本地验证未通过" in captured.out
    else:
        assert "本地验证通过" in captured.out
    assert "test-only-key" not in captured.out + captured.err

def test_test_process_does_not_inherit_live_credentials():
    assert ai.AiSession().configured() is False


def test_live_provider_transport_is_blocked_even_with_a_test_key():
    with pytest.raises(RuntimeError, match="禁止真实 DeepSeek"):
        ai.chat(session(), [{"role":"user", "content":"test-only"}])


def test_changing_dependency_during_validation_invalidates_its_source_snapshot(tmp_path):
    (tmp_path/'dep.py').write_text('old',encoding='utf-8')
    context={'files':grading._snapshot_files(tmp_path,['dep.py'])}
    (tmp_path/'dep.py').write_text('new',encoding='utf-8')
    grading.check_snapshot(context,tmp_path)
    assert context['files']==[{'path':'dep.py','status':'changed_during_run'}]
    sources,records=grading._evidence(context,'',{'passed':False})
    assert 'file1' not in sources and '验证期间改变' in records['missing1']['detail']


def test_varied_results_remain_authoritative_when_model_prose_disagrees(monkeypatch):
    provider(monkeypatch)
    feedback = evaluate(result={'passed':False,'cases':[{'actual':'6','passed':False},{'actual':'12','passed':False}]})
    assert feedback['reason'] and feedback['local_passed'] is False


def test_current_variation_title_and_requirements_do_not_become_original_assignment(curriculum_data):
    task=curriculum_data['tasks'][3];section=task['lesson'][0]
    variation={'title':'独立变式题','instructions':'检查当前变式条件。','review_rubric':'核对当前结果。'}
    context=grading.lesson_context(task,section,variation)
    assert context['title']=='独立变式题' and context['lesson_title']==section['title']
    assert all('当前' in r['text'] for r in grading._requirements(context))
    assert context['files']==[]


def test_json_and_assignment_secrets_are_redacted():
    value='{"api_key": "not-a-test-key", "token":"another-secret"}\npassword = "third-secret"'
    safe=grading._redact(value,None)
    assert all(secret not in safe for secret in ['not-a-test-key','another-secret','third-secret'])


def test_runtime_evidence_keeps_actual_input_without_expected_answer(monkeypatch):
    def use_run(data,_):
        data['issues'][0]['evidence']=['cases1','submission:2'];return data
    provider(monkeypatch,transform=use_run)
    f=evaluate(result={'passed':False,'cases':[{'input':[2,3],'actual':'0','expected':'PRIVATE_EXPECTED_VALUE','passed':False}]})
    evidence=f['issues'][0]['evidence'][0]['text']
    assert '[2, 3]' in evidence and '实际结果：0' in evidence and 'PRIVATE_EXPECTED_VALUE' not in evidence


def test_requirement_display_does_not_echo_code_or_scalar_example_answers(monkeypatch):
    calls=provider(monkeypatch)
    context={'title':'矩形面积','task':'D04','exercise':{'instructions':'定义 rectangle_area(width, height)，返回 width * height。第一轮不增加输入校验。D06 再补输入校验。','expected_behavior':'12；0；10.0'}}
    f=evaluate(context)
    payload=json.loads(calls[0]['messages'][-1]['content'])
    assert len(payload['requirements'])==2
    assert 'width * height' in payload['requirements'][0]['text']
    assert all('D06' not in r['text'] for r in payload['requirements'])
    assert 'width * height' not in json.dumps(f,ensure_ascii=False)
    assert not any(r['requirement'] in {'12','0','10.0'} for r in f['requirements'])


def test_code_in_a_model_requirement_summary_is_plain_feedback(monkeypatch):
    def malicious(data,_):data['requirements'][0]['requirement']='返回 width * height 作为当前结果。';return data
    provider(monkeypatch,transform=malicious)
    feedback = evaluate()
    assert 'width * height' in feedback['requirements'][0]['requirement']
    assert feedback['local_passed'] is False


def test_failed_checks_and_cases_are_not_double_counted(monkeypatch):
    provider(monkeypatch)
    f=evaluate(result={'passed':False,'cases':[{'passed':False,'actual':'0'}],'checks':[{'passed':False,'name':'same case'}]})
    assert f['evidence']=='依据本次运行：1 个测试用例未通过。'


def test_expected_exception_is_distinct_from_observed_exception(monkeypatch):
    def explain(data,_):
        data['issues'][0]['cause']='本题要求非法值触发 ValueError，实际运行报告的是 TypeError，当前拒绝路径没有满足题面要求。'
        data['issues'][0]['evidence']=['error1','submission:2'];return data
    provider(monkeypatch,transform=explain)
    f=evaluate({'title':'输入校验','exercise':{'instructions':'非法值抛出 ValueError。'}},'def validate(value):\n    raise TypeError',{'passed':False,'errors':['TypeError: wrong type']})
    assert 'ValueError' in f['reason'] and 'TypeError' in f['reason']


def test_model_exception_prose_is_advisory_and_real_exception_evidence_is_preserved(monkeypatch):
    def invent(data,_):
        data['issues'][0]['cause']='本次运行出现 ValueError，当前分支需要重新检查。'
        data['issues'][0]['evidence']=['error1'];return data
    provider(monkeypatch,transform=invent)
    feedback = evaluate({'title':'输入校验','exercise':{'instructions':'非法值抛出 ValueError。'}},'def validate(value):\n    raise TypeError',{'passed':False,'errors':['TypeError: wrong type']})
    assert feedback['reason'] and feedback['local_passed'] is False
    assert feedback['issues'][0]['evidence'][0]['text'] == 'TypeError: wrong type'


def test_model_output_prose_does_not_replace_actual_output_evidence(monkeypatch):
    def invent(data,_):
        data['issues'][0]['cause']='实际返回为2，与本题要求不一致。';data['issues'][0]['evidence']=['cases1'];return data
    provider(monkeypatch,transform=invent)
    feedback = evaluate(result={'passed':False,'cases':[{'passed':False,'input':[2,3],'actual':'0'}]})
    assert feedback['reason'] and feedback['local_passed'] is False
    assert feedback['issues'][0]['evidence'][0]['actual'] == '0'


def test_empty_list_observation_can_be_explained_in_chinese(monkeypatch):
    def explain(data,_):
        data['issues'][0]['cause']='实际返回为空列表，没有展示当前题目要求的数据。';data['issues'][0]['evidence']=['cases1'];return data
    provider(monkeypatch,transform=explain)
    f=evaluate(result={'passed':False,'cases':[{'passed':False,'actual':'[]'}]})
    assert '空列表' in f['reason']


def test_timeout_and_output_limit_remain_visible_as_real_evidence():
    sources,records=grading._evidence({},'',{'passed':False,'timeout':True,'output_limited':True,'exit_code':1})
    evidence=grading._references(['run'],sources,records)
    assert '时间限制' in evidence[0]['text'] and '长度限制' in evidence[0]['text'] and '退出码：1' in evidence[0]['text']


@pytest.mark.parametrize('text', [
    '缺少 return 语句，导致当前执行路径没有结果。',
    '检查 raise 关键字是否位于本题指定的分支。',
    '检查 assert 语句所验证的条件。',
    '这里需要比较 HTTP/JSON 的解析结果。',
    '本节介绍 Python/API/AI 的数据流概念。',
    '检查当前分支是否读取了本题的输入。',
    '检查 `return` 语句是否使用当前输入。',
    '先检查本题输入。\n再跟踪当前返回路径。',
])
def test_normal_chinese_diagnoses_and_imperative_hints_are_accepted(monkeypatch, text):
    def normalize(data, _):
        data['issues'][0]['cause'] = text
        data['issues'][0]['hints'][0] = text
        return data
    calls = provider(monkeypatch, transform=normalize)
    f = evaluate()
    assert f['reason'] == f['hint'] and '\n' not in f['reason']
    assert f['local_passed'] is False and len(calls) == 1


def test_function_references_do_not_become_style_failures(monkeypatch):
    def signature(data, _):
        data['requirements'][0]['requirement'] = '保持 `rectangle_area(width, height)` 的函数接口。'
        data['issues'][0]['cause'] = '`rectangle_area(width, height)` 的 return 语句只提供固定结果，没有体现当前输入。'
        return data
    provider(monkeypatch, transform=signature)
    f = evaluate(content='def rectangle_area(width, height):\n    return 0')
    assert 'rectangle_area(width, height)' in f['reason']
    other = evaluate(content='def unrelated(a):\n    return 0')
    assert other['local_passed'] is False


@pytest.mark.parametrize('text', [
    '请使用 `return width * height` 即可。',
    '请填写正确表达式 width/height。',
    '请填写正确表达式 WIDTH/HEIGHT。',
    '请返回 widthHTTP/JSONheight 作为完整结果。',
    '请执行 return 语句value 得到结果。',
    '请执行 `os.system()`。',
    '请执行 f(7) 得到完整结果。',
    '请填写以下代码。\nreturn a',
    '请填写以下代码。\nwhile True: pass',
    '请填写以下代码。\n```python\nreturn a\n```',
])
def test_code_fragments_do_not_override_objective_results(monkeypatch, text):
    def unsafe(data, _): data['issues'][0]['cause'] = text; return data
    calls = provider(monkeypatch, transform=unsafe)
    feedback = evaluate()
    assert feedback['local_passed'] is False and len(calls) == 1


@pytest.mark.parametrize('omission', ['requirement', 'label', 'explanation', 'evidence', 'requirements_field'])
def test_missing_analysis_is_honestly_uncertain_without_losing_safe_diagnosis(monkeypatch, omission):
    def incomplete(data, _):
        if omission == 'requirement': data['requirements'].pop()
        elif omission == 'requirements_field': del data['requirements']
        else: del data['requirements'][0][{'label':'requirement','explanation':'explanation','evidence':'evidence'}[omission]]
        return data
    provider(monkeypatch, transform=incomplete)
    f = evaluate()
    assert len(f['requirements']) == 2 and any(r['status'] == 'uncertain' for r in f['requirements'])
    assert f['reason'] and f['limitations'] and f['local_passed'] is False


def test_missing_requirements_cannot_produce_a_pass_claim(monkeypatch):
    def incomplete(data, _): data['requirements'].pop(); return data
    provider(monkeypatch, verdict='passed', transform=incomplete)
    f = evaluate(result={'passed': True})
    assert f['advisory'] == 'uncertain' and 'AI 未发现明显问题' not in f['summary']
    assert any(r['status'] == 'uncertain' for r in f['requirements'])


def test_met_from_only_failed_evidence_is_downgraded_not_a_format_failure(monkeypatch):
    def failed_basis(data, _):
        data['requirements'][1]['status'] = 'met'
        data['requirements'][1]['evidence'] = ['cases1']
        data['issues'][0]['requirement_ids'] = ['r1']
        return data
    provider(monkeypatch, transform=failed_basis)
    f = evaluate()
    assert f['requirements'][1]['status'] == 'uncertain' and f['reason']
    assert '不能据此确认' in f['requirements'][1]['explanation']


def test_grading_format_rejection_remains_explicit_without_blind_retry(web_server, monkeypatch):
    web_server.ai_session.set_key('test-only-key')
    token = web_server.grading.add({'exercise': {'instructions':'核对当前输入。'}}, 'def f(a):\n    return 0', {'passed': False})
    def invalid(data, _):
        data['judgement'] = 'unsupported'
        return data
    provider(monkeypatch, transform=invalid)
    _, failed, _ = request(web_server, 'POST', '/api/ai/grade', {'grading_token':token})
    assert not failed['ok'] and failed['error_code'] == 'grading_format'
    assert failed['retryable'] is False and '请重试' not in failed['error']
    assert 'test-only-key' not in json.dumps(failed) and 'return a' not in failed['error']


def test_public_status_identifies_loaded_validation_revision(web_server):
    _, status, _ = request(web_server, 'GET', '/api/ai/status')
    assert status['grading_analysis_version'] == 2
    assert status['grading_validation_revision'] == 4


@pytest.mark.parametrize('text', [
    '核对 GET/POST 的响应内容与请求参数。',
    '分别检查 GET/POST/PATCH/DELETE 的状态与响应。',
    '请求头需要使用 application/json 这一媒体类型。',
    '检查 text/plain 与 text/html 的内容类别。',
    'Mock 响应还需要支持 with/read 这两个接口概念。',
    '检查 URL/timeout 这两个已声明的请求参数。',
])
def test_http_notation_is_terminology_not_a_solution_expression(monkeypatch, text):
    def describe(data, _): data['requirements'][0]['requirement']=text; return data
    provider(monkeypatch, transform=describe)
    f=evaluate()
    assert f['requirements'][0]['status']=='unmet' and text == f['requirements'][0]['requirement']


@pytest.mark.parametrize('text', [
    '请使用 WIDTH/HEIGHT 作为结果。',
    '请返回 widthGET/POSTheight 作为结果。',
    '请返回 widthapplication/jsonheight 作为结果。',
    '请填写 x = application/json 得到结果。',
])
def test_http_and_expression_fragments_are_text_only(monkeypatch, text):
    def unsafe(data, _): data['issues'][0]['cause']=text; return data
    provider(monkeypatch, transform=unsafe)
    feedback = evaluate()
    assert feedback['reason'] == text and feedback['local_passed'] is False


def test_request_prompt_lists_only_actual_evidence_ids(monkeypatch):
    calls=provider(monkeypatch)
    evaluate()
    message=calls[0]['messages'][0]['content']
    assert '本次已有运行记录ID：' in message and 'cases1' in message
    assert '不写数组下标' in message and '不写行号区间' in message


@pytest.mark.parametrize('value', [
    'return 的作用是将结果交给调用方。',
    '输出没有通过 return 返回到调用方。',
    '函数只计算了 width + height，却没有返回值。',
    '定义函数，接收两个参数，并返回两数相乘的结果。',
    '要让 rectangle_area(3,4) 得到 12，函数体里缺少哪个关键字或语句？',
])
def test_previous_style_false_positives_are_usable_feedback(monkeypatch, value):
    def describe(data, _):
        data['requirements'][0]['requirement'] = value
        data['issues'][0]['cause'] = value
        data['issues'][0]['hints'][2] = value
        return data
    calls = provider(monkeypatch, transform=describe)
    feedback = evaluate()
    assert feedback['reason'] == value and feedback['local_passed'] is False
    assert len(calls) == 1


@pytest.mark.parametrize('field', ['requirement', 'explanation', 'cause', 'hint', 'limitation'])
def test_model_sensitive_values_are_redacted_without_discarding_guidance(monkeypatch, field):
    text = '请核对 test-only-key；Bearer abc-private；api_key=another-private'
    def sensitive(data, _):
        if field in {'requirement', 'explanation'}: data['requirements'][0][field] = text
        elif field == 'cause': data['issues'][0]['cause'] = text
        elif field == 'hint': data['issues'][0]['hints'][0] = text
        else: data['limitations'] = [text]
        return data
    provider(monkeypatch, transform=sensitive)
    feedback = evaluate()
    output = json.dumps(feedback, ensure_ascii=False)
    assert all(secret not in output for secret in ['test-only-key', 'abc-private', 'another-private'])
    assert '已隐藏' in output and feedback['local_passed'] is False


def test_long_model_explanation_is_honestly_truncated_not_a_style_failure(monkeypatch):
    def verbose(data, _): data['issues'][0]['cause'] = '当前提交需要核对返回路径。' * 40; return data
    provider(monkeypatch, transform=verbose)
    feedback = evaluate()
    assert len(feedback['reason']) < 300 and '内容已截断' in feedback['reason']


def test_failure_diagnostics_identify_field_without_submission_or_model_text(web_server, monkeypatch):
    web_server.ai_session.set_key('test-only-key')
    token = web_server.grading.add({'task':'D04', 'section':'D04-def-return', 'exercise': {'instructions':'核对当前提交。'}}, 'PRIVATE_SUBMISSION', {'passed':False})
    def invent(data, _): data['issues'][0]['cause'] = ['private-text-test-only-key']; return data
    provider(monkeypatch, transform=invent)
    _, failure, _ = request(web_server, 'POST', '/api/ai/grade', {'grading_token':token})
    assert not failure['ok'] and failure['error_code'] == 'grading_format'
    _, report, _ = request(web_server, 'GET', '/api/ai/grading-diagnostics')
    entry = report['diagnostics'][-1]
    assert entry['id'] == failure['diagnostic_id'] and entry['field'] == 'issues[0].cause'
    assert entry['rule'] == 'text_type' and entry['validation_revision'] == 4
    assert entry['task'] == 'D04' and entry['section'] == 'D04-def-return'
    encoded = json.dumps(report)
    assert all(value not in encoded for value in [token, 'PRIVATE_SUBMISSION', 'private-text', 'test-only-key'])


def test_api_returns_partial_analysis_when_issue_citations_are_unverifiable(web_server, monkeypatch):
    web_server.ai_session.set_key('test-only-key')
    token = web_server.grading.add({'exercise': {'instructions': '核对当前提交。'}}, 'def f():\n    return 0', {'passed': False})
    def invent(data, _):
        data['issues'][0]['evidence'] = ['submission:999', 'submission:2']
        return data
    calls = provider(monkeypatch, transform=invent)
    _, response, _ = request(web_server, 'POST', '/api/ai/grade', {'grading_token': token})
    assert response['ok'] and response['feedback']['reason'] and response['feedback']['hint']
    assert [item['id'] for item in response['feedback']['issues'][0]['evidence']] == ['submission:2']
    assert response['feedback']['limitations'] and response['feedback']['local_passed'] is False
    assert not web_server.grading.diagnostic_snapshot() and len(calls) == 1


def test_diagnostic_metadata_is_bounded_expiring_and_not_persisted(monkeypatch):
    def malformed(data, _): data['judgement'] = 'unsupported'; return data
    provider(monkeypatch, transform=malformed)
    store = grading.GradingStore()
    token = store.add({'exercise':{'instructions':'核对当前提交。'}}, 'a\nb', {'passed':False})
    for _ in range(35):
        with pytest.raises(grading.GradingOutputError): store.evaluate(token, session(), 1)
    assert len(store.diagnostic_snapshot()) == 32
    store.diagnostics[0]['_created'] -= 601
    assert len(store.diagnostic_snapshot()) == 31


def test_grading_prompt_prefers_guidance_without_a_zero_snippet_promise(monkeypatch):
    calls = provider(monkeypatch)
    evaluate()
    prompt = calls[0]['messages'][0]['content']
    assert '尽量不直接给标准答案' in prompt
    assert '可引用学生提交' in prompt and '错误原因' in prompt


def test_received_revision2_d04_reply_replays_without_style_failure(monkeypatch, curriculum_data):
    fixture = json.loads((Path(__file__).parent / 'fixtures/grading_d04_received_reply.json').read_text(encoding='utf-8'))
    task = next(task for task in curriculum_data['tasks'] if task['id'] == 'D04')
    section = next(section for section in task['lesson'] if section['id'] == 'D04-def-return')
    calls = provider(monkeypatch, response=fixture['analysis'])
    store = grading.GradingStore()
    token = store.add(grading.lesson_context(task, section), fixture['submission'], fixture['local_result'])
    feedbacks = [store.evaluate(token, session(), level) for level in (1,2,3)]
    assert len(calls) == 1
    assert all(item['local_passed'] is False for item in feedbacks)
    assert all([requirement['id'] for requirement in item['requirements']] == ['r1','r2'] for item in feedbacks)
    assert 'None' in feedbacks[0]['reason'] and 'return' in feedbacks[0]['reason']
    assert 'rectangle_area(3,4)' in feedbacks[2]['hint']
    assert not store.diagnostic_snapshot()

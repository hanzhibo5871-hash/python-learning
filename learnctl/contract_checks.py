"""Observable, section-specific behavior checks for the practice-first revision.

The cases are authored by the course, not executable input supplied by a browser.
Every displayed actual value is obtained from the learner's running implementation.
Fixtures supply inputs/infrastructure only; project dependencies come from workspace.
"""
from __future__ import annotations

import ast
import json
from typing import Any


def value_case(expression: str, expected: Any, label: str = '') -> dict[str, Any]:
    return {'expression': expression, 'expected_value': repr(expected), 'label': label or expression.replace('M.', '')}


def error_case(expression: str, error: str, label: str = '') -> dict[str, Any]:
    return {'expression': expression, 'error': error, 'label': label or expression.replace('M.', '')}


def behavior(cases: list[dict[str, Any]], *, setup: str = '', module: str = 'main',
             file: str = 'main.py', scaffolds: list[tuple[str, str]] | None = None):
    def validate(code: str, ctx: Any, section: dict[str, Any]) -> dict[str, Any]:
        from . import practice as p
        ctx.write(file, code)
        for path, source in scaffolds or []:
            ctx.write_scaffold(path, source)
        harness = '\n'.join([
            'import json, math, inspect, typing, asyncio, sqlite3, os',
            'from pathlib import Path',
            f'import {module} as M', setup,
            f'cases = {cases!r}',
            'results = []',
            'for case in cases:',
            "    expected = case.get('expected_value', case.get('error', ''))",
            '    try:',
            "        value = eval(case['expression'])",
            '        actual = repr(value)',
            "        passed = 'error' not in case and value == eval(case['expected_value'])",
            '    except Exception as error:',
            "        actual = type(error).__name__ + ': ' + str(error)",
            "        passed = 'error' in case and isinstance(error, eval(case['error']))",
            "    results.append({'name': case['label'], 'input': case['expression'].replace('M.', ''),",
            "                    'expected': expected, 'actual': actual, 'passed': passed,",
            "                    'detail': '' if passed else '对照输入、预期结果和实际结果检查本节实现。'})",
            "Path('_result.json').write_text(json.dumps(results, ensure_ascii=False), encoding='utf-8')",
        ])
        proc, checks = p._run_harness(ctx, harness, '_result.json')
        result = p._finalize(checks, proc)
        # A result file left by a failing process must not count as success.
        if proc.get('exit_code') != 0 or proc.get('timeout'):
            result['passed'] = False
        result['cases'] = [c for c in checks if 'actual' in c]
        return result
    return validate


HTTP_SETUP = '''
from urllib.request import Request
from urllib.error import HTTPError
seen = []
class Response:
    def __init__(self, body=b'{"ok": true}', status=200):
        self.body, self.status, self.closed = body, status, False
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True
    def read(self): return self.body
responses = []
def opener(request, **kwargs):
    seen.append((request, kwargs))
    response = Response()
    responses.append(response)
    return response
def timed_out(request, **kwargs):
    seen.append((request, kwargs))
    raise TimeoutError('模拟超时')
'''


def _pytest_real(code: str, ctx: Any, section: dict[str, Any]) -> dict[str, Any]:
    from . import practice as p
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {'passed': False, 'checks': [{'name': '测试语法', 'passed': False, 'detail': str(exc)}], 'stdout': '', 'stderr': str(exc), 'exit_code': None}
    tests = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')]
    if not tests or not any(isinstance(n, ast.Assert) for n in ast.walk(tree)):
        return {'passed': False, 'checks': [{'name': '至少一个 test_ 函数和行为断言', 'passed': False, 'detail': '顶层 assert 或只有 pass 不算运行测试。'}], 'stdout': '', 'stderr': '', 'exit_code': None}
    fixtures = []
    if section['id'] == 'D15-mock':
        fixtures = [('client.py', p._API_CLIENT_REF)]
        if not any(isinstance(n, ast.Call) and (getattr(n.func, 'id', '') == 'patch' or getattr(n.func, 'attr', '') == 'patch') for n in ast.walk(tree)):
            return {'passed': False, 'checks': [{'name': '用 patch 隔离网络', 'passed': False, 'detail': '请按照本题要求替换 client.urllib.request.urlopen。'}], 'stdout': '', 'stderr': '', 'exit_code': None}
    if section['id'] == 'D15-api':
        fixtures = [('conftest.py', 'import pytest\nfrom app import app as example_app\n@pytest.fixture\ndef app(): return example_app\n'), ('app.py', "from fastapi import FastAPI\napp=FastAPI()\n@app.get('/health')\ndef health(): return {'status':'ok'}\n@app.post('/tasks',status_code=201)\ndef create(body:dict): return {'id':1,**body}\n")]
    result = p._pytest_validator('test_submission.py', fixtures)(code, ctx, section)
    if result.get('passed') and section['id'] == 'D15-assert':
        # Check the actual function too, rather than accepting tests of unrelated 1+1.
        ctx.write('main.py', code)
        result2 = behavior([value_case('M.add_tax(100)', 113), value_case('M.add_tax(0)', 0), value_case('M.add_tax(200)', 226)])(code, ctx, section)
        result['checks'] += result2['checks']
        result['cases'] = result2['cases']
        result['passed'] = result2['passed']
    return result


def validate_contract(section: dict[str, Any], submission: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    def add(name: str, passed: bool, detail: str = '') -> None:
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})
    try:
        data = json.loads(submission)
    except json.JSONDecodeError as exc:
        add('JSON 可解析', False, f'第 {exc.lineno} 行：{exc.msg}')
        data = None
    if not isinstance(data, dict):
        add('顶层为 JSON 对象', False, '不能提交数组、数字或 null。')
    else:
        task = data.get('task')
        if not isinstance(task, dict):
            add('task 为对象', False)
        else:
            input_data, output = task.get('input'), task.get('output')
            add('task.input.title 为 string', isinstance(input_data, dict) and input_data.get('title') == 'string')
            add('task.output 含整数 id、字符串 title、布尔 done', isinstance(output, dict) and type(output.get('id')) is int and isinstance(output.get('title'), str) and type(output.get('done')) is bool)
        errors = data.get('errors')
        add('errors 声明 empty_title=422、unknown_id=404', isinstance(errors, dict) and errors.get('empty_title') == 422 and errors.get('unknown_id') == 404)
        if section['id'] == 'D18-api-contract':
            endpoints = data.get('endpoints')
            add('endpoints 为对象数组', isinstance(endpoints, list) and all(isinstance(e, dict) for e in endpoints))
            pairs = {(e.get('method'), e.get('path')) for e in endpoints or [] if isinstance(e, dict) and isinstance(e.get('method'), str) and isinstance(e.get('path'), str)} if isinstance(endpoints, list) else set()
            for method, path in [('GET','/'), ('GET','/health'), ('GET','/api/tasks'), ('POST','/api/tasks'), ('PATCH','/api/tasks/{task_id}/done'), ('DELETE','/api/tasks/{task_id}')]:
                add(f'{method} {path}', (method,path) in pairs)
    passed = bool(checks) and all(c['passed'] for c in checks)
    return {'passed': passed, 'checks': checks, 'stdout': '', 'stderr': '', 'exit_code': None}


def register(registry: dict[str, Any]) -> None:
    from . import practice as p
    v, e = value_case, error_case
    specs: dict[str, list[dict[str, Any]]] = {
        'D02-numbers': [v('M.divide_parts(17,5)', (3,2)),v('M.divide_parts(-7,2)',(-4,1)),e('M.divide_parts(1,0)','ValueError')],
        'D02-bool-none': [v('M.describe_value(None)','missing'),v("M.describe_value('')",'empty text'),v('M.describe_value(0)','present'),v('M.describe_value([0])','present')],
        'D02-string-methods': [v("M.format_tags(' a,,b ')",'a / b'),v("M.format_tags('  ')",'无标签'),v("M.format_tags(' py, test, , api ')",'py / test / api')],
        'D03-if': [v('M.classify_score(90)','A'),v('M.classify_score(60)','B'),v('M.classify_score(59)','C'),e('M.classify_score(-1)','ValueError')],
        'D03-while': [v('M.countdown(3)',[3,2,1]),v('M.countdown(0)',[]),v('M.countdown(-2)',[])],
        'D03-break-continue': [v('M.first_large([None,2,8,10],7)',8),v('M.first_large([1,3],7)',None),v('M.first_large([],7)',None)],
        'D03-enumerate-zip': [v("M.pair_scores(['A','B'],[90,80])",[{'name':'A','score':90,'position':1},{'name':'B','score':80,'position':2}]),v('M.pair_scores([],[])',[]),e("M.pair_scores(['A'],[1,2])",'ValueError')],
        'D03-comprehension': [v('M.summarize_numbers([1,2,2,3])',{'even_squares':[4,4],'unique':{1,2,3},'by_value':{1:1,2:4,3:9}}),v('M.summarize_numbers([])',{'even_squares':[],'unique':set(),'by_value':{}})],
        'D04-def-return': [v('M.rectangle_area(3,4)',12),v('M.rectangle_area(0,4)',0),v('M.rectangle_area(2.5,4)',10.0)],
        'D04-default-keyword': [v("M.make_message('林')",'你好，林!'),v("M.make_message('林',prefix='早上好',suffix='。')",'早上好，林。')],
        'D04-scope': [v("M.read_config('A')",'A'),v("M.read_config('B')",'B')],
        'D04-type-hints': [v("M.format_user('林',20)",'林: 20'),v("M.format_user('A',0)",'A: 0'),v("typing.get_type_hints(M.format_user)",{'name':str,'age':int,'return':str})],
        'D05-list-tuple': [v('M.normalize_pair([1,2])',(1,2)),e('M.normalize_pair([1])','ValueError')],
        'D05-unpacking': [v("M.merge_task({'title':'旧'},{'title':'新'})",{'title':'新'}),v('M.split_edges([1,2,3,4])',(1,[2,3],4)),e('M.split_edges([1])','ValueError')],
        'D05-traversal': [v("M.titles([{'title':'A'},{},{'title':'C'}])",['A','未命名','C']),v('M.titles([])',[])],
        'D05-comprehensions': [v("M.build_indexes(['Py','py',''])",{'lengths':{'Py':2,'py':2},'unique':{'py'}}),v('M.build_indexes([])',{'lengths':{},'unique':set()})],
        'D06-exception-types': [v("M.error_label('convert')",'ValueError'),v("M.error_label('key')",'KeyError'),v("M.error_label('index')",'IndexError'),e("M.error_label('other')",'ValueError')],
        'D06-try-except': [v("M.parse_int('42')",42),v("M.parse_int('x')",None),e('M.parse_int(None)','TypeError')],
        'D06-raise': [v("M.require_nonempty(' ok ')",'ok'),e("M.require_nonempty('  ')",'ValueError'),e('M.require_nonempty(None)','ValueError'),e('M.require_nonempty(3)','TypeError')],
        'D06-custom': [v("M.parse_name(' 林 ')",'林'),e("M.parse_name('  ')",'M.InputError'),v('issubclass(M.InputError,ValueError)',True)],
        'D07-import': [v("M.show_path('a.txt')",('.txt',3)),v("M.show_path('data/a.json')",('.json',3))],
        'D08-json-read': [v("M.read_task('{\"title\":\"学习\"}')",{'title':'学习'}),e("M.read_task('[]')",'ValueError'),e("M.read_task('{\"title\":\"  \"}')",'ValueError'),e("M.read_task('{bad}')",'json.JSONDecodeError')],
        'D09-parser': [v('M.parse_args([]).limit',10),v("M.parse_args(['--limit','3','--verbose']).limit",3),v("M.parse_args(['--verbose']).verbose",True)],
        'D10-env': [v("M.get_setting('A','default',{'A':'value'})",'value'),v("M.get_setting('A','default',{'A':''})",'default'),v("M.get_setting('A','default',{})",'default')],
        'D10-convert': [v("M.parse_bool('true')",True),v("M.parse_bool('false')",False),v("M.parse_port('8080')",8080),e("M.parse_bool('maybe')",'ValueError'),e("M.parse_port('0')",'ValueError'),e("M.parse_port('65536')",'ValueError')],
        'D17-coroutine': [v('asyncio.run(M.fetch_value(3))',3),v('asyncio.run(M.fetch_value(0))',0)],
        'D17-gather': [v('asyncio.run(M.run_all([1,2,3]))',[1,2,3]),v('asyncio.run(M.run_all([]))',[])],
        'D17-boundary': [v('asyncio.run(M.safe_call())','invalid-input')],
    }
    # Type objects need source expressions, not their non-evaluable repr.
    specs['D04-type-hints'][-1]['expected_value'] = "{'name': str, 'age': int, 'return': str}"
    for sid, cases in specs.items():
        registry[sid] = behavior(cases)
    registry['D07-stdlib'] = behavior([v("M.read_metadata('meta.json')",'林'),e("M.read_metadata('bad.json')",'ValueError'),e("M.read_metadata('missing.json')",'FileNotFoundError')],
        scaffolds=[('meta.json','{"name":"林"}'),('bad.json','[]')])
    registry['D08-pathlib'] = behavior([v("M.list_json(Path('files'))",['a.json','b.json']),e("M.list_json(Path('missing'))",'FileNotFoundError')],setup="Path('files/nested.json').mkdir(parents=True)\nPath('files/a.json').write_text('{}')\nPath('files/b.json').write_text('{}')\nPath('files/a.txt').write_text('x')")
    registry['D08-utf8'] = behavior([v("M.round_trip(Path('note.txt'),'你好\\n世界')",'你好\n世界'),v("Path('note.txt').read_text(encoding='utf-8')",'你好\n世界')])
    registry['D12-request'] = behavior([v("M.fetch_text('https://example.test',opener)",'{"ok": true}'),v("seen[0][0].get_method()",'GET'),v('len(seen)',1),v('responses[0].closed',True)],setup=HTTP_SETUP)
    registry['D12-post'] = behavior([v("M.post_json('https://example.test',{'title':'学习'},opener)",{'ok':True}),v("json.loads(seen[0][0].data)",{'title':'学习'}),v("seen[0][0].get_method()",'POST'),v("seen[0][0].get_header('Content-type')",'application/json'),v('len(seen)',1),v('responses[0].closed',True)],setup=HTTP_SETUP)
    registry['D12-response'] = behavior([v('M.parse_response(Response())',{'ok':True}),e("M.parse_response(Response(b'{bad}'))",'json.JSONDecodeError'),e("M.parse_response(Response(b'{}',404))",'RuntimeError')],setup=HTTP_SETUP)
    registry['D12-timeout'] = behavior([v("M.fetch_with_timeout('https://example.test',opener,timeout=3)",'{"ok": true}'),v("seen[0][1]['timeout']",3),e("M.fetch_with_timeout('https://example.test',timed_out,timeout=0.1)",'TimeoutError'),v('len(seen)',2)],setup=HTTP_SETUP)
    registry['D13-route'] = behavior([v("client.get('/tasks/7').json()",{'id':7}),v("client.get('/tasks').json()",{'limit':20}),v("client.get('/tasks?limit=3').json()",{'limit':3}),v("client.get('/tasks/no').status_code",422)],setup='from fastapi.testclient import TestClient\nclient=TestClient(M.app)')
    registry['D14-model'] = behavior([v("M.TaskIn(title='学习').model_dump()",{'title':'学习','priority':0}),e('M.TaskIn(priority=1)','pydantic.ValidationError'),e("M.TaskIn(title='x',priority='bad')",'pydantic.ValidationError')],setup='import pydantic')
    registry['D14-service'] = behavior([v("M.create_task(repo,' 学习 ')",{'id':1,'title':'学习'}),e("M.create_task(repo,'   ')",'ValueError'),v("repo.calls",['学习'])],setup="class Repo:\n    def __init__(self): self.calls=[]\n    def add(self,title):\n        self.calls.append(title)\n        return {'id':1,'title':title}\nrepo=Repo()")
    registry['D14-errors'] = behavior([v('M.get_or_404(repo,1)',{'id':1}),e('M.get_or_404(repo,9)','fastapi.HTTPException'),v('missing_status()',404)],setup="import fastapi\nclass Repo:\n    def get(self,task_id): return {'id':1} if task_id==1 else None\nrepo=Repo()\ndef missing_status():\n    try: M.get_or_404(repo,9)\n    except fastapi.HTTPException as error: return error.status_code")
    registry['D14-deps'] = behavior([v("client.get('/tasks').json()",[{'title':'真实数据'}]),v("override_result()",[{'title':'测试数据'}])],setup="from fastapi.testclient import TestClient\nclient=TestClient(M.app)\ndef override_result():\n    M.app.dependency_overrides[M.get_repo]=lambda: [{'title':'测试数据'}]\n    try: return client.get('/tasks').json()\n    finally: M.app.dependency_overrides.clear()")
    for sid in ['D15-assert','D15-fixture','D15-mock','D15-api']:
        registry[sid] = _pytest_real
    registry['D17-timeout'] = behavior([v('asyncio.run(M.run_with_timeout(1))','done'),e('asyncio.run(M.run_with_timeout(0.001))','TimeoutError'),v('asyncio.run(check_cancel())',True)],setup="async def check_cancel():\n    closed=[]\n    async def controlled():\n        try: await asyncio.sleep(10)\n        finally: closed.append(True)\n    old=M.slow\n    M.slow=controlled\n    try:\n        try: await M.run_with_timeout(0.001)\n        except TimeoutError: pass\n    finally: M.slow=old\n    return closed==[True]")
    # Project checks must follow the progressive artifact chain, not the final app.
    registry['D21-crud-routes'] = p._ast_validator({'file':'taskproj/api.py','checks':[
        ('TaskIn 和 Task 模型',lambda t: 'title' in p._class_fields(t,'TaskIn') and {'id','title','done'} <= set(p._class_fields(t,'Task'))),
        ('健康与 CRUD 路由',lambda t: {('GET','/health'),('GET','/api/tasks'),('POST','/api/tasks'),('PATCH','/api/tasks/{task_id}/done'),('DELETE','/api/tasks/{task_id}')} <= set(p._route_paths(t))),
        ('未知 ID 返回 404',lambda t:p._func_raises_http(t,None,404))]})
    registry['D21-static'] = p._ast_validator({'file':'taskproj/api.py','checks':[
        ('GET / 页面入口',lambda t:('GET','/') in p._route_paths(t)),
        ('保留 API 列表路由',lambda t:('GET','/api/tasks') in p._route_paths(t)),
        ('页面通过 FileResponse 返回',lambda t:p._has_call(t,'FileResponse'))]})

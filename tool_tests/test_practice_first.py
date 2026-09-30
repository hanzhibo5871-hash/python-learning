from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from conftest import REPOSITORY, request, section_of
from learnctl.curriculum import load_curriculum, validate_curriculum
from learnctl.errors import DataError, UsageError
from learnctl.experiments import run_experiment
from learnctl.practice import validate_code, validate_json

DATA = json.loads((REPOSITORY / 'data/curriculum.json').read_text(encoding='utf-8'))
SECTIONS = {s['id']: s for t in DATA['tasks'] for s in t['lesson']}
CARDS = [(s['id'], i, c) for s in SECTIONS.values() for i,c in enumerate(s['practice_first']['cards'])]
DRILLS = [(s['id'], i, c) for s in SECTIONS.values() for i,c in enumerate(s['practice_first']['drills'])]


def test_all_28_tasks_have_short_practice_and_safe_prerequisites():
    r = validate_curriculum(copy.deepcopy(DATA))
    assert len(r['tasks']) == 28
    assert len(SECTIONS) == 146
    assert len(DRILLS) > 100
    for s in SECTIONS.values():
        brief=s['practice_first']
        assert brief['goal'] and len(brief['rules']) <= 3
    assert SECTIONS['D13-lifecycle']['optional'] is True
    assert '不要求类型判断或抛异常' in SECTIONS['D04-def-return']['practice']['instructions']
    assert 'and' in SECTIONS['D03-if']['practice_first']['cards'][0]['code']


def test_future_and_optional_prerequisites_are_rejected():
    r=copy.deepcopy(DATA)
    r['tasks'][3]['lesson'][0]['practice_first']['prerequisites']=['D17-coroutine']
    with pytest.raises(DataError,match='尚未教授'):
        validate_curriculum(r)
    r=copy.deepcopy(DATA)
    r['tasks'][5]['lesson'][0]['practice_first']['prerequisites']=['D05-iterators-generators']
    with pytest.raises(DataError,match='不得依赖选修'):
        validate_curriculum(r)


@pytest.mark.parametrize('sid,index,card',CARDS,ids=[f'{sid}-{i}' for sid,i,_ in CARDS])
def test_every_bridge_card_really_runs(sid,index,card):
    result=run_experiment(SECTIONS[sid],{'mode':'card','index':index})
    assert result['passed'], (sid,index,result)
    assert result['completed'] is False


@pytest.mark.parametrize('sid,index,drill',DRILLS,ids=[f'{sid}-{i}' for sid,i,_ in DRILLS])
def test_every_extra_exercise_has_verified_reference_output(sid,index,drill):
    result=run_experiment(SECTIONS[sid],{'mode':'drill','index':index,'content':drill['reference']})
    assert result['passed'], (sid,index,result)


@pytest.mark.parametrize('sid,index,drill',DRILLS,ids=[f'{sid}-{i}' for sid,i,_ in DRILLS])
def test_extra_exercise_requires_a_meaningful_edit(sid,index,drill):
    result=run_experiment(SECTIONS[sid],{'mode':'drill','index':index})
    assert not result['passed'], (sid,index,'Unedited starter already passes')


def test_experiments_no_progress_changes_and_solutions_not_published(web_server):
    status,payload,_=request(web_server,'GET','/api/tasks/D03')
    assert status==200
    s=next(s for s in payload['task']['lesson']['sections'] if s['id']=='D03-if')
    assert all('reference' not in d for d in s['practice_first']['drills'])
    progress=web_server.project_root/'.learn'/'progress.json'
    before=progress.read_bytes() if progress.exists() else None
    status,result,_=request(web_server,'POST','/api/tasks/D03/sections/D03-if/experiment',{'mode':'card','index':0})
    assert status==200 and result['passed'] and not result['completed']
    assert (progress.read_bytes() if progress.exists() else None)==before


def test_experiment_rejects_commands_bad_indexes_and_large_payload():
    with pytest.raises(UsageError): run_experiment(SECTIONS['D01-detect'],{'mode':'example','index':0})
    with pytest.raises(UsageError): run_experiment(SECTIONS['D03-if'],{'mode':'card','index':True})
    with pytest.raises(UsageError): run_experiment(SECTIONS['D03-if'],{'mode':'card','index':999})
    with pytest.raises(UsageError): run_experiment(SECTIONS['D03-if'],{'mode':'card','index':0,'content':'#' * 40000})


def test_real_syntax_error_is_displayed_not_marked_success():
    r=run_experiment(SECTIONS['D03-if'],{'mode':'card','index':0,'content':'if True\n    print(1)'})
    assert not r['passed'] and 'SyntaxError' in r['stderr']


SOLUTIONS = {
    'D02-numbers': "def divide_parts(total,size):\n    if size==0: raise ValueError('zero')\n    return total//size,total%size\n",
    'D02-bool-none': "def describe_value(value):\n    if value is None: return 'missing'\n    if value=='': return 'empty text'\n    return 'present'\n",
    'D02-string-methods': "def format_tags(raw):\n    tags=[p.strip() for p in raw.strip().split(',') if p.strip()]\n    return ' / '.join(tags) if tags else '无标签'\n",
    'D03-if': "def classify_score(score):\n    if score<0: raise ValueError('negative')\n    if score>=90: return 'A'\n    if score>=60: return 'B'\n    return 'C'\n",
    'D03-comprehension': "def summarize_numbers(values):\n    return {'even_squares':[x*x for x in values if x%2==0],'unique':set(values),'by_value':{x:x*x for x in values}}\n",
    'D04-def-return': "def rectangle_area(width,height):\n    return width*height\n",
    'D04-default-keyword': "def make_message(name,prefix='你好',suffix='!'):\n    return prefix+'，'+name+suffix\n",
    'D04-type-hints': "def format_user(name:str,age:int)->str:\n    return f'{name}: {age}'\n",
    'D06-raise': "def require_nonempty(text):\n    if text is None: raise ValueError('empty')\n    if not isinstance(text,str): raise TypeError('type')\n    if not text.strip(): raise ValueError('empty')\n    return text.strip()\n",
    'D12-post': "import json\nfrom urllib.request import Request\ndef post_json(url,payload,opener):\n    req=Request(url,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')\n    with opener(req) as r: return json.loads(r.read())\n",
    'D12-response': "import json\ndef parse_response(response):\n    if not 200<=response.status<300: raise RuntimeError('HTTP')\n    return json.loads(response.read().decode('utf-8'))\n",
    'D12-timeout': "from urllib.request import Request\ndef fetch_with_timeout(url,opener,timeout=2):\n    with opener(Request(url,method='GET'),timeout=timeout) as r: return r.read().decode('utf-8')\n",
    'D13-route': "from fastapi import FastAPI\napp=FastAPI()\n@app.get('/tasks/{task_id}')\ndef task(task_id:int): return {'id':task_id}\n@app.get('/tasks')\ndef tasks(limit:int=20): return {'limit':limit}\n",
    'D14-model': "from pydantic import BaseModel\nclass TaskIn(BaseModel):\n    title:str\n    priority:int=0\n",
    'D14-errors': "from fastapi import HTTPException\ndef get_or_404(repo,task_id):\n    result=repo.get(task_id)\n    if result is None: raise HTTPException(404,detail='任务不存在')\n    return result\n",
    'D17-timeout': "import asyncio\nasync def slow():\n    await asyncio.sleep(0.05)\n    return 'done'\nasync def run_with_timeout(seconds):\n    return await asyncio.wait_for(slow(),timeout=seconds)\n",
}

@pytest.mark.parametrize('sid',list(SOLUTIONS))
def test_public_contracts_accept_correct_implementation(sid,tmp_path):
    result=validate_code(SECTIONS[sid],SOLUTIONS[sid],tmp_path)
    assert result['passed'],result
    assert result.get('cases')
    assert all('actual' in c and 'expected' in c for c in result['cases'])


def test_wrong_function_output_has_actual_and_expected(tmp_path):
    r=validate_code(SECTIONS['D04-def-return'],'def rectangle_area(width,height): return 0',tmp_path)
    assert not r['passed']
    assert r['cases'][0]['expected']=='12' and r['cases'][0]['actual']=='0'


def test_correct_exception_is_a_passed_case(tmp_path):
    r=validate_code(SECTIONS['D06-raise'],SOLUTIONS['D06-raise'],tmp_path)
    assert r['passed'] and r['cases'][1]['passed']
    assert r['cases'][1]['actual'].startswith('ValueError')


def test_data_contract_is_valid_before_routes_exist():
    obj={'task':{'input':{'title':'string'},'output':{'id':1,'title':'string','done':False}},'errors':{'empty_title':422,'unknown_id':404}}
    text=json.dumps(obj)
    assert validate_json(SECTIONS['D18-data-contract'],text)['passed']
    assert not validate_json(SECTIONS['D18-api-contract'],text)['passed']
    obj['endpoints']=[{'method':m,'path':p} for m,p in [('GET','/'),('GET','/health'),('GET','/api/tasks'),('POST','/api/tasks'),('PATCH','/api/tasks/{task_id}/done'),('DELETE','/api/tasks/{task_id}')]]
    assert validate_json(SECTIONS['D18-api-contract'],json.dumps(obj))['passed']
    assert not validate_json(SECTIONS['D18-data-contract'],'[]')['passed']


def test_print_only_is_not_a_return_value(tmp_path):
    r=validate_code(SECTIONS['D04-def-return'],'def rectangle_area(width,height): print(width*height)',tmp_path)
    assert not r['passed'] and r['cases'][0]['actual']=='None' and '12' in r['stdout']


def test_real_pytest_not_a_top_level_assert(tmp_path):
    assert not validate_code(SECTIONS['D15-assert'],'assert 1+1==2',tmp_path)['passed']
    good='def add_tax(price): return round(price*1.13,2)\ndef test_normal(): assert add_tax(100)==113\ndef test_zero(): assert add_tax(0)==0\n'
    assert validate_code(SECTIONS['D15-assert'],good,tmp_path)['passed']
    assert not validate_code(SECTIONS['D15-assert'],good.replace('==113','==999'),tmp_path)['passed']


def test_experiment_bad_mode_is_a_usage_error():
    with pytest.raises(UsageError):
        run_experiment(SECTIONS['D03-if'], {'mode': [], 'index': 0})


def test_experiment_timeout_and_output_limit(monkeypatch):
    import learnctl.experiments as experiments
    monkeypatch.setattr(experiments, 'EXPERIMENT_TIMEOUT', 0.2)
    result=run_experiment(SECTIONS['D03-if'], {'mode':'card','index':0,'content':'while True: pass'})
    assert result['timeout'] and not result['passed']
    monkeypatch.setattr(experiments, 'EXPERIMENT_TIMEOUT', 5)
    monkeypatch.setattr(experiments, 'MAX_OUTPUT_BYTES', 1024)
    result=run_experiment(SECTIONS['D03-if'], {'mode':'card','index':0,'content':"print('x' * 5000)"})
    assert result['output_limited'] and len(result['stdout'].encode())<=1024 and not result['passed']


def test_experiment_does_not_inherit_api_key(monkeypatch):
    monkeypatch.setenv('EXAMPLE_API_KEY', 'dummy-never-a-real-key')
    result=run_experiment(SECTIONS['D03-if'], {'mode':'card','index':0,
        'content':"import os; print('EXAMPLE_API_KEY' in os.environ)"})
    assert result['actual']=='False'

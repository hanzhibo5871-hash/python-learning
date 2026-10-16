"""Draft integration regression + replacement private fixture sources.

Replace matching _GOOD_DB, _GOOD_CONFIG, _GOOD_API/_GOOD_API_FULL, _TEST_DB,
_TEST_API in tool_tests/test_practice.py and tool_tests/test_web.py with exports below.
Do not expose these solutions through curriculum/API payloads.
Run: python -m pytest -q <this file> (copy to test_d18_d24.py for pytest discovery).
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import pytest
from learnctl import practice as p

from learnctl import project_checks as validators

GOOD_DB = r'''import sqlite3

def create_connection(path=':memory:'):
    conn=sqlite3.connect(path,check_same_thread=False)
    conn.row_factory=sqlite3.Row
    return conn

def init_db(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')
    conn.commit()

def add_task(conn,title):
    title=title.strip()
    if not title: raise ValueError('标题不能为空')
    result=conn.execute('INSERT INTO tasks(title) VALUES (?)',(title,))
    conn.commit()
    return result.lastrowid

def list_tasks(conn):
    rows=conn.execute('SELECT id,title,done FROM tasks ORDER BY id').fetchall()
    return [{**dict(row),'done':bool(row['done'])} for row in rows]

def complete_task(conn,task_id):
    result=conn.execute('UPDATE tasks SET done=1 WHERE id=?',(task_id,))
    conn.commit()
    return result.rowcount>0

def delete_task(conn,task_id):
    result=conn.execute('DELETE FROM tasks WHERE id=?',(task_id,))
    conn.commit()
    return result.rowcount>0
'''
GOOD_CONFIG = "import os\nfrom pathlib import Path\ndef get_db_path(): return Path((os.environ.get('TASKPROJ_DB') or 'taskproj.db'))\n"
GOOD_APP = r'''from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from pathlib import Path
from taskproj.db import create_connection, init_db, add_task, list_tasks, complete_task, delete_task
from taskproj.config import get_db_path

@asynccontextmanager
async def lifespan(app):
    conn=create_connection(get_db_path())
    try: init_db(conn)
    finally: conn.close()
    yield

def get_db():
    conn=create_connection(get_db_path())
    try: yield conn
    finally: conn.close()

app=FastAPI(lifespan=lifespan)
@app.get('/health')
def health(): return {'status':'ok'}
'''
GOOD_MODELS = r'''
class TaskIn(BaseModel):
    title:str
    @field_validator('title')
    @classmethod
    def nonempty(cls,value):
        if not value.strip(): raise ValueError('标题不能为空')
        return value.strip()

class Task(BaseModel):
    id:int
    title:str
    done:bool
'''
GOOD_ROUTES = r'''
@app.get('/api/tasks',response_model=list[Task])
def tasks(conn=Depends(get_db)):
    return list_tasks(conn)

@app.post('/api/tasks',status_code=201,response_model=Task)
def create(body:TaskIn,conn=Depends(get_db)):
    task_id=add_task(conn,body.title)
    return next(row for row in list_tasks(conn) if row['id']==task_id)

@app.patch('/api/tasks/{task_id}/done',response_model=Task)
def complete(task_id:int,conn=Depends(get_db)):
    if not complete_task(conn,task_id): raise HTTPException(404,'任务不存在')
    return next(row for row in list_tasks(conn) if row['id']==task_id)

@app.delete('/api/tasks/{task_id}')
def remove(task_id:int,conn=Depends(get_db)):
    if not delete_task(conn,task_id): raise HTTPException(404,'任务不存在')
    return {'ok':True}
'''
GOOD_STATIC = r'''
@app.get('/')
def index():
    return FileResponse(Path(__file__).parent/'static'/'index.html')
'''
GOOD_API = GOOD_APP+GOOD_MODELS+GOOD_ROUTES
GOOD_API_FULL=GOOD_API+GOOD_STATIC
GOOD_CONTRACT = json.dumps({'task':{'input':{'title':'string'},'output':{'id':1,'title':'散步','done':False}},'errors':{'empty_title':422,'unknown_id':404},'endpoints':[{'method':method,'path':path} for method,path in [('GET','/'),('GET','/health'),('GET','/api/tasks'),('POST','/api/tasks'),('PATCH','/api/tasks/{task_id}/done'),('DELETE','/api/tasks/{task_id}')]]},ensure_ascii=False)
TEST_DB = r'''import pytest
from taskproj.db import create_connection,init_db,add_task,list_tasks,complete_task,delete_task

@pytest.fixture
def db(tmp_path):
    conn=create_connection(tmp_path/'case.db')
    init_db(conn)
    try: yield conn
    finally: conn.close()

def test_fields_and_sort(db):
    assert list_tasks(db)==[]
    a=add_task(db,'甲')
    b=add_task(db,'乙')
    assert list_tasks(db)==[{'id':a,'title':'甲','done':False},{'id':b,'title':'乙','done':False}]

def test_complete(db):
    assert list_tasks(db)==[]
    tid=add_task(db,'甲')
    assert complete_task(db,tid) is True
    assert list_tasks(db)[0]['done'] is True

def test_delete(db):
    tid=add_task(db,'乙')
    assert delete_task(db,tid) is True
    assert list_tasks(db)==[]

def test_unknown(db):
    assert complete_task(db,999999) is False
    assert delete_task(db,999999) is False
    assert list_tasks(db)==[]
'''
TEST_API_FLOW = r'''import pytest
from fastapi.testclient import TestClient
from taskproj.api import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('TASKPROJ_DB',str(tmp_path/'api.db'))
    with TestClient(app) as client:
        yield client

def test_flow(client):
    assert client.get('/health').status_code==200
    assert client.get('/api/tasks').json()==[]
    created=client.post('/api/tasks',json={'title':'散步'})
    assert created.status_code==201
    task=created.json()
    assert type(task['id']) is int
    assert task['title']=='散步'
    assert task['done'] is False
    tid=task['id']
    assert client.get('/api/tasks').json()==[task]
    assert client.patch(f'/api/tasks/{tid}/done').status_code==200
    assert client.get('/api/tasks').json()[0]['done'] is True
    deleted=client.delete(f'/api/tasks/{tid}')
    assert deleted.status_code==200
    assert deleted.json()=={'ok':True}
    assert client.get('/api/tasks').json()==[]
'''
TEST_API_ERRORS = r'''
def test_errors(client):
    before=client.get('/api/tasks').json()
    for body in ({},{'title':''},{'title':'  '}):
        response=client.post('/api/tasks',json=body)
        assert response.status_code==422
        assert response.json()['detail']
        assert 'Traceback' not in response.text
    assert client.get('/api/tasks').json()==before
    for response in (client.patch('/api/tasks/999999/done'),client.delete('/api/tasks/999999')):
        assert response.status_code==404
        assert response.json()['detail']
        assert 'Traceback' not in response.text
    task=client.post('/api/tasks',json={'title':'可删除'}).json()
    assert client.delete(f"/api/tasks/{task['id']}").status_code==200
    assert client.delete(f"/api/tasks/{task['id']}").status_code==404
'''
TEST_CONTRACT = r'''
def test_contract():
    import json
    from pathlib import Path
    contract=json.loads(Path('contract.json').read_text(encoding='utf-8'))
    assert contract['task']['input']['title']=='string'
    output=contract['task']['output']
    assert type(output['id']) is int and type(output['title']) is str and type(output['done']) is bool
    assert contract['errors']['empty_title']==422
    assert contract['errors']['unknown_id']==404
'''
TEST_API=TEST_API_FLOW+TEST_API_ERRORS
TEST_API_ACCEPTANCE=TEST_API+TEST_CONTRACT
INPUTS={'taskproj/__init__.py':'','taskproj/db.py':GOOD_DB,'taskproj/config.py':GOOD_CONFIG,'taskproj/api.py':GOOD_API_FULL,'contract.json':GOOD_CONTRACT}

@pytest.fixture(autouse=True)
def install_draft(monkeypatch):
    saved=dict(p._CODE_VALIDATORS)
    old=p._ACCEPT_API_HARNESS
    validators.register(p._CODE_VALIDATORS)
    None  # Production harness is already corrected
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    yield
    p._CODE_VALIDATORS.clear()
    p._CODE_VALIDATORS.update(saved)
    p._ACCEPT_API_HARNESS=old


def run(section_id,code,tmp_path,inputs=None):
    with p.PracticeContext(tmp_path) as ctx:
        values=INPUTS if inputs is None else inputs
        ctx.ws_deps=set(values)
        for path,source in values.items(): ctx.write(path,source)
        file='tests/test_project.py' if section_id in ('D20-db-tests','D22-db-fixtures') else 'tests/test_api.py'
        return p._CODE_VALIDATORS[section_id](code,ctx,{'id':section_id,'practice':{'file_name':file}})

@pytest.mark.parametrize('sid',['D20-create-list','D20-update-delete'])
def test_d20_row_conversion(sid,tmp_path):
    result=run(sid,GOOD_DB,tmp_path)
    assert result['passed'],result


def test_d20_requires_bool_and_persistence(tmp_path):
    broken=GOOD_DB.replace('return result.rowcount>0','return None')
    result=run('D20-update-delete',broken,tmp_path)
    assert not result['passed']
    assert any('True' in x['name'] and not x['passed'] for x in result['checks'])

@pytest.mark.parametrize('sid,source',[('D21-app',GOOD_APP),('D21-schema',GOOD_APP+GOOD_MODELS),('D21-crud-routes',GOOD_API),('D21-static',GOOD_API_FULL)])
def test_d21_progressive_correct(sid,source,tmp_path):
    result=run(sid,source,tmp_path)
    assert result['passed'],result

@pytest.mark.parametrize('sid,source',[('D21-app',GOOD_APP.replace("return {'status':'ok'}","return {'status':'wrong'}")),('D21-schema',(GOOD_APP+GOOD_MODELS).replace("if not value.strip(): raise ValueError('标题不能为空')","if False: raise ValueError('标题不能为空')")),('D21-crud-routes',GOOD_API.replace('status_code=201','status_code=200')),('D21-crud-routes',GOOD_API.replace("return list_tasks(conn)","return []")),('D21-static',GOOD_API_FULL.replace("Path(__file__).parent/'static'/'index.html'","Path('/not-this-package/index.html')"))])
def test_d21_rejects_actual_wrong_behavior(sid,source,tmp_path):
    result=run(sid,source,tmp_path)
    assert not result['passed'],result


def test_d21_static_does_not_require_html(tmp_path):
    result=run('D21-static',GOOD_API_FULL,tmp_path)
    assert result['passed'],result


def test_d24_context_runs_lifespan(tmp_path):
    with p.PracticeContext(tmp_path) as ctx:
        for path,source in INPUTS.items(): ctx.write(path,source)
        ctx.write('taskproj/static/index.html','<html><input><button></button><script>fetch("/api/tasks")</script></html>')
        proc,checks=p._run_harness(ctx,p._ACCEPT_API_HARNESS,'_result.json')
        assert proc['exit_code']==0,proc
        assert all(item['passed'] for item in checks),checks

@pytest.mark.parametrize('sid,source',[('D20-db-tests',TEST_DB),('D22-db-fixtures',TEST_DB),('D22-api-tests',TEST_API_FLOW),('D22-api-errors',TEST_API_FLOW+TEST_API_ERRORS),('D22-acceptance',TEST_API_ACCEPTANCE)])
def test_real_test_suites_pass(sid,source,tmp_path):
    result=run(sid,source,tmp_path)
    assert result['passed'],result

@pytest.mark.parametrize('sid',['D20-db-tests','D22-db-fixtures','D22-api-tests','D22-api-errors','D22-acceptance'])
def test_assert_true_is_not_quality_evidence(sid,tmp_path):
    result=run(sid,'def test_x():\n    assert True\n',tmp_path)
    assert not result['passed'],result


def test_d20_one_task_does_not_prove_sorting(tmp_path):
    source=TEST_DB.replace("    b=add_task(db,'乙')\n    assert list_tasks(db)==[{'id':a,'title':'甲','done':False},{'id':b,'title':'乙','done':False}]","    assert list_tasks(db)==[{'id':a,'title':'甲','done':False}]")
    result=run('D20-db-tests',source,tmp_path)
    assert not result['passed']
    assert any('列表排序' in c['name'] and not c['passed'] for c in result['checks'])


def test_d22_fixture_must_close_connection(tmp_path):
    broken=TEST_DB.replace('finally: conn.close()','finally: pass')
    result=run('D22-db-fixtures',broken,tmp_path)
    assert not result['passed'],result
    assert any('关闭连接' in c['name'] and not c['passed'] for c in result['checks'])


def test_d22_fixture_must_use_tmp_path(tmp_path):
    broken=TEST_DB.replace("tmp_path/'case.db'","':memory:'")
    result=run('D22-db-fixtures',broken,tmp_path)
    assert not result['passed'],result
    assert any('tmp_path' in c['name'] and not c['passed'] for c in result['checks'])


def test_mutation_does_not_write_original_project(tmp_path):
    ws=tmp_path/'learner_workspace'/'task-manager'
    for path,source in INPUTS.items():
        target=ws/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(source,encoding='utf-8')
    before={path:(ws/path).read_bytes() for path in INPUTS}
    result=run('D20-db-tests',TEST_DB,tmp_path)
    assert result['passed'],result
    assert {path:(ws/path).read_bytes() for path in INPUTS}==before
    assert not list(ws.rglob('*.db'))

def test_d21_app_requires_lifespan_initialization(tmp_path):
    broken=GOOD_APP.replace('FastAPI(lifespan=lifespan)','FastAPI()')
    result=run('D21-app',broken,tmp_path)
    assert not result['passed'],result
    assert any('lifespan' in c['name'] and not c['passed'] for c in result['checks'])


def test_d21_app_rejects_import_database_creation(tmp_path):
    broken=GOOD_APP+"\ncreate_connection('taskproj.db').close()\n"
    result=run('D21-app',broken,tmp_path)
    assert not result['passed'],result
    assert any('导入模块' in c['name'] and not c['passed'] for c in result['checks'])


@pytest.mark.parametrize('sid',['D23-cli-parser','D23-cli-mutate'])
def test_declared_cli_stages_real_persistence(sid,tmp_path):
    from tool_tests.test_practice import _GOOD_CLI
    result=run(sid,_GOOD_CLI,tmp_path)
    assert result['passed'],result

@pytest.mark.parametrize('mutant',["return 2", "file=sys.stderr", "if not complete_task(conn,args.task_id)"])
def test_cli_mutation_rejects_false_success_wrong_channel_or_missing_write(mutant,tmp_path):
    from tool_tests.test_practice import _GOOD_CLI
    replacement={"return 2":"return 0", "file=sys.stderr":"file=sys.stdout", "if not complete_task(conn,args.task_id)":"if not True"}[mutant]
    broken=_GOOD_CLI.replace(mutant,replacement)
    assert broken!=_GOOD_CLI
    result=run('D23-cli-mutate',broken,tmp_path)
    assert not result['passed'],result

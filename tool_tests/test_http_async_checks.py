"""Independent regression deliverable for validators-d12-d17.py.
Run from repo: python -m pytest -q <absolute path to this file>.
Uses only disposable PracticeContext directories and mock HTTP. No live AI.
"""
import importlib.util
import json
from pathlib import Path
import pytest
from learnctl import practice as p

from learnctl import http_async_checks as _DRAFT
REGISTRY = dict(p._CODE_VALIDATORS)
_DRAFT.register_audit_validators(REGISTRY)
ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/curriculum.json').read_text(encoding='utf-8'))
SECTIONS = {s['id']:s for t in DATA['tasks'] for s in t['lesson']}

@pytest.fixture(autouse=True)
def isolated_ai_configuration(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE','1')


def validate(sid,code,tmp_path):
    with p.PracticeContext(tmp_path) as ctx:
        return REGISTRY[sid](code,ctx,SECTIONS[sid])

GOOD = {
'D13-app': """from fastapi import FastAPI
app=FastAPI()
@app.get('/health')
def health(): return {'status':'ok'}
""",
'D13-response': """from fastapi import FastAPI
from pydantic import BaseModel
class TaskOut(BaseModel):
    id:int
    title:str
    done:bool=False
app=FastAPI()
@app.post('/tasks',response_model=TaskOut,status_code=201)
def create(body:dict): return {'id':1,'title':body['title'],'done':False}
""",
'D13-lifecycle': """from fastapi import FastAPI,Depends
from contextlib import asynccontextmanager
events=[]
@asynccontextmanager
async def lifespan(app):
    events.append('start')
    try: yield
    finally: events.append('stop')
app=FastAPI(lifespan=lifespan)
def get_value(): return 'ready'
@app.get('/value')
def get(value=Depends(get_value)): return {'value':value}
""",
'D16-connect': "import sqlite3\ndef create_connection(path): return sqlite3.connect(path)\n",
'D16-schema': """def init_db(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,title TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0)')
    conn.commit()
""",
'D16-transaction': """def add_two(conn,first,second):
    with conn:
        conn.execute('INSERT INTO tasks(title) VALUES (?)',(first,))
        conn.execute('INSERT INTO tasks(title) VALUES (?)',(second,))
""",
'D17-coroutine': """import asyncio
async def fetch_value(value):
    await asyncio.sleep(0)
    return value
async def wrapper(value): return await fetch_value(value)
""",
'D17-gather': """import asyncio
async def item(value):
    await asyncio.sleep(0)
    return value
async def run_all(values): return await asyncio.gather(*(item(v) for v in values))
""",
'D17-boundary': """async def fail(): raise ValueError('bad input')
async def safe_call():
    try: return await fail()
    except ValueError: return 'invalid-input'
""",
'D15-fixture': """import pytest
@pytest.fixture
def note_path(tmp_path): return tmp_path/'note.txt'
def test_roundtrip(note_path):
    note_path.write_text('你好',encoding='utf-8')
    assert note_path.read_text(encoding='utf-8')=='你好'
""",
'D15-mock': """import json
from unittest.mock import MagicMock,patch
import client
def test_get():
    response=MagicMock()
    response.__enter__.return_value.read.return_value=b'{"ok":true}'
    with patch('client.urllib.request.urlopen',return_value=response) as opener:
        assert client.get_json('https://example.test')=={'ok':True}
        opener.assert_called_once_with('https://example.test',timeout=10)
def test_post():
    response=MagicMock()
    response.__enter__.return_value.read.return_value=b'{"id":7}'
    payload={'title':'风'}
    with patch('client.urllib.request.urlopen',return_value=response) as opener:
        assert client.post_json('https://example.test',payload)=={'id':7}
        assert opener.call_count==1
        req=opener.call_args.args[0]
        assert req.get_method()=='POST'
        assert req.get_header('Content-type')=='application/json'
        assert json.loads(req.data)==payload
        assert opener.call_args.kwargs=={'timeout':10}
""",
'D15-api': """from fastapi.testclient import TestClient
def test_health(app):
    with TestClient(app) as client:
        response=client.get('/health')
        assert response.status_code==200
        assert response.json()=={'status':'ok'}
def test_create(app):
    with TestClient(app) as client:
        response=client.post('/tasks',json={'title':'风'})
        assert response.status_code==201
        assert response.json()=={'id':1,'title':'风'}
def test_missing(app):
    with TestClient(app) as client:
        assert client.get('/missing').status_code==404
""",
}

BAD = {
'D13-app': GOOD['D13-app'].replace("{'status':'ok'}",'None'),
'D13-response': 'class Unrelated:\n    pass\n',
'D13-lifecycle': 'def unrelated():\n    pass\n',
'D16-connect': 'def create_connection(path):\n    return None\ndef unused():\n    import sqlite3\n    sqlite3.connect(path)\n',
'D16-schema': "def init_db(conn):\n    sql='CREATE TABLE nowhere(x TEXT)'\n    return None\n",
'D16-transaction': 'def add_two(conn,first,second):\n    try: return True\n    except ValueError: conn.rollback()\n',
'D17-coroutine': 'async def fetch_value(value): return value\nasync def wrapper(value): return value\n',
'D17-gather': 'async def run_all(values): return list(values)\n',
'D17-boundary': "async def safe_call(): return 'invalid-input'\n",
'D15-fixture': 'def test_irrelevant(): assert 1+1==2\n',
'D15-mock': 'from unittest.mock import patch\ndef test_irrelevant():\n    with patch("client.urllib.request.urlopen"): assert 1+1==2\n',
'D15-api': 'def test_irrelevant(): assert 1+1==2\n',
}

@pytest.mark.parametrize('sid',list(GOOD))
def test_correct_submissions_satisfy_real_contract(sid,tmp_path):
    result=validate(sid,GOOD[sid],tmp_path)
    assert result['passed'],result

@pytest.mark.parametrize('sid',list(BAD))
def test_proven_or_semantically_wrong_submissions_are_rejected(sid,tmp_path):
    result=validate(sid,BAD[sid],tmp_path)
    assert not result['passed'],result


def test_transaction_accepts_explicit_commit_rollback_as_well_as_with(tmp_path):
    source="""def add_two(conn,first,second):
    try:
        conn.execute('INSERT INTO tasks(title) VALUES (?)',(first,))
        conn.execute('INSERT INTO tasks(title) VALUES (?)',(second,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
"""
    assert validate('D16-transaction',source,tmp_path)['passed']


def test_fixture_must_assert_read_content_not_just_read_it(tmp_path):
    source=GOOD['D15-fixture'].replace("assert note_path.read_text(encoding='utf-8')=='你好'", "note_path.read_text(encoding='utf-8')\n    assert note_path.exists()")
    assert not validate('D15-fixture',source,tmp_path)['passed']


def test_fixture_must_use_per_test_tmp_path(tmp_path):
    source=GOOD['D15-fixture'].replace("return tmp_path/'note.txt'", "return tmp_path/'other.txt'")
    assert not validate('D15-fixture',source,tmp_path)['passed']


def test_mock_get_only_tests_do_not_cover_post(tmp_path):
    source=GOOD['D15-mock'].split('def test_post():')[0]
    assert not validate('D15-mock',source,tmp_path)['passed']


def test_api_health_only_tests_do_not_cover_create_and_404(tmp_path):
    source=GOOD['D15-api'].split('def test_create(app):')[0]
    assert not validate('D15-api',source,tmp_path)['passed']


def test_async_unknown_errors_and_cancellation_are_not_swallowed(tmp_path):
    source=GOOD['D17-boundary'].replace('except ValueError:', 'except BaseException:')
    result=validate('D17-boundary',source,tmp_path)
    assert not result['passed']
    assert any(not c['passed'] for c in result['checks'])

def test_fixture_allows_path_open_and_builtin_open(tmp_path):
    code = """import pytest
@pytest.fixture
def note_path(tmp_path): return tmp_path/'note.txt'
def test_roundtrip(note_path):
    with note_path.open('w',encoding='utf-8') as stream:
        stream.write('测试')
    with open(note_path,encoding='utf-8') as stream:
        assert stream.read()=='测试'
"""
    assert validate('D15-fixture',code,tmp_path)['passed']


def test_fixture_allows_explicit_utf8_bytes(tmp_path):
    code = """import pytest
@pytest.fixture
def note_path(tmp_path): return tmp_path/'note.txt'
def test_roundtrip(note_path):
    with note_path.open('wb') as stream:
        stream.write('测试'.encode('utf-8'))
    with note_path.open('rb') as stream:
        assert stream.read().decode('utf-8')=='测试'
"""
    assert validate('D15-fixture',code,tmp_path)['passed']


def test_fixture_can_prepare_the_file_before_return(tmp_path):
    code = """import pytest
@pytest.fixture
def note_path(tmp_path):
    path=tmp_path/'note.txt'
    path.write_text('准备完成',encoding='utf-8')
    return path
def test_roundtrip(note_path):
    assert note_path.read_text(encoding='utf-8')=='准备完成'
"""
    assert validate('D15-fixture',code,tmp_path)['passed']

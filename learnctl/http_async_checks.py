"""Behavior checks for HTTP, tests, SQLite and async lesson contracts."""
from __future__ import annotations

from learnctl.contract_checks import behavior, value_case as v, error_case as e


def _register_basic_audit_validators(registry):
    registry['D13-app'] = behavior([
        v("client.get('/health').status_code", 200),
        v("client.get('/health').json()", {'status': 'ok'}),
    ], setup='from fastapi.testclient import TestClient\nclient=TestClient(M.app)')

    registry['D13-response'] = behavior([
        v('issubclass(M.TaskOut, BaseModel)', True),
        v('route.response_model is M.TaskOut', True),
        v("client.post('/tasks',json={'title':'风'}).status_code", 201),
        v("client.post('/tasks',json={'title':'风'}).json()", {'id': 1, 'title': '风', 'done': False}),
        v("client.post('/tasks',json={'title':'雨'}).json()", {'id': 1, 'title': '雨', 'done': False}),
    ], setup="from fastapi.testclient import TestClient\nfrom pydantic import BaseModel\nclient=TestClient(M.app)\nroute=next(r for r in M.app.routes if getattr(r,'path',None)=='/tasks' and 'POST' in getattr(r,'methods',set()))")

    registry['D13-lifecycle'] = behavior([
        v('list(M.events)', []),
        v('lifecycle_probe()', (['start'], {'value': 'ready'}, ['start', 'stop'])),
        v('dependency_probe()', {'value': 'test'}),
    ], setup='''
from fastapi.testclient import TestClient
def lifecycle_probe():
    with TestClient(M.app) as client:
        entered = list(M.events)
        body = client.get('/value').json()
    return entered, body, list(M.events)
def test_value(): return 'test'
def dependency_probe():
    M.app.dependency_overrides[M.get_value] = test_value
    try:
        with TestClient(M.app) as client:
            return client.get('/value').json()
    finally:
        M.app.dependency_overrides.clear()
''')

    registry['D16-connect'] = behavior([
        v('isinstance(memory, sqlite3.Connection)', True),
        v("memory.execute('SELECT 1').fetchone()", (1,)),
        v('caller_can_close()', True),
        v('file_path_is_used()', 'saved'),
    ], setup='''
memory = M.create_connection(':memory:')
def caller_can_close():
    memory.close()
    try: memory.execute('SELECT 1')
    except sqlite3.ProgrammingError: return True
    return False
def file_path_is_used():
    connection = M.create_connection(Path('chosen.db'))
    try:
        connection.execute('CREATE TABLE audit_note (value TEXT)')
        connection.execute('INSERT INTO audit_note VALUES (?)', ('saved',))
        connection.commit()
    finally: connection.close()
    connection = sqlite3.connect('chosen.db')
    try: return connection.execute('SELECT value FROM audit_note').fetchone()[0]
    finally: connection.close()
''')

    registry['D16-schema'] = behavior([
        v('(M.init_db(conn), schema_ok())[1]', True),
        v('insert_observes_defaults()', True),
        e("conn.execute('INSERT INTO tasks (title) VALUES (?)', (None,))", 'sqlite3.IntegrityError'),
        v('repeat_preserves_rows()', True),
    ], setup='''
conn = sqlite3.connect(':memory:')
def schema_ok():
    fields = {row[1]: row for row in conn.execute('PRAGMA table_info(tasks)').fetchall()}
    return (set(fields) >= {'id','title','done'} and fields['id'][5] == 1
            and fields['title'][3] == 1 and fields['done'][4] is not None)
def insert_observes_defaults():
    conn.execute('INSERT INTO tasks (title) VALUES (?)', ('kept',))
    row = conn.execute('SELECT id,title,done FROM tasks').fetchone()
    return type(row[0]) is int and row[0] > 0 and row[1:] == ('kept',0)
def repeat_preserves_rows():
    conn.commit()
    before = conn.execute('SELECT id,title,done FROM tasks ORDER BY id').fetchall()
    M.init_db(conn)
    M.init_db(conn)
    return conn.execute('SELECT id,title,done FROM tasks ORDER BY id').fetchall() == before
''')

    registry['D16-transaction'] = behavior([
        v("(M.add_two(conn,'A','B'), rows())[1]", [('A',), ('B',)]),
        e("M.add_two(conn,'C',None)", 'sqlite3.IntegrityError'),
        v('rows()', [('A',), ('B',)]),
        v('conn.in_transaction', False),
    ], setup="conn=sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)')\nconn.commit()\ndef rows(): return conn.execute('SELECT title FROM tasks ORDER BY id').fetchall()")

    registry['D17-gather'] = behavior([
        v('asyncio.run(M.run_all([3,1,2]))', [3,1,2]),
        v('bool(gather_calls) and gather_calls[0] == (3,True)', True),
        v('asyncio.run(M.run_all([]))', []),
    ], setup='''
original_gather = asyncio.gather
gather_calls = []
def observed_gather(*awaitables, **kwargs):
    gather_calls.append((len(awaitables), all(inspect.isawaitable(item) for item in awaitables)))
    return original_gather(*awaitables, **kwargs)
# Support normal module calls and common from-import aliases.
for name, value in tuple(vars(M).items()):
    if value is original_gather: setattr(M, name, observed_gather)
asyncio.gather = observed_gather
''')

    registry['D17-boundary'] = behavior([
        v("asyncio.run(probe_error(ValueError('invalid')))", 'invalid-input'),
        v("asyncio.run(probe_success())", 'success'),
        e("asyncio.run(probe_error(RuntimeError('unexpected')))", 'RuntimeError'),
        v('asyncio.run(probe_cancel())', True),
    ], setup='''
async def probe_error(error):
    async def provider(): raise error
    previous = getattr(M,'fail',None)
    M.fail = provider
    try: return await M.safe_call()
    finally: M.fail = previous
async def probe_success():
    async def provider(): return 'success'
    previous = getattr(M,'fail',None)
    M.fail = provider
    try: return await M.safe_call()
    finally: M.fail = previous
async def probe_cancel():
    closed = []
    async def provider():
        try: await asyncio.sleep(10)
        finally: closed.append(True)
    previous = getattr(M,'fail',None)
    M.fail = provider
    try:
        task = asyncio.create_task(M.safe_call())
        await asyncio.sleep(0)
        task.cancel()
        try: await task
        except asyncio.CancelledError: return closed == [True]
        return False
    finally: M.fail = previous
''')


def mutation_sensitive_pytest(code, ctx, section, base_scaffolds, mutants):
    """Reusable D15 proposal: learner assertions must detect supplied bad behavior.

    `mutants` is iterable[(name, list[(path, source)])]. Each deliberately broken
    scaffold must cause an ordinary pytest assertion failure (exit 1), rather
    than collection/import/usage failure. Preserve baseline result and append
    observable mutation checks. Provided code mutates only the temporary ctx.
    """
    from learnctl import practice as p
    result = p._pytest_validator('test_submission.py', base_scaffolds)(code, ctx, section)
    if not result.get('passed'): return result
    checks = list(result.get('checks', []))
    for name, scaffold in mutants:
        for path, source in base_scaffolds: ctx.write_scaffold(path, source)
        for path, source in scaffold: ctx.write_scaffold(path, source)
        mutant = p._pytest_validator('test_submission.py', [])(code, ctx, section)
        # Actual pytest output exit 1 is test failure; exits 2/4 are not evidence
        # of an assertion against the intended behavior.
        detected = mutant.get('exit_code') == 1
        checks.append({'name': name, 'passed': detected,
                       'detail': '坏行为被测试发现' if detected else '测试未发现该坏行为（或未正常收集）'})
    result['checks'] = checks
    result['passed'] = all(check['passed'] for check in checks)
    return result


# D15 concrete mutant plans (parent may use stronger private fixtures):
# - mock: mutate provided get_json result; mutate post_json result; change GET
#   URL/timeout; change POST method/Content-Type/data/timeout separately.
#   First disclose the provided client's timeout=10 and request protocol.
# - API: replace health JSON; change create status 201->200; remove returned id;
#   add catch-all missing-path route returning 200. Preserve app fixture.
# - fixture: a private pytest hook can observe note_path fixture has function
#   scope and returns tmp_path/'note.txt', and record real UTF8 write/read.
#   A Path.read_text mutant for that tracked file must be rejected by assertions.
#   Do not accept tests of unrelated 1+1 merely because pytest exited zero.
_NETWORK_GUARD = '''
import sys, urllib.request
sys.dont_write_bytecode = True
def _offline_only(*args, **kwargs):
    raise RuntimeError('本审核只允许本地替身')
urllib.request.urlopen = _offline_only
'''


def _validate_mock(code, ctx, section):
    from learnctl import practice as p
    source = p._API_CLIENT_REF
    get_part, post_part = source.split('def post_json', 1)
    base = [('client.py', source), ('conftest.py', _NETWORK_GUARD)]
    pairs = [
        ('GET返回值断言', get_part.replace('return json.loads(r.read())', "return {'wrong': True}") + 'def post_json' + post_part),
        ('POST返回值断言', get_part + 'def post_json' + post_part.replace('return json.loads(r.read())', "return {'wrong': True}")),
        ('GET URL参数断言', get_part.replace('urlopen(url,', "urlopen(url + '/wrong',") + 'def post_json' + post_part),
        ('GET timeout断言', get_part.replace('timeout=10', 'timeout=9') + 'def post_json' + post_part),
        ('POST方法断言', get_part + 'def post_json' + post_part.replace("method='POST'", "method='GET'")),
        ('POST Content-Type断言', get_part + 'def post_json' + post_part.replace('application/json', 'text/plain')),
        ('POST请求体断言', get_part + 'def post_json' + post_part.replace("json.dumps(payload).encode('utf-8')", "b'{}'")),
        ('POST timeout断言', get_part + 'def post_json' + post_part.replace('timeout=10', 'timeout=9')),
    ]
    return mutation_sensitive_pytest(code, ctx, section, base, [(name, [('client.py', text)]) for name,text in pairs])


_API_SOURCE = """from fastapi import FastAPI
app=FastAPI()
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/tasks',status_code=201)
def create(body:dict): return {'id':1,**body}
"""
_API_FIXTURE = _NETWORK_GUARD + '''
import pytest
from app import app as example_app
@pytest.fixture
def app(): return example_app
'''


def _validate_api(code, ctx, section):
    base = [('app.py', _API_SOURCE), ('conftest.py', _API_FIXTURE)]
    pairs = [
        ('健康JSON断言', _API_SOURCE.replace("{'status':'ok'}", "{'status':'broken'}")),
        ('创建状态码断言', _API_SOURCE.replace('status_code=201', 'status_code=200')),
        ('创建字段断言', _API_SOURCE.replace("{'id':1,**body}", "dict(body)")),
        ('未知路径404断言', _API_SOURCE + "\n@app.get('/{path:path}')\ndef missing(path): return {'detail':'fake'}\n"),
    ]
    return mutation_sensitive_pytest(code, ctx, section, base, [(name,[('app.py', text)]) for name,text in pairs])


_FIXTURE_MONITOR = r'''

import json, os, io, builtins
from pathlib import Path
import pytest
used = []
tracked = set()
written = {}
writes = []
reads = []
original_io_open = io.open
original_builtin_open = builtins.open
def _identity(file):
    try: return str(Path(os.fsdecode(file)).resolve())
    except (TypeError, ValueError, OSError): return None
def _text(value):
    if isinstance(value, str): return value
    if isinstance(value, bytes):
        try: return value.decode('utf-8')
        except UnicodeDecodeError: return None
    return None
class WatchedFile:
    def __init__(self, key, stream, mode):
        self.key, self.stream = key, stream
        self.encoding = getattr(stream, 'encoding', None) or 'utf-8'
        self.read_accum = ''
        if 'w' in mode: written[key] = ''
    def __getattr__(self, name): return getattr(self.stream, name)
    def __enter__(self):
        self.stream.__enter__()
        return self
    def __exit__(self, *args): return self.stream.__exit__(*args)
    def write(self, value):
        result = self.stream.write(value)
        text = _text(value)
        if text is not None:
            written[self.key] = written.get(self.key, '') + text
            writes.append([self.key, written[self.key], self.encoding])
        return result
    def writelines(self, values):
        for value in values: self.write(value)
    def observe_read(self, value):
        if @CORRUPT@: value = b'corrupted' if isinstance(value,bytes) else 'corrupted'
        text = _text(value)
        if text is not None:
            self.read_accum += text
            reads.append([self.key,self.read_accum,self.encoding])
        return value
    def read(self,*args,**kwargs): return self.observe_read(self.stream.read(*args,**kwargs))
    def readline(self,*args,**kwargs): return self.observe_read(self.stream.readline(*args,**kwargs))
    def readlines(self,*args,**kwargs):
        return [self.observe_read(value) for value in self.stream.readlines(*args,**kwargs)]
    def __iter__(self): return self
    def __next__(self): return self.observe_read(next(self.stream))
def _open(original,file,*args,**kwargs):
    stream = original(file,*args,**kwargs)
    key = _identity(file)
    mode = args[0] if args else kwargs.get('mode','r')
    return WatchedFile(key,stream,mode) if key in tracked else stream
def watched_io_open(file,*args,**kwargs): return _open(original_io_open,file,*args,**kwargs)
def watched_builtin_open(file,*args,**kwargs): return _open(original_builtin_open,file,*args,**kwargs)
io.open = watched_io_open
builtins.open = watched_builtin_open
@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    expected = None
    if fixturedef.argname == 'note_path' and fixturedef.scope == 'function':
        expected = request.getfixturevalue('tmp_path') / 'note.txt'
        tracked.add(_identity(expected))
    outcome = yield
    if fixturedef.argname == 'note_path':
        result = outcome.get_result()
        valid = fixturedef.scope == 'function' and isinstance(result,Path) and result == expected
        used.append(valid)
def pytest_sessionfinish(session, exitstatus):
    Path(@REPORT@).write_text(json.dumps({'used':used,'writes':writes,'reads':reads},ensure_ascii=False),encoding='utf-8')
'''


def _validate_fixture(code, ctx, section):
    import codecs, json
    from learnctl import practice as p
    report = ctx.temp / 'audit-fixture-observation.json'
    def scaffold(corrupt):
        return _NETWORK_GUARD + _FIXTURE_MONITOR.replace('@CORRUPT@', str(corrupt)).replace('@REPORT@', repr(str(report)))
    result = p._pytest_validator('test_submission.py', [('conftest.py',scaffold(False))])(code,ctx,section)
    if not result.get('passed'): return result
    observed = json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
    def utf8(value):
        try: return codecs.lookup(value).name == 'utf-8'
        except (TypeError,LookupError): return False
    used = observed.get('used', [])
    valid = bool(used) and all(used)
    valid = valid and any(
        write[0] == read[0] and write[1] == read[1] and utf8(write[2]) and utf8(read[2])
        and any('\u4e00' <= char <= '\u9fff' for char in write[1])
        for write in observed.get('writes', []) for read in observed.get('reads', [])
    )
    result['checks'].append({'name':'实际使用隔离fixture与UTF8中文写读','passed':bool(valid),'detail':'' if valid else '没有观察到本题要求的fixture/临时路径/中文写读。'})
    if not valid:
        result['passed'] = False
        return result
    broken = p._pytest_validator('test_submission.py',[('conftest.py',scaffold(True))])(code,ctx,section)
    detected = broken.get('exit_code') == 1
    result['checks'].append({'name':'读回内容错误能被断言发现','passed':detected,'detail':'' if detected else '测试没有发现读回内容错误。'})
    result['passed'] = detected
    return result


def register_audit_validators(registry):
    _register_basic_audit_validators(registry)
    registry['D15-fixture'] = _validate_fixture
    registry['D15-mock'] = _validate_mock
    registry['D15-api'] = _validate_api
    registry['D17-coroutine'] = behavior([
        v('inspect.iscoroutinefunction(M.fetch_value)',True),
        v('inspect.iscoroutinefunction(M.wrapper)',True),
        v('asyncio.run(M.fetch_value(3))',3),
        v('asyncio.run(M.fetch_value(0))',0),
        v('asyncio.run(M.wrapper(3))',3),
        v('asyncio.run(probe_wrapper())',('awaited',5)),
    ],setup='''
async def probe_wrapper():
    original = M.fetch_value
    async def provider(value): return ('awaited',value)
    M.fetch_value = provider
    try: return await M.wrapper(5)
    finally: M.fetch_value = original
''')
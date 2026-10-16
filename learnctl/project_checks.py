"""Private project behavior validators; all execution uses isolated copies.

Parent integration: copy into learnctl/project_checks.py, then invoke register(registry)
from contract_checks.register. Replace the original D20 fixture connect with Row,
and replace D24 TestClient assignment with a context manager in practice.py.
apply_minimal_harness_fixes is provided ONLY for exercising this draft unchanged.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any




_API_PREFIX = r'''
import json, os, sys, inspect, asyncio, sqlite3
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse
from pydantic import ValidationError
sys.path.insert(0, os.getcwd())
results=[]
def check(name, actual, expected):
    results.append({'name':name,'passed':actual == expected,'actual':repr(actual),
                    'expected':repr(expected),'detail':'' if actual == expected else '对照本节输入和实际结果，检查对应行为。'})
def attempt(name, action, expected):
    try: check(name, action(), expected)
    except Exception as error:
        results.append({'name':name,'passed':False,'actual':type(error).__name__ + ': ' + str(error),
                        'expected':repr(expected),'detail':'本项运行失败，请先检查异常类型和位置。'})
def rejected(action):
    try: action()
    except ValidationError: return True
    return False
os.environ['TASKPROJ_DB']=str(Path.cwd() / '_section_api.db')
def database_files():
    return {path.resolve() for pattern in ('*.db','*.sqlite','*.sqlite3') for path in Path.cwd().rglob(pattern)}
before_import=database_files()
try:
    import taskproj.api as M
'''
_API_SUFFIX = r'''
except Exception as error:
    results.append({'name':'导入和执行本节 API','passed':False,
                    'detail':type(error).__name__ + ': ' + str(error)})
Path('_result.json').write_text(json.dumps(results,ensure_ascii=False),encoding='utf-8')
'''

_APP_BODY = r'''
    check('app 为 FastAPI', isinstance(M.app, FastAPI), True)
    check('导入模块不创建数据库', database_files()-before_import, set())
    check('get_db 可覆盖依赖', callable(getattr(M,'get_db',None)), True)
    with TestClient(M.app) as client:
        check('lifespan 启动准备数据库',Path(os.environ['TASKPROJ_DB']).exists(),True)
        def initialized():
            conn=sqlite3.connect(os.environ['TASKPROJ_DB'])
            try: return conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone() is not None
            finally: conn.close()
        attempt('lifespan 启动准备 tasks 表',initialized,True)
        attempt('健康检查状态', lambda: client.get('/health').status_code, 200)
        attempt('健康检查 JSON', lambda: client.get('/health').json(), {'status':'ok'})
        # A private diagnostic route tests only this section's get_db dependency.
        @M.app.get('/__learnctl_db_probe')
        def probe(conn=Depends(M.get_db)):
            return {'value':conn.execute('SELECT 1').fetchone()[0]}
        attempt('get_db 提供可用连接', lambda:client.get('/__learnctl_db_probe').json(), {'value':1})
        class TestDB:
            def execute(self, sql):
                return self
            def fetchone(self):
                return (17,)
        M.app.dependency_overrides[M.get_db]=lambda:TestDB()
        try:
            attempt('get_db 的测试覆盖生效',lambda:client.get('/__learnctl_db_probe').json(),{'value':17})
        finally:
            M.app.dependency_overrides.clear()
'''
_SCHEMA_BODY = r'''
    attempt('TaskIn 正常标题',lambda:M.TaskIn(title='散步').title,'散步')
    attempt('TaskIn 拒绝缺失 title',lambda:rejected(lambda:M.TaskIn()),True)
    attempt('TaskIn 拒绝空字符串',lambda:rejected(lambda:M.TaskIn(title='')),True)
    attempt('TaskIn 拒绝纯空白',lambda:rejected(lambda:M.TaskIn(title=' \t ')),True)
    attempt('Task 输出字段和类型',lambda:M.Task(id=6,title='散步',done=False).model_dump(),{'id':6,'title':'散步','done':False})
    attempt('Task 拒绝无效 id',lambda:rejected(lambda:M.Task(id='bad',title='散步',done=False)),True)
    with TestClient(M.app) as client:
        attempt('保留健康检查',lambda:client.get('/health').json(),{'status':'ok'})
'''
_CRUD_BODY = r'''
    with TestClient(M.app) as client:
        attempt('GET /api/tasks 从空库开始',lambda:client.get('/api/tasks').json(),[])
        created=client.post('/api/tasks',json={'title':'散步'})
        check('POST 返回 201',created.status_code,201)
        task=created.json()
        tid=task.get('id')
        check('POST 字段和类型',isinstance(tid,int) and not isinstance(tid,bool) and tid>0 and task.get('title')=='散步' and task.get('done') is False,True)
        listed=client.get('/api/tasks')
        check('GET 列表 200',listed.status_code,200)
        check('新增可在列表观察到',any(row.get('id')==tid and row.get('title')=='散步' and row.get('done') is False for row in listed.json()),True)
        if isinstance(tid,int):
            done=client.patch('/api/tasks/{}/done'.format(tid))
            check('PATCH 返回 200',done.status_code,200)
            check('PATCH 实际修改状态',any(row.get('id')==tid and row.get('done') is True for row in client.get('/api/tasks').json()),True)
            deleted=client.delete('/api/tasks/{}'.format(tid))
            check('DELETE 返回 200',deleted.status_code,200)
            check('DELETE 返回 JSON',isinstance(deleted.json(),dict),True)
            check('DELETE 实际移除任务',any(row.get('id')==tid for row in client.get('/api/tasks').json()),False)
            again=client.delete('/api/tasks/{}'.format(tid))
            check('重复删除返回 404',again.status_code,404)
        for method,path in [('patch','/api/tasks/999999/done'),('delete','/api/tasks/999999')]:
            response=getattr(client,method)(path)
            check(method.upper()+' 未知 ID 状态',response.status_code,404)
            body=response.json()
            check(method.upper()+' 未知 ID 安全 detail',bool(body.get('detail')) and 'Traceback' not in response.text,True)
        before=client.get('/api/tasks').json()
        for body in ({},{'title':''},{'title':'  \t '}):
            response=client.post('/api/tasks',json=body)
            check('POST 拒绝非法 title '+repr(body),response.status_code,422)
        check('非法提交没有写入数据',client.get('/api/tasks').json(),before)
'''
_STATIC_BODY = r'''
    roots=[route for route in M.app.routes if getattr(route,'path','')=='/' and 'GET' in getattr(route,'methods',set())]
    check('存在 GET / 入口',len(roots),1)
    if roots:
        response=roots[0].endpoint()
        if inspect.isawaitable(response): response=asyncio.run(response)
        check('首页 endpoint 返回 FileResponse',isinstance(response,FileResponse),True)
        expected=Path(M.__file__).parent/'static'/'index.html'
        check('首页路径从模块定位',Path(response.path).resolve(),expected.resolve())
    # Do not open / or require D23 HTML; verify existing API still works.
    with TestClient(M.app) as client:
        attempt('保留 API 列表状态',lambda:client.get('/api/tasks').status_code,200)
        attempt('保留 API 列表数据',lambda:client.get('/api/tasks').json(),[])
'''


def _project_api(kind: str):
    body={'app':_APP_BODY,'schema':_SCHEMA_BODY,'crud':_CRUD_BODY,'static':_STATIC_BODY}[kind]
    def validate(code: str, ctx: Any, section: dict[str,Any]):
        from learnctl import practice as p
        ctx.write('taskproj/api.py',code)
        # __init__.py is input infrastructure, never a hidden app/db implementation.
        ctx.write_scaffold('taskproj/__init__.py','')
        proc,checks=p._run_harness(ctx,_API_PREFIX+body+_API_SUFFIX,'_result.json',timeout=p.PYTEST_TIMEOUT)
        result=p._finalize(checks,proc)
        result['cases']=[item for item in checks if 'actual' in item]
        if proc.get('exit_code')!=0: result['passed']=False
        return result
    return validate


_D20_SETUP = r'''
DB='_check.db'
conn=M.create_connection(DB)
M.init_db(conn)
def unchanged_after_failure():
    before=M.list_tasks(conn)
    try: M.add_task(conn,' \t ')
    except ValueError: return M.list_tasks(conn)==before
    return False
def persisted_title():
    M.add_task(conn,"它's 的")
    other=M.create_connection(DB)
    try: return any(row['title']=="它's 的" for row in M.list_tasks(other))
    finally: other.close()
def update_check():
    task_id=M.list_tasks(conn)[0]['id']
    result=M.complete_task(conn,task_id)
    other=M.create_connection(DB)
    try: return result is True and any(row['id']==task_id and row['done'] is True for row in M.list_tasks(other))
    finally: other.close()
def delete_check():
    task_id=M.list_tasks(conn)[0]['id']
    result=M.delete_task(conn,task_id)
    other=M.create_connection(DB)
    try: return result is True and not any(row['id']==task_id for row in M.list_tasks(other))
    finally: other.close()
def unknown_check(fn):
    before=M.list_tasks(conn)
    return fn(conn,999999) is False and M.list_tasks(conn)==before
'''

_DB_MUTANTS = {
    '字段内容': "\n_original_list=list_tasks\ndef list_tasks(conn):\n    return [{k:v for k,v in row.items() if k != 'title'} for row in _original_list(conn)]\n",
    '列表排序': "\n_original_list=list_tasks\ndef list_tasks(conn):\n    return list(reversed(_original_list(conn)))\n",
    '完成状态': "\ndef complete_task(conn, task_id):\n    return True\n",
    '删除效果': "\ndef delete_task(conn, task_id):\n    return True\n",
    '未知 ID': "\n_original_complete=complete_task\n_original_delete=delete_task\ndef complete_task(conn, task_id):\n    return _original_complete(conn,task_id) or True\ndef delete_task(conn, task_id):\n    return _original_delete(conn,task_id) or True\n",
}
_STATUS_MUTANT = "\n@app.middleware('http')\nasync def _learnctl_mutant(request, call_next):\n    response=await call_next(request)\n    if response.status_code == {status}: response.status_code=200\n    return response\n"


def _project_test_quality(test_kind: str):
    """Run real tests, then verify tests detect one scoped fault at a time.

    Mutation runs have fresh independent PracticeContexts; no student file changes,
    hidden correct implementation, or global testing of not-yet-created artifacts.
    """
    def validate(code: str, ctx: Any, section: dict[str,Any]):
        from learnctl import practice as p
        test_file=section.get('practice',{}).get('file_name','tests/test_api.py')
        # Save dependencies before submitted tests can alter temporary inputs.
        inputs={rel:(ctx.temp/rel).read_text(encoding='utf-8') for rel in ctx.ws_deps if (ctx.temp/rel).is_file()}
        base=p._pytest_validator(test_file,[])(code,ctx,section)
        if not base['passed']: return base
        mutations=[]
        if test_kind=='db':
            mutations=[('taskproj/db.py',label,delta) for label,delta in _DB_MUTANTS.items()]
        elif test_kind=='api-flow':
            mutations=[('taskproj/db.py',label,_DB_MUTANTS[label]) for label in ('字段内容','完成状态','删除效果')]
            mutations.append(('taskproj/api.py','创建状态码',_STATUS_MUTANT.format(status=201)))
        elif test_kind=='api-errors':
            mutations=[('taskproj/api.py','未知 ID 状态',_STATUS_MUTANT.format(status=404)),('taskproj/api.py','非法标题状态',_STATUS_MUTANT.format(status=422))]
        elif test_kind=='acceptance':
            mutations=[('contract.json','数据契约','{}'),('taskproj/db.py','完成状态',_DB_MUTANTS['完成状态']),('taskproj/db.py','删除效果',_DB_MUTANTS['删除效果'])]
        for path,label,delta in mutations:
            if path not in inputs:
                base['checks'].append({'name':'测试检出 '+label,'passed':False,'detail':'缺少本节声明的依赖文件 '+path})
                continue
            with p.PracticeContext(ctx.project_root) as trial:
                trial.ws_deps=set(inputs)
                for rel,content in inputs.items(): trial.write(rel,content)
                trial.write(path,delta if path=='contract.json' else inputs[path]+delta)
                trial.write(test_file,code)
                proc=p._run_proc([p.sys.executable,'-m','pytest','-q',test_file],cwd=trial.temp,timeout=p.PYTEST_TIMEOUT)
                # Only actual failing tests count: syntax/collection errors are not evidence.
                detected=proc['exit_code']==1 and 'FAILED' in proc['stdout'] and not proc['timeout']
                base['checks'].append({'name':'测试检出 '+label,'passed':detected,
                                       'detail':'测试已检出该类故障。' if detected else '实现故意破坏这一行为后，测试仍未失败；请增加能观察此行为的输入与断言。'})
        base['passed']=all(item['passed'] for item in base['checks'])
        return base
    return validate



_FIXTURE_PROBE = r'''import json, sqlite3
from pathlib import Path
import pytest
created=[]
results=[]
real_connect=sqlite3.connect

def tracked_connect(*args,**kwargs):
    conn=real_connect(*args,**kwargs)
    created.append(conn)
    return conn
sqlite3.connect=tracked_connect

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    start=len(created)
    yield
    item._learnctl_connections=created[start:]
    available=item._learnctl_connections
    results.append({'name':'独立连接 '+item.name,'passed':bool(available),'detail':'每个测试都应通过 fixture 创建新的连接。'})
    for conn in available:
        try:
            count=conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
            results.append({'name':'隔离空表 '+item.name,'passed':count==0,'detail':'测试开始时 tasks 应为空。'})
            db_path=conn.execute('PRAGMA database_list').fetchone()[2]
            temp=item.funcargs.get('tmp_path')
            inside=temp is not None and bool(db_path) and Path(db_path).resolve().is_relative_to(Path(temp).resolve())
            results.append({'name':'tmp_path 数据库 '+item.name,'passed':inside,'detail':'fixture 应使用当前测试的 tmp_path。'})
        except Exception as error:
            results.append({'name':'fixture 初始化 '+item.name,'passed':False,'detail':type(error).__name__+': '+str(error)})

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item,nextitem):
    yield
    for conn in getattr(item,'_learnctl_connections',[]):
        try:
            conn.execute('SELECT 1')
            closed=False
        except sqlite3.ProgrammingError:
            closed=True
        except Exception:
            closed=False
        results.append({'name':'teardown 关闭连接 '+item.name,'passed':closed,'detail':'yield 后的 finally 应关闭连接。'})

def pytest_sessionfinish(session,exitstatus):
    count=sum(item['name'].startswith('独立连接 ') for item in results)
    results.append({'name':'至少两例证明隔离','passed':count>=2,'detail':'用至少两个测试观察各自初始空表和资源清理。'})
    Path('_fixture_checks.json').write_text(json.dumps(results,ensure_ascii=False),encoding='utf-8')
'''


def _project_db_fixture(code: str, ctx: Any, section: dict[str,Any]):
    from learnctl import practice as p
    test_file=section['practice'].get('file_name','tests/test_project.py')
    ctx.write(test_file,code)
    ctx.write('_learnctl_fixture_probe.py',_FIXTURE_PROBE)
    proc=p._run_proc([p.sys.executable,'-m','pytest','-q','-p','_learnctl_fixture_probe',test_file],cwd=ctx.temp,timeout=p.PYTEST_TIMEOUT)
    checks=[{'name':'pytest fixture 测试通过','passed':proc['exit_code']==0,'detail':p._tail(proc['stdout'] or proc['stderr'])}]
    checks += p._read_result(ctx,'_fixture_checks.json')
    if len(checks)==1:
        checks.append({'name':'fixture 实际运行证据','passed':False,'detail':'没有获得连接初始化与清理结果。'})
    return p._finalize(checks,proc)


def _project_cli(require_mutation: bool):
    """Exercise declared CLI stages against the submitted dependency files."""
    def validate(code: str, ctx: Any, section: dict[str,Any]):
        from learnctl import practice as p
        import sqlite3
        ctx.write('taskproj/cli.py',code)
        database=ctx.temp/'_section_cli.db'
        environment={'TASKPROJ_DB':str(database)}
        checks=[]
        last={'timeout':False,'exit_code':None}
        def check(name,passed,actual='',expected=''):
            checks.append({'name':name,'passed':bool(passed),'actual':actual,'expected':expected,
                           'detail':'' if passed else '对照本节命令、退出码、错误通道与实际数据库变化。'})
        def command(*argv):
            nonlocal last
            last=p._run_proc([p.sys.executable,'-m','taskproj.cli',*argv],cwd=ctx.temp,env=environment)
            if last.get('timeout'):
                check('CLI 命令限时',False,'超时',f'{p.TIMEOUT_SECONDS} 秒内结束')
            return last
        def finish():
            # Error streams may contain configuration; report observable checks.
            return p._finalize(checks,{'timeout':False,'stdout':'','stderr':'','exit_code':last.get('exit_code')})
        def rows():
            if not database.is_file():
                return None
            try:
                conn=sqlite3.connect(database)
                try: return conn.execute('SELECT id,title,done FROM tasks ORDER BY id').fetchall()
                finally: conn.close()
            except sqlite3.Error:
                return None
        for title in ('散步',"它's 的便签"):
            proc=command('add',title)
            check('add 成功退出：'+title,proc['exit_code']==0 and not proc['stderr'],repr(proc['exit_code']),'0，stderr 为空')
            if proc.get('timeout'): return finish()
        current=rows()
        check('两个 add 实际持久写入',current is not None and len(current)==2 and [r[1] for r in current]==['散步',"它's 的便签"] and all(r[2]==0 for r in current),'符合' if current is not None and len(current)==2 else '数量或结构不符','两条正确标题，done 均为 0')
        proc=command('list')
        check('list 跨进程观察新增',proc['exit_code']==0 and not proc['stderr'] and '散步' in proc['stdout'] and "它's 的便签" in proc['stdout'],repr(proc['exit_code']),'0，两条标题可见')
        if proc.get('timeout') or not require_mutation: return finish()
        if not current or len(current)!=2: return finish()
        target=current[0][0]
        proc=command('done',str(target))
        check('done 成功退出',proc['exit_code']==0 and not proc['stderr'],repr(proc['exit_code']),'0，stderr 为空')
        if proc.get('timeout'): return finish()
        changed=rows()
        check('done 实际提交状态',changed is not None and any(r[0]==target and r[2]==1 for r in changed),'符合' if changed is not None and any(r[0]==target and r[2]==1 for r in changed) else '未观察到完成','目标 done=1')
        proc=command('rm',str(target))
        check('rm 成功退出',proc['exit_code']==0 and not proc['stderr'],repr(proc['exit_code']),'0，stderr 为空')
        if proc.get('timeout'): return finish()
        after=rows()
        check('rm 实际提交删除',after is not None and len(after)==1 and not any(r[0]==target for r in after),'符合' if after is not None and len(after)==1 else '数量或结构不符','目标被删除，其他任务保留')
        for label,argv in [('空白标题',('add','   ')),('未知完成',('done','999999')),('未知删除',('rm','999999')),('重复删除',('rm',str(target))),('非法编号',('done','not-an-int'))]:
            before=rows()
            proc=command(*argv)
            valid_code=type(proc['exit_code']) is int and proc['exit_code']!=0
            check(label+'：非零且错误写 stderr',valid_code and bool(proc['stderr'].strip()),repr(proc['exit_code']),'非零整数，stderr 有错误')
            if proc.get('timeout'): return finish()
            check(label+'：没有修改已有记录',rows()==before,'未变' if rows()==before else '有变化','记录保持不变')
        return finish()
    return validate


def register(registry: dict[str,Any]) -> None:
    from learnctl import practice as p
    # Creates a real submitted connection with Row, rather than a bare tuple fixture.
    common={'file':'taskproj/db.py','module':'taskproj.db','scaffold':[('taskproj/__init__.py','')],'setup':_D20_SETUP}
    first=[('新增自增 id',"(lambda i:type(i) is int and i>0)(M.add_task(conn,'任务一'))"),
           ('查询字段、状态与排序',"M.list_tasks(conn) == [{'id':1,'title':'任务一','done':False}]"),
           ('拒绝空白且不写库','unchanged_after_failure()'),('引号标题安全且已提交','persisted_title()'),
           ('两条数据按 id 升序',"len(M.list_tasks(conn))==2 and [row['id'] for row in M.list_tasks(conn)] == sorted(row['id'] for row in M.list_tasks(conn))")]
    registry['D20-create-list']=p._function_validator({**common,'checks':first})
    registry['D20-update-delete']=p._function_validator({**common,'checks':first+[
        ('完成返回 True 且状态已提交','update_check()'),('删除返回 True 且结果已提交','delete_check()'),
        ('完成未知 ID 返回 False', 'unknown_check(M.complete_task)'),('删除未知 ID 返回 False','unknown_check(M.delete_task)')]})
    for sid,kind in [('D21-app','app'),('D21-schema','schema'),('D21-crud-routes','crud'),('D21-static','static')]:
        registry[sid]=_project_api(kind)
    registry['D20-db-tests']=_project_test_quality('db')
    registry['D22-db-fixtures']=_project_db_fixture
    registry['D22-api-tests']=_project_test_quality('api-flow')
    registry['D22-api-errors']=_project_test_quality('api-errors')
    registry['D22-acceptance']=_project_test_quality('acceptance')
    registry['D23-cli-parser']=_project_cli(False)
    registry['D23-cli-mutate']=_project_cli(True)

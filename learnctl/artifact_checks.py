"""Execute the D19 artifact contracts in a bounded temporary subprocess.

The instrumentation records and rejects ordinary Python file writes, database
connections, networking, process/thread starts during import and explicit calls.
It is regression instrumentation, not a security sandbox for hostile Python.
Dependencies are only the files PracticeContext received from the workspace.
"""
from __future__ import annotations

from typing import Any

ARTIFACT_TIMEOUT = 5

_IMPORT_HARNESS = r'''
import sys
sys.dont_write_bytecode = True
import contextlib, hashlib, importlib, io, json, os, runpy, threading, traceback
from pathlib import Path
sys.path.insert(0, os.getcwd())
KIND = __KIND__
MODULE = __MODULE__
results = []
active = False
blocked = []

class ImportSideEffect(RuntimeError):
    pass

def forbidden(label):
    blocked.append(label)
    raise ImportSideEffect(label)

def audit(event, args):
    if not active:
        return
    if event == 'open':
        mode = args[1] if len(args)>1 else ''
        flags = args[2] if len(args)>2 else 0
        writing = isinstance(mode,str) and any(letter in mode for letter in 'wax+')
        writing = writing or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        if writing:
            forbidden('文件写入')
    elif event in {'os.remove','os.rename','os.rmdir','os.mkdir','os.link','os.symlink','os.truncate','os.chmod','os.utime','shutil.copyfile'}:
        forbidden('文件或目录修改')
    elif event in {'os.putenv','os.unsetenv'}:
        forbidden('环境写入')
    elif event == 'os.chdir':
        forbidden('工作目录切换')
    elif event.startswith('sqlite3.connect'):
        forbidden('数据库连接')
    elif event in {'socket.connect','socket.bind','socket.getaddrinfo','socket.__new__'}:
        forbidden('联网或服务监听')
    elif event in {'subprocess.Popen','os.system','os.exec','os.posix_spawn','os.fork','_winapi.CreateProcess'}:
        forbidden('子进程或服务启动')
sys.addaudithook(audit)
real_thread_start = threading.Thread.start

def checked_thread_start(self,*args,**kwargs):
    if active:
        forbidden('后台线程启动')
    return real_thread_start(self,*args,**kwargs)
threading.Thread.start = checked_thread_start


def files():
    return {str(path.relative_to(Path.cwd())):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path.cwd().rglob('*') if path.is_file()}


def check(name, passed, actual='', expected='', detail=''):
    results.append({'name':name,'passed':bool(passed),'actual':actual,'expected':expected,
                    'detail':detail if not passed else ''})


def location(error):
    if isinstance(error,SyntaxError):
        return error.lineno
    current = error.__traceback__
    found = None
    while current:
        if '/taskproj/' in current.tb_frame.f_code.co_filename.replace('\\','/'):
            found=current.tb_lineno
        current=current.tb_next
    return found


def capture(action, *, allow_exit=False):
    global active
    out,err=io.StringIO(),io.StringIO()
    value,error,exit_code=None,None,None
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        active=True
        try:
            value=action()
        except SystemExit as exc:
            if allow_exit:
                exit_code=0 if exc.code is None else exc.code
            else:
                error=exc
        except BaseException as exc:
            error=exc
        finally:
            active=False
    return value,out.getvalue(),err.getvalue(),error,exit_code


def error_detail(error):
    if error is None:
        return ''
    line=location(error)
    return type(error).__name__ + (('，第 '+str(line)+' 行') if line else '')


def check_import(module,out,err,error):
    check('当前模块可导入',error is None,error_detail(error),'合法 Python 模块',error_detail(error))
    # Do not echo accidental configuration dumps or arbitrary exception messages.
    check('导入没有 stdout/stderr',not out and not err,'无输出' if not out and not err else '检测到输出','无输出','请将输出移到显式入口；配置内容不应打印。')

before=files()
os.environ['TASKPROJ_DB']='_import_setting.db'
module,out,err,error,_=capture(lambda:importlib.import_module(MODULE))
check_import(module,out,err,error)
if error is None:
    if KIND=='package':
        version=getattr(module,'__version__',None)
        doc=getattr(module,'__doc__',None)
        meaningful=(isinstance(version,str) and bool(version.strip())) or (isinstance(doc,str) and bool(doc.strip()))
        check('声明版本字符串或模块说明',meaningful,str(meaningful),'True','只需版本字符串或模块文档说明；不要求 __all__。')
    elif KIND=='config':
        for label,setting,expected in [('缺失',None,'taskproj.db'),('空值','','taskproj.db'),('自定义','sample.db','sample.db'),('中文相对路径','data/学习.db','data/学习.db')]:
            if setting is None:
                os.environ.pop('TASKPROJ_DB',None)
            else:
                os.environ['TASKPROJ_DB']=setting
            value,out,err,error,_=capture(lambda:module.get_db_path())
            typed=isinstance(value,Path)
            matches=typed and value==Path(expected)
            actual=(repr(Path(expected)) if matches else ('返回 '+type(value).__name__+'；路径或类型不符合当前输入'))
            check(label+'配置返回 Path',error is None and matches,actual,repr(Path(expected)),error_detail(error) or '检查缺失/空值回退及 Path 返回类型。')
            check(label+'配置读取无输出',not out and not err,'无输出' if not out and not err else '检测到输出','无输出','配置函数只返回路径，不打印环境。')
    elif KIND=='main':
        for label,args in [('默认入口',()),('显式 argv',([],))]:
            value,out,err,error,_=capture(lambda:module.main(*args))
            actual=repr(value) if value is None or type(value) in (int,float,bool) else type(value).__name__
            check(label+'返回整数 0',error is None and type(value) is int and value==0,actual,'0',error_detail(error) or 'main 应返回整数状态，交由调用方退出。')
            correct=out=='任务管理项目已启动\n' and not err
            check(label+'只输出规定的一行',error is None and correct,'规定的一行' if correct else '输出内容、行数或 stderr 不符','任务管理项目已启动（单行 stdout）',error_detail(error) or '显式执行时输出一行规定提示。')
        # Fresh execution avoids runpy's warning about an already imported module.
        sys.modules.pop(MODULE,None)
        _,out,err,error,exit_code=capture(lambda:runpy.run_module(MODULE,run_name='__main__'),allow_exit=True)
        if error is None and exit_code is None:
            exit_code=0
        check('直接运行成功退出',error is None and type(exit_code) is int and exit_code==0,repr(exit_code),'0',error_detail(error) or '使用入口守卫，从项目根可直接运行该模块。')
        correct=out=='任务管理项目已启动\n' and not err
        check('直接运行调用入口一次',error is None and correct,'规定的一行' if correct else '输出内容、行数或 stderr 不符','任务管理项目已启动（单行 stdout）',error_detail(error) or '导入与直接执行应分开：导入安静，直接执行调用入口。')

after=files()
check('不创建或改写文件',after==before,'文件树未变' if after==before else '文件树有变化','文件树未变','将资源写入移至后续显式操作。')
check('没有数据库、网络、文件或服务副作用',not blocked,'、'.join(dict.fromkeys(blocked)) if blocked else '未触发副作用','未触发副作用','禁止的资源操作已被检测并阻止；当前只声明包、读取配置或执行规定提示。')
Path('_result.json').write_text(json.dumps(results,ensure_ascii=False),encoding='utf-8')
'''


def _artifact_validator(kind: str, module: str, file: str):
    def validate(code: str, ctx: Any, section: dict[str,Any]) -> dict[str,Any]:
        from . import practice as p
        ctx.write(file,code)
        if kind!='package':
            # Only a package marker; actual declared package dependencies win.
            ctx.write_scaffold('taskproj/__init__.py','')
        harness=(_IMPORT_HARNESS.replace('__KIND__',repr(kind))
                 .replace('__MODULE__',repr(module)))
        proc,checks=p._run_harness(ctx,harness,'_result.json',timeout=ARTIFACT_TIMEOUT)
        if proc.get('timeout'):
            checks=[{'name':'导入和入口运行限时','passed':False,'detail':f'超过 {ARTIFACT_TIMEOUT} 秒；当前任务不应启动长期运行服务。'}]
        elif proc.get('stdout') or proc.get('stderr'):
            checks.append({'name':'子进程没有额外输出','passed':False,'detail':'检测到绕过普通输出捕获的输出或运行错误；不回显可能包含配置的内容。'})
        clean_proc={'timeout':False,'stdout':'','stderr':'','exit_code':proc.get('exit_code')}
        result=p._finalize(checks,clean_proc)
        if proc.get('exit_code')!=0 or proc.get('timeout'):
            result['passed']=False
        result['cases']=[item for item in checks if 'actual' in item]
        return result
    return validate


def register(registry: dict[str,Any]) -> None:
    registry['D19-package']=_artifact_validator('package','taskproj','taskproj/__init__.py')
    registry['D19-config']=_artifact_validator('config','taskproj.config','taskproj/config.py')
    registry['D19-main']=_artifact_validator('main','taskproj.main','taskproj/main.py')
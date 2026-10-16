from __future__ import annotations

from pathlib import Path

import pytest

from learnctl import artifact_checks
from learnctl import practice


PACKAGE_VERSION='__version__ = "0.1.0"\n'
PACKAGE_DOC='"""任务管理包说明。"""\n'
CONFIG='''import os
from pathlib import Path

def get_db_path():
    return Path(os.environ.get('TASKPROJ_DB') or 'taskproj.db')
'''
MAIN='''def main(argv=None):
    print('任务管理项目已启动')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
'''


def validate(identifier: str, source: str, root: Path, *, package: str | None=None):
    registry={}
    artifact_checks.register(registry)
    with practice.PracticeContext(root) as ctx:
        if package is not None:
            ctx.ws_deps.add('taskproj/__init__.py')
            ctx.write('taskproj/__init__.py',package)
        result=registry[identifier](source,ctx,{'id':identifier})
        assert not list(ctx.temp.rglob('*.db')), '被检测的数据库操作不应真正建库'
        return result


@pytest.mark.parametrize('source',[PACKAGE_VERSION,PACKAGE_DOC,PACKAGE_VERSION+'__all__ = ["__version__"]\n'])
def test_package_accepts_version_or_doc_without_extra_exports(source,tmp_path):
    result=validate('D19-package',source,tmp_path)
    assert result['passed'],result


@pytest.mark.parametrize('source',[
    '# only a placeholder\n',
    '__version__=1\n',
    '__version__=""\n',
    'def invalid(\n',
    PACKAGE_VERSION+'print("unexpected")\n',
    PACKAGE_VERSION+'import sys\nsys.stderr.write("unexpected")\n',
    PACKAGE_VERSION+'import os\nos.write(1,b"unexpected")\n',
    PACKAGE_VERSION+'import sqlite3\nsqlite3.connect(":memory:")\n',
    PACKAGE_VERSION+'import sqlite3\nsqlite3.connect("bad.db")\n',
    PACKAGE_VERSION+'from pathlib import Path\nPath("side.txt").write_text("bad")\n',
    PACKAGE_VERSION+'from pathlib import Path\nPath("taskproj/__init__.py").unlink()\n',
    PACKAGE_VERSION+'import socket\nsocket.create_connection(("example.test",443))\n',
    PACKAGE_VERSION+'from http.server import HTTPServer,BaseHTTPRequestHandler\nHTTPServer(("127.0.0.1",0),BaseHTTPRequestHandler)\n',
    PACKAGE_VERSION+'import subprocess,sys\nsubprocess.run([sys.executable,"-c","print(1)"])\n',
    PACKAGE_VERSION+'import threading\nthreading.Thread(target=lambda:None).start()\n',
])
def test_package_rejects_invalid_or_observed_side_effects(source,tmp_path):
    result=validate('D19-package',source,tmp_path)
    assert not result['passed'],result
    assert result['stdout']==result['stderr']==''


def test_catching_database_error_does_not_hide_attempt(tmp_path):
    source=PACKAGE_VERSION+'''import sqlite3
try:
    sqlite3.connect('bad.db')
except Exception:
    pass
'''
    result=validate('D19-package',source,tmp_path)
    assert not result['passed'],result
    check=next(item for item in result['checks'] if item['name']=='没有数据库、网络、文件或服务副作用')
    assert '数据库连接' in check['actual']


def test_config_exact_runtime_env_and_path_contract(tmp_path):
    result=validate('D19-config',CONFIG,tmp_path,package=PACKAGE_VERSION)
    assert result['passed'],result


@pytest.mark.parametrize('source',[
    CONFIG.replace("os.environ.get('TASKPROJ_DB') or 'taskproj.db'","os.environ.get('TASKPROJ_DB','taskproj.db')"),
    CONFIG.replace("return Path(os.environ.get('TASKPROJ_DB') or 'taskproj.db')","return os.environ.get('TASKPROJ_DB') or 'taskproj.db'"),
    CONFIG.replace("return Path(os.environ.get('TASKPROJ_DB') or 'taskproj.db')","return Path('taskproj.db')"),
    CONFIG.replace('def get_db_path():',"saved=os.environ.get('TASKPROJ_DB') or 'taskproj.db'\ndef get_db_path():").replace("Path(os.environ.get('TASKPROJ_DB') or 'taskproj.db')","Path(saved)"),
    CONFIG+'\nprint("configuration dump")\n',
    CONFIG+'\nimport sqlite3\nsqlite3.connect("bad.db")\n',
])
def test_config_rejects_wrong_fallback_type_cached_import_or_side_effect(source,tmp_path):
    result=validate('D19-config',source,tmp_path)
    assert not result['passed'],result


def test_real_declared_package_is_not_replaced_by_scaffold(tmp_path):
    result=validate('D19-config',CONFIG,tmp_path,package=PACKAGE_VERSION+'print("package side effect")\n')
    assert not result['passed'],result
    assert any(check['name']=='导入没有 stdout/stderr' and not check['passed'] for check in result['checks'])


def test_main_import_call_and_direct_execute(tmp_path):
    result=validate('D19-main',MAIN,tmp_path,package=PACKAGE_DOC)
    assert result['passed'],result


@pytest.mark.parametrize('source',[
    MAIN.replace('return 0','return None'),
    MAIN.replace('return 0','return False'),
    MAIN.replace('return 0','return 2'),
    MAIN.replace('if __name__ == \'__main__\':','if True:'),
    MAIN.replace("print('任务管理项目已启动')","print('different')"),
    MAIN.replace("print('任务管理项目已启动')","print('任务管理项目已启动'); print('extra')"),
    MAIN.replace("if __name__ == '__main__':\n    raise SystemExit(main())",''),
    MAIN+'\nfrom taskproj.api import app\n',
])
def test_main_rejects_behavior_that_old_stdout_check_missed(source,tmp_path):
    result=validate('D19-main',source,tmp_path)
    assert not result['passed'],result


def test_sensitive_accidental_output_is_not_echoed(tmp_path):
    secret='fake-test-secret-do-not-echo'
    result=validate('D19-package',PACKAGE_VERSION+f'print({secret!r})\n',tmp_path)
    assert not result['passed']
    assert secret not in repr(result)


def test_deadline_rejects_hanging_import_without_service(tmp_path,monkeypatch):
    monkeypatch.setattr(artifact_checks,'ARTIFACT_TIMEOUT',1)
    result=validate('D19-package',PACKAGE_VERSION+'while True:\n    pass\n',tmp_path)
    assert not result['passed']
    assert result['checks'][0]['name']=='导入和入口运行限时'
    assert '1 秒' in result['checks'][0]['detail']


def test_artifact_checks_do_not_write_learner_workspace(tmp_path):
    ws=tmp_path/'learner_workspace'/'task-manager'/'taskproj'
    ws.mkdir(parents=True)
    init=ws/'__init__.py'
    init.write_text(PACKAGE_VERSION,encoding='utf-8')
    before=init.read_bytes()
    assert validate('D19-package',PACKAGE_DOC,tmp_path)['passed']
    assert init.read_bytes()==before
    assert list(ws.iterdir())==[init]

def test_import_error_locates_student_line_without_echoing_message(tmp_path):
    result=validate('D19-package',PACKAGE_VERSION+'1/0\n',tmp_path)
    check=next(item for item in result['checks'] if item['name']=='当前模块可导入')
    assert not check['passed']
    assert check['detail']=='ZeroDivisionError，第 2 行'


def test_config_reads_environment_without_modifying_it(tmp_path):
    broken=CONFIG.replace('def get_db_path():','def get_db_path():\n    os.environ["UNRELATED_CONFIG"]="changed"')
    result=validate('D19-config',broken,tmp_path)
    assert not result['passed']
    assert any('环境写入' in check.get('actual','') for check in result['checks'])

"""Staged D06-D11 behavior regressions, run with an isolated temporary workspace."""
from __future__ import annotations
import importlib.util
import json
import os
import sys
from pathlib import Path
import pytest

# In the final repository use its installed validator; in staging load sibling draft.
REPOSITORY = Path(__file__).resolve().parents[1]
if not (REPOSITORY/'learnctl/practice.py').is_file():
    REPOSITORY = Path(os.environ.get('LEARNCTL_REPOSITORY',r'D:\codex\MY-工作台'))
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0,str(REPOSITORY))
from learnctl.practice import _CODE_VALIDATORS, validate_code
from scripts.d09_course import BUILD_PARSER, PARSE_ERROR, ENTRY
DATA=json.loads((REPOSITORY/'data/curriculum.json').read_text(encoding='utf-8'))
SECTIONS={s['id']:s for t in DATA['tasks'] for s in t['lesson']}

GOOD={
'D07-main':'''def main():
    print('直接运行')
if __name__ == '__main__':
    main()
''',
'D07-inheritance':'''class Task:
    def __init__(self,title): self.title=title
    def label(self): return self.title
class TimedTask(Task):
    def __init__(self,title,deadline):
        super().__init__(title)
        self.deadline=deadline
    def label(self): return super().label()+' ('+str(self.deadline)+')'
''',
'D08-json-report':'''import json
from pathlib import Path
def write_report(rows,path):
    done=sum(row['done'] for row in rows)
    report={'total':len(rows),'done':done,'pending':len(rows)-done}
    Path(path).write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
''',
'D09-errors':PARSE_ERROR,
'D09-subcommands':BUILD_PARSER,
'D09-entry':ENTRY,
'D10-config':'''from dataclasses import dataclass
@dataclass
class Settings:
    db_path: str='taskproj.db'
    debug: bool=False
    port: int=8000
    @classmethod
    def from_env(cls,env):
        raw=env.get('DEBUG','false').strip().lower()
        if raw in {'true','1','yes'}: debug=True
        elif raw in {'false','0','no'}: debug=False
        else: raise ValueError('invalid DEBUG')
        port=int(env.get('PORT','8000'))
        if not 1<=port<=65535: raise ValueError('invalid PORT')
        return cls(env.get('DB_PATH') or 'taskproj.db',debug,port)
''',
'D11-logger':'''import logging
def get_logger():
    logger=logging.getLogger('course.base')
    logger.setLevel(logging.INFO); logger.propagate=False
    if not logger.handlers: logger.addHandler(logging.NullHandler())
    return logger
''',
'D11-format':'''import logging
def build_formatter():
    return logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
''',
'D11-stream':'''import logging,io
def build_stream_logger():
    logger=logging.getLogger('course.stream')
    for handler in logger.handlers[:]:
        logger.removeHandler(handler); handler.close()
    stream=io.StringIO(); handler=logging.StreamHandler(stream)
    handler.setLevel(logging.WARNING); logger.setLevel(logging.INFO)
    logger.addHandler(handler); logger.propagate=False
    return logger,stream
''',
'D11-file':'''import logging
def configure_file_logger(path):
    logger=logging.getLogger('course.file')
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler); handler.close()
    handler=logging.FileHandler(path,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger
''',
}

@pytest.mark.parametrize('sid',list(GOOD))
def test_ready_contract_accepts_executed_implementation(sid,tmp_path):
    result=validate_code(SECTIONS[sid],GOOD[sid],tmp_path)
    assert result['passed'],(sid,result)
    assert result['cases'] and all('actual' in c for c in result['cases'])
    assert not (tmp_path/'.learn').exists()
    assert not (tmp_path/'learner_workspace').exists()

WRONG=[
('D07-main','import-side-effect',GOOD['D07-main']+"\nprint('导入污染')\n"),
('D07-main','guard-never-invokes',GOOD['D07-main'].replace('    main()','    pass')),
('D07-inheritance','no-parent-init',GOOD['D07-inheritance'].replace('super().__init__(title)','self.title=title')),
('D07-inheritance','fixed-title',GOOD['D07-inheritance'].replace('return self.title',"return '固定标题'")),
('D08-json-report','fake-counts',GOOD['D08-json-report'].replace("done=sum(row['done'] for row in rows)",'done=1')),
('D08-json-report','no-write',"import json\ndef write_report(rows,path): return json.dumps({'total':3,'done':1,'pending':2})"),
('D09-errors','title-optional',GOOD['D09-errors'].replace('parser.add_argument("title")','parser.add_argument("title",nargs="?",default="x")')),
('D09-errors','limit-text',GOOD['D09-errors'].replace('type=int,','')),
('D09-errors','swallow-error',GOOD['D09-errors'].replace('    return parser.parse_args(argv)',"    try: return parser.parse_args(argv)\n    except SystemExit: return argparse.Namespace(title='x',limit=10)")),
('D09-errors','unnecessary-positive-limit',GOOD['D09-errors'].replace('    return parser.parse_args(argv)',"    args=parser.parse_args(argv)\n    if args.limit<0: parser.error('positive only')\n    return args")),
('D09-subcommands','no-dispatch',GOOD['D09-subcommands'].replace('listing.set_defaults(func=handle_list)','listing.set_defaults(func=None)')),
('D09-subcommands','same-handler',GOOD['D09-subcommands'].replace('func=handle_add','func=handle_list')),
('D09-entry','ignore-argv',GOOD['D09-entry'].replace('args = adjustment_options(argv)','args = adjustment_options([])')),
('D09-entry','script-swallows-error-code',GOOD['D09-entry'].replace('raise SystemExit(main())','try:\n        main()\n    except SystemExit:\n        pass')),
('D10-config','false-truthy',GOOD['D10-config'].replace('debug=False','debug=True')),
('D10-config','no-port-boundary',GOOD['D10-config'].replace("        if not 1<=port<=65535: raise ValueError('invalid PORT')",'')),
('D10-config','blank-debug-default',GOOD['D10-config'].replace("env.get('DEBUG','false').strip().lower()","(env.get('DEBUG') or 'false').strip().lower()")),
('D11-logger','accumulate-handler',GOOD['D11-logger'].replace('if not logger.handlers: logger.addHandler','logger.addHandler')),
('D11-logger','hide-info',GOOD['D11-logger'].replace('logging.INFO','logging.WARNING')),
('D11-format','message-only',GOOD['D11-format'].replace('%(asctime)s %(levelname)s %(name)s %(message)s','%(message)s')),
('D11-format','old-signature',GOOD['D11-format'].replace('def build_formatter','def formatter')),
('D11-stream','allows-info',GOOD['D11-stream'].replace('handler.setLevel(logging.WARNING)','handler.setLevel(logging.INFO)')),
('D11-stream','accumulate-handler',GOOD['D11-stream'].replace('    for handler in logger.handlers[:]:\n        logger.removeHandler(handler); handler.close()\n','')),
('D11-file','logger-handler-tuple',GOOD['D11-file'].replace('return logger','return logger,handler')),
('D11-file','message-only-no-level',GOOD['D11-file'].replace('%(levelname)s %(message)s','%(message)s')),
('D11-file','accumulate-handler',GOOD['D11-file'].replace('    for handler in logger.handlers[:]:\n        logger.removeHandler(handler); handler.close()\n','')),
('D11-file','drop-without-close',GOOD['D11-file'].replace('logger.removeHandler(handler); handler.close()','logger.removeHandler(handler)')),
]

@pytest.mark.parametrize('sid,label,code',WRONG,ids=[sid+'-'+label for sid,label,_ in WRONG])
def test_ready_contract_rejects_observable_fault(sid,label,code,tmp_path):
    result=validate_code(SECTIONS[sid],code,tmp_path)
    assert not result['passed'],(sid,label,result)
    # Runtime faults are either actual cases or a real failed harness process.
    assert result.get('cases') or result['exit_code'] != 0,result


def test_parse_errors_preserves_actual_code_and_default(tmp_path):
    result=validate_code(SECTIONS['D09-errors'],GOOD['D09-errors'],tmp_path)
    assert result['passed']
    assert result['cases'][0]['actual']=="('盘点', 10)"
    error=next(case for case in result['cases'] if "abc" in case['input'])
    assert error['actual']=="{'退出码': 2, '普通输出': False, '错误输出': True}"


def test_import_noise_has_its_actual_stdout(tmp_path):
    result=validate_code(SECTIONS['D07-main'],GOOD['D07-main']+"\nprint('导入污染')\n",tmp_path)
    case=next(c for c in result['cases'] if c['name']=='导入不执行入口')
    assert not case['passed'] and '导入污染' in case['actual']


def test_file_logging_original_course_signature_remains_compatible(tmp_path):
    # Current repository regression defines a logger-only return, without setting propagation.
    assert validate_code(SECTIONS['D11-file'],GOOD['D11-file'],tmp_path)['passed']

@pytest.mark.parametrize('sid',list(GOOD))
def test_unedited_readiness_starter_is_not_accepted(sid,tmp_path):
    result=validate_code(SECTIONS[sid],SECTIONS[sid]['practice']['starter_content'],tmp_path)
    assert not result['passed'],(sid,result)


def test_subcommands_handlers_return_declared_business_result(tmp_path):
    code=GOOD['D09-subcommands'].replace('return "查看库存"','print("查看库存")').replace('return f"登记：{args.title}"','print(f"登记：{args.title}")')
    assert code != GOOD['D09-subcommands']
    result=validate_code(SECTIONS['D09-subcommands'],code,tmp_path)
    assert not result['passed']
    assert any(not case['passed'] and 'None' in case['actual'] for case in result['cases'])


def test_subcommands_shared_handler_does_not_implement_add(tmp_path):
    code=GOOD['D09-subcommands'].replace('    parser = argparse.ArgumentParser', "    def local_handler(args): return '查看库存'\n    parser = argparse.ArgumentParser").replace('func=handle_list','func=local_handler').replace('func=handle_add','func=local_handler')
    result=validate_code(SECTIONS['D09-subcommands'],code,tmp_path)
    assert not result['passed']
    assert any(c['name']=='list 绑定并调用查看函数' and c['passed'] for c in result['cases'])
    assert any(c['name']=='add 绑定并接收完整参数' and not c['passed'] for c in result['cases'])


def test_logger_allows_real_stream_handler(tmp_path):
    code=GOOD['D11-logger'].replace('logging.NullHandler()','logging.StreamHandler()')
    assert validate_code(SECTIONS['D11-logger'],code,tmp_path)['passed']


def test_entry_private_parser_helper_signature_is_unrestricted(tmp_path):
    helper = 'def build_parser(prog):\n    return argparse.ArgumentParser(prog=prog)\n'
    code=GOOD['D09-entry'].replace('import argparse\n','import argparse\n'+helper).replace('argparse.ArgumentParser(prog="stock_adjust")',"build_parser('local')")
    assert code != GOOD['D09-entry']
    assert validate_code(SECTIONS['D09-entry'],code,tmp_path)['passed']

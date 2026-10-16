"""D06-D11 observable course behavior checks."""
from __future__ import annotations
from learnctl.contract_checks import behavior, value_case, error_case

CLI_SETUP = '''
import argparse, contextlib, io, subprocess, sys
observations = []
def capture_parse(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = M.parse_or_error(argv)
            value = (result.title, result.limit, None, out.getvalue(), bool(err.getvalue()))
        except SystemExit as error:
            value = (None, None, error.code, out.getvalue(), bool(err.getvalue()))
    observations.append({'argv':argv,'result':value,'stderr':err.getvalue()})
    return value

def capture_subcommand(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = command_parser.parse_args(argv)
            returned = result.func(result)
            value = (result.command, getattr(result,'title',None), callable(result.func), True, None, bool(err.getvalue()))
        except SystemExit as error:
            value = (None,None,False,None,error.code,bool(err.getvalue()))
    observations.append({'argv':argv,'result':value,'stdout':out.getvalue(),'stderr':err.getvalue()})
    return value

def capture_entry(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = M.main(argv)
        except SystemExit as error:
            result = ('unexpected SystemExit',error.code)
    observations.append({'argv':argv,'return':result,'stdout':out.getvalue(),'stderr':err.getvalue()})
    return result,out.getvalue(),bool(err.getvalue())

def run_entry(argv):
    run = subprocess.run([sys.executable,*argv],capture_output=True,text=True,encoding='utf-8',timeout=3)
    observations.append({'argv':argv,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    return run.returncode,run.stdout,bool(run.stderr)
'''

MAIN_SETUP = '''
import subprocess, sys
# Run both forms in real separate processes so import side effects cannot hide.
direct = subprocess.run([sys.executable,'main.py'],capture_output=True,text=True,encoding='utf-8',timeout=3)
imported = subprocess.run([sys.executable,'-c','import main'],capture_output=True,text=True,encoding='utf-8',timeout=3)
explicit = subprocess.run([sys.executable,'-c','import main; main.main()'],capture_output=True,text=True,encoding='utf-8',timeout=3)
'''

INHERITANCE_SETUP = '''
parent_calls = []
original_init = M.Task.__init__
def tracked_init(self,title):
    parent_calls.append(title)
    original_init(self,title)
M.Task.__init__ = tracked_init
first = M.TimedTask('学习甲',30)
second = M.TimedTask('交付乙',7)
first_label,second_label = first.label(),second.label()
M.Task.__init__ = original_init
'''

REPORT_SETUP = '''
Path('reports').mkdir()
def read_report(rows,name):
    path=Path('reports')/name
    M.write_report(rows,path)
    text=path.read_text(encoding='utf-8')
    return json.loads(text),text.rstrip('\\n')
'''

LOGGER_SETUP = '''
import logging
logger = M.get_logger()
logger_again = M.get_logger()
configured_handlers = list(logger.handlers)
records = []
class Capture(logging.Handler):
    def emit(self,record): records.append((record.levelname,record.getMessage()))
capture=Capture()
logger.addHandler(capture)
try:
    logger.debug('隐藏调试')
    logger.info('正常记录')
    logger.warning('提醒记录')
finally:
    logger.removeHandler(capture)
    capture.close()
'''

FORMAT_SETUP = '''
import logging, sys
formatter = M.build_formatter()
record = logging.LogRecord('course.format',logging.INFO,'',0,'loaded %s',('中文',),None)
formatted = formatter.format(record)
try:
    raise ValueError('格式演示错误')
except ValueError:
    exception_record = logging.LogRecord('course.format',logging.ERROR,'',0,'failed',(),sys.exc_info())
exception_text = formatter.format(exception_record)
'''

STREAM_SETUP = '''
import logging
first_logger,first_stream = M.build_stream_logger()
logger,stream = M.build_stream_logger()
configured_handlers = list(logger.handlers)
stream.seek(0); stream.truncate(0)
logger.debug('隐藏调试')
logger.info('隐藏信息')
logger.warning('警告甲')
logger.error('错误乙')
stream_text = stream.getvalue()
for candidate in (first_logger,logger):
    for handler in list(candidate.handlers):
        candidate.removeHandler(handler); handler.close()
'''

FILE_SETUP = '''
import logging
Path('logs').mkdir()
def observe_file(name,tag):
    path=Path('logs')/name
    first=M.configure_file_logger(path)
    first_handlers=list(first.handlers)
    logger=M.configure_file_logger(path)
    handlers=list(logger.handlers)
    old_resources_ok=all(h in handlers or getattr(h,'stream',None) is None for h in first_handlers)
    logger.info('保存中文%s',tag)
    try:
        raise ValueError('日志演示'+tag)
    except ValueError:
        logger.exception('处理失败%s',tag)
    for candidate in (first,logger):
        for handler in list(candidate.handlers):
            candidate.removeHandler(handler); handler.close()
    closed=all(getattr(h,'stream',None) is None for h in handlers if isinstance(h,logging.FileHandler))
    text=path.read_text(encoding='utf-8')
    path.unlink()
    return {
        'file_handlers':sum(isinstance(h,logging.FileHandler) for h in handlers),
        'stable_format':all(isinstance(h.formatter,logging.Formatter) for h in handlers if isinstance(h,logging.FileHandler)) and 'INFO' in text and 'ERROR' in text,
        'info_once':text.count('保存中文'+tag),
        'info_level':'INFO' in text,
        'traceback':'Traceback' in text and ('ValueError: 日志演示'+tag) in text,
        'closed':closed,
        'old_resources_closed_or_reused':old_resources_ok,
        'file_deleted':not path.exists(),
    }
'''


def register(registry):
    v,e=value_case,error_case
    registry['D07-main'] = behavior([
        v('direct.returncode',0,'直接运行退出 0'),
        v('len(direct.stdout.splitlines())',1,'直接运行只输出一行'),
        v('bool(direct.stdout.strip())',True,'入口行非空'),
        v('direct.stderr','','直接运行不写错误流'),
        v('(imported.returncode,imported.stdout,imported.stderr)',(0,'',''),'导入不执行入口'),
        v('explicit.returncode',0,'main 可显式调用'),
        {'expression':'explicit.stdout','expected_value':'direct.stdout','label':'显式 main 与直接运行输出一致'},
    ],setup=MAIN_SETUP)
    registry['D07-inheritance'] = behavior([
        v("M.Task('基础甲').label()",'基础甲','父类保留标题'),
        v("M.Task('基础乙').label()",'基础乙','父类响应不同标题'),
        v('issubclass(M.TimedTask,M.Task)',True,'TimedTask 继承 Task'),
        v("parent_calls",['学习甲','交付乙'],'每次子类构造调用父初始化一次'),
        v("isinstance(first_label,str) and '学习甲' in first_label and '30' in first_label",True,'子类包含标题与 deadline'),
        v("isinstance(second_label,str) and '交付乙' in second_label and '7' in second_label",True,'不同子类输入得到对应标签'),
    ],setup=INHERITANCE_SETUP)
    registry['D08-json-report'] = behavior([
        v("read_report([{'done':True},{'done':False},{'done':False}], 'mixed.json')",({'total':3,'done':1,'pending':2},'{\n  "done": 1,\n  "pending": 2,\n  "total": 3\n}'),'统计并写回稳定 JSON'),
        v("read_report([], 'empty.json')",({'total':0,'done':0,'pending':0},'{\n  "done": 0,\n  "pending": 0,\n  "total": 0\n}'),'空输入写回全零'),
        v("read_report([{'done':True},{'done':True}], 'done.json')[0]",{'total':2,'done':2,'pending':0},'全部完成不产生未完成计数'),
    ],setup=REPORT_SETUP)
    registry['D09-errors'] = behavior([
        v("capture_parse(['买书'])",('买书',10,None,'',False),'成功返回 TITLE 与默认 limit'),
        v("capture_parse(['学习甲','--limit','3'])",('学习甲',3,None,'',False),'limit 转成整数'),
        v("capture_parse(['原样标题','--limit','-2'])",('原样标题',-2,None,'',False),'本节不额外限制整数范围'),
        v('capture_parse([])',(None,None,2,'',True),'缺少 TITLE：SystemExit(2)，仅 stderr'),
        v("capture_parse(['x','--limit','bad'])",(None,None,2,'',True),'坏整数：SystemExit(2)，仅 stderr'),
        v("capture_parse(['x','--unknown'])",(None,None,2,'',True),'未知选项：SystemExit(2)，仅 stderr'),
    ],setup=CLI_SETUP)
    registry['D09-subcommands'] = behavior([
        v("capture_subcommand(['list'])",('list',None,True,True,None,False),'list 分派到可调用处理函数'),
        v("capture_subcommand(['add','  原样标题  '])",('add','  原样标题  ',True,True,None,False),'add 保留 TITLE 并调用处理函数'),
        v("command_parser.parse_args(['list']).func is not command_parser.parse_args(['add','x']).func",True,'两个子命令绑定不同函数'),
        v('capture_subcommand([])',(None,None,False,None,2,True),'必须选择子命令'),
        v("capture_subcommand(['unknown'])",(None,None,False,None,2,True),'未知子命令报错'),
        v("capture_subcommand(['add'])",(None,None,False,None,2,True),'add 必须提供 TITLE'),
    ],setup=CLI_SETUP+'\ncommand_parser = M.build_parser()\n')
    registry['D09-entry'] = behavior([
        v('capture_entry([])',(0,'10\n',False),'main 默认 limit，返回 0'),
        v("capture_entry(['--limit','3','--verbose'])",(0,'3\n',False),'main 接收显式 argv'),
        v("capture_entry(['--limit','bad'])",(2,'',True),'main 参数错误返回 2'),
        v("capture_entry(['--unknown'])",(2,'',True),'main 未知选项返回 2'),
        v("run_entry(['main.py','--limit','7'])",(0,'7\n',False),'真实入口传递合法 argv'),
        v("run_entry(['main.py','--limit','bad'])",(2,'',True),'真实入口传递错误退出码'),
        v("run_entry(['main.py','--unknown'])",(2,'',True),'真实入口未知选项返回 2'),
        v("capture_entry(['--help'])[0]",0,'函数帮助路径返回 0'),
        v("run_entry(['main.py','--help'])[0]",0,'帮助退出 0'),
        v("run_entry(['-c',\"import sys; sys.argv=['ignored','--unknown']; import main\"])",(0,'',False),'导入不解析外部 argv 或打印'),
    ],setup=CLI_SETUP)
    registry['D10-config'] = behavior([
        v("(M.Settings.from_env({}).db_path,M.Settings.from_env({}).debug,M.Settings.from_env({}).port)",('taskproj.db',False,8000),'缺失配置使用默认'),
        v("(M.Settings.from_env({'DB_PATH':'data/custom.db','DEBUG':' YES ','PORT':'8080'}).db_path,M.Settings.from_env({'DEBUG':' YES '}).debug,M.Settings.from_env({'PORT':'8080'}).port)",('data/custom.db',True,8080),'覆盖与规范化转换'),
        v("M.Settings.from_env({'DB_PATH':''}).db_path",'taskproj.db','空路径采用默认'),
        v("M.Settings.from_env({'DEBUG':'false'}).debug",False,'false 不按非空字符串转换'),
        v("type(M.Settings.from_env({}).debug) is bool and type(M.Settings.from_env({}).port) is int",True,'返回实际 bool 与 int 类型'),
        v("M.Settings.from_env({'PORT':'65535'}).port",65535,'端口上界允许'),
        v("M.Settings.from_env({'PORT':'1'}).port",1,'端口下界允许'),
        e("M.Settings.from_env({'DEBUG':'maybe'})",'ValueError','非法布尔失败'),
        e("M.Settings.from_env({'DEBUG':''})",'ValueError','空布尔失败'),
        e("M.Settings.from_env({'PORT':''})",'ValueError','空端口失败'),
        e("M.Settings.from_env({'PORT':'no'})",'ValueError','非法整数失败'),
        e("M.Settings.from_env({'PORT':'0'})",'ValueError','端口下界之外失败'),
        e("M.Settings.from_env({'PORT':'65536'})",'ValueError','端口上界之外失败'),
    ])
    registry['D11-logger'] = behavior([
        v('isinstance(logger,logging.Logger)',True,'返回 Logger'),
        v('logger is logger_again',True,'重复配置返回同名 logger'),
        v('len(configured_handlers)',1,'重复配置只有一个 handler'),
        v('isinstance(configured_handlers[0],logging.Handler)',True,'基础 logger 配置实际 handler'),
        v('logger.propagate',False,'不向父 logger 重复传播'),
        v('records',[('INFO','正常记录'),('WARNING','提醒记录')],'实际日志过滤 DEBUG、允许 INFO/WARNING'),
    ],setup=LOGGER_SETUP)
    registry['D11-format'] = behavior([
        v('isinstance(formatter,logging.Formatter)',True,'返回 Formatter'),
        v("'INFO' in formatted and 'course.format' in formatted and 'loaded 中文' in formatted",True,'实际格式包含级别、名称与参数化消息'),
        v("bool(getattr(record,'asctime','')) and record.asctime in formatted",True,'实际格式包含记录时间'),
        v("'Traceback' in exception_text and 'ValueError: 格式演示错误' in exception_text",True,'异常记录保留 traceback'),
    ],setup=FORMAT_SETUP)
    registry['D11-stream'] = behavior([
        v('len(configured_handlers)',1,'重复配置只保留一个输出 handler'),
        v('isinstance(configured_handlers[0],logging.StreamHandler) and configured_handlers[0].stream is stream',True,'handler 使用返回的可读 stream'),
        v("'隐藏调试' in stream_text or '隐藏信息' in stream_text",False,'低于 WARNING 的消息不输出'),
        v("stream_text.count('警告甲')",1,'WARNING 实际写入一次'),
        v("stream_text.count('错误乙')",1,'ERROR 实际写入一次'),
    ],setup=STREAM_SETUP)
    expected_file={'file_handlers':1,'stable_format':True,'info_once':1,'info_level':True,'traceback':True,'closed':True,'old_resources_closed_or_reused':True,'file_deleted':True}
    registry['D11-file'] = behavior([
        v("observe_file('one.log','甲')",expected_file,'真实 UTF-8 文件、异常、幂等配置及资源关闭'),
        v("observe_file('two.log','乙')",expected_file,'传入其他路径仍正确写入与关闭'),
    ],setup=FILE_SETUP)
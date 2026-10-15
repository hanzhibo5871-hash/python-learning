"""Behavioral checks for staged D09 contracts, including real command execution."""
from __future__ import annotations
from .contract_checks import behavior, value_case

_SETUP = r'''
import argparse, contextlib, io, subprocess, sys

def fields(function, argv, *names):
    args = function(argv)
    if not isinstance(args, argparse.Namespace):
        raise TypeError('请返回解析得到的 Namespace')
    return tuple(getattr(args, name) for name in names)

def exit_streams(function, argv):
    out, err = io.StringIO(), io.StringIO()
    code = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: function(argv)
        except SystemExit as error: code = error.code
    return {'退出码': code, '普通输出': bool(out.getvalue()), '错误输出': bool(err.getvalue())}

def reset_stock():
    M.STOCK.clear()
    M.STOCK.update({'纸盒': 10, '原料': 20})

def stock_call(name, argv):
    reset_stock()
    result = getattr(M, name)(argv)
    return result, dict(M.STOCK)

def stock_error(name, argv):
    reset_stock()
    result = exit_streams(getattr(M, name), argv)
    return result, dict(M.STOCK)

def stock_sequence(name):
    reset_stock()
    prefix = [] if name == 'adjust_stock' else ['adjust']
    first = getattr(M, name)(prefix + ['纸盒', '--delta', '5'])
    second = getattr(M, name)(prefix + ['纸盒', '--delta', '-2'])
    return first, second, dict(M.STOCK)

def parse_bound(argv):
    parser = M.build_parser()
    if not isinstance(parser, argparse.ArgumentParser):
        raise TypeError('build_parser 应返回解析器，不是解析结果')
    return parser.parse_args(argv)

def dispatch(argv):
    args = parse_bound(argv)
    return args.command, callable(args.func), args.func(args)

def call_once():
    calls = []
    def handler(value):
        calls.append(value)
        return value * 2
    return M.call_action(handler, 4), calls

def run_entry(argv):
    result = subprocess.run([sys.executable, 'main.py', *argv], capture_output=True,
                            text=True, encoding='utf-8', timeout=4, shell=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def entry_status(argv):
    code, out, err = run_entry(argv)
    return {'退出码': code, '普通输出': bool(out), '错误输出': bool(err)}

def import_entry():
    result = subprocess.run([sys.executable, '-c', "import sys; sys.argv=['caller','--unknown']; import main; print(main.STOCK['原料'])"],
                            capture_output=True, text=True, encoding='utf-8', timeout=4, shell=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def direct_main():
    reset_stock()
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        value = M.main(['原料', '--delta', '-3'])
    return value, dict(M.STOCK), out.getvalue().strip(), err.getvalue().strip()
'''
_ERROR = {'退出码': 2, '普通输出': False, '错误输出': True}
_HELP = {'退出码': 0, '普通输出': True, '错误输出': False}
_INITIAL = {'纸盒': 10, '原料': 20}


def register(registry):
    v = value_case
    specs = {
        'D09-argv': [
            v("M.input_parts(['原料','--delta','-3'])", ('原料','--delta','-3'), '保留三个字符串'),
            v("M.input_parts(['纸盒','--delta','5'])", ('纸盒','--delta','5'), '换商品和正数输入'),
            v("M.input_parts(['原料','--delta','0'])", ('原料','--delta','0'), '零也保持文本形式')],
        'D09-position': [
            v("fields(M.product_options, ['原料'], 'product')", ('原料',), '商品名称进入 Namespace.product'),
            v("fields(M.product_options, ['纸盒'], 'product')", ('纸盒',), '不写死商品名')],
        'D09-options': [
            v("fields(M.adjustment_options, ['原料','--delta','-3'], 'product','delta')", ('原料',-3), '负数出库合法'),
            v("fields(M.adjustment_options, ['纸盒','--delta','5'], 'product','delta')", ('纸盒',5), '正数入库合法'),
            v("fields(M.adjustment_options, ['纸盒'], 'product','delta')", ('纸盒',0), '省略选项默认0'),
            v("type(M.adjustment_options(['原料','--delta','0']).delta).__name__", 'int', '调整量确实是整数'),
            v("fields(M.adjustment_options, ['原料','--delta','+7'], 'delta')", (7,), '带正号的整数合法')],
        'D09-stock': [
            v("stock_call('adjust_stock',['原料','--delta','-3'])", (17,{'纸盒':10,'原料':17}), '更新原库存并返回17'),
            v("stock_call('adjust_stock',['纸盒','--delta','5'])", (15,{'纸盒':15,'原料':20}), '入库不影响另一个商品'),
            v("stock_call('adjust_stock',['原料'])", (20,_INITIAL), '省略调整量不改变库存'),
            v("stock_call('adjust_stock',['原料','--delta','-30'])", (-10,{'纸盒':10,'原料':-10}), '不擅自禁止负库存'),
            v("stock_sequence('adjust_stock')", (15,13,{'纸盒':13,'原料':20}), '连续调用累计变化'),
            v("stock_error('adjust_stock',['原料','--delta','abc'])", (_ERROR,_INITIAL), '解析失败不修改库存')],
        'D09-parser': [
            v("fields(M.parse_args, [], 'limit','verbose')", (10,False), '默认条数和开关'),
            v("fields(M.parse_args, ['--limit','3','--verbose'], 'limit','verbose')", (3,True), '带值选项与开关'),
            v("fields(M.parse_args, ['--verbose'], 'limit','verbose')", (10,True), '开关不需要填写值'),
            v("fields(M.parse_args, ['--limit','-3'], 'limit','verbose')", (-3,False), '本节不限制整数正负'),
            v("(type(M.parse_args([]).limit).__name__,type(M.parse_args([]).verbose).__name__)", ('int','bool'), '整数与布尔类型')],
        'D09-command-name': [
            v("fields(M.command_options, ['show'], 'command')", ('show',), '只识别命令'),
            v("hasattr(M.command_options(['show']), 'product')", False, '商品参数只属于 adjust'),
            v("fields(M.command_options, ['adjust','原料','--delta','-3'], 'command','product','delta')", ('adjust','原料',-3), '命令与各自参数'),
            v("fields(M.command_options, ['adjust','纸盒'], 'command','product','delta')", ('adjust','纸盒',0), '子命令自己的默认值')],
        'D09-if-dispatch': [
            v("stock_call('run_stock',['show'])", (_INITIAL,_INITIAL), '查看不修改库存'),
            v("stock_call('run_stock',['adjust','原料','--delta','-3'])", (17,{'纸盒':10,'原料':17}), '选择更新分支'),
            v("stock_call('run_stock',['adjust','纸盒'])", (10,_INITIAL), '省略调整量'),
            v("stock_call('run_stock',['adjust','原料','--delta','-30'])", (-10,{'纸盒':10,'原料':-10}), '允许完整有符号范围'),
            v("stock_sequence('run_stock')", (15,13,{'纸盒':13,'原料':20}), '分派后保留累计状态'),
            v("stock_error('run_stock',['adjust','原料','--delta','abc'])", (_ERROR,_INITIAL), '坏整数不修改库存'),
            v("stock_error('run_stock',['missing'])", (_ERROR,_INITIAL), '未知命令不执行业务')],
        'D09-function-value': [
            v('call_once()', (8,[4]), '调用一次并返回结果'),
            v("M.call_action(lambda value: '查看：'+value, '原料')", '查看：原料', '支持不同处理函数'),
            v("M.call_action(lambda args: args.product, argparse.Namespace(product='纸盒'))", '纸盒', '参数对象也是普通的输入值')],
        'D09-subcommands': [
            v("dispatch(['list'])", ('list',True,'查看库存'), 'list 绑定并调用查看函数'),
            v("dispatch(['add','原料出库3袋'])", ('add',True,'登记：原料出库3袋'), 'add 绑定并接收完整参数'),
            v("dispatch(['add','纸盒 入库 5 个'])", ('add',True,'登记：纸盒 入库 5 个'), '标题不写死、不拆开')],
        'D09-errors': [
            v("fields(M.parse_or_error, ['盘点'], 'title','limit')", ('盘点',10), '成功返回参数和默认值'),
            v("fields(M.parse_or_error, ['盘点','--limit','-3'], 'title','limit')", ('盘点',-3), '负数不是形式错误')],
        'D09-entry': [
            v("run_entry(['原料','--delta','-3'])", (0,'原料 当前库存：17',''), '真实命令原料出库'),
            v("run_entry(['纸盒','--delta','5'])", (0,'纸盒 当前库存：15',''), '终端换商品必须生效'),
            v("run_entry(['原料'])", (0,'原料 当前库存：20',''), '终端省略调整量'),
            v("run_entry(['原料','--delta','-30'])", (0,'原料 当前库存：-10',''), '终端不禁止负库存'),
            v('import_entry()', (0,'20',''), '导入不解析、不输出、不更新库存'),
            v('direct_main()', (0,{'纸盒':10,'原料':17},'原料 当前库存：17',''), '显式列表调用返回0'),
            v('exit_streams(M.main, [])', _ERROR, '显式空列表不等于 None'),
            v("entry_status(['原料','--delta','abc'])", _ERROR, '终端拒绝坏整数'),
            v('entry_status([])', _ERROR, '缺商品退出2'),
            v("entry_status(['原料','--unknown'])", _ERROR, '终端拒绝未知选项'),
            v("entry_status(['--help'])", _HELP, '帮助输出并退出0')],
    }
    errors = {
        'D09-position': ('M.product_options',[[],['纸盒','--unknown']]),
        'D09-options': ('M.adjustment_options',[[],['原料','--delta','abc'],['原料','--unknown']]),
        'D09-parser': ('M.parse_args',[['--limit','abc'],['--unknown']]),
        'D09-command-name': ('M.command_options',[[],['other'],['adjust'],['show','原料']]),
        'D09-subcommands': ('parse_bound',[[],['other'],['add']]),
        'D09-errors': ('M.parse_or_error',[[],['盘点','--limit','abc'],['盘点','--limit'],['盘点','--unknown']]),
    }
    for sid, (function, arguments) in errors.items():
        for argv in arguments:
            specs[sid].append(v(f'exit_streams({function}, {argv!r})', _ERROR, f'库按规则拒绝 {argv!r}'))
        specs[sid].append(v(f"exit_streams({function}, ['--help'])", _HELP, '库提供帮助，不算错误'))
    for sid, cases in specs.items():
        registry[sid] = behavior(cases, setup=_SETUP)

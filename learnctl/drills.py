"""入门练习的服务端测试样例；不随课程 API 返回。"""

# 脚本练习：stdin、预期 stdout。多个输入可发现只打印固定答案的程序。
SCRIPT_CASES = {
    'D02-input': [('3\n', '6'), ('0\n', '0'), ('12\n', '24')],
    'D02-receipt': [('12.5\n2\n', '总价：25.00'), ('3.2\n3\n', '总价：9.60'), ('0\n3\n', '总价：0.00')],
    'D02-normalize': [('  Alice  \n', 'alice'), ('PYTHON_01\n', 'python_01'), ('   \n', '')],
    'D03-delivery': [('98.99\n', '8'), ('99\n', '0'), ('0\n', '8'), ('120\n', '0')],
    'D03-odd-total': [('5\n', '9'), ('6\n', '9'), ('0\n', '0'), ('7\n', '16')],
    'D03-countdown': [('3\n', '3\n2\n1\n完成'), ('0\n', '完成'), ('1\n', '1\n完成')],
}

FUNCTION_CASES = {
    'D04-shipping': [('达到免运费边界', 'M.shipping(99) == 0'), ('未达到边界', 'M.shipping(98.99) == 8'), ('零金额', 'M.shipping(0) == 8')],
    'D04-greeting': [('默认问候语', "M.greet('小林') == '你好，小林'"), ('关键字参数', "M.greet('阿青', greeting='欢迎') == '欢迎，阿青'"), ('位置参数', "M.greet('小林', '早上好') == '早上好，小林'")],
    'D04-convert': [('零度', 'M.to_fahrenheit(0) == 32'), ('负温度', 'M.to_fahrenheit(-40) == -40'), ('沸点', 'M.to_fahrenheit(100) == 212')],
    'D05-tags': [('首次出现顺序', "M.unique_tags(['py','js','py']) == ['py','js']"), ('空列表', 'M.unique_tags([]) == []'), ('不修改原列表', "(lambda x: (M.unique_tags(x), x)[1])(['a','a']) == ['a','a']")],
    'D05-counts': [('中文商品计数', "M.count_items(['茶','水','茶']) == {'茶':2,'水':1}"), ('空输入', 'M.count_items([]) == {}'), ('单项', "M.count_items(['a']) == {'a':1}")],
    'D05-cart': [('多项购物车', "M.cart_total([{'price':10,'quantity':2},{'price':3,'quantity':4}]) == 32"), ('空购物车', 'M.cart_total([]) == 0'), ('数量为零', "M.cart_total([{'price':12.5,'quantity':0}]) == 0"), ('不修改商品', "(lambda x: (M.cart_total(x),x)[1])([{'price':2,'quantity':3}]) == [{'price':2,'quantity':3}]")],
    'D06-parse': [('合法文本与空白', "M.parse_quantity(' 12 ') == 12"), ('无效文本', "M.parse_quantity('abc') is None"), ('零是合法数值', "M.parse_quantity('0') == 0"), ('负整数', "M.parse_quantity('-2') == -2")],
    'D06-positive': [('合法数量', "M.positive_quantity('3') == 3"), ('零必须报错', "_raises(ValueError, M.positive_quantity, '0')"), ('负数必须报错', "_raises(ValueError, M.positive_quantity, '-1')"), ('非法文本', "_raises(ValueError, M.positive_quantity, 'abc')")],
    'D06-average': [('普通平均值', 'M.average([2,4,6]) == 4'), ('真实的零', 'M.average([0,0]) == 0'), ('空输入抛错', '_raises(ValueError, M.average, [])'), ('小数结果', 'M.average([1,2]) == 1.5')],
    'D07-slug': [('文本清理', "M.slugify(' Hello Python ') == 'hello-python'"), ('空文本', "M.slugify('') == ''"), ('中文文本', "M.slugify(' Python 入门 ') == 'python-入门'")],
    'D07-counter': [('初始状态', 'M.Counter().value == 0'), ('连续调用', '(lambda c: (c.increment(),c.increment(),c.value))(M.Counter()) == (1,2,2)'), ('对象相互独立', '(lambda a,b: (a.increment(),b.value))(M.Counter(),M.Counter()) == (1,0)')],
    'D07-dataclass-total': [('金额计算', 'M.LineItem(12.5,2).total() == 25'), ('零数量', 'M.LineItem(5,0).total() == 0'), ('使用数据类', '__import__("dataclasses").is_dataclass(M.LineItem)')],
    'D08-read-lines': [('清理姓名和空行', "M.read_names('names.txt') == ['小林','阿青']"), ('空文件', "M.read_names('empty.txt') == []"), ('文件不存在', "_raises(FileNotFoundError, M.read_names, 'missing.txt')")],
    'D08-json-total': [('汇总金额', "M.total_expenses('expenses.json') == 20"), ('空账单', "M.total_expenses('empty.json') == 0"), ('解析错误可见', "_raises(json.JSONDecodeError, M.total_expenses, 'broken.json')")],
    'D08-json-report-drill': [('真实文件内容', "(M.write_report('report.json',['小林']),json.loads(Path('report.json').read_text(encoding='utf-8')))[1] == {'count':1,'names':['小林']}"), ('中文未转义', "'小林' in Path('report.json').read_text(encoding='utf-8')"), ('可覆盖空报告', "(M.write_report('report.json',[]),json.loads(Path('report.json').read_text(encoding='utf-8')))[1] == {'count':0,'names':[]}")],
}

FILE_FIXTURES = {
    'D08-read-lines': [('names.txt', ' 小林 \n\n 阿青 \n'), ('empty.txt', '')],
    'D08-json-total': [('expenses.json', '[{"amount":12.5},{"amount":7.5}]'), ('empty.json', '[]'), ('broken.json', '{bad}')],
}

# argv、预期输出、预期退出码；None 只表示输出内容可随 argparse 版本改变。
CLI_CASES = {
    'D09-greet-cli': [(['main.py','--name','小林'], '你好，小林', 0), (['main.py','--name','阿青'], '你好，阿青', 0), (['main.py'], None, 2), (['main.py','--help'], None, 0)],
    'D09-repeat-cli': [(['main.py','--word','hi','--count','2'], 'hi\nhi', 0), (['main.py','--word','茶'], '茶', 0), (['main.py','--word','hi','--count','0'], None, 2), (['main.py','--word','hi','--count','-1'], None, 2)],
    'D09-square-cli': [(['main.py','-3'], '9', 0), (['main.py','0'], '0', 0), (['-c','import main; print(main.square(4))'], '16', 0)],
}

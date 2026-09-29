"""零基础的离线加练题。题目与输入输出公开，判定实现留在服务端。"""

from copy import deepcopy


# 每题接续一个已讲解的知识点；不新增完成门槛，也不重置已有学习记录。
DRILLS = [
    ("D02-input", "D02-names", "加练 · 输入与类型转换", "把键盘输入的数量变成可计算的整数。",
     "input() 读入一行文字，即使输入 3，得到的也是字符串。int() 才把数字文本转换成整数；print() 将计算结果显示出来。页面验证会自动提供输入，在自己的终端运行时则由你输入并按回车。",
     "读取一行非负整数数量，输出它的两倍。使用 input() 读取，不添加输入提示文字，只输出一行结果。",
     "quantity = input()\n# 先转成 int，再计算两倍并打印\n", "3 → 6；0 → 0；12 → 24。",
     "先试 int('3') 和 '3' * 2 的区别；后者得到重复文本。", [("3", "6"), ("0", "0")]),
    ("D02-receipt", "D02-string-methods", "加练 · 购物小票", "把计算、类型转换和格式化组合起来。",
     "小票需要把价格作为 float、数量作为 int，再用乘法计算总额。f-string 的 :.2f 只决定显示两位小数，不会把价格变成整数，也不改变原数值；先计算再展示更容易检查错误。",
     "用两个 input() 依次读取单价和数量，只输出一行 总价：金额，金额保留两位小数，例如 总价：25.00。",
     "price = float(input())\nquantity = int(input())\n# 计算总价，用 f-string 输出\n", "12.5 和 2 → 总价：25.00；0 和 3 → 总价：0.00。",
     "花括号里写表达式，冒号后写 .2f；不要把单价和数量当文本拼接。", [("12.5\n2", "总价：25.00"), ("3.2\n3", "总价：9.60")]),
    ("D02-normalize", "D02-strings", "加练 · 清理账号输入", "从一条带空白和大小写的文本得到统一账号。",
     "strip() 只移除两端空白，不会删除姓名或账号内部的空格。lower() 返回小写的新字符串；Python 字符串不能原地修改，所以需要接住返回值，最后再打印清理后的结果。",
     "读取一行账号，先去掉首尾空白，再全部转小写，只打印清理后的账号。只含空白时输出空行。",
     "account = input()\n# 依次清理两端空白和大小写\n", "  Alice  → alice；全空白 → 空行。",
     "可以分两次赋值，也可以链式调用；输入与输出均为字符串。", [("  Alice  ", "alice"), ("PYTHON_01", "python_01")]),
    ("D03-delivery", "D03-if", "加练 · 运费边界", "练习把文字规则变成互斥分支。",
     "订单金额达到 99 元免运费，意味着 99 本身应进入免运费分支。用 >= 表达包含边界的判断，else 负责其余合法金额；测试 98.99、99 和 100 可以发现大于号写错的问题。",
     "读取一行非负订单金额；金额 >= 99 输出 0，否则输出 8。只输出运费数字。",
     "amount = float(input())\n# 按免运费边界写 if/else\n", "98.99 → 8；99 → 0；0 → 8。",
     "不要用两个相互覆盖的 if；确认恰好达到 99 的情况。", [("98.99", "8"), ("99", "0")]),
    ("D03-odd-total", "D03-for", "加练 · 奇数累加", "独立完成范围、判断与累加。",
     "range 的右端不包含在循环中，要包含 n 就写到 n + 1。总和需要在循环前初始化为 0，每次只把奇数加入；当 n 为 0 时循环为空，初始的 0 就是合理结果。",
     "读取一行非负整数 n，使用循环计算 1 到 n（包含 n）中所有奇数的和，打印总和。",
     "n = int(input())\ntotal = 0\n# 用循环和取余判断完成累加\n", "5 → 9；6 → 9；0 → 0。",
     "number % 2 != 0 可以识别奇数；print 应放在循环结束后。", [("5", "9"), ("0", "0")]),
    ("D03-countdown", "D03-while", "加练 · 修复倒计时", "通过更新循环变量让程序正确结束。",
     "while 每轮重新判断条件，条件成立才执行循环体。倒计时从 n 开始，每输出一次要减一；减法放在循环外会让正数输入一直循环，输出顺序也会影响是否包含起点。",
     "读取非负整数 n，用 while 逐行输出 n 到 1，最后输出 完成。n=0 时只输出 完成。",
     "remaining = int(input())\nwhile remaining > 0:\n    print(remaining)\n    # 补充更新条件的语句\nprint('完成')\n", "3 → 三行 3/2/1 后一行 完成；0 → 完成。",
     "检查 remaining 是否在每轮循环中减少。", [("3", "3\n2\n1\n完成"), ("0", "完成")]),
    ("D04-shipping", "D04-def-return", "加练 · 可复用的运费函数", "把学过的分支提取为可多次调用的函数。",
     "相同的运费规则可以封装进 shipping(amount)，由调用者传入金额。函数应 return 数字而不是只 print；测试代码需要拿到返回值继续计算，屏幕上出现正确数字不能代替返回值正确。",
     "定义 shipping(amount)：amount >= 99 返回整数 0，否则返回整数 8。参数保证为非负数，不在函数内调用 input。",
     "def shipping(amount):\n    # 根据金额返回运费\n    pass\n", "shipping(99) == 0；shipping(98.99) == 8。",
     "把上一题的输入改成参数，把输出改成 return。", [("shipping(99)", "0"), ("shipping(0)", "8")]),
    ("D04-greeting", "D04-default-keyword", "加练 · 默认参数与关键字", "用一个默认值支持两种调用方式。",
     "默认参数在调用没有传值时生效，显式传入的值会覆盖它。把问候语设为默认参数，比复制两份函数更清楚；返回字符串时要保留中文逗号，调用者才能稳定展示结果。",
     "定义 greet(name, greeting='你好')，返回 greeting + 中文逗号 + name。支持 greet('小林') 和 greet('小林', greeting='早上好')。",
     "def greet(name, greeting='你好'):\n    pass\n", "greet('小林') → 你好，小林；传入 早上好 → 早上好，小林。",
     "默认值写在定义中，关键字参数写在调用中。", [("greet('小林')", "你好，小林"), ("greet('阿青', greeting='欢迎')", "欢迎，阿青")]),
    ("D04-convert", "D04-def-return", "加练 · 温度换算", "把公式写成只依赖参数的函数。",
     "摄氏度转华氏度的公式是 c * 9 / 5 + 32；运算符优先级决定先乘除再加。函数不需要读取全局变量，每次调用都应使用本次传入的 c，负温度和零温度也属于正常输入。",
     "定义 to_fahrenheit(c)，返回 c * 9 / 5 + 32 的数值结果，不要返回带单位的字符串。",
     "def to_fahrenheit(c):\n    pass\n", "0 → 32；100 → 212；-40 → -40。",
     "先计算数值，显示单位留给调用者。", [("to_fahrenheit(0)", "32.0"), ("to_fahrenheit(-40)", "-40.0")]),
    ("D05-tags", "D05-dict-set", "加练 · 保持顺序的去重", "同时考虑唯一性、顺序和原数据。",
     "set 可以去重，但不能用于承诺按首次出现的次序输出。这里用结果列表记录第一次见到的元素，重复项不再加入；输入列表属于调用者，不应在遍历时删除其中的元素。",
     "定义 unique_tags(tags)，返回按首次出现顺序去重的新列表，且不修改 tags。tags 中均为字符串。",
     "def unique_tags(tags):\n    result = []\n    # 遍历 tags，把第一次出现的项加入 result\n    return result\n", "['py','js','py'] → ['py','js']；[] → []；原列表不变。",
     "用 not in 检查结果列表；不要直接返回 list(set(tags))。", [("unique_tags(['py', 'js', 'py'])", "['py', 'js']"), ("unique_tags([])", "[]")]),
    ("D05-counts", "D05-traversal", "加练 · 统计商品数量", "把循环得到的元素累积到字典中。",
     "字典把商品名映射到出现次数。第一次见到一个商品时没有对应键，可以用 get(name, 0) 取得初始计数，再加一写回；空列表没有任何商品，因此返回空字典。",
     "定义 count_items(items)，返回每个字符串出现次数的字典；不改变输入列表。",
     "def count_items(items):\n    counts = {}\n    # 每遇到一次商品，把其计数加一\n    return counts\n", "['茶','水','茶'] → {'茶':2,'水':1}；[] → {}。",
     "每次更新一个键，不要把整个字典替换为当前商品。", [("count_items(['茶','水','茶'])", "{'茶': 2, '水': 1}"), ("count_items([])", "{}")]),
    ("D05-cart", "D05-traversal", "加练 · 独立写购物车汇总", "将列表、字典、函数和循环组合为一个小功能。",
     "购物车是由商品字典组成的列表，每项有 price 和 quantity。先计算单项金额，再把每项金额累加；不要只求单价之和，也不要把最后一项金额直接当作总价。空购物车的总金额是 0。",
     "定义 cart_total(items)，每项含数值 price 和整数 quantity，返回 sum(price * quantity) 的金额。不要改写输入数据。",
     "def cart_total(items):\n    total = 0\n    # 读取每项的 price 与 quantity\n    return total\n", "价格 10 数量 2 加价格 3 数量 4 → 32；空列表 → 0。",
     "先用一项商品验证，再增加第二项和数量为零的项。", [("cart_total([{'price':10,'quantity':2}])", "20"), ("cart_total([])", "0")]),
    ("D06-parse", "D06-try-except", "加练 · 识别无效整数", "只捕获题目规定的转换错误。",
     "int('12') 成功，而 int('abc') 抛 ValueError；这表示文本无法按整数解析。题目约定对这种输入返回 None，保留 0 作为真实数值；只捕获 ValueError 可以避免掩盖其他编程错误。",
     "定义 parse_quantity(text)，整数文本返回 int；无效整数文本返回 None。输入保证是字符串，允许负数和首尾空白。",
     "def parse_quantity(text):\n    # 在 try 中转换，只捕获 ValueError\n    pass\n", "' 12 ' → 12；'abc' → None；'0' → 0；'-2' → -2。",
     "不要用 if not result 判断失败，因为 0 是有效数量。", [("parse_quantity(' 12 ')", "12"), ("parse_quantity('x')", "None")]),
    ("D06-positive", "D06-raise", "加练 · 明确拒绝非法数量", "用异常表达业务输入不符合规则。",
     "转换成功只说明输入是整数，不代表符合业务规则。正整数数量不能为 0 或负数，应在转换后额外判断；主动 raise ValueError 让调用者知道失败，返回 0 则会把失败伪装成合法数量。",
     "定义 positive_quantity(text)：返回转换后的正整数。文本不是整数或数值 <= 0 时必须抛 ValueError。",
     "def positive_quantity(text):\n    quantity = int(text)\n    # 检查正整数约束，最后返回 quantity\n", "'3' → 3；'0'、'-1'、'abc' → ValueError。",
     "int 本身会拒绝非法文本，你只需补数值范围检查。", [("positive_quantity('3')", "3"), ("positive_quantity('0')", "抛 ValueError")]),
    ("D06-average", "D06-raise", "加练 · 空列表与平均值", "分清没有数据和结果恰好为零。",
     "平均值是总和除以个数；空列表的个数是 0，必须先明确没有数据时的行为。这里约定抛 ValueError，而 [0, 0] 应得到真正的 0；这样的接口才不会混淆缺失与计算结果。",
     "定义 average(values)，非空数值列表返回平均值，空列表抛 ValueError；不修改原列表。",
     "def average(values):\n    # 先处理空列表，再计算平均值\n    pass\n", "[2,4,6] → 4；[0,0] → 0；[] → ValueError。",
     "len(values) 是数量；先处理数量为零的输入。", [("average([2,4,6])", "4.0"), ("average([])", "抛 ValueError")]),
    ("D07-slug", "D07-import", "加练 · 可被导入的文本工具", "把字符串处理函数交给另一个模块调用。",
     "模块被 import 时会执行顶层语句，因此可复用工具不应在导入时询问输入或打印演示。定义函数不会立刻运行函数体，调用者之后可多次传入不同标题生成稳定的短标识。",
     "定义 slugify(title)：去掉两端空白、转小写，把剩余的普通空格替换为连字符。导入 main 时不得打印内容。",
     "def slugify(title):\n    pass\n\n# 若要演示，放在 __main__ 守卫内\n", "' Hello Python ' → 'hello-python'；'' → ''；导入无输出。",
     "复用 strip/lower/replace，演示与工具定义分开。", [("slugify(' Hello Python ')", "hello-python"), ("slugify('')", "")]),
    ("D07-counter", "D07-class-instance", "加练 · 两个独立的计数器", "理解每个对象拥有自己的属性。",
     "self.value 应在 __init__ 中为每个新对象设置为 0。increment 修改当前对象的属性并返回新值，两个 Counter 实例不应互相影响；使用共享的全局计数会破坏这种隔离。",
     "定义 Counter 类：初始化 value=0，increment() 加一并返回新值；两个实例各自计数。",
     "class Counter:\n    def __init__(self):\n        self.value = 0\n\n    def increment(self):\n        pass\n", "同一对象连续调用 → 1、2；新对象第一次调用 → 1。",
     "读取和写入都使用 self.value；不要创建全局 count。", [("c=Counter(); c.increment()", "1"), ("a=Counter(); b=Counter(); a.increment(); b.value", "0")]),
    ("D07-dataclass-total", "D07-dataclass", "加练 · 数据对象与计算", "为结构化商品数据增加一个小方法。",
     "dataclass 根据字段声明生成初始化方法，让 price 和 quantity 的来源清晰。方法仍是普通 Python 函数，必须通过 self 读取当前商品字段；不同对象的金额要根据各自数据计算。",
     "用 @dataclass 定义 LineItem，字段 price: float、quantity: int；total() 返回 price * quantity。",
     "from dataclasses import dataclass\n\n@dataclass\nclass LineItem:\n    price: float\n    quantity: int\n\n    def total(self):\n        pass\n", "LineItem(12.5,2).total() → 25；数量 0 → 0。",
     "字段声明写在类中，计算写在方法中。", [("LineItem(12.5, 2).total()", "25.0"), ("LineItem(5, 0).total()", "0")]),
    ("D08-read-lines", "D08-utf8", "加练 · 整理文本名单", "将文件内容清理为可使用的姓名列表。",
     "read_text(encoding='utf-8') 明确文本编码，splitlines() 处理换行。每行去掉首尾空白后，仅保留非空姓名；文件不存在应保留 FileNotFoundError，让调用者知道源数据缺失。",
     "定义 read_names(path)，UTF-8 读取文本文件，返回去掉空白行和姓名首尾空白的列表。保留原顺序，文件不存在时让异常传出。",
     "from pathlib import Path\n\ndef read_names(path):\n    # 读取文件、分行、清理后返回列表\n    pass\n", "包含 小林、空白行、阿青 的文件 → ['小林','阿青']；空文件 → []。",
     "验证器会准备临时文件并传入路径，不需要自己填写电脑上的绝对路径。", [("read_names('names.txt')，文件：小林\\n\\n 阿青 ", "['小林', '阿青']"), ("read_names('empty.txt')，空文件", "[]")]),
    ("D08-json-total", "D08-json-read", "加练 · 从 JSON 汇总金额", "把文件读取、JSON 解析和容器计算连接起来。",
     "JSON 文件里存放的是文本，json.loads 后才变成可遍历的 Python 列表。每项 amount 是数值，函数计算所有金额之和；非法 JSON 应保留解析错误，不能改成空列表后报告 0。",
     "定义 total_expenses(path)，读取 UTF-8 JSON 列表，每项有数值 amount，返回金额之和。空列表返回 0；非法 JSON 抛 JSONDecodeError。",
     "from pathlib import Path\nimport json\n\ndef total_expenses(path):\n    pass\n", "[{'amount':12.5},{'amount':7.5}] → 20；[] → 0。",
     "文件文本 → Python 列表 → 累加；分别检查这三个步骤。", [("total_expenses('expenses.json')，内容为两笔 12.5、7.5", "20.0"), ("total_expenses('empty.json')，内容为 []", "0")]),
    ("D08-json-report-drill", "D08-json-report", "加练 · 写出可读的中文报告", "让自己的程序产生一个可再次读取的文件。",
     "序列化把字典变成 JSON 文本，写文件时仍需要指定 UTF-8。ensure_ascii=False 让中文在文件里直接可读；返回路径或在屏幕上打印字典都不能代替真正写入指定文件。",
     "定义 write_report(path, names)，写入 {'count': len(names), 'names': names}，UTF-8 且中文不转义。无需返回值；允许覆盖指定报告文件。",
     "from pathlib import Path\nimport json\n\ndef write_report(path, names):\n    pass\n", "names=['小林'] → 文件可读回 {'count':1,'names':['小林']}。",
     "json.dumps(..., ensure_ascii=False) 生成文本，再 write_text。", [("write_report('report.json', ['小林'])", "文件内含中文 小林，count 为 1"), ("write_report('report.json', [])", "count 为 0，names 为 []")]),
    ("D09-greet-cli", "D09-parser", "加练 · 第一个问候命令", "在命令行参数中传入姓名。",
     "argparse 从程序参数读取 --name，required=True 将缺失参数变成明确的用法错误。命令行提示和业务输出应该分开，--help 自动给出帮助；用户无需修改源代码就能传入不同姓名。",
     "编写 main.py：必填参数 --name，运行时输出 你好，姓名。缺少参数应非零退出，--help 应成功退出。",
     "import argparse\n\nparser = argparse.ArgumentParser()\n# 声明必填 --name，解析后打印问候\n", "--name 小林 → 你好，小林；不传 --name → 参数错误。",
     "声明参数、parse_args()、使用 args.name，按这三步完成。", [("python main.py --name 小林", "你好，小林"), ("python main.py --help", "显示帮助并成功退出")]),
    ("D09-repeat-cli", "D09-errors", "加练 · 命令参数的合法范围", "用类型转换和业务检查拒绝错误参数。",
     "type=int 只保证参数可以转为整数，不会拒绝 0 和负数。解析后检查 count >= 1，不满足时调用 parser.error；这样用户既能看到原因，也能从非零退出码判断失败。",
     "main.py 接收必填 --word 与 --count（整数，默认 1）；逐行输出 word 共 count 次，count <= 0 时用 parser.error 拒绝。",
     "import argparse\n\nparser = argparse.ArgumentParser()\n# 声明参数、校验 count，再逐行输出\n", "--word hi --count 2 → 两行 hi；--count 0 → 非零退出。",
     "默认值也是合法输入；print 每轮一次，不要一次打印列表。", [("python main.py --word hi --count 2", "hi\nhi"), ("python main.py --word 茶", "茶")]),
    ("D09-square-cli", "D09-entry", "加练 · 可导入的计算命令", "同时提供函数接口和终端入口。",
     "一个文件可以同时服务于其他模块和命令行用户：square(n) 负责计算，守卫中的代码负责解析参数。import main 时应只定义函数，既不读参数也不打印结果，避免导入时触发命令错误。",
     "定义 square(n) 返回平方；直接运行 main.py 时接收一个整数位置参数并打印平方。用 __main__ 守卫保护参数解析，import main 不产生输出。",
     "import argparse\n\ndef square(n):\n    pass\n\nif __name__ == '__main__':\n    # 在这里解析整数参数并调用 square\n    pass\n", "python main.py -3 → 9；import main; main.square(4) → 16。",
     "参数解析只能在直接运行时发生，函数必须始终可导入。", [("python main.py -3", "9"), ("python main.py 0", "0")]),
]


DRILL_ERRORS = {
    'D02-input': [("print(input() * 2)", '输入 3 得到 33', '数量仍是文本，乘法重复了文本', '先用 int 转换数量再乘二'), ("int(quantity)\nprint(quantity * 2)", '转换后仍在重复文本', 'int 返回新值，没有改写 quantity', '接住转换结果，再用这个整数计算')],
    'D02-receipt': [("print(price + quantity)", '小票总额算成了相加', '购物金额是单价乘数量，不是两项相加', '用乘法计算总额'), ("print(f'总价：{total}')", '小票小数位数不固定', '没有指定显示精度，25.0 不等于题目的 25.00', '在表达式后使用 :.2f')],
    'D02-normalize': [("account.strip()\nprint(account)", '账号两端仍有空白', '清理方法返回的新字符串没有被使用', '把 strip 结果重新赋值或直接链式调用'), ("print(account.replace(' ', ''))", '账号内部空格也被删掉', 'replace 会移除所有普通空格，超出了清理两端的规则', '用 strip 去两端，再 lower')],
    'D03-delivery': [("if amount > 99: print(0)", '99 元仍被收运费', '大于号没有包含免运费的起点', '使用 >=99 判断'), ("if amount >= 99: print(0)\nprint(8)", '免运费订单输出两行', '第二个 print 位于分支外，总会执行', '将收费输出放入 else 分支')],
    'D03-odd-total': [("for n in range(1, n):\n    total += n", '既漏终点又加了偶数', 'range 终点不包含，且没有取余筛选', '使用 n+1 并只累加奇数'), ("for number in range(n):\n    total = 0", '奇数总和反复归零', '累计变量在循环体里重新初始化', '把 total=0 放在循环前')],
    'D03-countdown': [("while remaining > 0:\n    print(remaining)", '倒计时一直输出同一个数', '决定是否继续的 remaining 没有减少', '每轮在块内执行 remaining -= 1'), ("while remaining >= 0:\n    print(remaining)\n    remaining -= 1", '倒计时多输出了零', '条件把零也包含进循环', '只在 remaining>0 时进入循环')],
    'D04-shipping': [("def shipping(amount):\n    print(8)", '函数调用拿到 None', '运费被打印了，但没有返回给调用者', '使用 return 把数值交给调用方'), ("def shipping(amount):\n    return '0'", '运费类型变成了字符串', '引号让数字变成文本，后续无法直接相加', '返回数值 0 或 8')],
    'D04-greeting': [("def greet(name, greeting):\n    return name", '只传姓名时报缺少参数', 'greeting 没有声明默认值', "定义时设置 greeting='你好'"), ("return greeting + ',' + name", '问候语的逗号不一致', '使用了英文逗号而题目约定中文逗号', '逐字核对输出契约，使用中文逗号')],
    'D04-convert': [("return c * (9 // 5) + 32", '华氏度换算斜率错误', '整除把 9/5 截成了 1', '使用普通除法 /'), ("return str(c * 9 / 5 + 32)", '温度返回文本', '把计算结果提前格式化，不再是可计算数值', '直接返回计算结果，单位交给显示层')],
    'D05-tags': [("return list(set(tags))", '标签顺序不稳定', '集合去重没有承诺首次出现的列表顺序', '按原列表遍历，第一次出现才追加'), ("tags.remove(tag)", '原始标签列表被改动', '遍历时删除输入元素，既改原数据又容易漏项', '维护一个新的结果列表')],
    'D05-counts': [("counts[item] += 1", '首次遇到商品就 KeyError', '字典没有该商品的初始计数', '使用 get(item,0) 再加一'), ("counts = {item: 1}", '只保留了最后一个商品', '每一轮都创建新字典替换之前的累计结果', '只更新 counts[item] 这一个键')],
    'D05-cart': [("total += item['price']", '购物车忽略数量', '累计了单价而不是每项的金额', '每次先乘 quantity 再相加'), ("for item in items:\n    total = item['price'] * item['quantity']", '购物车只有末项金额', '赋值覆盖已有总额，没有执行累加', '用 += 保留前面各项金额')],
    'D06-parse': [("return int(text)", '无效数量文本直接崩溃', '没有按约定捕获整数转换产生的 ValueError', '用 try/except ValueError 返回 None'), ("return int(text) or None", '有效的零被当作失败', 'or 使用真值规则，0 会选择 None', '转换成功后直接返回整数，包括 0')],
    'D06-positive': [("return int(text)", '负数数量也被接受', '只检查了格式，没有检查正数约束', '转换后在 quantity<=0 时 raise ValueError'), ("if quantity <= 0: return 0", '非法数量被包装成零', '返回正常数值掩盖了应当抛出的业务错误', '明确 raise ValueError 并说明数量应为正')],
    'D06-average': [("return sum(values) / len(values)", '空数据变成除零错误', '尚未判断列表是否为空就做除法', '空列表先抛题目约定的 ValueError'), ("if not sum(values): raise ValueError()", '全零数据也被拒绝', '用总和而不是数量判断有没有数据', '检查 values 是否为空，保留零平均值')],
    'D07-slug': [("print(slugify('Hello'))", '导入工具时出现演示输出', '模块顶层语句在 import 时就会执行', '演示调用放入 __main__ 守卫'), ("return title.lower().replace(' ', '-')", '短标识两端多了连字符', '替换前没有去掉标题两端空白', '先 strip，再 lower 和 replace')],
    'D07-counter': [("count = 0\ndef increment(self):\n    global count", '多个对象共享计数', '计数放在全局变量中，所有实例访问同一份数据', '在 __init__ 中设置每个对象的 self.value'), ("self.value + 1\nreturn self.value", '计数器一直返回零', '加法只算出了结果，没有重新赋值给属性', '使用 self.value += 1 更新当前对象')],
    'D07-dataclass-total': [("class LineItem:\n    price: float\n    quantity: int", '无法通过字段参数初始化', '漏写 @dataclass，普通类型标注不会自动生成初始化方法', '导入并应用 dataclass 装饰器'), ("def total(self):\n    return price * quantity", '商品方法里名字未定义', '字段属于当前对象，不是函数局部变量', '通过 self.price 和 self.quantity 读取')],
    'D08-read-lines': [("return Path(path).read_text().splitlines()", '名单仍有空行和首尾空白', '分行没有完成逐行清理，也未明确编码', '用 UTF-8 读取后，逐行 strip 并过滤空行'), ("except FileNotFoundError:\n    return []", '文件丢失被当成空名单', '捕获异常后返回正常结果，无法区分缺文件与空文件', '保留 FileNotFoundError，让调用者处理')],
    'D08-json-total': [("for item in Path(path).read_text():\n    total += item['amount']", '把字符当成了账单项', '文件文本尚未经 json.loads 解析为列表', '先解析 JSON，再遍历字典项'), ("except json.JSONDecodeError:\n    return 0", '损坏账单也报告零支出', '错误数据被包装成合法空账单结果', '让解析异常传出，只有真正空列表返回零')],
    'D08-json-report-drill': [("return {'count': len(names), 'names': names}", '报告文件没有生成', '返回内存字典不等于将文本写入文件', '序列化字典并用指定路径写文件'), ("json.dumps(report)", '中文报告里出现转义序列', '默认 ensure_ascii=True 会把非 ASCII 字符转义', '设置 ensure_ascii=False 并以 UTF-8 写入')],
    'D09-greet-cli': [("parser.add_argument('--name')", '缺少姓名时仍可运行', '参数没有被标记为 required', '将 --name 声明为 required=True'), ("name = input()", '问候命令等待键盘输入', '题目要求从命令参数读取，而不是 stdin', '使用 parse_args().name 获取传入姓名')],
    'D09-repeat-cli': [("parser.add_argument('--count', default=1)", '指定次数后无法传给 range', '显式命令参数仍是字符串，未声明 type=int', '为 count 增加 type=int'), ("for _ in range(args.count): print(args.word)", '负数次数静默不输出', 'range 对负数为空，但业务规则要求拒绝', '循环前对 count<=0 调用 parser.error')],
    'D09-square-cli': [("args = parser.parse_args()", '导入计算模块也读取命令参数', '参数解析放在了守卫外，import 会执行', '把解析和打印放在 __main__ 守卫内'), ("def square(n):\n    return n * 2", '平方被算成两倍', '相乘两次同一个数与乘二是不同运算', '用 n*n 或 n**2，并测试负数')],
}


def add_beginner_drills(data):
    tasks = {task['id']: task for task in data['tasks']}
    for section_id, parent_id, title, goal, reason, instructions, starter, expected, hints, cases in DRILLS:
        task = tasks[section_id[:3]]
        parent = next(section for section in task['lesson'] if section['id'] == parent_id)
        section = deepcopy(parent)
        section.update(id=section_id, title=title, optional=True, objective=goal,
                       explanation=[reason, *parent['explanation'][:2]])
        section['key_points'] = [goal, hints, expected]
        section['steps'] = ['先用第一个输入检查正常结果', '独立补全代码，再检查边界输入', '读懂失败反馈，修改后重新验证']
        section['common_errors'] = [
            {'error': symptom, 'symptom': symptom, 'cause': cause, 'fix': fix,
             'example': {'code': code, 'symptom': symptom, 'fix': fix}}
            for code, symptom, cause, fix in DRILL_ERRORS[section_id]
        ]
        section['guided_practice'] = {
            'goal': goal, 'starter': starter,
            'steps': [{'action': f'使用输入：{value}', 'expected': output if output else '空字符串'} for value, output in cases],
            'check': expected,
        }
        section['practice'] = {
            'kind': 'code', 'file_name': 'main.py', 'scenario': goal,
            'instructions': instructions, 'starter_content': starter,
            'starter_policy': 'complete', 'expected_behavior': expected, 'hints': hints,
            'input_examples': [{'label': f'练习输入 {i + 1}', 'value': value, 'expected': output if output else '空字符串'}
                               for i, (value, output) in enumerate(cases)],
        }
        task['lesson'].append(section)


def align_beginner_contracts(data):
    """基础课先写顺序程序，D04 再引入自定义函数。"""
    tasks = {task['id']: task for task in data['tasks']}
    sections = {s['id']: s for t in data['tasks'] for s in t['lesson']}
    contracts = {
        'D02-names': ("score = 88\n# 输出类型名和是否为 int，再重新绑定到字符串 '88'\n",
                      "令 score=88，依次打印 type(score).__name__、isinstance(score, int)；再把 score 绑定到字符串 '88' 并打印类型名。",
                      [('运行 main.py', 'int\nTrue\nstr'), ("将整数和字符串的类型作比较", '整数为 int，文本为 str')]),
        'D02-numbers': ("total = int(input())\nsize = int(input())\n# 在同一行打印整数商与余数\n",
                        "依次读取两个整数 total 和 size（保证 size>0），用 // 和 % 计算商与余数，print 在同一行输出，中间一个空格。",
                        [('17\n5', '3 2'), ('0\n4', '0 0')]),
        'D02-bool-none': ("value = None\n# 打印 value is None 和 bool(value)\n# 再分别对 0 和空字符串重复这一步\n",
                          "依次令 value 为 None、0、空字符串；每次都用 print(value is None, bool(value)) 输出两个判断，共三行。此处不需要分支或函数。",
                          [('value = None', 'True False'), ('value = 0 或空字符串', 'False False')]),
        'D02-strings': ("text = input()\n# 去掉首尾空白后，用切片反转并打印\n",
                        "读取一行文本，先 strip() 去掉两端空白，再用 [::-1] 反转并打印。空文本输出空行，不用定义函数。",
                        [(' ab ', 'ba'), ('Python', 'nohtyP')]),
        'D02-string-methods': ("raw = input()\n# strip 清理两端，split 按逗号分割，再用 ' / ' 连接\n",
                               "读取一行逗号分隔的标签，先去掉整行两端空白，再 split(',') 并用 ' / '.join(...) 输出。输入保证每个标签非空，标签内部无多余空白。",
                               [('  a,b  ', 'a / b'), ('python', 'python')]),
        'D03-if': ("score = int(input())\n# 按从高到低的顺序判断，并输出一个等级\n",
                   "读取整数分数：负数输出 非法；>=90 输出 A；60到89 输出 B；0到59 输出 C。用 if/elif/else，不需要定义函数或抛异常。",
                   [('90', 'A'), ('59', 'C')]),
        'D03-match': ("command = input()\n# 匹配 list、add 和其他命令\n",
                      "读取命令字符串，用 match/case 对 list 输出 查看，对 add 输出 新增，其他字符串输出 未知。",
                      [('list', '查看'), ('delete', '未知')]),
        'D03-for': ("n = int(input())\ntotal = 0\n# for 遍历 1 到 n，把偶数加入 total\n",
                    "读取非负整数 n，用 for 和 range 累加 1 到 n（包含 n）的偶数，最后打印 total。n=0 输出 0。",
                    [('5', '6'), ('0', '0')]),
        'D03-while': ("remaining = int(input())\nwhile remaining > 0:\n    print(remaining)\n    # 每轮减一\n",
                      "读取非负整数 n，用 while 逐行打印 n 到 1；n=0 不打印任何内容。记得在循环内更新 remaining。",
                      [('3', '3\n2\n1'), ('0', '无输出')]),
        'D03-break-continue': ("n = int(input())\nfor number in range(1, n + 1):\n    # 超过 5 时 break，偶数时 continue，否则打印\n    pass\n",
                               "读取非负整数 n，遍历 1 到 n；超过 5 时 break，遇偶数时 continue，其余数字逐行打印。",
                               [('8', '1\n3\n5'), ('2', '1')]),
    }
    for section_id, (starter, instructions, cases) in contracts.items():
        section = sections[section_id]
        practice = section['practice']
        practice.pop('input_identifiers', None)
        practice.update(starter_content=starter, starter_policy='complete', instructions=instructions,
                        scenario=section['objective'], expected_behavior=instructions,
                        input_examples=[{'label': f'输入 {i+1}', 'value': value, 'expected': output}
                                        for i, (value, output) in enumerate(cases)])
        section['guided_practice'] = {'goal': section['objective'], 'starter': starter,
            'steps': [{'action': f'用 {value} 检查程序', 'expected': output} for value, output in cases],
            'check': instructions}
        section['steps'] = ['阅读示例并预测输出', '补全实践区中的代码', '运行验证，并根据输入与实际输出修正']
        if 'input()' in starter:
            section['explanation'] = [
                "实践区会用 input() 接收文本；int(input()) 将一行整数文本转成整数。点击运行时工具会自动提供题目中的输入；你在终端运行同一程序时，需自己输入并按回车。现在只写顺序语句，不必提前学习函数定义。",
                *section['explanation'][:2],
            ]
    # 容器和推导式会在 D05 系统讲解，先完成控制流即可继续基础主线。
    for section_id in ('D03-enumerate-zip', 'D03-comprehension', 'D04-varargs'):
        sections[section_id]['optional'] = True
    sections['D02-execution']['examples'][0]['explanation'] = (
        "if True 的缩进行在条件成立时执行，所以先打印第一句，再打印缩进块。Python 要求同一块缩进一致，通常使用四个空格；把块内语句完全顶格会报 IndentationError，单行缩进三个空格本身并不必然报错。"
    )
    sections['D02-execution']['practice']['input_examples'][1].update(
        value='将 BLOCK 行取消缩进后运行 main.py', expected='解释器报告 IndentationError，程序无法执行。')
    tasks['D02'].update(
        learning_goal='从打印第一行文字开始，认识变量与类型，完成数字计算、输入转换和字符串清理。',
        coding_task='在本页完成顺序执行、类型观察、数字计算和字符串处理；加练输入、小票和账号清理。',
        artifacts=['exercises/form.py'],
        acceptance=['能解释每行代码的执行顺序', '区分整数、文本、布尔值和 None', '根据实际输入得到正确输出'],
    )
    tasks['D03']['learning_goal'] = '用分支表达不同规则，用 for/while 完成重复计算；函数与容器组合在后续任务系统学习。'
    tasks['D04']['learning_goal'] = '把已经会写的小程序封装成函数，掌握参数、默认值、返回值与局部作用域。'

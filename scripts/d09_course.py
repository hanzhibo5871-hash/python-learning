"""D09: one concept at a time, with executable examples and deliberate gaps.

This is build-time course content, not a learner solution module. Keep the four
historical core IDs and three optional IDs so saved submissions remain addressable.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

ADJUST_OPTIONS = '''import argparse

def adjustment_options(argv):
    parser = argparse.ArgumentParser(prog="stock_adjust")
    parser.add_argument("product")
    parser.add_argument("--delta", type=int, default=0)
    return parser.parse_args(argv)
'''
STOCK = '\nSTOCK = {"纸盒": 10, "原料": 20}\n'
ADJUST_STOCK = ADJUST_OPTIONS + STOCK + '''
def adjust_stock(argv):
    args = adjustment_options(argv)
    STOCK[args.product] += args.delta
    return STOCK[args.product]
'''
COMMAND_OPTIONS = '''import argparse

def command_options(argv):
    parser = argparse.ArgumentParser(prog="stock")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show")
    adjust = subparsers.add_parser("adjust")
    adjust.add_argument("product")
    adjust.add_argument("--delta", type=int, default=0)
    return parser.parse_args(argv)
'''
RUN_STOCK = COMMAND_OPTIONS + STOCK + '''
def run_stock(argv):
    args = command_options(argv)
    if args.command == "show":
        return STOCK
    elif args.command == "adjust":
        STOCK[args.product] += args.delta
        return STOCK[args.product]
'''
PARSE_ARGS = '''import argparse

def parse_args(argv):
    parser = argparse.ArgumentParser(prog="stock_report")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)
'''
BUILD_PARSER = '''import argparse

def handle_list(args):
    return "查看库存"

def handle_add(args):
    return f"登记：{args.title}"

def build_parser():
    parser = argparse.ArgumentParser(prog="stock_note")
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing = subparsers.add_parser("list")
    listing.set_defaults(func=handle_list)
    adding = subparsers.add_parser("add")
    adding.add_argument("title")
    adding.set_defaults(func=handle_add)
    return parser
'''
PARSE_ERROR = '''import argparse

def parse_or_error(argv):
    parser = argparse.ArgumentParser(prog="stock_note")
    parser.add_argument("title")
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args(argv)
'''
ENTRY = ADJUST_OPTIONS + STOCK + '''
def main(argv=None):
    args = adjustment_options(argv)
    STOCK[args.product] += args.delta
    print(f"{args.product} 当前库存：{STOCK[args.product]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def example(code, output, explanation, *, kind="python", target="main.py"):
    item = dict(language="python", code=code, output=output,
                explanation=explanation, source_kind=kind, runnable=kind == "python")
    if kind != "python":
        item["target_path"] = target
    return item


def gap(demo, before, after, instructions):
    assert before in demo["code"], before
    return dict(title=instructions, instructions=instructions + "。只改 TODO 对应位置，然后对比预期和实际输出。",
                starter="# TODO：" + instructions + "\n" + demo["code"].replace(before, after, 1),
                reference=demo["code"], output=demo["output"], source_kind="python", runnable=True)


def mistake(title, cause, wrong, fix):
    return dict(error=title, cause=cause, symptom=cause, fix=fix,
                example=dict(code=wrong, symptom=cause, fix=fix))


def section(sid, title, intro, paragraphs, rules, demos, instructions, starter,
            inputs, errors, drills, prerequisites, *, cards=(), provided=""):
    practice = dict(kind="code", file_name="main.py", scenario=intro[1],
                    instructions=instructions, expected_behavior="；".join(x[1] for x in inputs),
                    hints=rules[0], starter_content=starter, starter_policy="complete",
                    input_examples=[dict(label=f"检查 {i+1}", value=value, expected=output)
                                    for i, (value, output) in enumerate(inputs)])
    return dict(id=sid, title=title, catalog_refs=["py-87", "linux-06"],
                objective=intro[0], syntax="；".join(rules), explanation=paragraphs,
                js_bridge="本节不需要 JavaScript 知识。先在 Python 中运行示例，再完成本节的小步练习。",
                frontend_bridge="只用已学的 Python 函数、条件和字典，不要求了解前端框架。",
                key_points=rules, examples=demos, example=copy.deepcopy(demos[0]),
                common_errors=errors, practice=practice,
                guided_practice=dict(goal=instructions, starter=starter,
                                     steps=[dict(action=value, expected=output) for value, output in inputs],
                                     check=practice["expected_behavior"]),
                steps=["先读用途和逐行注释，预测第一个示例的输出", "运行示例，再补全两道小练习", "独立作业只实现本节要求，查看真实返回值"],
                practice_first=dict(goal=instructions, rules=rules, prerequisites=prerequisites,
                                    cards=list(cards), drills=[dict(d, id=f"step-{i+1}") for i, d in enumerate(drills)],
                                    intro=intro,
                                    provided=provided or "每个示例可独立运行。补全题不覆盖主作业；主作业中的函数需 return，调试时可以 print。"))


def lessons():
    result = []
    def add(*args, **kwargs):
        result.append(section(*args, **kwargs))

    a = example('''argv = ["原料", "--delta", "-3"]
print(argv[0])
print(argv[2])
print(type(argv[2]).__name__)
''', "原料\n-3\nstr", "argv 是我们自选的变量名，里面每一项都是文字；索引 0 取商品名，索引 2 取调整量文本。看到 -3 不代表它已经是整数，最后一行的 str 证明转换还没发生。")
    b = example('''def input_parts(argv):
    return argv[0], argv[1], argv[2]

print(input_parts(["纸盒", "--delta", "5"]))
''', "('纸盒', '--delta', '5')", "函数接收整个列表，再把三个字符串组成元组返回；return 才把结果交给外面的 print。这里不解析参数、不检查业务，只复习列表索引和函数传参，为下一步准备输入。")
    add("D09-argv", "01 · 先看输入：命令行为什么是一串文字", ["看清 argv 列表里存了什么，暂时不学新库。", "仓库收到“原料减少 3 个”的操作指令时。", "把输入看成三个字符串，先用索引观察，再把列表传给函数。"], [
        "先看效果：原料 --delta -3 表示调整原料，减少 3 个。程序先接到的是 ['原料', '--delta', '-3'] 这样的文字列表，还没有修改库存。",
        "argv 是我们自己取的参数名，不是 Python 关键字。函数接收列表后可以用 argv[0] 读取原料；这里列表恰好有三项，不要求额外判断长度。",
        "终端命令中的 python main.py 是启动方式，不放进传给 parse_args 的模拟列表。现在直接传列表就能练习；最后一节再接真实终端，不同时学习两套入口。"],
        ["argv 是自选变量名，列表里的 '-3' 仍是字符串。", "本节只观察输入，不转整数、不修改库存。"], [a, b],
        "定义 input_parts(argv)，将恰好三项的字符串列表按原顺序返回为三项元组；不转换类型，不加长度或业务校验。",
        'def input_parts(argv):\n    # TODO：返回列表中的三项\n    pass\n',
        [("input_parts(['原料', '--delta', '-3'])", "('原料', '--delta', '-3')"), ("input_parts(['纸盒', '--delta', '5'])", "('纸盒', '--delta', '5')")],
        [mistake("把 argv 当成自动产生输入的关键字", "这个函数参数必须由调用者传入，改成 items 也能工作。", "input_parts()", "调用时显式传入三项列表。"), mistake("看到负号就当成 int", "带引号的 '-3' 是文本，当前练习要保留文本。", 'return int(argv[2])', "先原样返回三项，整数转换在第 03 节学习。")],
        [gap(a, "print(argv[0])", "print(None)", "读出商品名称"), gap(b, "return argv[0], argv[1], argv[2]", "return None", "返回三个原始字符串")], ["D04-def-return", "D05-list-tuple"])

    a = example('''import argparse
parser = argparse.ArgumentParser(prog="stock_adjust")  # 创建翻译员
parser.add_argument("product")  # 先约定：必须提供一个商品名
args = parser.parse_args(["原料"])  # 现在才翻译这次输入
print(args.product)
''', "原料", "ArgumentParser 创建解析器，add_argument 只登记输入规则，parse_args 才读取这次列表。product 是自己起的结果字段名，原料是用户填入的值；prog 只影响帮助提示，不会改文件名。")
    b = example('''import argparse
parser = argparse.ArgumentParser()
parser.add_argument("item")
args = parser.parse_args(["纸盒"])
print(args.item)
''', "纸盒", "把字段名从 product 换成 item 后，读取结果也要跟着写 args.item；用户仍然只输入纸盒。位置参数没有 -- 前缀，在本例中必须填写，不是要求用户输入字面量 item。")
    add("D09-position", "02 · 创建解析器：先只接收商品名", ["让 argparse 把商品名称保存到一个命名字段中。", "输入必须包含一个商品名，但暂时没有调整量时。", "创建解析器 → add_argument 登记规则 → parse_args 解析 → args.product 取值。"], [
        "argparse 是 Python 自带的命令行翻译员，先 import 才能使用。ArgumentParser() 创建一个解析器；parser 是自选变量名，prog='stock_adjust' 只是帮助信息里的程序名称。",
        "parser.add_argument('product') 约定接收商品名，并把它放进 product 字段。这是位置参数：用户写原料，不写 product 原料，也不写 --product 原料。",
        "parser.parse_args(['原料']) 真正执行解析，返回装着结果的对象。把它保存为 args 后，用 args.product 读出原料；add_argument 负责立规则，不会直接拿到这次输入。"],
        ["固定方法名不用背实现；parser、args、product 都是本例自选名字。", "先登记规则，再解析输入；本节不加入 --delta。"], [a,b],
        "定义 product_options(argv)，创建解析器，声明必填位置参数 product，返回 parse_args(argv) 的结果。商品名保持字符串，缺少参数由库自动处理。",
        'import argparse\n\ndef product_options(argv):\n    # TODO：创建、声明、解析并返回\n    pass\n',
        [("product_options(['原料']).product", "原料"), ("product_options(['纸盒']).product", "纸盒")],
        [mistake("以为 product 是用户必须输入的单词", "product 是结果字段名，实际输入应是商品名称。", 'parser.parse_args(["product", "原料"])', "只传 ['原料']，用 args.product 取值。"), mistake("把登记规则的结果当成解析结果", "add_argument 没有解析原料，不能用它代替 parse_args。", 'args = parser.add_argument("product")', "args = parser.parse_args(argv)。")],
        [gap(a, 'parser = argparse.ArgumentParser(prog="stock_adjust")', "parser = None", "创建一个参数解析器"), gap(b, "print(args.item)", "print(None)", "读取自己命名的 item 字段")], ["D09-argv", "D07-import"])

    a = example(ADJUST_OPTIONS + '\nargs = adjustment_options(["原料", "--delta", "-3"])\nprint(args.product, args.delta)\nprint(type(args.delta).__name__)\n', "原料 -3\nint", "--delta 后面的 '-3' 原本是字符串，type=int 让库在解析时把它转成整数，所以结果类型是 int。正数、零和负数都是整数；库不会自动加上“只能入库”这样的业务限制。")
    b = example(ADJUST_OPTIONS + '\nargs = adjustment_options(["纸盒"])\nprint(args.product, args.delta)\n', "纸盒 0", "这次没有写 --delta，解析器使用 default=0，所以商品名保留纸盒，调整量为零。默认值只在没传这个选项时使用，不会覆盖用户明确传来的 5、0 或 -3。")
    add("D09-options", "03 · 加上调整量：--delta、type 与 default", ["把调整量文字转成整数，并规定省略时使用什么值。", "同一张调整单可能入库、出库，也可能只提供商品名时。", "声明 --delta，配置 type=int 和 default=0，再读 args.delta。"], [
        "位置参数 product 说明调整哪个商品；--delta 是带名字的选项，它后面跟调整量。delta 表示变化量，正数入库、负数出库，这是业务约定，不是 Python 语法。",
        "type 和 default 是 add_argument 的配置参数名。type=int 表示用 int 做转换，注意写 int 而不是 int()；default=0 表示没提供 --delta 时用零，不是把所有输入改成零。",
        "输入列表仍然写字符串，例如 ['原料', '--delta', '-3']。得到的 args.delta 才是整数 -3；负数合法，本节不检查库存是否够用，也不要求学习者手写转换异常。"],
        ["--delta 的结果字段默认叫 delta，不带两个横线。", "type=int 只检查整数形式，default=0 只负责省略时的值。"], [a,b],
        "定义 adjustment_options(argv)：必填商品名 product，选项 --delta 使用 type=int、default=0，返回 Namespace。允许正数、零、负数；不增加业务范围限制。",
        'import argparse\n\ndef adjustment_options(argv):\n    parser = argparse.ArgumentParser(prog="stock_adjust")\n    parser.add_argument("product")\n    # TODO：声明 --delta，并解析后返回\n    pass\n',
        [("adjustment_options(['原料','--delta','-3']).delta", "整数 -3"), ("adjustment_options(['纸盒']).delta", "整数 0"), ("adjustment_options(['纸盒','--delta','5']).delta", "整数 5")],
        [mistake("调整量仍是字符串", "没有配置 type=int，取出的 '-3' 不能直接参与整数加法。", 'parser.add_argument("--delta", default=0)', "给 --delta 加上 type=int。"), mistake("自行禁止负数调整", "出库本来就用负数，本节没有只能为正的业务规则。", 'if args.delta < 0: parser.error("不能为负")', "删去范围限制，保留整数形式检查。")],
        [gap(a, "type=int", "type=str", "让调整量的类型变成 int"), gap(b, "default=0", "default=None", "设置省略调整量时的默认值")], ["D09-position"])

    a = example(ADJUST_STOCK + '\nprint(STOCK["原料"])\nprint(adjust_stock(["原料", "--delta", "-3"]))\nprint(STOCK)\n', "20\n17\n{'纸盒': 10, '原料': 17}", "先解析出 product='原料' 和 delta=-3，再执行 STOCK['原料'] = STOCK['原料'] + (-3)，库存从 20 变为 17。函数返回新库存，外面的 print 显示它；解析失败时不会走到更新那一行。")
    b = example(ADJUST_OPTIONS + '\nargs = adjustment_options(["原料", "--delta", "-3"])\nprint(args)\nprint(args.product)\nprint(args.delta)\n', "Namespace(product='原料', delta=-3)\n原料\n-3", "Namespace 可以先理解为装着解析结果的对象，点号用来读取其中的属性。它不是字典：这里写 args.product，不是 args['product']；STOCK 才是用方括号读写商品库存的字典。")
    add("D09-stock", "04 · 串起来：Namespace → 读取参数 → 更新库存", ["把解析结果交给已经学过的字典更新代码。", "收到库存调整单后，确认输入能解析，再修改库存时。", "先 args = adjustment_options(argv)，再用 args.product 与 args.delta 更新 STOCK。"], [
        "把两层函数串起来看：adjust_stock 接到列表，把同一列表传给 adjustment_options；后者返回 Namespace，再赋给前者的 args。argv 是输入，args 是结果，不是两个互不相干的库对象。",
        "print(args) 可以看到 Namespace(product='原料', delta=-3)。读对象属性用 args.product；读字典用 STOCK[args.product]，这时键就是原料。两种括号写法不同，是因为读取的对象不同。",
        "STOCK[args.product] += args.delta 等价于原库存加调整量再写回。练习要求 return 新库存，print 只用于观察；商品明确已存在，不检查余额，也不新增商品或写文件。"],
        ["先解析成功，再修改 STOCK；本例商品明确已经存在。", "Namespace 用点号取属性，库存字典用方括号读写。", "本题返回新库存；只打印而不 return 仍会返回 None。"], [a,b],
        "已提供 STOCK 和 adjustment_options。补全 adjust_stock(argv)：先解析，再按商品名累加 delta，修改原字典并返回该商品新库存。商品一定存在，允许结果为负数，不增加商品、类型或余额限制。",
        ADJUST_OPTIONS + STOCK + '\ndef adjust_stock(argv):\n    # TODO：解析 → 更新字典 → 返回新库存\n    pass\n',
        [("初始原料20；adjust_stock(['原料','--delta','-3'])", "返回 17，原料库存变为 17"), ("初始纸盒10；adjust_stock(['纸盒','--delta','5'])", "返回 15，纸盒库存变为 15"), ("初始原料20；adjust_stock(['原料','--delta','-30'])", "返回 -10，不额外拒绝")],
        [mistake("把 Namespace 当成字典读", "args 不是库存字典，args['product'] 会导致类型错误。", 'STOCK[args["product"]] += args.delta', "使用 STOCK[args.product]。"), mistake("只在局部算出新库存", "仅计算或打印数值不会写回 STOCK，下一次仍读到旧库存。", 'return STOCK[args.product] + args.delta', "先用 += 更新 STOCK，再 return 新值。")],
        [gap(a, "STOCK[args.product] += args.delta", "STOCK[args.product] += 0", "把解析出的变化量加回库存"), gap(b, "print(args.product)", "print(None)", "从 Namespace 中读出商品")], ["D09-options", "D05-dict-set"],
        provided="解析函数和库存字典已完整提供，不必重复默写。这里只补 adjust_stock 的三步；不同实验互不共享库存。")

    a = example(PARSE_ARGS + '\nargs = parse_args(["--limit", "3", "--verbose"])\nprint(args.limit, args.verbose)\n', "3 True", "--limit 后跟一个整数，--verbose 则是无需填写值的开关；action='store_true' 表示出现时记为 True。二者的填写方式不同，不要给 --verbose 再加上字符串 True。")
    b = example(PARSE_ARGS + '\nargs = parse_args([])\nprint(args.limit, args.verbose)\n', "10 False", "空列表表示本次没有提供选项，因此 limit 使用默认 10，store_true 开关保持默认 False。parse_args([]) 只解析这个空列表，不会偷偷改读运行工作台时的真实命令行。")
    add("D09-parser", "05 · 普通参数小结：带值选项与布尔开关", ["区分需要填写数值的选项和只表示开关的选项。", "库存报告需要限制显示条数，并可选择详细模式时。", "--limit 配 type=int；--verbose 配 action='store_true'，只写开关名。"], [
        "前面的库存调整程序只有一种操作，并没有子命令。现在仍然只做普通参数解析，只把业务换成库存报告：--limit 代表显示条数，--verbose 代表是否详细显示。",
        "action='store_true' 是 argparse 提供的一种开关配置，出现 --verbose 就得到 True，不出现就得到 False。action 是库规定的参数名，verbose 是我们选的选项名，不用自己写字符串转布尔的函数。",
        "本节保留旧作业名 parse_args(argv)，默认 limit=10。它与 parser.parse_args(argv) 名称相似，但前者是自己定义的包装函数，后者是库对象的方法；本节不限制整数大小或正负。"],
        ["带值选项：--limit 3；布尔开关：--verbose，后面不加 True。", "type、default、action 是库的配置项，不是需要自己实现的方法。"], [a,b],
        "定义 parse_args(argv)，支持 --limit INTEGER，默认 10；支持 --verbose 开关，不传为 False、传入为 True。返回 Namespace，非法整数和未知选项交给 argparse，不限制 limit 正负。",
        'import argparse\n\ndef parse_args(argv):\n    # TODO：创建 parser，声明带值选项与开关，再返回解析结果\n    pass\n',
        [("parse_args([])", "limit=10，verbose=False"), ("parse_args(['--limit','3','--verbose'])", "limit=3，verbose=True")],
        [mistake("给布尔开关再填写 True", "store_true 只看开关是否出现，多出的 True 会被当成未知输入。", 'parse_args(["--verbose", "True"])', "只传 ['--verbose']。"), mistake("把自己写的 parse_args 与库方法混为一谈", "在包装函数内直接再次调用自己，会无限递归。", 'def parse_args(argv):\n    return parse_args(argv)', "创建 parser 后调用 parser.parse_args(argv)。")],
        [gap(a, '    parser.add_argument("--verbose", action="store_true")', '    # TODO：这里声明 --verbose 开关', "声明出现即为 True 的开关"), gap(b, "default=10", "default=0", "恢复报告条数的默认值 10")], ["D09-stock"])

    a = example(COMMAND_OPTIONS + '\nprint(command_options(["show"]))\nprint(command_options(["adjust", "原料", "--delta", "-3"]))\n', "Namespace(command='show')\nNamespace(command='adjust', product='原料', delta=-3)", "add_subparsers 建立可选的操作菜单，add_parser 为其中一个操作建立自己的参数解析器。dest='command' 把选中的菜单名放进 args.command；show 不需要商品，只有 adjust 分支才带 product 和 delta。")
    b = example('''import argparse
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="action", required=True)
subparsers.add_parser("show")
args = parser.parse_args(["show"])
print(args.action)
''', "show", "dest 是库规定的配置名，但字符串 action 是我们自己决定的结果字段名，所以这里读 args.action。它保存的是用户选择的 show，不会自动执行查看库存；选择动作和执行动作要分开理解。")
    add("D09-command-name", "06 · 只识别子命令：add_parser 与 dest", ["先知道用户选了哪个功能，暂时不要自动执行功能。", "同一个仓库程序既要查看库存，又要调整库存时。", "add_subparsers 建菜单，add_parser 加菜单项，dest 指定菜单名称存到哪里。"], [
        "普通参数回答“哪个商品、调整多少”，子命令回答“要做什么”。现在输入 show 是查看，输入 adjust 原料 --delta -3 是调整；本节只返回解析结果，仍然不修改库存。",
        "parser 是总解析器；subparsers 管理子命令菜单；adjust 是 adjust 菜单项自己的解析器。写 adjust.add_argument('product')，商品参数就只属于 adjust，不会要求 show 也填商品。",
        "dest='command' 可以读作“把选中的命令名字存进 command 字段”。dest 是库的固定配置名，command 可以改名，但读取属性也要同步改；required=True 表示必须选择一个子命令，不是自动选择 show。"],
        ["dest 决定结果属性叫什么，add_parser 决定有哪些命令。", "show 没有 product；只在 adjust 的结果中读取商品和调整量。"], [a,b],
        "定义 command_options(argv)：必须选择 show 或 adjust。show 不带商品；adjust 接收必填 product 和 --delta（int，默认0）。dest='command'，返回 Namespace；这里只解析，不分派、不修改库存。",
        'import argparse\n\ndef command_options(argv):\n    parser = argparse.ArgumentParser(prog="stock")\n    # TODO：建立子命令菜单，给 adjust 添加自己的参数\n    pass\n',
        [("command_options(['show'])", "command='show'，没有 product 属性"), ("command_options(['adjust','原料','--delta','-3'])", "command='adjust'，product='原料'，delta=-3")],
        [mistake("把子命令商品参数加给总 parser", "总解析器的必填商品会连 show 也一起要求填写。", 'parser.add_argument("product")', "在 adjust = subparsers.add_parser('adjust') 后，使用 adjust.add_argument。"), mistake("认为 dest='command' 会执行函数", "dest 只设置结果属性，得到的仍然是命令名称字符串。", 'args.command()', "先 print(args.command)，下一节再写 if 决定做什么。")],
        [gap(a, 'dest="command"', 'dest="other"', "把选中命令的名称存进 command 字段"), gap(b, "print(args.action)", "print(None)", "字段改名后从 action 读取")], ["D09-parser"])

    a = example(RUN_STOCK + '\nprint(run_stock(["show"]))\nprint(run_stock(["adjust", "原料", "--delta", "-3"]))\nprint(run_stock(["show"]))\n', "{'纸盒': 10, '原料': 20}\n17\n{'纸盒': 10, '原料': 17}", "先用 args.command 判断用户选择 show 还是 adjust；只有进入 adjust 分支，才读取 product 和 delta。两个 show 分别显示调整前后库存，证明不是只计算了 17，而是真的更新了字典。")
    b = example(RUN_STOCK + '\nprint(run_stock(["adjust", "纸盒", "--delta", "5"]))\nprint(run_stock(["adjust", "纸盒", "--delta", "-2"]))\n', "15\n13", "同一段程序中的两次调用共享 STOCK，第一次纸盒由 10 变成 15，第二次在 15 上减 2 得到 13。分派只是在已有 if 中选择正确的代码，不需要引入新类或函数映射技巧。")
    add("D09-if-dispatch", "07 · 先用 if 分派：选哪个功能就走哪个分支", ["用已经学过的 if，把命令名称连接到实际操作。", "已经解析出 show 或 adjust，需要执行对应库存功能时。", "检查 args.command；show 返回库存，adjust 分支读取商品并更新库存。"], [
        "参数解析只负责把文字整理成字段，不会替你改库存。“分派”就是根据字段选择执行哪段代码；最容易看懂的写法正是你学过的 if / elif。",
        "run_stock 先调用 command_options，再判断 args.command。show 分支直接返回库存，adjust 分支才用 args.product 和 args.delta；这样 show 没有商品字段也不会报错。",
        "现在先把 if 分派写熟，不要求 set_defaults。相同列表、相同库存应得到相同结果；出库仍允许负数，解析失败则在进入分支前停止，不需要自己补业务错误处理。"],
        ["解析是整理输入；分派是根据命令选择代码。", "先判断命令，再读取那个命令专有的参数。"], [a,b],
        "已提供 command_options 和 STOCK。补全 run_stock(argv)：show 返回库存字典且不修改；adjust 累加指定商品库存并返回新数量。商品一定存在，允许有符号调整和负库存，错误输入不得修改库存。",
        COMMAND_OPTIONS + STOCK + '\ndef run_stock(argv):\n    args = command_options(argv)\n    # TODO：先判断命令，再分别查看或调整\n    pass\n',
        [("初始库存；run_stock(['show'])", "{'纸盒': 10, '原料': 20}"), ("随后 run_stock(['adjust','原料','--delta','-3'])", "17；再 show 看到原料17")],
        [mistake("在 if 前无条件读取商品字段", "show 的结果没有 product，会在选择分支前就报错。", 'name = args.product\nif args.command == "show":\n    return STOCK', "将商品读取移到 adjust 分支内部。"), mistake("用调整量覆盖总库存", "delta 是变化量，不是调整后的总量。", 'STOCK[args.product] = args.delta', "用 += 累加，再返回更新后的数量。")],
        [gap(a, 'if args.command == "show":', "if False:", "让 show 进入查看分支"), gap(b, "STOCK[args.product] += args.delta", "STOCK[args.product] += 0", "让 adjust 分支真正累加变化量")], ["D09-command-name", "D03-if"])

    a = example('''def show_stock():
    print("现在才查看库存")

action = show_stock
print("函数已经存好，还没有执行")
action()
''', "函数已经存好，还没有执行\n现在才查看库存", "action = show_stock 保存的是函数本身，这一行没有执行函数体，所以先看到“还没有执行”。到 action() 才真正调用函数；多加一对括号就改变了执行时机，不只是写法不同。")
    b = example('''def call_action(action, value):
    return action(value)

def double(number):
    return number * 2

print(call_action(double, 4))
print(call_action(double, -3))
''', "8\n-6", "double 不带括号，表示把函数交给 call_action；action(value) 才拿着传入的值调用它。call_action 不知道具体业务，只负责调用并返回结果，所以同一个函数也能处理负数。")
    add("D09-function-value", "08 · 暂离 argparse：函数名与函数调用", ["分清保存一个函数和立刻调用这个函数的区别。", "希望先选好处理函数，等参数准备好以后再执行时。", "action = 函数名保存函数；action(value) 调用函数；return 把结果交回去。"], [
        "这里先不使用 argparse，只复习函数。函数本身也可以赋给变量或传给另一个函数；action = show_stock 保存函数，action = show_stock() 则立刻执行并保存它的返回值。",
        "如果 show_stock 只 print 而没有 return，它的返回值就是 None。因此错误地写 action = show_stock()，后面再 action() 就是在调用 None；这也是下一节容易绕的原因。",
        "call_action(action, value) 只需要 return action(value)。以后把 action 换成 args.func，把 value 换成 args，就是 args.func(args)；本质仍然是普通函数调用，不是新语法。"],
        ["函数名不带括号：保存或传递函数；带括号：立即调用。", "调用之后要 return 结果；print 不能代替返回。"], [a,b],
        "定义 call_action(action, value)，调用传入的 action(value)，并原样返回结果。函数和值由测试提供，不需要判断类型，也不要自己固定写 double。",
        'def call_action(action, value):\n    # TODO：调用传进来的函数，再返回结果\n    pass\n',
        [("call_action(double, 4)，其中 double(n) 返回 n*2", "8"), ("call_action(greet, '原料')，其中 greet(x) 返回 '查看：'+x", "查看：原料")],
        [mistake("保存的是函数返回值而不是函数", "加括号会提前执行，变量可能变成 None 或字符串。", 'action = show_stock()', "保存函数写 action = show_stock，准备好再调用。"), mistake("调用正确但忘了返回", "只执行 action(value) 会丢掉结果，外层收到 None。", 'def call_action(action, value):\n    action(value)', "写 return action(value)。")],
        [gap(a, "action = show_stock", "action = None", "保存函数但不要立刻执行"), gap(b, "return action(value)", "return None", "调用传来的函数并返回结果")], ["D09-if-dispatch", "D04-def-return"])

    a = example('''import argparse

def handle_list(args):
    return "查看库存"

parser = argparse.ArgumentParser()
parser.set_defaults(func=handle_list)
args = parser.parse_args([])
print(args.func is handle_list)
print(args.func(args))
''', "True\n查看库存", "set_defaults 可以在解析结果里放入额外默认字段；这里把 handle_list 这个函数放进 func 字段，没有执行它。第一行 True 证明拿到的是同一个函数，第二行 args.func(args) 才执行并返回文字。")
    b = example(BUILD_PARSER + '\nparser = build_parser()\nargs = parser.parse_args(["list"])\nprint(args.func(args))\nargs = parser.parse_args(["add", "原料出库3袋"])\nprint(args.func(args))\n', "查看库存\n登记：原料出库3袋", "每个子解析器只绑定自己的处理函数：list 对应 handle_list，add 对应 handle_add。parse_args 按用户选择把对应函数放进 args.func，随后统一调用 args.func(args)；本例登记文字，不写文件或新增库存商品。")
    add("D09-subcommands", "09 · 再用 set_defaults 分派：存函数，再调用", ["把已经理解的 if 分派改成先绑定函数、再统一调用。", "子命令变多，希望每个命令有独立处理函数时。", "子解析器.set_defaults(func=处理函数)，解析后再执行 args.func(args)。"], [
        "set_defaults 是库方法，不是 Python 新语法。它给解析结果补默认字段：func 是我们选的字段名，handle_list 是一个函数；这行没有括号，所以只是保存，不会立即执行。",
        "每个子解析器分别设置自己的 func。输入 list 后 args.func 是查看函数，输入 add 后 args.func 是登记函数；再执行 args.func(args)，就是把整个参数对象交给选中的函数。",
        "if 分派与函数分派都正确，只是组织方式不同。本节保留旧作业 build_parser() 和 list / add TITLE，作为从 show / adjust 迁移的小练习；TITLE 是登记文字，不要求写数据库或修改库存。"],
        ["dest='command' 存命令名字；set_defaults(func=...) 存处理函数，二者不是一回事。", "func 是自选字段名；set_defaults 不会自动执行函数。", "绑定时不要加括号，解析后才 args.func(args)。"], [a,b],
        "定义 build_parser()，返回支持必选子命令 list 和 add TITLE 的解析器。结果含 command 和可调用的 func；args.func(args) 对 list 返回'查看库存'，对 add 返回 f'登记：{args.title}'。处理函数名不限。缺命令、未知命令或 add 缺标题交给 argparse。",
        'import argparse\n\ndef build_parser():\n    # TODO：可先在外面定义两个处理函数，再建立菜单并绑定\n    pass\n',
        [("args = build_parser().parse_args(['list']); args.func(args)", "查看库存"), ("args = build_parser().parse_args(['add','原料出库3袋']); args.func(args)", "登记：原料出库3袋")],
        [mistake("在 set_defaults 里提前调用处理函数", "这里尚未解析 args，且 func 会变成返回值而不是函数。", 'listing.set_defaults(func=handle_list())', "使用 func=handle_list，不带括号。"), mistake("只绑定函数，忘记最后调用", "parse_args 只整理参数和选择函数，不会产生业务返回值。", 'args = parser.parse_args(["list"])', "解析之后调用 args.func(args)，再使用它的返回值。")],
        [gap(a, "parser.set_defaults(func=handle_list)", "parser.set_defaults(func=None)", "将函数本身保存到 func 字段"), gap(b, "print(args.func(args))", "print(None)", "真正调用选中的处理函数")], ["D09-function-value"])

    a = example(PARSE_ERROR + '''
for argv in [[], ["盘点", "--limit", "abc"]]:
    try:
        parse_or_error(argv)
    except SystemExit as error:
        print("退出码", error.code)
''', "退出码 2\n退出码 2", "缺少标题和无法转成整数的 abc 都由 parse_args 拒绝，抛出 SystemExit(2)。这里专门捕获它只是为了观察退出码；usage 和 error 会同时出现在错误输出区，不需要学习者手写这一套提示。")
    b = example(PARSE_ERROR + '\nargs = parse_or_error(["盘点", "--limit", "-3"])\nprint(args.title, args.limit)\n', "盘点 -3", "-3 仍然是合法整数，所以解析成功并保留标题盘点，不会进入错误退出。type=int 只校验输入形式；只有题目明确要求正数时才应增加 parser.error 的业务校验，本节没有这条要求。")
    add("D09-errors", "10 · 故意输错一次：错误输出、退出码和帮助", ["读懂输入失败与查看帮助的区别，不把失败当成成功。", "缺商品或标题、写错整数、使用未知选项时。", "让 parse_args 自动报错；错误通常退出2，--help 打印帮助并退出0。"], [
        "stdout 是普通输出，stderr 是错误输出。缺少必填参数、非法整数、未知选项会让 argparse 把说明写到 stderr 并抛出 SystemExit(2)；成功返回的才是 Namespace。",
        "--help 不是失败：它把帮助写到 stdout，随后抛出 SystemExit(0)。SystemExit 和普通 Exception 不是同一个捕获范围；示例显式 except SystemExit，只为展示 code，作业不需要吞掉错误。",
        "本节仍只检查输入形式：title 必填，--limit 是整数，默认10，负整数合法。不要 catch 后返回0、不要用默认值掩盖 abc，也不要把上一道选修题的次数必须为正规则套到这里。"],
        ["默认解析错误：stderr + SystemExit(2)；--help：stdout + SystemExit(0)。", "错误不应伪装成成功；正负范围要由题目另行规定。"], [a,b],
        "定义 parse_or_error(argv)：必填位置参数 title，--limit 使用 type=int、default=10，成功返回 Namespace。缺标题、坏整数、未知选项必须保留 SystemExit(2)；--help 保留 SystemExit(0)。允许负整数，不手动捕获成成功。",
        'import argparse\n\ndef parse_or_error(argv):\n    # TODO：声明 title 和 --limit；直接返回库的解析结果\n    pass\n',
        [("parse_or_error(['盘点','--limit','-3'])", "title='盘点'，limit=-3"), ("parse_or_error([]) / ['盘点','--limit','abc']", "SystemExit(2)，错误提示在 stderr"), ("parse_or_error(['--help'])", "SystemExit(0)，帮助在 stdout")],
        [mistake("捕获输入错误后返回成功值", "输入不正确却显示成功，后面的代码可能使用无效参数。", 'except SystemExit:\n    return 0', "不要在作业里吞掉 SystemExit，直接交给调用者。"), mistake("以为 --help 也必须提供标题", "帮助选项会优先显示用法，不应该被普通参数检查阻止。", 'if not argv or len(argv) < 2:\n    raise SystemExit(2)', "由 argparse 同时处理必填参数和 --help。")],
        [gap(a, "type=int", "type=str", "让 abc 被整数解析规则拒绝"), gap(b, "return parser.parse_args(argv)", "return None", "成功时返回真正的 Namespace")], ["D09-subcommands", "D06-try-except"])

    # sys.argv is supplied only in the web demonstration, never in the assignment.
    demo_entry = 'import sys\n# 网页演示提供模拟终端；真实 main.py 不写这两行设置。\nsys.argv = ["main.py", "原料", "--delta", "-3"]\n' + ENTRY
    a = example(demo_entry, "原料 当前库存：17", "网页演示先提供一组模拟 sys.argv，然后 main() 把默认 None 传到 parse_args，库读取脚本名之后的真实参数。正式提交不要设置 sys.argv，也不要在底部写死原料列表，否则在终端换成纸盒也不会生效。")
    b = example(ENTRY, "原料 当前库存：17", "把这份文件保存为 main.py 后，在终端输入示例命令，main() 会读取这一次提供的商品与调整量。导入 main 时守卫不执行，因此不解析导入者的参数、不打印库存；每次重新启动进程都会重建初始 STOCK。", kind="file_fragment")
    drill2_demo = example(demo_entry.replace('["main.py", "原料", "--delta", "-3"]', '["main.py", "纸盒", "--delta", "5"]'), "纸盒 当前库存：15", a["explanation"])
    add("D09-entry", "11 · 接上真实终端：argv=None 与入口守卫", ["把前面能接收列表的库存程序变成真正的命令行工具。", "希望修改终端参数就能调整不同商品，而不是每次改代码时。", "main(argv=None) 把 argv 交给解析器；守卫中调用 main()，不要写死列表。"], [
        "前面传 ['原料','--delta','-3'] 是模拟输入。parse_args(None) 才读取 sys.argv[1:]，也就是去掉脚本名后的终端参数；parse_args([]) 则是明确没有参数，这两个含义不能混淆。",
        "def main(argv=None) 让同一个函数既可以 main(['纸盒',...]) 离线练习，也可以 main() 读取终端。main 是自选的普通函数名，不会自动执行；if __name__ == '__main__' 决定直接运行文件时才调用它。",
        "main 成功后 return 0，由 raise SystemExit(main()) 交给终端；参数错误在解析时就抛 SystemExit(2)。导入模块时只定义函数和库存，不读取命令、不输出；工作台代你运行子进程检查，不要求本节另写 subprocess 测试。"],
        ["None = 读取真实命令行；[] = 明确传入空参数；不能用 argv or [] 混在一起。", "真实入口调用 main()；写死列表会忽略终端新输入。", "导入不执行，成功返回0；每次新进程的库存从初始值开始。"], [a,b],
        "已提供 adjustment_options 和 STOCK。补全 main(argv=None)：传递 argv、调整库存、打印“商品 当前库存：数量”、返回0；底部用 __name__ 守卫及 raise SystemExit(main())。真实终端参数必须生效；导入无输出、不解析参数。只验证已有商品，允许负调整和负库存。",
        ADJUST_OPTIONS + STOCK + '\ndef main(argv=None):\n    # TODO：接收输入，更新库存，打印结果，返回0\n    pass\n\nif __name__ == "__main__":\n    # TODO：调用 main() 并交给 SystemExit\n    pass\n',
        [("python main.py 原料 --delta -3", "原料 当前库存：17；退出码0"), ("python main.py 纸盒 --delta 5", "纸盒 当前库存：15；退出码0"), ("python main.py / python main.py --help", "前者错误退出2；后者显示帮助并退出0")],
        [mistake("真实入口仍写死模拟列表", "不管终端输入什么，程序都只处理固定的原料出库。", 'raise SystemExit(main(["原料", "--delta", "-3"]))', "底部调用 main()，让 argv 的默认 None 传到解析器。"), mistake("用 argv or [] 覆盖 None", "默认 None 被改成空列表，库无法读取真实终端输入。", 'args = adjustment_options(argv or [])', "直接传 argv，保留 None 与 [] 的区别。")],
        [gap(a, "args = adjustment_options(argv)", "args = adjustment_options([])", "保留 argv 的 None 语义"), gap(drill2_demo, "raise SystemExit(main())", 'raise SystemExit(main(["原料", "--delta", "-3"]))', "入口不要写死另一组商品参数")], ["D09-errors", "D07-main"],
        provided="解析函数已提供。网页演示中的 sys.argv 设置只是实验输入；主作业不要复制它。真实命令行回归由工作台完成，无须自己编写 subprocess。")
    return result


def apply_d09(data):
    task = next(t for t in data["tasks"] if t["id"] == "D09")
    optional_ids = {"D09-greet-cli", "D09-repeat-cli", "D09-square-cli"}
    optional = [s for s in task["lesson"] if s["id"] in optional_ids]
    core = lessons()
    task["lesson"] = core + optional
    task["title"] = "常用开发二：命令行从输入到分派"
    task["learning_goal"] = "先看效果、读懂每个新方法，再补全与独立练习；先学 if 分派，最后连接函数分派和真实终端。"
    task["concepts"] = ["argv 与 Namespace", "位置参数与带值选项", "布尔开关", "子命令与 dest", "if 分派", "函数作为值", "set_defaults", "SystemExit 与 --help", "argv=None 与入口守卫"]
    task["coding_task"] = "按 11 个小步完成库存命令行练习；已有 3 节加练继续选修，不必一次学完全部小节。"
    task["actions"] = ["先看输入与解析结果", "逐步编写库存调整", "先 if 后函数分派", "运行真实命令行回归"]
    task["snippet"] = {"language": "python", "code": core[0]["examples"][0]["code"]}
    task["acceptance"] = ["能解释输入列表如何变成结果字段", "能用 if 与函数绑定分别分派", "负数调整、错误输入与真实终端行为符合题目"]
    data["meta"]["d09_step_by_step_revision"] = 1


def write_teaching_catalog(data, root: Path):
    """Keep the concise UI catalog synchronized without rewriting other lessons."""
    path = root / "learnctl/web/static/teaching-catalog.js"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"Object\.freeze\((\{.*\})\);", text, re.DOTALL)
    if not match:
        raise ValueError("teaching-catalog.js format is not recognized")
    catalog = json.loads(match[1])
    for task in data["tasks"]:
        for lesson in task["lesson"]:
            intro = lesson.get("practice_first", {}).get("intro")
            if task["id"] == "D09" and intro:
                catalog[lesson["id"]] = intro
    body = "{\n" + ",\n".join("  " + json.dumps(k, ensure_ascii=False) + ": " + json.dumps(v, ensure_ascii=False) for k,v in catalog.items()) + "\n}"
    path.write_text(text[:match.start(1)] + body + text[match.end(1):], encoding="utf-8")

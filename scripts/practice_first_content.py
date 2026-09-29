"""Practice-first teaching overlay, applied at BUILD time (never on learner state).

Keep stable task/section IDs. Short cards are the default UI; the existing detailed
reference remains available. Drills have independent editors and do not mark a
lesson complete. New concepts used before their full chapter get runnable cards.
"""
from __future__ import annotations

import ast
import copy
from typing import Any

# Concrete prerequisites, not a claim that reading a later chapter is mandatory.
TASK_PREREQUISITES = {
    'D01': [], 'D02': ['D01-verify'], 'D03': ['D02-names', 'D02-numbers', 'D02-bool-none'],
    'D04': ['D03-if', 'D02-string-methods'], 'D05': ['D03-for', 'D04-def-return'],
    'D06': ['D03-if', 'D04-def-return'], 'D07': ['D04-def-return', 'D06-try-except'],
    'D08': ['D07-import', 'D06-with', 'D05-traversal'],
    'D09': ['D04-default-keyword', 'D07-main', 'D06-try-except'],
    'D10': ['D07-import', 'D05-dict-set', 'D06-raise', 'D07-dataclass'],
    'D11': ['D07-import', 'D06-with'], 'D12': ['D08-json-read', 'D06-with', 'D06-raise'],
    'D13': ['D04-def-return', 'D04-type-hints', 'D12-response'],
    'D14': ['D13-app', 'D07-class-instance', 'D06-raise'],
    'D15': ['D04-def-return', 'D08-pathlib', 'D13-app'],
    'D16': ['D04-def-return', 'D06-try-except', 'D15-assert'],
    'D17': ['D04-def-return', 'D06-try-except'],
    'D18': ['D08-json-read', 'D13-route', 'D14-errors'],
    'D19': ['D07-package', 'D07-main', 'D10-env', 'D15-assert'],
    'D20': ['D16-schema', 'D16-crud', 'D19-config'],
    'D21': ['D14-model', 'D14-deps', 'D17-coroutine', 'D20-update-delete'],
    'D22': ['D15-fixture', 'D15-api', 'D21-crud-routes'],
    'D23': ['D09-subcommands', 'D20-update-delete', 'D21-crud-routes'],
    'D24': ['D19-readme', 'D22-api-errors', 'D23-html-fetch'],
    'D25': ['D12-post', 'D12-timeout', 'D06-custom', 'D24-review'],
    'D26': ['D08-json-read', 'D02-string-methods', 'D25-chat'],
    'D27': ['D25-errors', 'D26-parse', 'D26-prompt'],
    'D28': ['D15-mock', 'D27-flow'],
}

TASK_PRACTICE = {
    'D01': '依次点击环境按钮；以实际检测通过为准，不必背术语。',
    'D02': '先改变量或表达式，运行看变化。函数外壳由起始代码提供，D04 再从头编写。',
    'D03': '先运行条件表，再补分支或循环。and 是同时成立，or 是至少一个成立，not 是取反。',
    'D04': '先写返回值，再打印观察；参数、默认值、作用域分开练，不把输入校验混进第一题。',
    'D05': '打印容器修改前后，再写函数处理新数据。空容器用 []、{}、set() 区分。',
    'D06': '先制造一次错误，再处理它。预期要求抛异常时，正确抛出也会显示为通过。',
    'D07': '先调用一个模块，再创建一个小对象。平台提供的辅助文件会明确列出。',
    'D08': '每次写文件后立即读回，观察真实内容；实验在临时目录进行，不改你的项目文件。',
    'D09': '先传一组 argv，再传错误参数；分别观察正常输出、错误输出和退出码。',
    'D10': '使用一份小字典模拟环境，逐项读取和转换；不要打印真实密钥。',
    'D11': '只发一条日志，比较级别、输出位置和重复次数，再增加处理器。',
    'D12': '先构造请求，再用本页提供的假响应观察结果；不需要联网或自己编写 mock 框架。',
    'D13': '先让一个 GET 接口返回 JSON，再改路径和参数；复杂异步生命周期放到 D17 后复练。',
    'D14': '依次练模型、业务函数、错误映射和依赖；不要求提前安装数据库。',
    'D15': '先运行一个成功测试，再故意改错一次，阅读差异；不是只有 assert 就算通过。',
    'D16': '用内存数据库练连接、建表、增删改查；每一步查询表内容，不只看“执行成功”。',
    'D17': '先 await 一个结果，再并发两个任务，最后观察超时和取消；先不接真实网络。',
    'D18': '先完成数据字段，再增加接口；这一节不要求实现后续路由或项目文件。',
    'D19': '一次只生成一个真实文件。说明中的函数名、路径和验证器保持一致。',
    'D20': '先连接和建表，再新增查询，最后完成删除；不提前检查下一节功能。',
    'D21': '先健康接口和模型，再 CRUD，最后首页路径；完整 HTML 在 D23 才生成。',
    'D22': '只测试当前已经生成的文件。15 个交付文件的完整核对放在 D24。',
    'D23': '先 add/list，再 done/rm；网页先结构，再逐次接入 GET/POST/PATCH/DELETE。',
    'D24': '用现有真实文件演示一次重建、测试和三种入口，不用另写一篇长报告。',
    'D25': '先模拟请求体和响应，再写客户端；真实调用需自行配置 Key，本地验证不用 Key。',
    'D26': '提示词只组织已授权内容；解析后检查形状，不把坏 JSON 当成功。',
    'D27': '把请求、解析和字段检查接起来；平台提供的模块只是本地测试夹具，不冒充你的交付物。',
    'D28': '写正常、401 和非 JSON 三个真实测试；最后用简短文字记录证据。',
}


def card(title: str, rule: str, code: str, output: str) -> dict[str, Any]:
    return {'title': title, 'rule': rule, 'code': code, 'output': output,
            'source_kind': 'python', 'runnable': True}

LOGIC = card('and / or / not：先看这三行', 'and 要求两边都成立；or 只需一边成立；not 把真假取反。用括号明确组合顺序。',
    "has_ticket = True\nis_blocked = False\nprint(has_ticket and not is_blocked)\nprint(False or has_ticket)\nprint(not (True and False))\n", 'True\nTrue\nTrue')
RAISE = card('主动拒绝：raise ValueError', 'raise 会立即停止当前路径。下面捕获错误只是为了让你看清类型；D06 再练完整处理。',
    "age = -1\ntry:\n    if age < 0:\n        raise ValueError('年龄不能为负数')\nexcept ValueError as error:\n    print(type(error).__name__)\n    print(error)\n", 'ValueError\n年龄不能为负数')
CONTAINERS = card('列表、元组、字典：只先看形状', '列表 [] 保存多个值，元组 () 保存一组值，字典 {键: 值} 按名称取值。空集合写 set()，不是 {}。',
    "items = [3, 4]\npair = (3, 4)\nrecord = {'name': '小林'}\nprint(items[0], pair[1], record['name'])\n", '3 4 小林')
CALLABLE = card('把函数作为参数', '参数也可以接收函数。调用传进来的 opener(...)，就能用本地假函数替代网络请求。',
    "def use_reader(reader):\n    return reader()\ndef fake_reader():\n    return '本地结果'\nprint(use_reader(fake_reader))\n", '本地结果')
BYTES = card('字符串与 bytes', 'encode 把文字编码为 bytes；decode 还原为文字。HTTP 的 read() 通常返回 bytes。',
    "text = '你好'\nbody = text.encode('utf-8')\nprint(type(body).__name__)\nprint(body.decode('utf-8'))\n", 'bytes\n你好')
DECORATOR = card('@ 装饰器最小读法', '这里 @ 标记注册函数，不需要你手写装饰器实现。下面等价于先定义 hello，再执行 hello = register(hello)。',
    "def register(fn):\n    print('注册', fn.__name__)\n    return fn\n@register\ndef hello():\n    return '你好'\nprint(hello())\n", '注册 hello\n你好')
YIELD = card('必需的 yield：先生成两个值', 'yield 每次产生一个值；完整迭代器协议仍可选修。后面的资源 fixture 会用到这种暂停和继续。',
    "def values():\n    yield '准备'\n    yield '清理'\nprint(list(values()))\n", "['准备', '清理']")
SUPPORT = {
    'D02-numbers': [card('函数外壳由平台提供', 'def 的缩进内填计算式，return 后的结果交给调用者。今天只改表达式；D04 再完整学习函数。',
        "def multiply(a, b):\n    return a * b\nprint(multiply(3, 4))\n", '12')],
    'D02-bool-none': [card('最小 if / elif / else', '按顺序判断，只执行第一个成立的分支。每层使用四个空格缩进。',
        "value = None\nif value is None:\n    print('缺失')\nelif value == '':\n    print('空文本')\nelse:\n    print('有值')\n", '缺失')],
    'D02-string-methods': [CONTAINERS],
    'D03-if': [LOGIC, RAISE],
    'D03-for': [CONTAINERS], 'D03-enumerate-zip': [CONTAINERS, RAISE],
    'D03-comprehension': [CONTAINERS],
    'D04-def-return': [card('return 不等于 print', 'print 负责显示；return 负责把结果交给后续代码。只打印而不 return，调用结果就是 None。',
        "def show_area(a, b):\n    print(a * b)\nvalue = show_area(3, 4)\nprint('返回值:', value)\n", '12\n返回值: None')],
    'D04-varargs': [CONTAINERS], 'D04-type-hints': [card('标注不会自动校验', 'name: str 和 -> str 说明输入输出类型，不会替你检查年龄范围；本节只写格式化和标注。',
        "def label(name: str, age: int) -> str:\n    return f'{name}: {age}'\nprint(label('林', 20))\n", '林: 20')],
    'D06-custom': [card('先借用一个异常类模板', '括号中的 ValueError 是父类；pass 表示类体没有额外实现。D07 再讲类、实例和继承。',
        "class InputError(ValueError):\n    pass\ntry:\n    raise InputError('名字为空')\nexcept InputError as error:\n    print(error)\n", '名字为空')],
    'D07-stdlib': [card('本节先借用 JSON 与路径', 'JSON 文本先解析成字典，再取 name；文件读写细节会在 D08 深入练。本题的临时文件由验证器准备。',
        "import json\nfrom pathlib import Path\nprint(Path('data/meta.json').suffix)\nprint(json.loads('{\"name\": \"林\"}')['name'])\n", '.json\n林')],
    'D07-dataclass': [DECORATOR],
    'D09-entry': [card('入口与退出码', 'main 返回整数，由 SystemExit 交给终端。0 表示成功；不要在导入模块时调用 main。',
        "def main(argv=None):\n    print('命令完成')\n    return 0\nif __name__ == '__main__':\n    raise SystemExit(main())\n", '命令完成')],
    'D12-request': [CALLABLE, BYTES], 'D12-post': [BYTES, CALLABLE], 'D12-timeout': [CALLABLE],
    'D13-app': [DECORATOR],
    'D13-response': [card('响应模型的最小写法', 'BaseModel 让框架识别字段。必填字段没有默认值，done=False 是默认值；D14 再深入输入验证。',
        "from pydantic import BaseModel\nclass TaskOut(BaseModel):\n    id: int\n    title: str\n    done: bool = False\nprint(TaskOut(id=1, title='学习').model_dump())\n", "{'id': 1, 'title': '学习', 'done': False}")],
    'D14-deps': [CALLABLE], 'D15-fixture': [DECORATOR], 'D15-mock': [CALLABLE],
    'D16-connect': [card('连接上下文不等于关闭连接', 'sqlite3 的 with conn 管事务，不会自动 close。连接由创建者在 finally 中关闭。',
        "import sqlite3\nconn = sqlite3.connect(':memory:')\ntry:\n    print(conn.execute('SELECT 1').fetchone())\nfinally:\n    conn.close()\n", '(1,)')],
    'D17-coroutine': [card('async def 先看一个完整调用', 'await 放在 async 函数里；脚本最外层用 asyncio.run。下一段不需要 Promise 或线程知识。',
        "import asyncio\nasync def value():\n    return 3\nasync def main():\n    return await value()\nprint(asyncio.run(main()))\n", '3')],
    'D21-app': [YIELD, DECORATOR], 'D22-db-fixtures': [YIELD],
    'D23-html-fetch': [card('先检查有没有响应体', '本项目删除统一返回 200 和 JSON。若其他接口返回 204，应先判断状态，不能无条件 response.json()。',
        "status = 204\nprint('无响应体' if status == 204 else '解析 JSON')\n", '无响应体')],
    'D25-chat': [BYTES], 'D27-client': [CALLABLE],
}


def _set_contract(section: dict[str, Any], instructions: str, starter: str | None = None,
                  examples: list[tuple[str, str]] | None = None) -> None:
    p = section['practice']
    p['instructions'] = instructions
    if starter is not None:
        p['starter_content'] = starter
        p['starter_policy'] = 'function_body' if 'NotImplementedError' in starter else 'complete'
    if examples:
        p['input_examples'] = [{'label': f'用例 {i + 1}', 'value': a, 'expected': b} for i, (a, b) in enumerate(examples)]
        if 'input_identifiers' in p:
            p['input_identifiers'] = [x for x in p['input_identifiers'] if any(x in a for a, _ in examples)]
    p['expected_behavior'] = '；'.join(x['expected'] for x in p['input_examples'])
    section['guided_practice']['goal'] = instructions
    if starter is not None:
        section['guided_practice']['starter'] = starter or '# 从给定的函数签名开始\n'
    section['guided_practice']['check'] = p['expected_behavior']


def _fill_drill(example: dict[str, Any], index: int) -> dict[str, Any] | None:
    """One deliberate coding gap in an already runnable, local example.

    Never invent output or execute code during generation. The full source is a
    test fixture for regeneration tests, not an alleged learner achievement.
    """
    if not example.get('runnable') or example.get('source_kind') != 'python':
        return None
    code = example['code']
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    candidates = [n for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.Return))
                  and getattr(n, 'value', None) is not None and n.lineno == n.end_lineno
                  and not isinstance(n.value, (ast.Await, ast.Yield, ast.YieldFrom))]
    if not candidates:
        return None
    # Prefer a computation/return to a bare setup constant when one exists.
    target = next((n for n in candidates if isinstance(n, ast.Return)), candidates[-1])
    value = target.value
    lines = code.splitlines(keepends=True)
    line = lines[value.lineno - 1]
    # AST columns are UTF-8 byte offsets, not Unicode character offsets.
    raw = line.encode('utf-8')
    lines[value.lineno - 1] = (raw[:value.col_offset] + b'None' + raw[value.end_col_offset:]).decode('utf-8')
    starter = ''.join(lines)
    starter = '# TODO：补全下面第 %d 行的 None，使输出与右侧预期一致。\n' % (value.lineno + 1) + starter
    if starter == code:
        return None
    return {'id': f'fill-{index}', 'title': f'补全练习 {index + 1}',
            'instructions': '替换 TODO 指出的占位 None，保留其他输入；运行后对比每一行输出，再完成下方独立作业。',
            'starter': starter, 'output': example['output'], 'reference': code,
            'source_kind': 'python', 'runnable': True}


def apply_practice_first(data: dict[str, Any]) -> None:
    sections = {s['id']: s for t in data['tasks'] for s in t['lesson']}
    # The outer API/guard is scaffolding here; the learner writes the arithmetic.
    _set_contract(sections['D02-numbers'],
        '保留平台提供的函数外壳和除零保护，只补 return 后的商与余数表达式。D04 再从头练函数，D06 再练异常。',
        "def divide_parts(total, size):\n    if size == 0:  # 平台提供，今天不用编写异常处理\n        raise ValueError('除数不能为零')\n    return None  # TODO：返回商、余数组成的元组\n",
        [('print(divide_parts(17, 5))', '(3, 2)'), ('print(divide_parts(-7, 2))', '(-4, 1)'), ('divide_parts(17, 0)', 'ValueError（平台保护代码）')])
    _set_contract(sections['D02-bool-none'],
        "保留函数与分支外壳，补三个返回值：None -> 'missing'，空字符串 -> 'empty text'，其他值 -> 'present'。先运行上方最小 if 示例。",
        "def describe_value(value):\n    if value is None:\n        return None  # TODO：缺失标签\n    elif value == '':\n        return None  # TODO：空文本标签\n    else:\n        return None  # TODO：其他值标签\n")
    _set_contract(sections['D02-string-methods'],
        "完成 strip/split/join：平台已提供过滤空标签的循环，不要求提前学循环。format_tags(' a,,b ') 返回 'a / b'，空输入返回 '无标签'。",
        "def format_tags(raw):\n    cleaned = None  # TODO：去除 raw 首尾空白\n    parts = None  # TODO：按逗号拆分 cleaned\n    # 下列循环由平台提供，D03/D05 再独立实现\n    tags = []\n    for part in parts:\n        if part.strip():\n            tags.append(part.strip())\n    if not tags:\n        return '无标签'\n    return None  # TODO：用 ' / ' 连接 tags\n")
    _set_contract(sections['D04-def-return'],
        '定义 rectangle_area(width, height)，返回 width * height。第一轮只传非负数字，不要求类型判断或抛异常；D06 再为这个函数增加输入校验。',
        "def rectangle_area(width, height):\n    return None  # TODO：把计算结果返回，不只 print\n",
        [('print(rectangle_area(3, 4))', '12'), ('print(rectangle_area(0, 4))', '0'), ('print(rectangle_area(2.5, 4))', '10.0')])
    # Remove contradictory advanced requirements in the reference for this task.
    s = sections['D04-def-return']
    s['explanation'][2] = '先把输入、计算和返回三个动作连起来，使用非负数字完成本题即可。类型校验、负数拒绝和异常处理会在 D06 的回访练习中加入，现在不同时考查这些新知识。'
    s['guided_practice']['steps'] = [{'action': '补全 return 后的乘法表达式。', 'expected': '3 和 4 返回 12。'}, {'action': '换成 0 和小数再运行。', 'expected': '0 返回 0，小数可继续参与计算。'}]
    _set_contract(sections['D04-default-keyword'],
        "定义 make_message(name, prefix='你好', suffix='!')，返回 prefix + '，' + name + suffix。只练默认值和关键字覆盖；可变默认参数在 D05 学完容器后再复练。",
        "def make_message(name, prefix='你好', suffix='!'):\n    return None  # TODO：组合问候\n",
        [("print(make_message('林'))", '你好，林!'), ("print(make_message('林', prefix='早上好', suffix='。'))", '早上好，林。')])
    _set_contract(sections['D04-type-hints'],
        "定义 format_user(name: str, age: int) -> str，精确返回 f'{name}: {age}'（英文冒号后一个空格），不要求用反射 API 自检。",
        "def format_user(name: str, age: int) -> str:\n    return None  # TODO：姓名、英文冒号、空格、年龄\n")
    _set_contract(sections['D03-comprehension'],
        '定义 summarize_numbers(values)：even_squares 保留每个偶数的平方（不去重），unique 为原值集合，by_value 为原值到平方的映射。空输入返回三个空容器。',
        examples=[('print(summarize_numbers([1, 2, 2, 3]))', "{'even_squares': [4, 4], 'unique': {1, 2, 3}, 'by_value': {1: 1, 2: 4, 3: 9}}（集合顺序不考查）"), ('print(summarize_numbers([]))', "{'even_squares': [], 'unique': set(), 'by_value': {}}")])
    _set_contract(sections['D03-enumerate-zip'],
        "定义 pair_scores(names, scores)：返回 name/score/position 三个键的字典列表，position 从 1 开始。长度不同抛 ValueError，先运行上方 raise 示例。")
    _set_contract(sections['D05-comprehensions'],
        "定义 build_indexes(words)，返回 {'lengths': 非空原词到长度的字典, 'unique': 非空词的小写集合}；忽略空字符串，保留原词大小写作为 lengths 的键。")
    _set_contract(sections['D06-exception-types'],
        "定义 error_label(operation)：'convert' 返回 'ValueError'，'key' 返回 'KeyError'，'index' 返回 'IndexError'。分别实际触发并捕获对应异常；未知操作抛 ValueError。")
    _set_contract(sections['D07-import'],
        "导入 pathlib.Path 和 math；show_path(path) 返回 (Path(path).suffix, math.ceil(2.1))。例如 report.txt -> ('.txt', 3)。")
    _set_contract(sections['D07-stdlib'],
        '定义 read_metadata(path)，读取 UTF-8 JSON；顶层须为 dict 且 name 为字符串，否则抛 ValueError。缺文件保留 FileNotFoundError，坏 JSON 保留 JSONDecodeError。测试文件由验证器准备。')
    _set_contract(sections['D12-post'],
        "定义 post_json(url,payload,opener)：dumps 后 UTF-8 encode，发送 POST Request，Content-Type 为 application/json。用 with 读取响应并 json.loads，返回 dict；opener 只调用一次。")
    _set_contract(sections['D12-response'],
        "定义 parse_response(response)：非 2xx 抛 RuntimeError；成功时 UTF-8 解码并 json.loads 返回解析结果。坏 JSON 保留 JSONDecodeError。response 由平台提供，含 status 和 read()。")
    _set_contract(sections['D12-timeout'],
        "定义 fetch_with_timeout(url,opener,timeout=2)：传入 GET Request 与 timeout，with 读取 UTF-8 文本并返回 str。超时和网络异常继续传播，不自动重试。")
    _set_contract(sections['D14-errors'],
        "定义 get_or_404(repo,task_id)：调用 repo.get(task_id)，返回 None 时 raise HTTPException(404, detail='任务不存在')，有值则返回原对象。平台提供 repo。")
    _set_contract(sections['D15-api'],
        "平台提供 app.py 和 app fixture：GET /health 返回 200/{'status':'ok'}，POST /tasks 返回 201/{'id':1,**请求体}。写 test_ 函数，用 TestClient 测健康、创建和不存在路径 404，不启动端口。")
    _set_contract(sections['D13-route'],
        "创建 app；GET /tasks/{task_id}（task_id:int）返回 {'id': task_id}；GET /tasks（limit:int=20）返回 {'limit': limit}。非法数字由框架返回 422。")
    sections['D13-lifecycle']['optional'] = True
    sections['D13-lifecycle']['title'] = 'D17 后选修：异步生命周期'
    _set_contract(sections['D14-model'],
        '定义 TaskIn(BaseModel)，title 必填字符串，priority 为 int 默认 0。本节直接构造对象：错误会抛 ValidationError；通过 FastAPI 接收请求时才转换成 422。')
    _set_contract(sections['D14-deps'],
        "定义 app、get_repo()，默认返回内含一条 {'title': '真实数据'} 的列表；GET /tasks 使用 Depends(get_repo) 并原样返回列表。验证器替换 get_repo 后检查输出，不需要未定义的 RealRepo。",
        "from fastapi import FastAPI, Depends\napp = FastAPI()\ndef get_repo():\n    return [{'title': '真实数据'}]\n@app.get('/tasks')\ndef list_tasks(repo=Depends(get_repo)):\n    return None  # TODO：返回注入的列表\n")
    _set_contract(sections['D15-mock'],
        "本题提交 test_client.py。平台提供 client.py，含 get_json(url)、post_json(url,payload)，内部使用 urllib.request.urlopen。用 patch('client.urllib.request.urlopen') 替换查找位置，测试返回 JSON 和请求参数；不要另写 load_value。",
        "import json\nfrom unittest.mock import MagicMock, patch\nimport client\n\ndef test_get_json():\n    response = MagicMock()\n    response.__enter__.return_value.read.return_value = b'{\"ok\": true}'\n    with patch('client.urllib.request.urlopen', return_value=response) as opener:\n        # TODO：调用 client.get_json('https://example.test') 并断言结果和调用参数\n        pass\n")
    _set_contract(sections['D17-timeout'],
        "定义 async slow()：await asyncio.sleep(0.05) 后返回 'done'。定义 async run_with_timeout(seconds)，await asyncio.wait_for(slow(), timeout=seconds)。足够时间返回 'done'，超时传播 TimeoutError；验证器会额外注入可控慢任务检查取消。",
        "import asyncio\nasync def slow():\n    await asyncio.sleep(0.05)\n    return 'done'\nasync def run_with_timeout(seconds):\n    return None  # TODO：等待 slow，同时限制超时\n")
    _set_contract(sections['D18-data-contract'],
        '只写数据契约：task.input.title="string"；task.output 为 {"id":1,"title":"string","done":false}；errors 记录 empty_title=422、unknown_id=404。本节不检查 endpoints。',
        '{\n  "task": {"input": {"title": "string"}, "output": {"id": 1, "title": "string", "done": false}},\n  "errors": {"empty_title": 422, "unknown_id": 404}\n}\n',
        [('task.input.title / task.output.id,title,done', '输入输出字段类型明确'), ('删除 errors.unknown_id 后验证', '提示缺少 unknown_id 错误约定')])
    _set_contract(sections['D18-api-contract'],
        '保留 task 与 errors，添加 endpoints 数组：GET /、GET /health、GET /api/tasks、POST /api/tasks、PATCH /api/tasks/{task_id}/done、DELETE /api/tasks/{task_id}。每项含 method/path；创建 201，删除统一 200 返回 JSON。')
    _set_contract(sections['D19-config'],
        '定义 get_db_path() -> Path，读取非空 TASKPROJ_DB，否则默认 taskproj.db。函数名固定为 get_db_path，供 API 和 CLI 复用；本节不要求额外 database_path 函数。',
        "import os\nfrom pathlib import Path\ndef get_db_path():\n    return None  # TODO：读取路径并转为 Path\n")
    _set_contract(sections['D19-main'],
        "定义 main(argv=None)：打印一行'任务管理项目已启动'并返回 0。使用 __name__ 守卫调用入口，import 时不输出；数据库初始化在 D20 加入。",
        "def main(argv=None):\n    # TODO：打印启动提示并返回 0\n    pass\nif __name__ == '__main__':\n    raise SystemExit(main())\n")
    _set_contract(sections['D21-schema'],
        '保留上一节 app 与 /health，定义 TaskIn（title 非空、拒绝纯空白）和 Task（id:int,title:str,done:bool）。本节只验收模型；POST 路由留到下一节。')
    _set_contract(sections['D21-crud-routes'],
        '接入 GET/POST /api/tasks、PATCH /api/tasks/{task_id}/done、DELETE /api/tasks/{task_id}；创建返回 201，删除统一返回 200 和 JSON，未知 ID 为 404。此时不检查 GET /，首页在下一节接入。')
    _set_contract(sections['D21-static'],
        "保留 API 路由，添加 GET /，通过 FileResponse 返回 Path(__file__).parent/'static'/'index.html'；完整 HTML 到 D23 才生成，此处只检查路由声明，不要求尚未生成的页面可打开。")
    _set_contract(sections['D22-acceptance'],
        '补充测试：验证当前已存在的 contract.json 和 CRUD/API 行为。本节不要断言尚未生成的 CLI、HTML、runbook、review；15 文件完整验收由 D24 执行。')
    _set_contract(sections['D23-html-fetch'],
        '实现 GET 加载、POST 创建、PATCH 完成、DELETE 删除；本项目删除返回 200 JSON。先检查 response.ok 再解析；兼容 204 时跳过 response.json()。用 textContent 展示用户标题，避免 innerHTML 注入。')
    # Earlier chapters must never ask learners to invent a not-yet-taught wrapper.
    wrappers = {
        'D02-strings': "def transform_text(text):\n    cleaned = text.strip()  # 平台提供去首尾空白；字符串方法在下一节练\n    return None  # TODO：用切片反转 cleaned\n",
        'D03-if': "def classify_score(score):\n    # TODO：参照上方 if 和 raise 示例，处理 -1、59、60、90\n    pass\n",
        'D03-while': "def countdown(start):\n    result = []\n    # TODO：while 中把 start 加入 result，再递减\n    return result\n",
        'D03-break-continue': "def first_large(items, limit):\n    # TODO：遍历，跳过 None，命中后返回；否则返回 None\n    return None\n",
        'D03-enumerate-zip': "def pair_scores(names, scores):\n    # TODO：先检查长度，使用 zip/enumerate 构造记录\n    result = []\n    return result\n",
        'D03-comprehension': "def summarize_numbers(values):\n    return {'even_squares': [], 'unique': set(), 'by_value': {}}  # TODO：填三种推导式\n",
        'D04-scope': "def read_config(default):\n    return None  # TODO：只返回本次传入的值\n",
    }
    for sid, starter in wrappers.items():
        _set_contract(sections[sid], sections[sid]['practice']['instructions'], starter)
    _set_contract(sections['D05-unpacking'],
        '定义 merge_task(defaults,overrides)，用字典解包生成新字典，后者覆盖前者；split_edges(values) 返回 (first,middle,last)，middle 是列表，长度不足两项抛 ValueError。')
    # Consistent project explanations: no alternate, unimplemented public interface.
    sections['D19-config']['examples'][0]['code'] = "import os\nfrom pathlib import Path\n\ndef get_db_path():\n    return Path(os.environ.get('TASKPROJ_DB') or 'taskproj.db')\n"
    sections['D19-config']['examples'][0]['output'] = "调用 get_db_path() 返回 Path；默认 taskproj.db"
    sections['D19-config']['examples'][1]['code'] = "# 调用者设置 TASKPROJ_DB=demo.db 后，get_db_path() 返回 Path('demo.db')。\n# 配置函数只读取环境，不在导入时修改环境变量。\n"
    sections['D19-config']['examples'][1]['output'] = "demo.db"
    sections['D21-static']['examples'][0]['code'] = "from pathlib import Path\nfrom fastapi.responses import FileResponse\n\n@app.get('/')\ndef index():\n    return FileResponse(Path(__file__).parent / 'static' / 'index.html')\n"
    sections['D21-static']['examples'][0]['output'] = "GET / 路由已声明；页面文件在 D23 创建后才能展示。"
    sections['D21-static']['examples'][1]['code'] = "# D23 完成 HTML 后，用浏览器打开 http://127.0.0.1:8000/\n# API 仍通过 /api/tasks 访问，不被首页路由覆盖。\n"
    sections['D21-static']['examples'][1]['output'] = "显示任务列表页面；GET /api/tasks 仍返回 JSON。"
    for sid in ['D19-config','D21-static']:
        sections[sid]['example'] = sections[sid]['examples'][0]
        for ex in sections[sid]['examples']:
            ex['code'] = '# ' + ex['target_path'] + '\n' + ex['code']
            ex['explanation'] = '此代码片段写入本节指定的真实项目文件，并与已经完成的前置文件一起使用。它不是独立实验程序；按照本题函数名和路径操作，后续章节再接入完整运行入口。'
    # These cards teach the small mandatory subset, not the optional whole topic.
    collect_card = card('用列表收集循环结果', '先建空列表，再用 append 追加一个值。不要把 append 的返回值赋给列表。',
        "values = []\nfor number in range(1, 4):\n    values.append(number)\nprint(values)\n", '[1, 2, 3]')
    for sid in ['D03-for','D03-while','D03-enumerate-zip']:
        if not any(c['title'] == collect_card['title'] for c in SUPPORT.get(sid, [])):
            SUPPORT.setdefault(sid, []).append(collect_card)
    SUPPORT['D21-schema'] = [card('非空字符串与 field_validator',
        '先让 Pydantic 检查字符串，再 strip；清洗后为空就 raise ValueError。此函数由装饰器注册，不是让你学习新的验证框架。',
        "from pydantic import BaseModel, field_validator\nclass TaskIn(BaseModel):\n    title: str\n    @field_validator('title')\n    @classmethod\n    def nonempty(cls, value):\n        value = value.strip()\n        if not value:\n            raise ValueError('标题不能为空')\n        return value\nprint(TaskIn(title=' 学习 ').title)\n", '学习')]
    # Full asyncio is deliberately deferred; mandatory work must not depend on it here.
    for t in data['tasks']:
        tid = t['id']
        t['learning_goal'] = TASK_PRACTICE[tid]
        for s in t['lesson']:
            sid = s['id']
            if s['practice']['kind'] == 'code':
                # Replace unexplained exception placeholders, not genuine error examples.
                s['practice']['starter_content'] = s['practice']['starter_content'].replace('raise NotImplementedError', 'pass  # TODO：实现这里')
                s['practice']['starter_policy'] = 'complete'
            prior = list(TASK_PREREQUISITES[tid])
            s['practice_first'] = {
                'goal': s['practice']['instructions'],
                'rules': [s['syntax'], TASK_PRACTICE[tid]],
                'prerequisites': prior,
                'cards': copy.deepcopy(SUPPORT.get(sid, [])),
                'drills': [],
            }
            pf = s['practice_first']
            if sid == 'D13-lifecycle':
                pf['deferred_until'] = 'D17'
                pf['rules'] = ['本节不阻塞主线。先完成 D17 的 async/await，再回来组合 lifespan。', 'yield 和 asynccontextmanager 的模板已提供；不是让你在 D13 自学整套异步。']
            if sid.startswith('D02-') or sid.startswith('D03-'):
                pf['provided'] = '起始代码中的函数签名及标注“平台提供”的代码可以保留；本题只编写 TODO 部分。'
            elif s['practice'].get('workspace_deps'):
                pf['provided'] = '继续编辑你已生成的真实文件；依赖：' + '、'.join(s['practice']['workspace_deps'])
            else:
                pf['provided'] = '主作业只提交当前编辑器内容。独立实验在临时目录运行，不覆盖作业和项目。'
            if sid in {'D12-request', 'D12-post', 'D12-timeout'}:
                pf['provided'] = '验证器提供 opener(request, timeout=...) 和支持 with/read 的假响应；下面示例可离线运行。提交时只写题目指定函数，不需要先学 Mock。'
            if sid == 'D15-mock':
                pf['provided'] = '平台提供 client.py（get_json/post_json）；patch 目标为 client.urllib.request.urlopen。'
            if sid in {'D27-client', 'D27-flow'}:
                pf['provided'] = '平台提供 deepseek_client.py（call_chat/ApiError）和 prompt.py（build_prompt/parse_ai_json）作为离线练习夹具；你负责当前组合函数。'
            # Existing examples remain reference. The gap exercise has its own state.
            # These examples contain an unexecuted branch, or replacing the chosen
            # value with None preserves the output. Keep them as demonstrations,
            # not meaningless gap exercises. Regression tests enforce this list.
            no_gap = {
                ('D02-bool-none', 0), ('D02-bool-none', 1), ('D03-if', 0), ('D06-try-except', 0),
                ('D09-entry', 0), ('D10-convert', 0), ('D11-stream', 0),
                ('D11-stream', 1), ('D11-file', 1), ('D14-service', 1),
            }
            if s['practice']['kind'] == 'code':
                for i, e in enumerate(s['examples']):
                    if (sid, i) in no_gap:
                        continue
                    drill = _fill_drill(e, i)
                    if drill:
                        pf['drills'].append(drill)
            if sid == 'D03-if':
                pf['drills'].insert(0, {'id': 'logic-entry', 'title': '独立写：通行条件',
                    'instructions': '用 and 和 not：有票且未被禁止才能进入。改一次 is_blocked，再比较结果。',
                    'starter': "has_ticket = True\nis_blocked = False\ncan_enter = None  # TODO：填写条件表达式\nprint(can_enter)\n",
                    'output': 'True', 'reference': "has_ticket = True\nis_blocked = False\ncan_enter = has_ticket and not is_blocked\nprint(can_enter)\n", 'runnable': True, 'source_kind': 'python'})
            if sid == 'D06-raise':
                c = card('回访 D04：给面积增加校验', '现在才把负数校验加回函数；or 表示任意边长为负就拒绝。',
                    "def rectangle_area(width, height):\n    if width < 0 or height < 0:\n        raise ValueError('边长不能为负数')\n    return width * height\ntry:\n    rectangle_area(-1, 4)\nexcept ValueError as error:\n    print(type(error).__name__, error)\n", 'ValueError 边长不能为负数')
                pf['cards'].append(c)
                drill = _fill_drill(c, 99)
                if drill:
                    drill['title'] = '回访练习：完善面积函数'
                    # Keep a runnable placeholder, with the colon outside the comment.
                    drill['starter'] = c['code'].replace('if width < 0 or height < 0:', 'if False:  # TODO：填写 or 条件')
                    pf['drills'].append(drill)
    # Register the revision separately: existing verified IDs and learner drafts survive.
    data['meta']['practice_first_revision'] = 1
    data['meta']['suggested_cycle'] = '按可投入时间推进，D01–D28 是任务编号，不是固定天数；先完成核心实践，再做选修巩固。'
    data['meta']['learning_mode'] = '先看短例子 → 补全代码 → 独立作业 → 对比实际结果；详细原理折叠查看'

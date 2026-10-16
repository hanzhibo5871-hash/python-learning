"""Audited, just-in-time teaching; applied only when building curriculum data.

Existing lesson IDs, assignment paths and independent drill IDs stay stable.
Examples deliberately use a different problem from the formal assignment.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def lesson_card(title: str, rule: str, code: str, output: str) -> dict[str, Any]:
    return dict(title=title, rule=rule, code=code, output=output,
                source_kind="python", runnable=True)


def gap(identifier: str, title: str, instructions: str, source: str,
        expression: str, output: str) -> dict[str, Any]:
    if source.count(expression) != 1:
        raise ValueError(f"{identifier}: gap must have one exact location")
    return dict(id=identifier, title=title, instructions=instructions,
                starter=source.replace(expression, "None"), reference=source,
                output=output, source_kind="python", runnable=True)


LENGTH = lesson_card(
    "len：取得元素个数",
    "作用：len(对象)返回元素个数。常用：检查输入数量、控制位置边界；字符串返回字符数。写法：count = len(items)，不是 items.len()；不需要导入。",
    "items = ['米', '水', '盐']\nprint(len(items))\nprint(len([]))\nprint(len('你好'))\n", "3\n0\n2")
LENGTH_CONDITION = lesson_card(
    "长度也是数字：比较后再分支",
    "作用：把个数与要求比较。写法：== 恰好、!= 不等、< 不足、>= 至少；条件成立才执行缩进内的代码。常用：先确认数量，再读取或处理数据。",
    "ingredients = ['米', '水']\nprint(len(ingredients) == 3)\nprint(len(ingredients) != 3)\nif len(ingredients) < 3:\n    print('材料不足')\nelse:\n    print('材料齐全')\n", "False\nTrue\n材料不足")
VALUE_REJECTION = lesson_card(
    "raise ValueError：明确拒绝不合要求的值",
    "作用：raise 异常类('原因')停止当前路径。常用：输入类型合适，但值不符合业务要求，用 ValueError；它不是 print，也不是 return。下面 try/except 是平台提供的展示外壳，D06 再系统练捕获。",
    "quantity = -3\ntry:  # 平台提供：让实验显示错误而不是直接退出\n    if quantity < 0:\n        raise ValueError('数量不能为负数')\n    print('继续处理')\nexcept ValueError as error:  # 平台提供\n    print(type(error).__name__)\n    print(error)\n", "ValueError\n数量不能为负数")
TUPLE_CONVERSION = lesson_card(
    "tuple：从已有序列创建元组",
    "作用：tuple(序列)把已有元素收集为元组。常用：返回固定的一组结果。写法：converted = tuple(items)；读取原序列，不会像 append/pop 那样改变原 list。",
    "measurements = [8, 13, 21]\nconverted = tuple(measurements)\nprint(converted)\nprint(measurements)\n", "(8, 13, 21)\n[8, 13, 21]")
SET_CONVERSION = lesson_card(
    "set：从序列去重；len：数唯一值",
    "作用：set(序列)创建去重集合，len(集合)返回不同元素的个数。常用：检查有哪些不同值。集合没有承诺展示顺序；本例只观察成员和数量。",
    "levels = [4, 4, 9]\nunique = set(levels)\nprint(4 in unique)\nprint(len(unique))\nprint(len(set([])))\n", "True\n2\n0")
SORTED = lesson_card(
    "sorted：创建有序的展示列表",
    "作用：sorted(可迭代对象)返回新的排序列表。常用：让集合或字典键的展示稳定；不改变原容器，也不让集合本身变成有序。",
    "levels = [9, 4, 9]\nprint(sorted(levels))\nprint(levels)\nprint(sorted({9, 4}))\n", "[4, 9, 9]\n[9, 4, 9]\n[4, 9]")
GET_DEFAULT = lesson_card(
    "dict.get：缺键时使用默认值",
    "作用：mapping.get(key, default)读取键；只有键不存在时才返回默认值。常用：处理外部记录的可选字段；它不会新增键，也不会把 None 或空字符串自动替换掉。",
    "record = {'city': '杭州', 'note': None}\nprint(record.get('city', '未知'))\nprint(record.get('color', '蓝色'))\nprint(record.get('note', '无备注'))\nprint('color' in record)\n", "杭州\n蓝色\nNone\nFalse")
LOWER = lesson_card(
    "str.lower 与过滤空字符串",
    "作用：text.lower()返回字母的小写形式，原字符串不变。常用：统一大小写后比较或去重。if word 可过滤空字符串；空格字符串仍为真，本题不要求额外 strip。",
    "word = 'HELLO'\nprint(word.lower())\nprint(word)\nprint({color.lower() for color in ['RED', 'red', ''] if color})\n", "hello\nHELLO\n{'red'}")
MEMBERSHIP = lesson_card(
    "in / not in：检查是否出现过",
    "作用：value in items判断成员是否存在，not in判断不存在。常用：重复检测、过滤已处理值；先作判断，再决定是否追加，才能保留原有顺序。",
    "visited = ['西湖', '故宫']\nprint('西湖' in visited)\nprint('黄山' not in visited)\nprint(visited)\n", "True\nTrue\n['西湖', '故宫']")
SUM = lesson_card(
    "sum 与累加：合并多项数值",
    "作用：sum(数值序列)求和，空序列结果为 0。常用：汇总数量或金额；逐项循环也可写 total += value，+= 等价于把新值加到旧值后赋回。",
    "distances = [2, 5, 8]\nprint(sum(distances))\nprint(sum([]))\ntotal = 0\nfor distance in distances:\n    total += distance\nprint(total)\n", "15\n0\n15")


D05_CARDS = {
    'D05-list-tuple': [LENGTH, LENGTH_CONDITION, VALUE_REJECTION, TUPLE_CONVERSION],
    'D05-dict-set': [SET_CONVERSION, SORTED],
    'D05-unpacking': [LENGTH_CONDITION, VALUE_REJECTION],
    'D05-traversal': [GET_DEFAULT],
    'D05-comprehensions': [LOWER],
    'D05-tags': [MEMBERSHIP],
    'D05-counts': [GET_DEFAULT],
    'D05-cart': [SUM],
}
D05_DRILLS = {
    'D05-list-tuple': [
        gap('ready-length', '先练：取得不同长度', '只替换 count 的 None，使用 len；输入分别为空、一项、三项。',
            "for samples in ([], ['风'], ['风', '雨', '雪']):\n    count = len(samples)  # TODO：替换这里\n    print(count)\n", 'len(samples)', '0\n1\n3'),
        gap('ready-length-condition', '再练：至少三项的条件', '只替换 allowed 的 None；判断当前序列是否至少有三项，不先处理元素。',
            "for samples in ([], ['风', '雨', '雪'], ['风', '雨', '雪', '云']):\n    allowed = len(samples) >= 3  # TODO：替换这里\n    print(allowed)\n", 'len(samples) >= 3', 'False\nTrue\nTrue'),
        gap('ready-raise', '再练：选择值错误类型', '把 raise 后的 None 换为带错误原因的 ValueError 异常对象，主动拒绝负数量。try/except 展示外壳已提供，保留它。',
            "quantity = -3\ntry:\n    if quantity < 0:\n        raise ValueError('数量不能为负数')  # TODO：异常类\nexcept ValueError as error:\n    print(type(error).__name__)\n    print(error)\n", "ValueError('数量不能为负数')", 'ValueError\n数量不能为负数'),
        gap('ready-tuple', '最后练：转换后保留原列表', '只替换 converted 的 None，把三个测量值转为元组；原列表不应改变。随后独立组合长度检查与返回。',
            "measurements = [8, 13, 21]\nconverted = tuple(measurements)  # TODO：替换这里\nprint(converted)\nprint(measurements)\n", 'tuple(measurements)', '(8, 13, 21)\n[8, 13, 21]'),
    ],
    'D05-traversal': [gap('ready-get', '先练：读取可选城市', '用 get 提供缺失默认值，不写入原记录。',
        "for record in ({'city': '杭州'}, {}):\n    city = record.get('city', '未知')  # TODO：替换这里\n    print(city)\n", "record.get('city', '未知')", '杭州\n未知')],
    'D05-comprehensions': [gap('ready-lower', '先练：大小写转换', '只替换 normalized 的 None，将当前单词转小写，不修改 word。',
        "for word in ('RED', 'Blue', ''):\n    normalized = word.lower()  # TODO：替换这里\n    print(normalized, word == '')\n", 'word.lower()', 'red False\nblue False\n True')],
    'D05-tags': [gap('ready-membership', '先练：判断是否尚未访问', '只替换 is_new 的 None，用 not in 判断景点尚未出现。',
        "visited = ['西湖', '故宫']\nfor place in ('西湖', '黄山'):\n    is_new = place not in visited  # TODO：替换这里\n    print(is_new)\n", 'place not in visited', 'False\nTrue')],
    'D05-cart': [gap('ready-sum', '先练：汇总不同距离', '只替换 total 的 None，用 sum 对当前数值列表求和；同时观察空输入。',
        "for distances in ([2, 5, 8], []):\n    total = sum(distances)  # TODO：替换这里\n    print(total)\n", 'sum(distances)', '15\n0')],
}


def _contract(section, instructions, starter, cases, steps):
    p = section['practice']
    p.update(instructions=instructions, starter_content=starter,
             starter_policy='complete', input_examples=cases,
             expected_behavior='；'.join(c['expected'] for c in cases))
    section['guided_practice'].update(goal=instructions, starter=starter,
                                     steps=steps, check=p['expected_behavior'])
    section['practice_first']['goal'] = instructions


def apply_course_readiness(data: dict[str, Any]) -> None:
    sections = {s['id']: s for t in data['tasks'] for s in t['lesson']}
    # Earlier zip also requires length checks; D05 repeats locally so learners
    # never have to go back to find a newly added teaching card.
    sections['D03-enumerate-zip']['practice_first']['cards'][:0] = copy.deepcopy([LENGTH, LENGTH_CONDITION])
    for sid, cards in D05_CARDS.items():
        sections[sid]['practice_first']['cards'].extend(copy.deepcopy(cards))
    for sid, drills in D05_DRILLS.items():
        sections[sid]['practice_first']['drills'].extend(copy.deepcopy(drills))
    first = sections['D05-list-tuple']
    first['syntax'] = 'len(values) 取得个数；比较后用 if 判断；raise ValueError 拒绝不合要求的值；tuple(values) 创建元组。'
    first['practice_first']['rules'][0] = first['syntax']
    _contract(first,
        '定义 normalize_pair(values)：输入为 list 或 tuple，恰好两个元素时返回 tuple；不修改输入 list。其他长度主动抛 ValueError，不要求额外类型校验。先完成本节 len、比较、raise、tuple 小练习，再独立组合。',
        'def normalize_pair(values):\n    # TODO：先检查数量，再返回所需容器；不要改变原输入\n    pass\n',
        [dict(label='正常与原列表', value='values = [1, 2]; print(normalize_pair(values)); print(values)', expected='返回 (1, 2)，原 list 仍为 [1, 2]。'),
         dict(label='已有元组', value="print(normalize_pair(('x', 'y')))", expected="返回 ('x', 'y')。"),
         dict(label='长度边界', value='normalize_pair([]) / normalize_pair([1]) / normalize_pair([1, 2, 3])', expected='这三种输入都抛 ValueError；错误说明可自行选择。')],
        [dict(action='先运行知识卡，再依次补长度、条件、异常和转换小练习。', expected='能解释每项输出，无须编写 try/except 展示外壳。'),
         dict(action='独立完成给定函数，测试有效长度并观察原输入。', expected='返回 tuple，原 list 保持不变。'),
         dict(action='对空、一项、三项输入分别运行。', expected='走拒绝路径而不继续返回正常结果。')])
    first['practice_first']['provided'] += ' raise 小实验中的 try/except 是展示外壳；正式作业只要求主动抛错，D06 再系统学习捕获。'
    unpacking = sections['D05-unpacking']
    _contract(unpacking, unpacking['practice']['instructions'],
        'def merge_task(defaults, overrides):\n    # TODO：创建新的合并字典\n    pass\n\ndef split_edges(values):\n    # TODO：先检查长度，再解包；中间部分是列表\n    pass\n',
        [dict(label='合并覆盖', value="merge_task({'title': '旧', 'done': False}, {'title': '新'})", expected="得到 {'title': '新', 'done': False}，原字典不变。"),
         dict(label='首中尾', value='split_edges([1, 2, 3, 4])', expected='返回 (1, [2, 3], 4)。'),
         dict(label='最短有效输入', value='split_edges([5, 6])', expected='返回 (5, [], 6)。'),
         dict(label='不足两项', value='split_edges([]) / split_edges([1])', expected='都抛 ValueError。')],
        [dict(action='观察字典覆盖和星号解包示例，分别实现两个函数。', expected='新字典后者覆盖前者，middle 保持列表。'),
         dict(action='比较两项与一项输入。', expected='两项可以解包，一项明确拒绝。')])
    unpacking['practice']['input_identifiers'] = ['merge_task', 'split_edges']
    for sid, signature in [('D05-traversal', 'titles(rows)'), ('D05-comprehensions', 'build_indexes(words)')]:
        section = sections[sid]
        starter = f'def {signature}:\n    # TODO：按本节要求读取和组合结果\n    pass\n'
        section['practice']['starter_content'] = starter
        section['guided_practice']['starter'] = starter
    # State is never migrated for these teaching additions: IDs and assignments
    # are identical, drills remain practice-only and cannot complete a lesson.
    data['meta']['practice_first_revision'] = 2
    apply_audited_updates(data)
    from course_readiness_project import apply as apply_project_teaching
    apply_project_teaching(data)
    append_agent_course(data)


def apply_audited_updates(data):
    """Apply reviewed source data, never learner workspace or progress records."""
    bundle = json.loads(Path(__file__).with_name('course_readiness_data.json').read_text(encoding='utf-8'))
    sections = {s['id']: s for t in data['tasks'] for s in t['lesson']}
    for update in bundle['updates']:
        section = sections[update['id']]
        for path, value in update.get('replace', {}).items():
            target = section
            parts = path.split('.')
            for key in parts[:-1]:
                target = target.setdefault(key, {})
            target[parts[-1]] = copy.deepcopy(value)
        section['practice_first']['cards'].extend(copy.deepcopy(update.get('append_cards', [])))
        section['practice_first']['drills'].extend(copy.deepcopy(update.get('append_drills', [])))
        if 'examples' in update.get('replace', {}):
            from practice_first_content import _fill_drill
            section['example'] = copy.deepcopy(section['examples'][0])
            # Keep corresponding fill IDs while replacing obsolete demonstrations.
            section['practice_first']['drills'] = [d for d in section['practice_first']['drills']
                                                   if not d['id'].startswith('fill-')]
            for index, example in enumerate(section['examples']):
                candidate = copy.deepcopy(update.get('fill_overrides', {}).get(str(index))) or _fill_drill(example, index)
                if candidate and index not in update.get('auto_drill_exclusions', []):
                    section['practice_first']['drills'].insert(index, candidate)
        section['practice_first']['goal'] = section['practice']['instructions']
        section['guided_practice']['goal'] = section['practice']['instructions']
        section['guided_practice']['check'] = section['practice']['expected_behavior']
        section['guided_practice']['starter'] = section['practice']['starter_content']
    for entry in bundle['coverage']:
        sid = entry.get('section', entry.get('id'))
        if sid in sections:
            scope = entry.get('requires', entry.get('required', entry.get('formal', [])))
            sections[sid]['practice_first']['knowledge_scope'] = [scope] if isinstance(scope, str) else scope
    data['meta']['course_audit_revision'] = 1


def append_agent_course(data):
    task = json.loads(Path(__file__).with_name('agent_course.json').read_text(encoding='utf-8'))
    if any(t['id'] == task['id'] for t in data['tasks']):
        raise ValueError('Agent course must be generated once from its authored source')
    data['tasks'].append(task)
    stage = next(stage for stage in data['stages'] if stage['id'] == 'S4')
    stage['task_ids'] = [tid for tid in stage['task_ids'] if tid != task['id']] + [task['id']]
    stage['title'] = 'AI 应用、Agent 与 FDE 交付'
    stage['goal'] = '先掌握API与结构化输出，再用离线模型完成受控工具循环和业务验收。'
    data['meta']['agent_course_revision'] = 1

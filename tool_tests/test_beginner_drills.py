from __future__ import annotations

from pathlib import Path

import pytest

from learnctl.curriculum import load_curriculum
from learnctl.drills import CLI_CASES, FUNCTION_CASES, SCRIPT_CASES
from learnctl.practice import find_section, run_validation


# 仅用于工具回归的参考实现，不进入课程数据或 Web 响应。
SOLUTIONS = {
    'D02-input': "print(int(input()) * 2)",
    'D02-receipt': "price=float(input())\nquantity=int(input())\nprint(f'总价：{price*quantity:.2f}')",
    'D02-normalize': "print(input().strip().lower())",
    'D03-delivery': "amount=float(input())\nif amount>=99: print(0)\nelse: print(8)",
    'D03-odd-total': "n=int(input())\ntotal=0\nfor number in range(1,n+1):\n    if number%2: total+=number\nprint(total)",
    'D03-countdown': "n=int(input())\nwhile n>0:\n    print(n)\n    n-=1\nprint('完成')",
    'D04-shipping': "def shipping(amount):\n    return 0 if amount>=99 else 8",
    'D04-greeting': "def greet(name,greeting='你好'):\n    return f'{greeting}，{name}'",
    'D04-convert': "def to_fahrenheit(c):\n    return c*9/5+32",
    'D05-tags': "def unique_tags(tags):\n    result=[]\n    for tag in tags:\n        if tag not in result: result.append(tag)\n    return result",
    'D05-counts': "def count_items(items):\n    counts={}\n    for item in items: counts[item]=counts.get(item,0)+1\n    return counts",
    'D05-cart': "def cart_total(items):\n    return sum(item['price']*item['quantity'] for item in items)",
    'D06-parse': "def parse_quantity(text):\n    try: return int(text)\n    except ValueError: return None",
    'D06-positive': "def positive_quantity(text):\n    quantity=int(text)\n    if quantity<=0: raise ValueError('必须为正数')\n    return quantity",
    'D06-average': "def average(values):\n    if not values: raise ValueError('没有数据')\n    return sum(values)/len(values)",
    'D07-slug': "def slugify(title):\n    return title.strip().lower().replace(' ','-')",
    'D07-counter': "class Counter:\n    def __init__(self): self.value=0\n    def increment(self):\n        self.value+=1\n        return self.value",
    'D07-dataclass-total': "from dataclasses import dataclass\n@dataclass\nclass LineItem:\n    price: float\n    quantity: int\n    def total(self): return self.price*self.quantity",
    'D08-read-lines': "from pathlib import Path\ndef read_names(path):\n    return [line.strip() for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]",
    'D08-json-total': "from pathlib import Path\nimport json\ndef total_expenses(path):\n    return sum(item['amount'] for item in json.loads(Path(path).read_text(encoding='utf-8')))",
    'D08-json-report-drill': "from pathlib import Path\nimport json\ndef write_report(path,names):\n    Path(path).write_text(json.dumps({'count':len(names),'names':names},ensure_ascii=False),encoding='utf-8')",
    'D09-greet-cli': "import argparse\np=argparse.ArgumentParser()\np.add_argument('--name',required=True)\na=p.parse_args()\nprint(f'你好，{a.name}')",
    'D09-repeat-cli': "import argparse\np=argparse.ArgumentParser()\np.add_argument('--word',required=True)\np.add_argument('--count',type=int,default=1)\na=p.parse_args()\nif a.count<=0: p.error('count必须为正数')\nfor _ in range(a.count): print(a.word)",
    'D09-square-cli': "import argparse\ndef square(n): return n*n\nif __name__=='__main__':\n    p=argparse.ArgumentParser()\n    p.add_argument('number',type=int)\n    a=p.parse_args()\n    print(square(a.number))",
}


@pytest.mark.parametrize('section_id', SOLUTIONS)
def test_new_drill_accepts_real_solution_and_rejects_empty_program(section_id, tmp_path):
    curriculum = load_curriculum(Path('data/curriculum.json'))
    good = run_validation(curriculum, section_id[:3], section_id, SOLUTIONS[section_id], tmp_path)
    assert good['passed'], good
    bad = run_validation(curriculum, section_id[:3], section_id, 'pass', tmp_path)
    assert not bad['passed']
    assert bad['learning_feedback']


@pytest.mark.parametrize('section_id, wrong', [
    ('D02-input', "print('6')"),
    ('D03-delivery', "print(0 if float(input())>99 else 8)"),
    ('D04-shipping', "def shipping(amount): print(0)"),
    ('D05-cart', "def cart_total(items): return sum(i['price'] for i in items)"),
    ('D06-parse', "def parse_quantity(text):\n    try: return int(text) or None\n    except ValueError: return None"),
    ('D06-average', "def average(values): return sum(values)/len(values)"),
    ('D07-slug', SOLUTIONS['D07-slug'] + "\nprint('导入时打印')"),
    ('D09-square-cli', SOLUTIONS['D09-square-cli'].replace('n*n', 'n*2')),
])
def test_drills_reject_plausible_but_incorrect_behavior(section_id, wrong, tmp_path):
    curriculum = load_curriculum(Path('data/curriculum.json'))
    assert not run_validation(curriculum, section_id[:3], section_id, wrong, tmp_path)['passed']


def test_drills_cover_eight_tasks_without_gating_existing_progress(curriculum_data):
    from learnctl.workflow import required_sections

    drills = [section for task in curriculum_data['tasks'] for section in task['lesson'] if section['title'].startswith('加练')]
    assert {s['id'] for s in drills} == set(SOLUTIONS)
    assert {s['id'][:3] for s in drills} == {f'D{i:02d}' for i in range(2, 10)}
    for task in curriculum_data['tasks']:
        required = required_sections(task)
        for section in task['lesson']:
            if section['id'] in SOLUTIONS:
                assert section['optional'] and section['id'] not in required


def test_first_tasks_do_not_require_functions_or_exceptions(curriculum_data):
    for task in curriculum_data['tasks'][1:3]:
        for section in task['lesson']:
            if section.get('optional'):
                continue
            starter = section['practice']['starter_content']
            assert 'def ' not in starter and 'raise ' not in starter
            assert '定义 ' not in section['practice']['instructions']


def test_feedback_reports_actual_values_and_explains_type_error(tmp_path):
    curriculum = load_curriculum(Path('data/curriculum.json'))
    result = run_validation(curriculum, 'D04', 'D04-shipping', 'def shipping(amount): return 123', tmp_path)
    assert any('期望：0；实际：123' in check['detail'] for check in result['checks'])
    result = run_validation(curriculum, 'D02', 'D02-input', "print(input() + 2)", tmp_path)
    assert 'TypeError' in result['stderr']
    assert 'input() 返回字符串' in result['learning_feedback']


def test_all_new_cases_are_private(curriculum_data):
    from learnctl.progress import initial_progress
    from learnctl.workflow import task_payload
    import json

    curriculum = load_curriculum(Path('data/curriculum.json'))
    state = initial_progress(curriculum)
    payload = task_payload(curriculum, state, curriculum['_index']['tasks']['D05'])
    text = json.dumps(payload, ensure_ascii=False)
    assert 'M.cart_total(' not in text
    assert 'FUNCTION_CASES' not in text
    assert set(SOLUTIONS) <= set(SCRIPT_CASES) | set(FUNCTION_CASES) | set(CLI_CASES)

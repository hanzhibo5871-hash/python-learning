"""Behavioral and contract regressions for audited just-in-time teaching."""
import ast
import json
from pathlib import Path

import pytest

from learnctl.experiments import run_experiment
from learnctl.practice import validate_code

DATA = json.loads((Path(__file__).resolve().parents[1] / 'data/curriculum.json').read_text(encoding='utf-8'))
SECTIONS = {s['id']: s for t in DATA['tasks'] for s in t['lesson']}
D05 = [s for s in SECTIONS.values() if s['id'].startswith('D05-')]
CARDS = [(s, i) for s in D05 for i, _ in enumerate(s['practice_first']['cards'])]
DRILLS = [(s, i, d) for s in D05 for i, d in enumerate(s['practice_first']['drills'])]


@pytest.mark.parametrize('section,index', CARDS, ids=[f"{s['id']}-card-{i}" for s, i in CARDS])
def test_d05_teaching_examples_have_real_outputs(section, index):
    result = run_experiment(section, {'mode': 'card', 'index': index})
    assert result['passed'], result
    assert not result['completed']


@pytest.mark.parametrize('section,index,drill', DRILLS, ids=[f"{s['id']}-{d['id']}" for s, i, d in DRILLS])
def test_d05_progressive_exercises_require_actual_edits(section, index, drill):
    assert run_experiment(section, {'mode': 'drill', 'index': index, 'content': drill['reference']})['passed']
    assert not run_experiment(section, {'mode': 'drill', 'index': index})['passed']


def test_d05_contract_explains_length_and_value_rejection_without_solution():
    section = SECTIONS['D05-list-tuple']
    cards = section['practice_first']['cards']
    assert [c['title'] for c in cards] == ['len：取得元素个数', '长度也是数字：比较后再分支', 'raise ValueError：明确拒绝不合要求的值', 'tuple：从已有序列创建元组']
    assert all('作用：' in c['rule'] and '常用：' in c['rule'] for c in cards)
    for source in [c['code'] for c in cards] + [d['starter'] for d in section['practice_first']['drills']]:
        tree = ast.parse(source)
        assert not any(isinstance(n, ast.FunctionDef) and n.name == 'normalize_pair' for n in ast.walk(tree))
    tree = ast.parse(section['practice']['starter_content'])
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    assert function.name == 'normalize_pair' and isinstance(function.body[0], ast.Pass)
    assert '不要求额外类型校验' in section['practice']['instructions']


@pytest.mark.parametrize('wrong', [
    'def normalize_pair(values): return tuple(values)',
    "def normalize_pair(values):\n    if len(values) != 2: return None\n    return tuple(values)",
    "def normalize_pair(values):\n    if len(values) != 2: raise TypeError('length')\n    return tuple(values)",
])
def test_length_rejection_is_objective_and_required(wrong, tmp_path):
    assert not validate_code(SECTIONS['D05-list-tuple'], wrong, tmp_path)['passed']


def test_d05_documented_function_and_unpacked_edges_pass_real_validation(tmp_path):
    correct = "def normalize_pair(values):\n    if len(values) != 2: raise ValueError('length')\n    return tuple(values)\n"
    assert validate_code(SECTIONS['D05-list-tuple'], correct, tmp_path)['passed']
    unpacking = SECTIONS['D05-unpacking']
    starter = ast.parse(unpacking['practice']['starter_content'])
    assert {n.name for n in starter.body if isinstance(n, ast.FunctionDef)} == {'merge_task', 'split_edges'}
    assert unpacking['practice']['input_identifiers'] == ['merge_task', 'split_edges']
    assert 'ValueError' in unpacking['practice']['expected_behavior']
    assert '(5, [], 6)' in unpacking['practice']['expected_behavior']

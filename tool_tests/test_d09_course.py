"""D09 sequence, real execution, deliberate wrong answers and progress safety."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from learnctl.curriculum import validate_curriculum
from learnctl.experiments import run_experiment
from learnctl.practice import validate_code
from scripts.d09_course import (ADJUST_OPTIONS, ADJUST_STOCK, COMMAND_OPTIONS,
                               RUN_STOCK, PARSE_ARGS, BUILD_PARSER, PARSE_ERROR,
                               ENTRY, apply_d09)
ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/curriculum.json').read_text(encoding='utf-8'))
TASK = next(t for t in DATA['tasks'] if t['id'] == 'D09')
SECTIONS = {s['id']: s for s in TASK['lesson']}
ORDER = ['D09-argv','D09-position','D09-options','D09-stock','D09-parser',
         'D09-command-name','D09-if-dispatch','D09-function-value',
         'D09-subcommands','D09-errors','D09-entry']
SOLUTIONS = {
    'D09-argv': 'def input_parts(argv): return tuple(argv)\n',
    'D09-position': 'import argparse\ndef product_options(argv):\n    parser=argparse.ArgumentParser()\n    parser.add_argument("product")\n    return parser.parse_args(argv)\n',
    'D09-options': ADJUST_OPTIONS, 'D09-stock': ADJUST_STOCK,
    'D09-parser': PARSE_ARGS, 'D09-command-name': COMMAND_OPTIONS,
    'D09-if-dispatch': RUN_STOCK,
    'D09-function-value': 'def call_action(action, value): return action(value)\n',
    'D09-subcommands': BUILD_PARSER, 'D09-errors': PARSE_ERROR, 'D09-entry': ENTRY,
}


def test_d09_order_old_ids_optional_exercises_and_prerequisites():
    assert [s['id'] for s in TASK['lesson'] if not s.get('optional')] == ORDER
    assert {s['id'] for s in TASK['lesson'] if s.get('optional')} == {
        'D09-greet-cli','D09-repeat-cli','D09-square-cli'}
    validate_curriculum(copy.deepcopy(DATA))
    for sid in ORDER:
        assert len(SECTIONS[sid]['practice_first']['drills']) == 2
        assert len(SECTIONS[sid]['practice_first']['intro']) == 3
    assert 'D09-function-value' in SECTIONS['D09-subcommands']['practice_first']['prerequisites']
    assert 'D09-command-name' in SECTIONS['D09-if-dispatch']['practice_first']['prerequisites']


def test_d09_overlay_is_idempotent_and_does_not_touch_other_tasks():
    value = copy.deepcopy(DATA)
    apply_d09(value)
    apply_d09(value)
    assert value == DATA
    assert value['curriculum_version'] == '3.0.0' and value['schema_version'] == 3


@pytest.mark.parametrize('sid', ORDER)
def test_d09_formal_reference_solutions(sid, tmp_path):
    result = validate_code(SECTIONS[sid], SOLUTIONS[sid], tmp_path)
    assert result['passed'], (sid, result)
    assert result['cases'] and all(c['passed'] for c in result['cases'])


@pytest.mark.parametrize('sid', ORDER)
def test_d09_unedited_formal_starters_cannot_pass(sid, tmp_path):
    assert not validate_code(SECTIONS[sid], SECTIONS[sid]['practice']['starter_content'], tmp_path)['passed'], sid


@pytest.mark.parametrize('sid,index', [(sid,i) for sid in ORDER for i,e in enumerate(SECTIONS[sid]['examples']) if e['runnable']])
def test_d09_visible_examples_have_matching_outputs(sid, index):
    result = run_experiment(SECTIONS[sid], {'mode':'example','index':index})
    assert result['passed'], (sid, index, result)


@pytest.mark.parametrize('sid,index', [(sid,i) for sid in ORDER for i in range(2)])
def test_d09_drills_require_edits(sid, index):
    item = SECTIONS[sid]['practice_first']['drills'][index]
    assert not run_experiment(SECTIONS[sid], {'mode':'drill','index':index})['passed']
    result = run_experiment(SECTIONS[sid], {'mode':'drill','index':index,'content':item['reference']})
    assert result['passed'], (sid, index, result)


@pytest.mark.parametrize('sid,source', [
    ('D09-argv', 'def input_parts(argv): return argv[0],argv[1],int(argv[2])'),
    ('D09-position', SOLUTIONS['D09-position'].replace('return parser.parse_args(argv)', 'return {"product":"原料"}')),
    ('D09-options', ADJUST_OPTIONS.replace('type=int','type=str')),
    ('D09-stock', ADJUST_STOCK.replace('STOCK[args.product] += args.delta','STOCK[args.product] = args.delta')),
    ('D09-stock', ADJUST_STOCK.replace('    return STOCK[args.product]','    print(STOCK[args.product])')),
    ('D09-stock', ADJUST_STOCK.replace('    STOCK[args.product] += args.delta','    if STOCK[args.product] + args.delta < 0: raise ValueError("余额不足")\n    STOCK[args.product] += args.delta')),
    ('D09-parser', PARSE_ARGS.replace('default=10','default=20')),
    ('D09-command-name', COMMAND_OPTIONS.replace('dest="command"','dest="action"')),
    ('D09-if-dispatch', RUN_STOCK.replace('    if args.command == "show":','    product = args.product\n    if args.command == "show":')),
    ('D09-function-value', 'def call_action(action,value): action(value)'),
    ('D09-subcommands', BUILD_PARSER.replace('func=handle_list)','func="handle_list")')),
    ('D09-subcommands', BUILD_PARSER.replace('func=handle_list)','func=handle_list(None))')),
    ('D09-errors', PARSE_ERROR.replace('    return parser.parse_args(argv)','    try: return parser.parse_args(argv)\n    except SystemExit: return 0')),
    ('D09-entry', ENTRY.replace('args = adjustment_options(argv)','args = adjustment_options(argv or [])')),
    ('D09-entry', ENTRY.replace('raise SystemExit(main())','raise SystemExit(main(["原料","--delta","-3"]))')),
    ('D09-entry', ENTRY.replace('if __name__ == "__main__":\n    raise SystemExit(main())','raise SystemExit(main())')),
])
def test_d09_common_wrong_answers_fail_behaviorally(sid, source, tmp_path):
    assert not validate_code(SECTIONS[sid], source, tmp_path)['passed'], sid


def test_d09_public_payload_omits_hidden_answers(web_server):
    from conftest import request
    status, payload, _ = request(web_server, 'GET', '/api/tasks/D09')
    assert status == 200
    sections = payload['task']['lesson']['sections']
    assert [s['id'] for s in sections if not s.get('optional')] == ORDER
    for section in sections:
        assert all('reference' not in item for item in section['practice_first']['drills'])


def test_old_d09_completion_and_draft_survive_without_completing_new_steps(tmp_path):
    from learnctl.progress import initial_progress, load_progress, save_progress
    old = copy.deepcopy(DATA)
    historical = {'D09-parser','D09-subcommands','D09-errors','D09-entry',
                  'D09-greet-cli','D09-repeat-cli','D09-square-cli'}
    task = next(t for t in old['tasks'] if t['id'] == 'D09')
    task['lesson'] = [s for s in task['lesson'] if s['id'] in historical]
    state = initial_progress(old)
    state['lesson_progress']['D09']['current_section'] = 'D09-subcommands'
    state['lesson_progress']['D09']['completed_sections'] = ['D09-parser']
    path = tmp_path / '.learn/progress.json'
    save_progress(path, state)
    draft = tmp_path / '.learn/lesson-submissions/D09-subcommands.py'
    draft.parent.mkdir(parents=True)
    draft.write_text('# 我的旧草稿\n', encoding='utf-8')
    before_progress, before_draft = path.read_bytes(), draft.read_bytes()
    loaded = load_progress(path, DATA)
    assert loaded['lesson_progress']['D09']['current_section'] == 'D09-subcommands'
    assert loaded['lesson_progress']['D09']['completed_sections'] == ['D09-parser']
    assert path.read_bytes() == before_progress
    assert draft.read_bytes() == before_draft

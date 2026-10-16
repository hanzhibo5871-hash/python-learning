"""Mock transport verifies the scope supplied to dynamic variations."""
import json
from pathlib import Path

from learnctl import ai
from learnctl.curriculum import load_curriculum


def test_variation_receives_current_teaching_and_only_earlier_required_lessons(monkeypatch):
    curriculum = load_curriculum(Path(__file__).resolve().parents[1] / 'data/curriculum.json')
    task = curriculum['_index']['tasks']['D05']
    section = task['lesson'][0]
    section['practice_first']['drills'][0]['reference'] = 'PRIVATE_DRILL_ANSWER'
    current_card = section['practice_first']['cards'][0]['rule']
    captured = []
    data = dict(title='练习', scenario='只改输入', instructions='练习已教内容', starter_content='def example(values):\n    pass', review_rubric='只观察已教知识')
    def provider(url, payload, api_key, timeout=60):
        captured.append(payload['messages'][0]['content'])
        return 200, json.dumps({'choices': [{'message': {'content': json.dumps(data)}}]}).encode()
    monkeypatch.setattr(ai, '_request', provider)
    session = ai.AiSession()
    session.set_key('test-only')
    assert ai.generate(session, curriculum, 'D05', section['id'], False) == data
    prompt = captured[0]
    assert current_card in prompt
    assert 'D04-def-return' in prompt and 'D03-if' in prompt
    assert 'D03-match' not in prompt and 'D06-try-except' not in prompt
    assert 'PRIVATE_DRILL_ANSWER' not in prompt
    assert '不得要求未来课程' in prompt and '不得包含完整实现' in prompt
    assert '尚未生成的文件' in prompt and '真实密钥' in prompt


def test_project_variation_contains_exact_declared_file_boundaries():
    curriculum = load_curriculum(Path(__file__).resolve().parents[1] / 'data/curriculum.json')
    task = curriculum['_index']['tasks']['D21']
    section = next(s for s in task['lesson'] if s['id'] == 'D21-static')
    prompt = ai.build_generate_prompt(task, section, [], False, prior_teaching=ai._prior_teaching(curriculum, section))
    assert section['practice']['project_file'] in prompt
    assert all(path in prompt for path in section['practice']['workspace_deps'])
    assert 'D23-html-fetch' not in prompt


def test_unintroduced_imports_and_calls_are_rejected_after_generation():
    import pytest
    curriculum = load_curriculum(Path(__file__).resolve().parents[1] / 'data/curriculum.json')
    section = curriculum['_index']['tasks']['D05']['lesson'][0]
    for source in ('import asyncio', 'values = unknown_api()', 'import requests\nrequests.get("https://example.test")'):
        with pytest.raises(ai.AiError, match='尚未教过'):
            ai._check_variation_starter(curriculum, section, {'starter_content': source})
    for source in ('def another(values):\n    pass', 'count = len([1, 2, 3])', 'def helper():\n    return 1\nvalue = helper()'):
        ai._check_variation_starter(curriculum, section, {'starter_content': source})

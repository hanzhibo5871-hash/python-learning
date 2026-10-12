"""Offline self-checks for private D25-D28 integration drafts; no learner data."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import types

from learnctl import ai_practice_fixtures as fix, ai_exercise_checks as validators
BASE = Path(__file__).resolve().parents[1]

# Private behavioral reference for the tool's regression suite only. Do not put
# this in curriculum/public prompts; public cards use unrelated StringIO/KeyError.
D28_REFERENCE_TESTS = '''import pytest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from ai_client import call_chat, ApiError

def response(body):
    fake = MagicMock()
    fake.__enter__.return_value = fake
    fake.status = 200
    fake.read.return_value = body
    return fake

def test_call_chat_ok():
    fake = response(b'{"choices":[{"message":{"content":"demo-content"}}]}')
    with patch("deepseek_client.urllib.request.urlopen", return_value=fake):
        assert call_chat("demo", [], base_url="https://example.invalid") == "demo-content"

def test_call_chat_401():
    error = HTTPError("https://example.invalid", 401, "bad key", {}, None)
    with patch("deepseek_client.urllib.request.urlopen", side_effect=error):
        with pytest.raises(ApiError) as caught:
            call_chat("demo", [], base_url="https://example.invalid")
    assert caught.value.status_code == 401

def test_call_chat_bad_json():
    with patch("deepseek_client.urllib.request.urlopen", return_value=response(b"not json")):
        with pytest.raises(ApiError) as caught:
            call_chat("demo", [], base_url="https://example.invalid")
    assert caught.value.status_code is None
'''
D28_VACUOUS = '''def test_call_chat_ok(): pass
def test_call_chat_401(): pass
def test_call_chat_bad_json(): pass
'''


def test_offline_behavior():
    assert len(fix.ai_reference_fixtures()) == 3
    reference = validators.grade_d28_tests(D28_REFERENCE_TESTS)
    assert reference["passed"], reference["checks"]
    vacuous = validators.grade_d28_tests(D28_VACUOUS)
    assert not vacuous["passed"], vacuous
    assert [x["passed"] for x in vacuous["checks"]] == [True, False, False, False]
    missing_patch = validators.grade_d28_tests('from ai_client import call_chat\ndef test_without_patch():\n    assert call_chat("demo", [], base_url="https://example.invalid") == "demo-content"\n')
    assert not missing_patch["passed"]
    assert not missing_patch["checks"][0]["passed"]
    assert "离线测试不能访问网络" in missing_patch["stdout"]

    parser = types.ModuleType("parser")
    exec(fix.PROMPT_SOURCE, parser.__dict__)
    parse_checks = validators.d26_parse_checks(parser)
    assert len(parse_checks) == 9 and all(x["passed"] for x in parse_checks), parse_checks
    wrong_parser = types.SimpleNamespace(parse_ai_json=lambda text: {"b": 2})
    assert not all(x["passed"] for x in validators.d26_parse_checks(wrong_parser))

    from learnctl.practice import PracticeContext, _DeepSeekMockHandler, _run_with_server
    harness = validators.d27_client_harness()
    for label, source, expected in [
        ("correct", fix.COMPOSITION_SOURCE, [True, True, True]),
        ("wrong-exception", fix.COMPOSITION_SOURCE.replace('messages = [{"role": "user", "content": prompt}]', 'if prompt == "NONJSON":\n        raise NameError("模拟实现错误")\n    messages = [{"role": "user", "content": prompt}]'), [True, False, True]),
    ]:
        with PracticeContext(BASE) as context:
            for relative, code in fix.ai_reference_fixtures():
                context.write(relative, code)
            context.write("main.py", source)
            result = _run_with_server(_DeepSeekMockHandler, harness, context)
            assert [x["passed"] for x in result["checks"]] == expected, (label, result)

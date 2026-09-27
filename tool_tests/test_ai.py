from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from urllib.error import HTTPError

from learnctl import ai
from learnctl.ai import (
    BASE_URL,
    CHAT_PATH,
    MODEL,
    STRUCTURED_TEMPERATURE,
    AiError,
    AiSession,
    build_tutor_messages,
    build_generate_prompt,
    build_review_prompt,
    build_variation_review_prompt,
    chat,
    generate,
    parse_ai_json,
    review,
    review_variation,
    tutor_chat,
)
from learnctl.curriculum import load_curriculum


def _curriculum() -> dict:
    return load_curriculum(Path("data/curriculum.json"))


def _session() -> AiSession:
    session = AiSession()
    session.set_key("sk-test")
    return session


def _ok_response(content: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")


def test_chat_uses_official_endpoint_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_request(url, payload, api_key, timeout=60):
        captured["url"] = url
        captured["payload"] = payload
        captured["api_key"] = api_key
        return 200, _ok_response("你好")

    monkeypatch.setattr(ai, "_request", fake_request)
    content = chat(_session(), [{"role": "user", "content": "hi"}])
    assert content == "你好"
    assert captured["url"] == f"{BASE_URL}{CHAT_PATH}"
    assert captured["payload"]["model"] == MODEL
    assert captured["payload"]["stream"] is False
    assert captured["api_key"] == "sk-test"


def test_chat_json_output_parameterizes_response_format(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_request(url, payload, api_key, timeout=60):
        captured["payload"] = payload
        return 200, _ok_response("x")

    monkeypatch.setattr(ai, "_request", fake_request)
    chat(_session(), [{"role": "user", "content": "hi"}], json_output=True)
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    chat(_session(), [{"role": "user", "content": "hi"}])
    assert "response_format" not in captured["payload"]


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (401, b'{"error":"unauthorized"}', "HTTP 401"),
        (429, b'{"error":"rate"}', "HTTP 429"),
        (500, b"boom", "HTTP 500"),
    ],
)
def test_chat_reports_http_errors_without_fallback(monkeypatch: pytest.MonkeyPatch, status: int, body: bytes, expected: str) -> None:
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (status, body))
    with pytest.raises(AiError, match=expected):
        chat(_session(), [{"role": "user", "content": "hi"}])


def test_chat_missing_key_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    session = AiSession()
    with pytest.raises(AiError, match="未配置"):
        chat(session, [{"role": "user", "content": "hi"}])


def test_chat_non_json_and_missing_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, b"not json"))
    with pytest.raises(AiError, match="不是合法 JSON"):
        chat(_session(), [{"role": "user", "content": "hi"}])
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, b'{"choices": []}'))
    with pytest.raises(AiError, match="缺少 content"):
        chat(_session(), [{"role": "user", "content": "hi"}])


def test_request_rejects_oversized_response_at_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """成功响应：_request 最多读取 MAX+1 字节，超出立即 AiError。"""

    class FakeResponse:
        def __init__(self, body: bytes, status: int = 200) -> None:
            self._body = body
            self.status = status

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self, n: int = -1) -> bytes:
            return self._body[:n] if n and n >= 0 else self._body

    big = b"x" * (ai.MAX_RESPONSE_BYTES + 100)
    monkeypatch.setattr(ai.urllib.request, "urlopen", lambda req, timeout=None: FakeResponse(big))
    with pytest.raises(AiError, match="超长"):
        ai._request("http://x", {"messages": []}, "k")


def test_request_rejects_oversized_http_error_at_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 错误响应：同样在读取阶段就拒绝超长，不先读入内存。"""

    def raise_err(req, timeout=None):
        big = b"y" * (ai.MAX_RESPONSE_BYTES + 100)
        raise HTTPError("http://x", 500, "Internal", {}, io.BytesIO(big))

    monkeypatch.setattr(ai.urllib.request, "urlopen", raise_err)
    with pytest.raises(AiError, match="超长"):
        ai._request("http://x", {"messages": []}, "k")


def test_session_key_never_leaks_or_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    session = AiSession()
    assert session.configured() is False
    session.set_key("sk-secret-123")
    assert session.configured() is True
    assert session.get_key() == "sk-secret-123"
    # 只在内存持有，不写盘（无文件产出）
    assert session._key == "sk-secret-123"


def test_parse_ai_json_requires_single_object_and_strips_fence() -> None:
    assert parse_ai_json('{"a": 1}') == {"a": 1}
    assert parse_ai_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(AiError, match="单个 JSON 对象"):
        parse_ai_json("没有")
    with pytest.raises(AiError, match="单个 JSON 对象"):
        parse_ai_json("[1, 2]")
    with pytest.raises(AiError, match="单个 JSON 对象"):
        parse_ai_json("前缀 {\"a\": 1} 后缀")
    with pytest.raises(AiError, match="解析失败"):
        parse_ai_json('{"a": 1} {"b": 2}')
    with pytest.raises(AiError, match="必须是字符串"):
        parse_ai_json(None)  # type: ignore[arg-type]


def test_generate_prompt_includes_practice_and_index(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    task = curriculum["_index"]["tasks"]["D02"]
    section = next(s for s in task["lesson"] if s["id"] == "D02-names")
    catalog = curriculum["_index"]["source_catalog"]
    titles = [f"{ref}：{catalog[ref]['title']}" for ref in section["catalog_refs"]]
    prompt = build_generate_prompt(task, section, titles, completed=False)
    assert "Python-10：Python-10-变量的基础应用" in prompt or "py-10：Python-10-变量的基础应用" in prompt
    assert "索引仅代表标题知识范围" in prompt
    assert "未完成" in prompt
    for marker in ("实践类型", "场景", "要求", "预期行为"):
        assert marker in prompt


def test_ai_prompts_define_review_fields_as_json_arrays(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    task = curriculum["_index"]["tasks"]["D02"]
    section = next(s for s in task["lesson"] if s["id"] == "D02-names")
    review_prompt = build_review_prompt(task, section, [], content="c", validation_summary="s")
    for field in ("strengths", "issues", "next_steps"):
        assert field in review_prompt
    assert "JSON 数组" in review_prompt


def test_tutor_chat_uses_current_section_context_and_recent_history(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    captured: dict = {}

    def fake_request(url, payload, api_key, timeout=60):
        captured["payload"] = payload
        return 200, _ok_response("缩进决定代码块；先看冒号后的四个空格。")

    monkeypatch.setattr(ai, "_request", fake_request)
    history = [
        {"role": "user", "content": f"旧问题 {index}"}
        if index % 2 == 0
        else {"role": "assistant", "content": f"旧回答 {index}"}
        for index in range(10)
    ]
    answer = tutor_chat(
        _session(),
        curriculum,
        "D02",
        "D02-execution",
        "为什么 Python 不能像 JS 一样用大括号？",
        history,
    )

    assert "缩进决定代码块" in answer
    messages = captured["payload"]["messages"]
    assert messages[0]["role"] == "system"
    assert "D02-execution" in messages[0]["content"]
    assert "程序如何执行：语句、缩进块与注释" in messages[0]["content"]
    assert "本节目标" in messages[0]["content"]
    assert "实践要求" in messages[0]["content"]
    assert "索引仅代表知识范围标题" in messages[0]["content"]
    assert "不得建议删除" in messages[0]["content"]
    assert "纯文本" in messages[0]["content"]
    assert "当前步骤尚未创建" in messages[0]["content"]
    assert messages[1]["content"] == "旧问题 2"
    assert len(messages[1:-1]) == 8
    assert messages[-1] == {"role": "user", "content": "为什么 Python 不能像 JS 一样用大括号？"}
    assert captured["payload"]["temperature"] == 0.7


def test_tutor_chat_rejects_empty_model_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response("   ")))
    with pytest.raises(AiError, match="回答为空"):
        tutor_chat(_session(), curriculum, "D02", "D02-execution", "请解释缩进", [])


def test_tutor_chat_normalizes_unsupported_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    monkeypatch.setattr(
        ai,
        "_request",
        lambda *a, **k: (200, _ok_response("**直接回答**\n```powershell\npython --version\n```")),
    )
    answer = tutor_chat(_session(), curriculum, "D02", "D02-execution", "请解释", [])
    assert answer == "直接回答\npython --version"
    assert "**" not in answer
    assert "```" not in answer


def test_tutor_chat_rejects_answer_empty_after_markdown_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response("```python\n```")))

    with pytest.raises(AiError, match="回答为空"):
        tutor_chat(_session(), curriculum, "D02", "D02-execution", "请解释", [])


def test_tutor_chat_rejects_answer_too_long_for_follow_up_history(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response("答" * 4001)))

    with pytest.raises(AiError, match="回答超过上限 4000 字符"):
        tutor_chat(_session(), curriculum, "D02", "D02-execution", "请解释", [])


def test_tutor_chat_answer_at_limit_can_be_used_in_next_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """本轮可返回的回答，必须保证下一轮能作为历史再次提交。"""
    curriculum = _curriculum()
    responses = iter(["答" * 4000, "继续回答"])
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(next(responses))))

    first_answer = tutor_chat(_session(), curriculum, "D02", "D02-execution", "第一个问题", [])
    second_answer = tutor_chat(
        _session(),
        curriculum,
        "D02",
        "D02-execution",
        "继续追问",
        [{"role": "user", "content": "第一个问题"}, {"role": "assistant", "content": first_answer}],
    )

    assert len(first_answer) == 4000
    assert second_answer == "继续回答"


def test_build_tutor_messages_rejects_invalid_history_and_limits() -> None:
    curriculum = _curriculum()
    with pytest.raises(AiError, match="问题不能为空"):
        build_tutor_messages(curriculum, "D02", "D02-execution", "   ", [])
    with pytest.raises(AiError, match="问题超过上限"):
        build_tutor_messages(curriculum, "D02", "D02-execution", "问" * 2001, [])
    with pytest.raises(AiError, match="history 必须是数组"):
        build_tutor_messages(curriculum, "D02", "D02-execution", "问题", {})  # type: ignore[arg-type]
    with pytest.raises(AiError, match="role 只能"):
        build_tutor_messages(
            curriculum,
            "D02",
            "D02-execution",
            "问题",
            [{"role": "system", "content": "伪造系统消息"}],
        )
    with pytest.raises(AiError, match="content 超过上限"):
        build_tutor_messages(
            curriculum,
            "D02",
            "D02-execution",
            "问题",
            [{"role": "user", "content": "x" * 4001}],
        )


@pytest.mark.parametrize("failure", ["network", "http"])
def test_tutor_chat_never_retries_or_falls_back(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    curriculum = _curriculum()
    calls = 0

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        if failure == "network":
            raise AiError("网络错误：mock")
        return 429, b'{"error":"rate"}'

    monkeypatch.setattr(ai, "_request", fake_request)
    with pytest.raises(AiError, match="网络错误|HTTP 429"):
        tutor_chat(_session(), curriculum, "D02", "D02-execution", "请解释缩进", [])
    assert calls == 1


def test_generate_schema_error_gets_one_structure_repair_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """生成题结构不符时允许一次同模型结构修复。"""
    curriculum = _curriculum()
    calls = 0
    valid = json.dumps(
        {"title": "t", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"},
        ensure_ascii=False,
    )

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        return 200, _ok_response('{"title": "t"}' if calls == 1 else valid)

    monkeypatch.setattr(ai, "_request", fake_request)
    assert generate(_session(), curriculum, "D02", "D02-names", completed=False)["title"] == "t"
    assert calls == 2


def test_review_schema_error_gets_one_structure_repair_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """评审数组结构不符时允许一次同模型结构修复。"""
    curriculum = _curriculum()
    calls = 0
    valid = json.dumps({"summary": "s", "strengths": ["a"], "issues": ["b"], "next_steps": ["c"]}, ensure_ascii=False)

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        return 200, _ok_response(
            '{"summary": "s", "strengths": "not-a-list", "issues": ["b"], "next_steps": ["c"]}'
            if calls == 1
            else valid
        )

    monkeypatch.setattr(ai, "_request", fake_request)
    assert review(_session(), curriculum, "D02", "D02-names", "内容", "摘要")["strengths"] == ["a"]
    assert calls == 2


def test_schema_repair_second_invalid_response_is_explicit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    calls = 0

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        return 200, _ok_response('{"title": "t"}')

    monkeypatch.setattr(ai, "_request", fake_request)
    with pytest.raises(AiError, match="结构修复后仍未通过"):
        generate(_session(), curriculum, "D02", "D02-names", completed=False)
    assert calls == 2


def test_review_schema_repair_second_invalid_response_is_explicit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    calls = 0

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        return 200, _ok_response('{"summary": "s", "strengths": "a", "issues": [], "next_steps": []}')

    monkeypatch.setattr(ai, "_request", fake_request)
    with pytest.raises(AiError, match="结构修复后仍未通过"):
        review(_session(), curriculum, "D02", "D02-names", "内容", "摘要")
    assert calls == 2


@pytest.mark.parametrize("operation", ["generate", "review"])
@pytest.mark.parametrize("failure", ["network", "http"])
def test_structured_requests_never_retry_request_failures(
    monkeypatch: pytest.MonkeyPatch, operation: str, failure: str
) -> None:
    curriculum = _curriculum()
    calls = 0

    def fake_request(url, payload, api_key, timeout=60):
        nonlocal calls
        calls += 1
        if failure == "network":
            raise ai.AiError("网络错误：mock")
        return 429, b'{"error":"rate"}'

    monkeypatch.setattr(ai, "_request", fake_request)
    with pytest.raises(AiError, match="网络错误|HTTP 429"):
        if operation == "generate":
            generate(_session(), curriculum, "D02", "D02-names", completed=False)
        else:
            review(_session(), curriculum, "D02", "D02-names", "内容", "摘要")
    assert calls == 1


def test_generate_requires_strict_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    valid = json.dumps({"title": "t", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}, ensure_ascii=False)

    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(valid)))
    data = generate(_session(), curriculum, "D02", "D02-names", completed=False)
    assert set(data) == {"title", "scenario", "instructions", "starter_content", "review_rubric"}

    # 缺键
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response('{"only": 1}')))
    with pytest.raises(AiError, match="缺少必要字段"):
        generate(_session(), curriculum, "D02", "D02-names", completed=False)

    # 多余字段
    extra = json.dumps({"title": "t", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r", "evil": "x"}, ensure_ascii=False)
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(extra)))
    with pytest.raises(AiError, match="未约定字段"):
        generate(_session(), curriculum, "D02", "D02-names", completed=False)

    # 空值 / 非字符串 / 超长标题
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response('{"title": "", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}')))
    with pytest.raises(AiError, match="非空字符串"):
        generate(_session(), curriculum, "D02", "D02-names", completed=False)
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response('{"title": ["x"], "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}')))
    with pytest.raises(AiError, match="非空字符串"):
        generate(_session(), curriculum, "D02", "D02-names", completed=False)
    long_title = json.dumps({"title": "x" * 201, "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}, ensure_ascii=False)
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(long_title)))
    with pytest.raises(AiError, match="超过上限"):
        generate(_session(), curriculum, "D02", "D02-names", completed=False)


def test_review_sends_only_visible_content_and_recent_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    captured: dict = {}

    def fake_request(url, payload, api_key, timeout=60):
        captured["payload"] = payload
        review_json = json.dumps({"summary": "s", "strengths": ["a"], "issues": ["b"], "next_steps": ["c"]}, ensure_ascii=False)
        return 200, _ok_response(review_json)

    monkeypatch.setattr(ai, "_request", fake_request)
    result = review(_session(), curriculum, "D02", "D02-names", content="我的练习代码", validation_summary="passed=True")
    assert set(result) == {"summary", "strengths", "issues", "next_steps"}
    prompt = captured["payload"]["messages"][0]["content"]
    assert "我的练习代码" in prompt
    assert "passed=True" in prompt
    assert "练习要求" in prompt
    for secret in ("DEEPSEEK_API_KEY", "Authorization", "sk-test"):
        assert secret not in prompt


def test_review_prompt_truncates_content_and_summary(curriculum_data: dict) -> None:
    curriculum = _curriculum()
    task = curriculum["_index"]["tasks"]["D02"]
    section = next(s for s in task["lesson"] if s["id"] == "D02-names")
    prompt = build_review_prompt(task, section, [], content="x" * 6000, validation_summary="y" * 3000)
    assert "x" * 4000 in prompt
    assert "x" * 4001 not in prompt
    assert "y" * 2000 in prompt
    assert "y" * 2001 not in prompt


def test_review_validates_lists_and_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    base = {"summary": "s", "strengths": ["a"], "issues": ["b"], "next_steps": ["c"]}
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(json.dumps(base, ensure_ascii=False))))
    assert set(review(_session(), curriculum, "D02", "D02-names", "c", "s")) == {"summary", "strengths", "issues", "next_steps"}

    bad = dict(base, strengths="not-a-list")
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(json.dumps(bad, ensure_ascii=False))))
    with pytest.raises(AiError, match="必须是字符串数组"):
        review(_session(), curriculum, "D02", "D02-names", "c", "s")

    bad = dict(base, summary="")
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(json.dumps(bad, ensure_ascii=False))))
    with pytest.raises(AiError, match="summary 必须是非空字符串"):
        review(_session(), curriculum, "D02", "D02-names", "c", "s")

    too_many = dict(base, next_steps=["x"] * 21)
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response(json.dumps(too_many, ensure_ascii=False))))
    with pytest.raises(AiError, match="项数超过上限"):
        review(_session(), curriculum, "D02", "D02-names", "c", "s")


def test_review_missing_keys_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, _ok_response('{"only": 1}')))
    with pytest.raises(AiError, match="缺少必要字段"):
        review(_session(), curriculum, "D02", "D02-names", "内容", "摘要")


def test_generate_and_review_use_low_structured_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    captured: list[dict] = []

    def fake_request(url, payload, api_key, timeout=60):
        captured.append(payload)
        content = json.dumps({"title": "t", "scenario": "s", "instructions": "i", "starter_content": "c", "review_rubric": "r"}, ensure_ascii=False)
        return 200, _ok_response(content)

    monkeypatch.setattr(ai, "_request", fake_request)
    generate(_session(), curriculum, "D02", "D02-names", completed=False)
    assert captured[-1]["temperature"] == STRUCTURED_TEMPERATURE
    assert STRUCTURED_TEMPERATURE == 0.2

    review_json = json.dumps({"summary": "s", "strengths": [], "issues": [], "next_steps": []}, ensure_ascii=False)

    def fake_review_request(url, payload, api_key, timeout=60):
        captured.append(payload)
        return 200, _ok_response(review_json)

    monkeypatch.setattr(ai, "_request", fake_review_request)
    review(_session(), curriculum, "D02", "D02-names", content="c", validation_summary="s")
    assert captured[-1]["temperature"] == STRUCTURED_TEMPERATURE


def test_generate_and_review_prompts_declare_strict_schema() -> None:
    curriculum = _curriculum()
    task = curriculum["_index"]["tasks"]["D02"]
    section = next(s for s in task["lesson"] if s["id"] == "D02-names")
    gen_prompt = build_generate_prompt(task, section, [], completed=False)
    assert "每个字段必须是非空字符串" in gen_prompt
    assert "禁止 null" in gen_prompt
    rev_prompt = build_review_prompt(task, section, [], content="c", validation_summary="")
    assert "summary 必须是非空字符串" in rev_prompt
    assert "字符串数组" in rev_prompt
    assert "可为空数组" in rev_prompt
    assert "禁止 null" in rev_prompt
    assert "额外字段" in rev_prompt


def test_review_variation_uses_variation_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    curriculum = _curriculum()
    variation = {
        "title": "变式标题",
        "scenario": "变式场景",
        "instructions": "变式要求",
        "starter_content": "变式起始",
        "review_rubric": "变式标准",
    }
    captured: dict = {}
    review_json = json.dumps({"summary": "s", "strengths": ["a"], "issues": [], "next_steps": []}, ensure_ascii=False)

    def fake_request(url, payload, api_key, timeout=60):
        captured["prompt"] = payload["messages"][0]["content"]
        return 200, _ok_response(review_json)

    monkeypatch.setattr(ai, "_request", fake_request)
    result = review_variation(_session(), curriculum, "D02", "D02-names", variation, content="我的提交", validation_summary="")
    assert set(result) == {"summary", "strengths", "issues", "next_steps"}
    prompt = captured["prompt"]
    assert "变式标题" in prompt
    assert "变式场景" in prompt
    assert "变式要求" in prompt
    assert "变式标准" in prompt
    assert "变式练习" in prompt
    # 变式评审不得再按原始固定练习的 clean_name 评审
    assert "clean_name" not in prompt


def test_build_variation_review_prompt_truncates_content() -> None:
    curriculum = _curriculum()
    task = curriculum["_index"]["tasks"]["D02"]
    section = next(s for s in task["lesson"] if s["id"] == "D02-names")
    variation = {
        "title": "变式标题",
        "scenario": "变式场景",
        "instructions": "变式要求",
        "starter_content": "变式起始",
        "review_rubric": "变式标准",
    }
    prompt = build_variation_review_prompt(variation, task, section, [], content="x" * 6000, validation_summary="y" * 3000)
    assert "x" * 4000 in prompt
    assert "x" * 4001 not in prompt
    assert "y" * 2000 in prompt
    assert "y" * 2001 not in prompt

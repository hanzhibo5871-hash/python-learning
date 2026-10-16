"""Private positive/negative regression for D25/D26/D27 protocol oracles."""
import importlib.util
import json
from pathlib import Path
import sys

from learnctl import ai_protocol_checks as oracle, ai_practice_fixtures as fixture
BASE = Path(__file__).resolve().parents[1]

FLOW = '''from prompt import build_prompt
from ai_client import send_message

def review_submission(api_key, submission, rubric, catalog_titles, *, base_url):
    prompt = build_prompt(catalog_titles, "评审用户提交", f"提交：{submission}\\n要求：{rubric}", False)
    result = send_message(api_key, prompt, base_url=base_url)
    required = {"summary", "strengths", "issues", "next_steps"}
    if not isinstance(result, dict) or not required <= result.keys():
        raise ValueError("缺字段")
    return result
'''


def run(validator, code):
    from learnctl.practice import PracticeContext
    with PracticeContext(BASE) as context:
        return validator(code, context, {})


def test_offline_behavior():
    counts = {"positive": 0, "negative": 0}
    details = []
    def check(label, validator, source, expected):
        result = run(validator, source)
        assert result["passed"] is expected, (label, result)
        counts["positive" if expected else "negative"] += 1
        details.append({"name": label, "passed": True, "oracle_result": result["passed"], "case_count":len(result["checks"])})

    check("D25实际本地POST两组输入", oracle.validate_d25_chat, fixture.CLIENT_SOURCE, True)
    mutations = {
        "错误路径": ('f"{base_url}/chat/completions"', 'f"{base_url}/wrong"'),
        "GET代替POST": ('method="POST"', 'method="GET"'),
        "model错误": ('"model": "deepseek-chat"', '"model": "wrong-model"'),
        "丢messages": ('"messages": messages', '"messages": []'),
        "streamTrue": ('"stream": False', '"stream": True'),
        "stream数字0冒充False": ('"stream": False', '"stream": 0'),
        "鉴权错误": ('"Authorization": f"Bearer {api_key}"', '"Authorization": "Bearer wrong-demo"'),
        "ContentType错误": ('"Content-Type": "application/json"', '"Content-Type": "text/plain"'),
        "缺少真实timeout": ('timeout=60', 'timeout=None'),
        "恒定content": ('return payload["choices"][0]["message"]["content"]', 'return "本地回复-1"'),
    }
    for label, (before, after) in mutations.items():
        assert fixture.CLIENT_SOURCE.count(before) == 1
        check("D25拒绝" + label, oracle.validate_d25_chat, fixture.CLIENT_SOURCE.replace(before, after), False)
    # A constant correct-looking first reply still has no actual I/O evidence.
    check("D25拒绝不请求直接返回", oracle.validate_d25_chat, 'def call_chat(api_key, messages, *, base_url):\n    return "本地回复-1"\n', False)
    # No guessed real host is reachable: guard blocks DNS before connect.
    external = fixture.CLIENT_SOURCE.replace('f"{base_url}/chat/completions"', '"https://example.invalid/chat/completions"')
    check("D25外部域名被阻断", oracle.validate_d25_chat, external, False)
    check("D25timeout布尔不是数字参数", oracle.validate_d25_chat, fixture.CLIENT_SOURCE.replace("timeout=60", "timeout=True"), False)
    check("D25任意正有限timeout可接受", oracle.validate_d25_chat, fixture.CLIENT_SOURCE.replace("timeout=60", "timeout=7"), True)

    check("D25错误路径精确类型状态消息", oracle.validate_d25_errors, fixture.CLIENT_SOURCE, True)
    check("D25errors同样不接受bool timeout", oracle.validate_d25_errors, fixture.CLIENT_SOURCE.replace("timeout=60", "timeout=True"), False)
    check("D25NameError不得冒充ApiError", oracle.validate_d25_errors, fixture.CLIENT_SOURCE.replace('raise ApiError("API 错误", error.code)', 'raise NameError("wrong type")'), False)
    check("D25坏JSON不能变成功", oracle.validate_d25_errors, fixture.CLIENT_SOURCE.replace('raise ApiError("响应不是 JSON", None)', 'return "accepted"'), False)
    check("D25网络status必须None", oracle.validate_d25_errors, fixture.CLIENT_SOURCE.replace('raise ApiError("网络错误", None)', 'raise ApiError("网络错误", 500)'), False)
    check("D25201不可忽略", oracle.validate_d25_errors, fixture.CLIENT_SOURCE.replace('            if response.status != 200:\n                raise ApiError("API 错误", response.status)\n', ''), False)
    check("D25错误不能不调用IO伪造", oracle.validate_d25_errors, 'class ApiError(RuntimeError):\n    pass\ndef call_chat(api_key, messages, *, base_url):\n    return "离线正常回复"\n', False)

    check("D26实际四输入与状态变化", oracle.validate_d26_prompt, fixture.PROMPT_SOURCE, True)
    # The explicit source is independent of fixture string quoting.
    localized = '''def build_prompt(titles, goal, instructions, completed):
    state = "是" if completed else "否"
    return f"知识范围标题：{titles}\\n索引仅代表标题知识范围，不代表视频正文。\\n目标：{goal}\\n要求：{instructions}\\n已完成：{state}"
'''
    check("D26允许中文状态表示", oracle.validate_d26_prompt, localized, True)
    check("D26不能忽略instructions", oracle.validate_d26_prompt, fixture.PROMPT_SOURCE.replace('{instructions}', '固定要求'), False)
    check("D26不能忽略completed", oracle.validate_d26_prompt, fixture.PROMPT_SOURCE.replace('{completed}', 'False'), False)
    check("D26不能硬编码titles", oracle.validate_d26_prompt, fixture.PROMPT_SOURCE.replace('"；".join(catalog_titles)', '"固定标题"'), False)
    check("D26需要返回str", oracle.validate_d26_prompt, 'def build_prompt(*args):\n    return {}\n', False)

    check("D27声明dict四键+实际输入", oracle.validate_d27_flow, FLOW, True)
    extra_imports = 'from ai_client import ApiError\nfrom prompt import parse_ai_json\n' + FLOW
    check("D27允许平台已声明额外依赖导入", oracle.validate_d27_flow, extra_imports, True)
    unused = FLOW.replace('result = send_message(api_key, prompt, base_url=base_url)', 'result = send_message(api_key, f"提交：{submission} 要求：{rubric} 标题：{catalog_titles}", base_url=base_url)')
    check("D27真正使用build_prompt产物", oracle.validate_d27_flow, unused, False)
    check("D27返回list不可冒充dict", oracle.validate_d27_flow, FLOW.replace('return result', 'return list(result)'), False)
    check("D27不可丢submission", oracle.validate_d27_flow, FLOW.replace('提交：{submission}', '固定提交'), False)
    check("D27不可丢rubric", oracle.validate_d27_flow, FLOW.replace('要求：{rubric}', '固定标准'), False)
    check("D27不可丢catalog", oracle.validate_d27_flow, FLOW.replace('build_prompt(catalog_titles,', 'build_prompt([], '), False)
    check("D27缺字段准确ValueError", oracle.validate_d27_flow, FLOW.replace('raise ValueError("缺字段")', 'raise KeyError("缺字段")'), False)
    filled = FLOW.replace('    required = ', '    for key in ["summary", "strengths", "issues", "next_steps"]:\n        result.setdefault(key, None)\n    required = ')
    check("D27不能默默补缺字段", oracle.validate_d27_flow, filled, False)
    strict_values = FLOW.replace('    return result', '    if not isinstance(result["summary"], str):\n        raise ValueError("暗加字段类型")\n    return result')
    # Negative test proves the validator accepts nonstandard but declared-valid
    # field values and does not silently impose str/list schema requirements.
    check("D27未声明字段类型不能暗加", oracle.validate_d27_flow, strict_values, False)

    registry = {}
    oracle.register(registry)
    assert set(registry) == {"D25-chat", "D25-errors", "D26-prompt", "D27-flow"}
    report = {"counts": counts, "paid_api_calls":0, "simulated_key":"demo", "registration":"passed", "checks":details}

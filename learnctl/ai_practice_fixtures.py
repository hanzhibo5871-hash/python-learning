"""Private offline fixtures for practice acceptance; never included in payloads."""
from __future__ import annotations

CLIENT_SOURCE = '''import json
import urllib.request
from urllib.error import HTTPError, URLError

class ApiError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

def call_chat(api_key, messages, *, base_url="https://api.deepseek.com"):
    body = json.dumps({"model": "deepseek-chat", "messages": messages, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise ApiError("API 错误", response.status)
            payload = json.loads(response.read())
            return payload["choices"][0]["message"]["content"]
    except HTTPError as error:
        raise ApiError("API 错误", error.code)
    except (URLError, TimeoutError):
        raise ApiError("网络错误", None)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ApiError("响应不是 JSON", None)
'''

PROMPT_SOURCE = '''import json

def build_prompt(catalog_titles, goal, instructions, completed):
    scope = "；".join(catalog_titles)
    return (f"知识范围标题：{scope}\\n"
            f"索引仅代表标题知识范围，不代表视频正文。\\n"
            f"目标：{goal}\\n要求：{instructions}\\n已完成：{completed}")

def parse_ai_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("没有 JSON")
    return json.loads(text[start:end + 1])
'''

COMPOSITION_SOURCE = '''import urllib.request
from deepseek_client import call_chat, ApiError
from prompt import parse_ai_json

def send_message(api_key, prompt, *, base_url):
    messages = [{"role": "user", "content": prompt}]
    return parse_ai_json(call_chat(api_key, messages, base_url=base_url))
'''


def ai_reference_fixtures():
    return [
        ("deepseek_client.py", CLIENT_SOURCE),
        ("prompt.py", PROMPT_SOURCE),
        ("ai_client.py", COMPOSITION_SOURCE),
    ]

# Patch where call_chat looks up the boundary. Existing global-urllib patches
# also remain compatible because both modules refer to the same urllib.request.
PATCH_TARGET = "deepseek_client.urllib.request.urlopen"
LEGACY_PATCH_TARGET = "ai_client.urllib.request.urlopen"

# D28 meaningful acceptance proposal, separate from the lesson source:
# 1. Run the submitted pytest file against the correct offline fixture.
# 2. Run it against behavior mutations, one at a time in fresh temporary dirs.
#    - Replace successful content with a wrong value.
#    - On HTTPError(401), return a success string instead of ApiError.
#    - On malformed outer JSON, return a success string instead of ApiError.
# 3. Correct fixture must pass; each mutant must fail. Do not accept pass-only
#    tests or AST-token presence as proof. Mutants must not add syntax errors.
# 4. Block all non-local networking in every run, including learner tests.
# 5. Confirm the reference tests fail on each mutant before integrating.
# Exact test names may remain those in the existing starter, but behavior wins.

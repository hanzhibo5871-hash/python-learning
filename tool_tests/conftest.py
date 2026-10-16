from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolate_live_ai_configuration(monkeypatch):
    """Never inherit user credentials; real provider transport requires a mock."""
    import urllib.parse
    import urllib.request
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    original = urllib.request.urlopen
    def guarded_urlopen(target, *args, **kwargs):
        url = target.full_url if isinstance(target, urllib.request.Request) else str(target)
        if urllib.parse.urlsplit(url).hostname == "api.deepseek.com":
            raise RuntimeError("测试禁止真实 DeepSeek 请求，请 mock AI 传输")
        return original(target, *args, **kwargs)
    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copy2(REPOSITORY / "data" / "curriculum.json", data_dir / "curriculum.json")
    return tmp_path


@pytest.fixture
def curriculum_data() -> dict:
    return json.loads((REPOSITORY / "data" / "curriculum.json").read_text(encoding="utf-8"))


def run_cli(project: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(REPOSITORY) if not existing else os.pathsep.join((str(REPOSITORY), existing))
    return subprocess.run(
        [sys.executable, "-m", "learnctl", *args],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        input=input_text,
        check=False,
    )


def section_of(curriculum_data: dict, task_id: str, section_id: str) -> dict:
    task = next(item for item in curriculum_data["tasks"] if item["id"] == task_id)
    return next(item for item in task["lesson"] if item["id"] == section_id)


@pytest.fixture
def web_server(project: Path):
    from learnctl.web.server import create_server

    server = create_server(project, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(server: Any, method: str, path: str, body: dict[str, Any] | None = None, **headers: str):
    import http.client

    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=60)
    request_headers = {"Host": f"127.0.0.1:{server.server_port}", **headers}
    encoded = None
    if body is not None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
        request_headers["Content-Length"] = str(len(encoded))
    connection.request(method, path, body=encoded, headers=request_headers)
    response = connection.getresponse()
    raw = response.read()
    content_type = response.getheader("Content-Type", "")
    result = json.loads(raw.decode("utf-8")) if raw and "application/json" in content_type else raw.decode("utf-8")
    output = (response.status, result, dict(response.getheaders()))
    connection.close()
    return output


def grading_reply(payload, verdict='needs_work'):
    """Mock the new protocol from the authoritative request, never real API."""
    data = json.loads(payload['messages'][-1]['content'])
    lines = data['submission'].splitlines()
    refs = [f'submission:{min(2,len(lines))}'] if lines else ['stdout'] if 'stdout' in data['evidence'] else ['run']
    local = data['local_evidence'].get('passed')
    status = 'met' if verdict == 'passed' else 'unmet' if local is False else 'uncertain'
    name = data['lesson'].get('title', '当前题目')
    items = [{'id': r['id'], 'requirement':f"{name}：核对当前要求第{i+1}项", 'status': status, 'explanation': f'{name}：已按当前证据逐项核对这一要求。', 'evidence': refs} for i,r in enumerate(data['requirements'])]
    issues = [] if verdict == 'passed' else [{'requirement_ids': [r['id'] for r in data['requirements']],
        'cause': f'{name}：当前提交的结果没有随输入变化，需要核对本题规定的数据流。',
        'evidence': refs, 'hints': ['比较本题两组不同输入时，实际结果是否跟着变化？',
        '追踪输入进入当前函数后，在哪一步停止影响结果？', '对照本题要求，返回位置是否使用了当前输入而非固定值？']}]
    if local is True and issues:
        issues[0]['cause'] = f'{name}：本地测试已经通过，但额外边界尚需复查，不能撤销完成记录。'
    return {'judgement': verdict, 'requirements': items, 'issues': issues, 'limitations': []}

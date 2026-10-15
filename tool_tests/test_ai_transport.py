"""Offline provider protocol tests: dummy keys and loopback HTTP only."""
from __future__ import annotations

import io
import json
import ssl
import threading
from http.client import IncompleteRead, RemoteDisconnected
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError

import pytest

from learnctl import ai
from learnctl.curriculum import load_curriculum
from pathlib import Path


DUMMY_KEY = "dummy-transport-key"


def session():
    result = ai.AiSession()
    result.set_key(DUMMY_KEY)
    return result


def response(content="你好", reason="stop", role="assistant"):
    return json.dumps({"choices": [{"finish_reason": reason, "message": {
        "role": role, "content": content}}]}, ensure_ascii=False).encode("utf-8")


class Response(io.BytesIO):
    status = 200


def test_transport_posts_utf8_headers_timeout_and_current_model(monkeypatch):
    captured = {}
    incoming = Response(b"\n \r\n" + response())

    def open_request(req, timeout):
        captured.update(url=req.full_url, method=req.get_method(),
                        headers=dict(req.header_items()), data=req.data, timeout=timeout)
        return incoming

    monkeypatch.setattr(ai, "_open_request", open_request)
    assert ai.chat(session(), [{"role": "user", "content": "解释缩进"}]) == "你好"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["method"] == "POST"
    assert captured["headers"]["Authorization"] == f"Bearer {DUMMY_KEY}"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["timeout"] == 60
    body = json.loads(captured["data"].decode("utf-8"))
    assert body == {"model": "deepseek-flash", "messages": [{"role": "user", "content": "解释缩进"}],
                    "stream": False, "temperature": 0.7, "thinking": {"type": "disabled"},
                    "max_tokens": ai.TEXT_MAX_TOKENS}
    assert DUMMY_KEY not in captured["data"].decode()
    assert incoming.closed


@pytest.mark.parametrize("phase", ["open", "success-read", "error-read"])
@pytest.mark.parametrize("error,expected", [
    (TimeoutError(DUMMY_KEY), "超时"),
    (URLError(TimeoutError(DUMMY_KEY)), "超时"),
    (URLError(ssl.SSLCertVerificationError(DUMMY_KEY)), "TLS"),
    (ssl.SSLError(DUMMY_KEY), "TLS"),
    (URLError(f"https://user:{DUMMY_KEY}@proxy.invalid"), "网络错误"),
    (ConnectionResetError(DUMMY_KEY), "网络错误"),
    (RemoteDisconnected(DUMMY_KEY), "网络错误"),
    (IncompleteRead(DUMMY_KEY.encode(), 100), "网络错误"),
])
def test_transport_sanitizes_connect_and_read_failures(monkeypatch, phase, error, expected):
    class BrokenResponse(Response):
        def read(self, size=-1):
            raise error

    incoming = BrokenResponse()

    def open_request(req, timeout):
        if phase == "open":
            raise error
        if phase == "error-read":
            raise HTTPError(req.full_url, 503, "upstream", {}, incoming)
        return incoming

    monkeypatch.setattr(ai, "_open_request", open_request)
    with pytest.raises(ai.AiError, match=expected) as caught:
        ai.chat(session(), [{"role": "user", "content": "hi"}])
    assert DUMMY_KEY not in str(caught.value)
    assert caught.value.__suppress_context__
    if phase != "open":
        assert incoming.closed


@pytest.mark.parametrize("status,hint", [(400, "格式"), (401, "鉴权"), (402, "余额"),
    (404, "模型"), (422, "参数"), (429, "过快"), (500, "服务端"), (503, "繁忙"), (418, "服务状态")])
def test_real_httperror_is_closed_and_body_is_not_exposed(monkeypatch, status, hint):
    incoming = Response(json.dumps({"error": {"message": DUMMY_KEY}}).encode())

    def open_request(req, timeout):
        raise HTTPError(req.full_url, status, DUMMY_KEY, {}, incoming)

    monkeypatch.setattr(ai, "_open_request", open_request)
    with pytest.raises(ai.AiError, match=f"HTTP {status}.*{hint}") as caught:
        ai.chat(session(), [{"role": "user", "content": "hi"}])
    assert DUMMY_KEY not in str(caught.value)
    assert incoming.closed


@pytest.mark.parametrize("key", ["bad\nsecret", "bad\rsecret", "bad secret", "bad\x00secret", "密钥", " " * 8, "x" * 513])
def test_invalid_session_and_environment_key_never_reach_transport(monkeypatch, key):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid key must not reach the network")

    monkeypatch.setattr(ai, "_open_request", forbidden)
    with pytest.raises(ai.AiError, match="格式无效"):
        ai.AiSession().set_key(key)
    # Operating systems reject NUL before it can enter an environment variable.
    if "\x00" in key:
        return
    monkeypatch.setenv("DEEPSEEK_API_KEY", key)
    with pytest.raises(ai.AiError, match="格式无效"):
        ai.chat(ai.AiSession(), [{"role": "user", "content": "hi"}])


def test_key_precedence_clear_and_normalization(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy-env-key")
    current = ai.AiSession()
    assert current.get_key() == "dummy-env-key"
    current.set_key("  dummy-session-key  ")
    assert current.get_key() == "dummy-session-key"
    current.clear_key()
    assert current.get_key() == "dummy-env-key"


@pytest.mark.parametrize("reason", ["length", "content_filter", "tool_calls", "insufficient_system_resource", "aborted", None, {}, "unexpected"])
@pytest.mark.parametrize("structured", [False, True])
def test_unfinished_response_is_never_accepted_or_structure_repaired(monkeypatch, reason, structured):
    calls = []

    def provider(*args, **kwargs):
        calls.append(args)
        return 200, response('{"title":"partial"}', reason=reason)

    monkeypatch.setattr(ai, "_request", provider)
    with pytest.raises(ai.AiError, match="未正常完成"):
        if structured:
            ai.generate(session(), load_curriculum(Path("data/curriculum.json")), "D02", "D02-names", False)
        else:
            ai.chat(session(), [{"role": "user", "content": "hi"}])
    assert len(calls) == 1
    if structured:
        assert calls[0][1]["max_tokens"] == ai.JSON_MAX_TOKENS
        assert calls[0][1]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("raw", [b"null", b"[]", b'{}', b'{"choices":{}}', b'{"choices":[null]}',
    b'{"choices":[{"message":[]}]}', b"\xff", response(None), response(""),
    response("   "), response(role="user")])
def test_invalid_responses_raise_aierror(monkeypatch, raw):
    monkeypatch.setattr(ai, "_request", lambda *a, **k: (200, raw))
    with pytest.raises(ai.AiError):
        ai.chat(session(), [{"role": "user", "content": "hi"}])


@pytest.mark.parametrize("role", [[], {}, None, 1])
def test_history_role_wrong_type_is_a_safe_aierror(role):
    with pytest.raises(ai.AiError, match="role 只能"):
        ai.build_tutor_messages(load_curriculum(Path("data/curriculum.json")), "D02", "D02-names",
                                "hi", [{"role": role, "content": "data"}])


@pytest.fixture
def provider_server(monkeypatch):
    calls = []
    status = [200]

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append((self.path, self.headers.get("Authorization"),
                          self.rfile.read(int(self.headers["Content-Length"]))))
            if status[0] != 200:
                self.send_response(status[0])
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/redirect-target")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            raw = b"\n\r\n" + response()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            calls.append((self.path, self.headers.get("Authorization"), b""))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(ai, "BASE_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        yield calls, status
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_urllib_roundtrip_uses_actual_http_without_a_real_key(provider_server):
    calls, _ = provider_server
    assert ai.chat(session(), [{"role": "user", "content": "解释变量"}]) == "你好"
    assert len(calls) == 1
    assert calls[0][0] == "/chat/completions"
    assert calls[0][1] == f"Bearer {DUMMY_KEY}"
    assert json.loads(calls[0][2])["messages"][0]["content"] == "解释变量"


@pytest.mark.parametrize("redirect_status", [301, 302, 303, 307, 308])
def test_urllib_never_follows_redirect_with_key(provider_server, redirect_status):
    calls, status = provider_server
    status[0] = redirect_status
    with pytest.raises(ai.AiError):
        ai.chat(session(), [{"role": "user", "content": "hi"}])
    assert len(calls) == 1
    assert calls[0][0] == "/chat/completions"

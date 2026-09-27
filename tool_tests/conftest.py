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

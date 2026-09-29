"""Short introductions must cover the real curriculum without changing tasks."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "learnctl" / "web" / "static"


def _catalog() -> dict[str, list[str]]:
    source = (STATIC / "teaching-catalog.js").read_text(encoding="utf-8")
    match = re.search(r"Object\.freeze\((\{.*\})\);", source, re.DOTALL)
    assert match is not None
    return json.loads(match.group(1))


def test_short_teaching_covers_every_current_section():
    data = json.loads((ROOT / "data/curriculum.json").read_text(encoding="utf-8"))
    sections = [s for t in data["tasks"] for s in t["lesson"]]
    catalog = _catalog()
    assert set(catalog) == {s["id"] for s in sections}
    for section in sections:
        assert section.get("examples"), section["id"]
        assert section["examples"][0].get("code"), section["id"]


@pytest.mark.parametrize("section_id", list(_catalog()))
def test_short_teaching_has_three_distinct_concise_explanations(section_id):
    fields = _catalog()[section_id]
    assert len(fields) == 3
    assert len(set(fields)) == 3
    assert all(isinstance(s, str) and 10 <= len(s) <= 120 for s in fields)
    assert not any("请自行搜索" in s or "自己查询" in s for s in fields)


def test_teaching_assets_load_before_existing_app_and_keep_accessibility():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assets = ["teaching-catalog.js", "teaching-view.js", "app.js"]
    assert [html.index(f'/static/{name}') for name in assets] == sorted(
        html.index(f'/static/{name}') for name in assets)
    assert '/static/teaching.css' in html
    assert 'aria-label="主导航"' in html
    assert 'id="page-feedback"' in html


def test_enhancement_does_not_execute_code_or_replace_existing_editors():
    source = (STATIC / "teaching-view.js").read_text(encoding="utf-8")
    for forbidden in ("fetch(", "eval(", "new Function", ".innerHTML", "localStorage", ".value =", ".click("):
        assert forbidden not in source
    assert "new WeakSet()" in source
    assert "body.insertBefore(examples, practice)" in source
    assert "body.insertBefore(drills, practice)" in source
    assert "first.open = true" in source
    assert "document.createTextNode(text)" in source


@pytest.mark.parametrize("filename", ["teaching-catalog.js", "teaching-view.js"])
def test_teaching_javascript_syntax(filename):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is optional locally; CI runs this check on both platforms")
    result = subprocess.run([node, "--check", str(STATIC / filename)], capture_output=True,
                            text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr

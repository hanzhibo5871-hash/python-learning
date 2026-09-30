"""Regeneration is tested in a copy, never in the learner checkout."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_committed_curriculum_rebuilds_without_drift(tmp_path):
    shutil.copytree(ROOT / "scripts", tmp_path / "scripts")
    (tmp_path / "data").mkdir()
    target = tmp_path / "data" / "curriculum.json"
    shutil.copyfile(ROOT / "data" / "curriculum.json", target)
    # Git may check out CRLF on Windows; compare the repository text content.
    expected = target.read_text(encoding="utf-8")
    learner_files = {
        ".learn/progress.json": '{"evidence": "keep progress"}',
        ".learn/lesson-submissions/D02/D02-numbers.py": "# saved learner draft",
        "learner_workspace/exercises/form.py": "# submitted learner exercise",
    }
    for name, content in learner_files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for seed in ("1", "42"):
        result = subprocess.run(
            [sys.executable, "scripts/build_curriculum_v3.py"],
            cwd=tmp_path, env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert target.read_text(encoding="utf-8") == expected, (
            "Rebuild data/curriculum.json and commit it with its generator changes"
        )
    for name, content in learner_files.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == content

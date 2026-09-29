# AGENTS.md

Offline, local Python-learning-progress tool (`learnctl`) for frontend developers. Reads `data/curriculum.json`, validates it strictly, and drives a stdlib-HTTP workbench plus a CLI. All user-facing text is Chinese.

## CLAUDE.md is stale

`CLAUDE.md` describes the old pre-web version (5 stages / 21 tasks / 20 modules / no web / no AI). Trust `README.md` + `docs/` instead. Current reality:

- Curriculum `schema_version` 3, `curriculum_version` 3.0.0; progress remains schema 2.
- 4 stages (S1–S4), 28 tasks (D01–D28), 146 lesson sections (including 24 optional offline drills), 22 modules, 1 optional track (`langchain-cloud`, off), 5 exercises, 6 diagnostics (D0–D5), 131 `source_catalog` entries.
- Modules not mentioned in CLAUDE.md: `workflow.py`, `practice.py`, `envcheck.py`, `ai.py`, `web/`.
- `docs/curriculum-v3-design.md` is the historical v3 design; current behavior is described in README and tool-spec.

## Commands (run from repo root — `data/`/`.learn/` paths resolve against `Path.cwd()`)

```powershell
python -m venv .venv && .\.venv\Scripts\Activate.ps1 && python -m pip install -e ".[dev]"
python -m learnctl serve --open          # main entry: workbench, binds 127.0.0.1 only
python -m learnctl today [--json]
python -m learnctl lesson [TASK] [--json]
python -m learnctl progress [mark|module|option ...]
python -m learnctl diagnose [--json] [--answers answers.json]   # optional, not mainline
python -m learnctl test <EXERCISE> [--verbose]
```

## Two test worlds — do NOT confuse

- `python -m pytest` runs ONLY `tool_tests/` (pyproject `testpaths`). One test: `python -m pytest tool_tests/test_cli.py -k name`.
- Learner exercises run only via `python -m learnctl test <exercise_id>` (executes the exact `learner_tests/*.py` declared in the curriculum). Never run them with plain pytest.
- No lint/typecheck/format config exists; pytest is the only verification.

## Exit codes & `--json`

`0` success / `1` blocked or exercise failed / `2` usage / `3` invalid curriculum or state.
In `--json` mode stdout must be exactly one JSON object; prompts/errors go to stderr.

## Architecture

- `curriculum.py` — `validate_curriculum` is the strict gatekeeper (curriculum schema v3 only, bidirectional cross-refs, DAG check, non-supplemental modules must exactly cover all 131 catalog refs). Attaches `root["_index"]` (ID→object maps) that everything else relies on.
- `workflow.py` — `today`/`lesson` payloads and completion rules (NOT in `__main__.py` as CLAUDE.md claims).
- `progress.py` — `.learn/progress.json` schema v2, atomic writes, local-timezone ISO timestamps. Schema 1 or legacy `courses`/`course_decisions` hard-fail (exit 3). Only explicit known curriculum-version transitions are supported, including the existing 3.0.0 transition; no fallback.
- `practice.py` — server-private validators `_CODE_VALIDATORS` keyed by section id (harness + local mock HTTP/DeepSeek servers). A `code` section without a registered validator → `DataError`.
- `envcheck.py` — D01 env actions (detect/create_venv/install/verify).
- `ai.py` — DeepSeek client, `urllib` only (no SDK).
- `test_runner.py` — subprocess runner for learner exercises.
- `web/server.py` — stdlib `ThreadingHTTPServer` workbench; 127.0.0.1 only; security headers + same-origin checks on writes.
- `errors.py` — `LearnctlError` with subclasses `DataError`(3) / `UsageError`(2) / `BlockedError`(1).

## Conventions / gotchas

- `data/curriculum.json` is GENERATED: edit `scripts/build_curriculum_v3.py` and `scripts/beginner_drills.py`, then run `python scripts/build_curriculum_v3.py` (reuses the existing 131-entry `source_catalog`). Don't hand-edit `curriculum.json` or rebuild v3 with the historical v2 scripts. Offline drill checks live in `learnctl/drills.py` and use the existing subprocess runner.
- Fail-loud, never guess-and-repair: invalid data → exit 3, no fallback file, no silent rewrites.
- Task `done` requires non-empty evidence + all task/stage prerequisites done + all required (non-`optional`) sections validated. Marking D24 `done` triggers end-to-end project acceptance (`validate_project_acceptance`).
- All writes (progress/drafts/notes/workspace files) are atomic (temp + fsync + `os.replace`).
- Windows console is cp936/GBK; `__main__._configure_utf8_streams()` reconfigures stdout/stderr to UTF-8. Subprocess runners force `PYTHONIOENCODING=utf-8`.
- Modules use `from __future__ import annotations` and `dict[str, Any]`-style generics; error paths raise `LearnctlError` subclasses rather than returning error codes.
- Stray artifacts (`_d1824_dump.json`, `build/`, `learnctl.egg-info/`, `.pytest_cache/`) should not be committed; the last three are already gitignored.

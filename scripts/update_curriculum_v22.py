# -*- coding: utf-8 -*-
"""v2.2.0 课程数据迁移：重构 D18-D24 的项目产物白名单。

可重复运行（幂等）：直接修改 data/curriculum.json。若目标小节已就位（如
D18-req 已存在），则相关转换自动跳过，重复运行不会二次损坏。

用法：python scripts/update_curriculum_v22.py

转换内容：
- D18-requirements -> D18-req（产物 docs/requirements.md 不变）。
- D18-readme（产物 README.md）移入 D19，更名为 D19-readme。
- D19-pyproject 由 project 类型改为 text（“简单输入”）。
- D20-crud、D21-errors 在 practice 上标记 continues_file: true（相邻续写同一产物）。
- D23-html -> D23-web，类型 html 改为 text（产物 taskproj/static/index.html）。
- D24-runbook -> D24-rebuild（产物 docs/runbook.md）。
- 课程版本固定为 2.2.0。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "curriculum.json"

TARGET_VERSION = "2.2.0"


def _task(root: dict, task_id: str) -> dict:
    for task in root["tasks"]:
        if task["id"] == task_id:
            return task
    raise KeyError(f"缺少任务 {task_id}")


def _section(task: dict, section_id: str) -> dict | None:
    return next((s for s in task["lesson"] if s["id"] == section_id), None)


def _drop(task: dict, section_id: str) -> dict | None:
    section = _section(task, section_id)
    if section is not None:
        task["lesson"] = [s for s in task["lesson"] if s["id"] != section_id]
    return section


def main() -> int:
    if not DATA.exists():
        print(f"缺少课程文件 {DATA}，请先在仓库根目录运行本脚本", file=sys.stderr)
        return 2

    root = json.loads(DATA.read_text(encoding="utf-8"))

    # 1. D18-requirements -> D18-req
    d18 = _task(root, "D18")
    if (req := _section(d18, "D18-requirements")) is not None:
        req["id"] = "D18-req"

    # 2. 把 README.md 产物小节从 D18 移入 D19（更名 D19-readme）
    readme = _drop(d18, "D18-readme")
    if readme is not None:
        readme["id"] = "D19-readme"
        d19 = _task(root, "D19")
        if _section(d19, "D19-readme") is None:
            d19["lesson"].append(readme)

    # 3. D19-pyproject：project 类型改为 text
    d19 = _task(root, "D19")
    if (pyproj := _section(d19, "D19-pyproject")) is not None:
        if pyproj["practice"].get("kind") == "project":
            pyproj["practice"]["kind"] = "text"

    # 4. 相邻续写产物：D20-crud、D21-errors 标记 continues_file
    for task_id, section_id in (("D20", "D20-crud"), ("D21", "D21-errors")):
        if (section := _section(_task(root, task_id), section_id)) is not None:
            section["practice"]["continues_file"] = True

    # 5. D23-html -> D23-web，html 类型改为 text
    d23 = _task(root, "D23")
    if (web := _drop(d23, "D23-html")) is not None:
        web["id"] = "D23-web"
        if web["practice"].get("kind") == "html":
            web["practice"]["kind"] = "text"
        if _section(d23, "D23-web") is None:
            d23["lesson"].append(web)

    # 6. D24-runbook -> D24-rebuild
    d24 = _task(root, "D24")
    if (runbook := _section(d24, "D24-runbook")) is not None:
        runbook["id"] = "D24-rebuild"

    # 7. 固定课程版本
    root["curriculum_version"] = TARGET_VERSION

    DATA.write_text(json.dumps(root, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已迁移到 {TARGET_VERSION}：{DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

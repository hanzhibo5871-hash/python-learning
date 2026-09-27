# -*- coding: utf-8 -*-
"""从 scripts/curriculum_content.py 生成 data/curriculum.json。

运行：python scripts/build_curriculum.py
- 保留现有 data/curriculum.json 中的 source_catalog（131 条，只作知识范围索引）。
- 按新路线生成阶段/模块/任务/练习/诊断结构。
- 校验：非 supplemental 模块的 catalog_refs 必须精确覆盖全部 131 条、且不重复。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "curriculum.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curriculum_content as cc  # noqa: E402


def main() -> None:
    if not DATA.exists():
        raise SystemExit(f"缺少现有课程文件 {DATA}，无法继承 source_catalog")
    old = json.loads(DATA.read_text(encoding="utf-8"))
    source_catalog = old["source_catalog"]
    source_ids = [item["id"] for item in source_catalog]
    if len(source_ids) != len(set(source_ids)):
        raise SystemExit("source_catalog 存在重复 id")

    # 非 supplemental 模块必须精确覆盖全部 131 条、不重复、不缺失
    claimed: list[str] = []
    for module in cc.MODULES:
        if module.get("supplemental"):
            if module["catalog_refs"]:
                raise SystemExit(f"supplemental 模块 {module['id']} 不应占用真实索引引用")
            continue
        claimed.extend(module["catalog_refs"])
    if len(claimed) != len(set(claimed)):
        duplicates = sorted({item for item in claimed if claimed.count(item) > 1})
        raise SystemExit(f"模块 catalog_refs 重复引用：{duplicates}")
    missing = [item for item in source_ids if item not in claimed]
    extra = [item for item in claimed if item not in source_ids]
    if missing or extra:
        raise SystemExit(f"模块覆盖不完整：缺少 {missing}，多出 {extra}")

    root: dict[str, Any] = {
        "schema_version": 2,
        "curriculum_version": "2.2.0",
        "meta": {
            "title": "前端开发者的 Python / API / AI 学习路径（可视化工具版）",
            "audience": "有前端基础、希望用 Python 完成真实项目与 AI 应用的学习者",
            "source_course_count": len(source_catalog),
            "suggested_cycle": "约 6 周，按阶段推进，每阶段验收后再进入下一阶段",
            "out_of_scope": ["深度学习训练", "数据库服务", "云端账户体系", "自动化刷题"],
        },
        "source_catalog": source_catalog,
        "modules": cc.MODULES,
        "optional_tracks": cc.OPTIONAL_TRACKS,
        "diagnostics": cc.DIAGNOSTICS,
        "diagnostic_thresholds": {
            "pass_min_percent": 80,
            "partial_min_percent": 60,
            "critical_cases_must_pass": True,
        },
        "stages": cc.STAGES,
        "tasks": cc.TASKS,
        "exercises": cc.EXERCISES,
    }

    DATA.write_text(json.dumps(root, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total_sections = sum(len(task["lesson"]) for task in cc.TASKS)
    by_kind: dict[str, int] = {}
    for task in cc.TASKS:
        for section in task["lesson"]:
            kind = section["practice"]["kind"]
            by_kind[kind] = by_kind.get(kind, 0) + 1
    print(f"已生成 {DATA}")
    print(f"阶段 {len(cc.STAGES)}，任务 {len(cc.TASKS)}，小节 {total_sections}")
    print(f"practice 类型分布：{by_kind}")
    print(f"source_catalog 保留 {len(source_catalog)} 条")


if __name__ == "__main__":
    main()

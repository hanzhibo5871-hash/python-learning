"""已废弃：D18-D24 的 project_file/workspace_deps 已内置于 scripts/curriculum_content.py。

本脚本保留旧的一次性映射，若重新运行会把已消除的 project_file 重复（README.md、
taskproj/db.py、taskproj/api.py 等）重新写回 data/curriculum.json，因此直接拒绝执行。
生成课程数据请运行：python scripts/build_curriculum.py
"""
import sys

print(
    "此脚本已废弃，不再修改 data/curriculum.json。\n"
    "project_file/workspace_deps 现由 scripts/curriculum_content.py 声明，"
    "重新生成请运行：python scripts/build_curriculum.py",
    file=sys.stderr,
)
sys.exit(1)

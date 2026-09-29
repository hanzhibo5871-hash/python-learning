# AGENTS.md

`learnctl` 是面向有开发经验、无 Python 经验学习者的本地 Python/API/AI 工作台。用户界面与课程说明使用中文。

## 事实来源

当前为 schema 3、curriculum 3.0.0、practice_first_revision 1：4 阶段、28 任务、122 小节，39 张前置知识卡和124道补全练习。旧 CLAUDE.md 和 v2 构建脚本不是当前主线。以 README、生成数据和实际测试为准。

## 构建与测试

- `data/curriculum.json` 是生成文件。编辑 `scripts/build_curriculum_v3.py` 和 `scripts/practice_first_content.py`，然后从仓库根运行 `python scripts/build_curriculum_v3.py`。必须同步提交生成结果，重复生成不得漂移。
- `python -m pip install -e ".[dev]"` 安装开发依赖；`python -m pytest -q tool_tests` 运行工具测试。学习者测试仍只经 `python -m learnctl test <exercise_id>` 执行白名单文件。
- `node --check learnctl/web/static/app.js` 检查前端语法。
- 可选浏览器回归：安装 playwright/Chromium 后，`python scripts/browser_smoke.py`。只操作临时工作区，不修改学习者进度。

## 课程约束

每题需要的知识必须已教或在本节提供短小可运行卡片。主作业的签名、返回格式、输入范围与验证器必须一致；必修不得暗中依赖尚未学习或选修章节。不要把函数练习顺便变成异常、类型校验和容器大题。

短规则、代码和实际输出优先，长原理折叠。补全练习要求实际运行参考代码且未修改 starter 不能通过，不能用凑字数或 AST 关键字充当行为验收。项目分步测试只能检查已生成的文件；全项目验收保留在 D24。

## 架构和边界

- `curriculum.py` + `practice_first_schema.py` 严格校验数据与已声明前置关系。
- `workflow.py` 组织任务和完成逻辑，公开 payload 不包含补全题参考答案。
- `practice.py` 保留既有验证/工作区基础；`contract_checks.py` 维护本轮对齐的行为用例。
- `experiments.py` 只执行显式点击的 Python 实验，临时目录、限时、限输出、shell=False，不是安全沙箱。
- `web/server.py` 仅绑定 127.0.0.1，保留同源写检查。实验端点不修改学习进度，正式作业仍经过后端解锁和验证。
- `progress.py` 的历史迁移不应因 UI 改版而重置。不要删除 `.learn`、`.venv` 或 `learner_workspace`；不要提交这些目录、密钥和临时测试产物。
- 所有持久写入继续使用现有原子写工具；CLI `--json` 保持 stdout 单一 JSON、错误去 stderr；Windows 子进程使用 UTF-8。

`main` 不强制推送。变更在分支通过回归后提出 PR，结果说明区分本地验证、CI 和未覆盖范围。

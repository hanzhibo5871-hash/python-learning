# learnctl 工具规格

## 1. 范围

`learnctl` 是一个 Python 3.11+ 的本地可视化学习工具，读取 `data/curriculum.json`，提供：

1. 4 阶段、28 任务、60 小节的真实实践路线（`code` / `json` / `text` / `command` / `env_action`，全部为输入型实践，没有任何选择题）。
2. D01 真实环境配置：实时检测解释器/`.venv`/pip/pytest/可编辑安装，并执行固定动作。
3. 本地确定性验证：服务端私有 validator，`GET task` 不返回 validator 与隐藏用例。
4. 草稿原子保存与断点恢复（`.learn/lesson-submissions/`）。
5. 标准库本地工作台和同源 JSON API（仅 `127.0.0.1`）。
6. 可选 AI 助教：默认且唯一的 provider 为 DeepSeek 官方 API；无 Key 也能完成固定课程与本地验证，AI 调用只在用户显式点击时发生。
7. 可选 D0-D5 能力诊断（非主线前置）。

原始 131 个来源条目只作为 `source_catalog` 知识范围标题索引。工具不访问来源、不抓取内容、不实现数据库服务、远程服务或自动答案。索引缺口（FastAPI、SQLite、asyncio、测试、配置/日志/CLI、JSON 工程实践、DeepSeek API 等）以 `supplemental: true` 标记为真实开发补充，绝不伪造索引标题、绝不声称看过视频正文。

## 2. 目录与状态

```text
learnctl/
  __main__.py       参数解析与退出码
  curriculum.py     读取并校验 curriculum.json
  diagnostic.py     D0-D5 诊断与模块建议（可选工具）
  progress.py       progress.json 原子读写与跨版本协调
  workflow.py       任务、前置与小节完成规则
  practice.py       实践校验器、草稿与本地 mock 服务
  envcheck.py       D01 环境实时检测与固定动作
  ai.py             DeepSeek 客户端（urllib，无 SDK）
  test_runner.py    执行指定 learner_tests 文件
  web/              标准库 HTTP 服务、存储边界和原生前端
data/curriculum.json
docs/
tool_tests/
learner_tests/      用户练习目录，不作为工具测试目录
.learn/             进度、笔记、草稿（gitignored）
```

课程文件必须是 `schema_version: 2`，`curriculum_version: 2.1.0`。每个任务包含标题、学习目标、概念、前端对照、编码任务、产物、验收和至少 2 个小节；每个小节包含讲解、关键点、前端对照、示例、步骤与 `practice` 实践。`practice.kind` 只允许 `code` / `json` / `text` / `command` / `env_action`：

- `code`：提交写章节临时目录，当前解释器子进程（`shell=False`）、固定超时与输出长度，服务端私有 validator 检查函数/输出；返回 `exit_code/stdout/stderr/checks`，不返回 validator 源码。
- `json`：确定性 JSON 解析与字段校验，绝不 eval。
- `text`：归一化关键词与长度校验，只用于 onboarding / 需求 / 复盘。
- `command`：只理解命令文本并做固定模式校验，绝不执行用户任意命令。
- `env_action`：只用于 D01 的固定动作（detect / create_venv / install / verify）。

进度文件的最小结构：

```json
{
  "schema_version": 2,
  "curriculum_version": "2.1.0",
  "tasks": {},
  "modules": {},
  "module_decisions": {},
  "options": {"langchain-cloud": false},
  "tests": {},
  "lesson_progress": {}
}
```

`tasks` 只使用 `todo`、`in_progress`、`done`；`modules` 与 `module_decisions` 只使用 `learn`、`practice`、`mastered`。当前课程为 curriculum 3.0.0 / schema 3：D01 → D02-D07 Python 语法 → D08-D17 常用开发 → D18-D24 真实项目 → D25-D28 AI。schema 1 或旧的 `courses` / `course_decisions` 直接报错，不自动迁移。读取旧课程版本时保留未知历史字段，但 D02-D28 的旧小节完成和旧 done 状态不能冒充 v3；D01 只在环境证据仍有效时保留。后端按任务与小节顺序门禁 validate/done，直接 URL 只能查看锁定说明。

## 3. CLI 契约

```powershell
python -m learnctl today [--json]
python -m learnctl lesson [TASK] [--json]
python -m learnctl progress                                  # 阶段/模块/下一任务概述
python -m learnctl progress mark <TASK> --status todo|in_progress|done [--evidence "..."]
python -m learnctl progress module <MODULE> --status learn|practice|mastered
python -m learnctl progress option <OPTION> --enabled|--disabled
python -m learnctl diagnose [--json] [--answers answers.json]   # 可选工具，非主线前置
python -m learnctl test <EXERCISE> [--verbose]
python -m learnctl serve --host 127.0.0.1 --port 8765 [--open]
```

- `today` 选择第一个未完成且前置条件满足的主线任务。
- `lesson` 省略任务 ID 时使用今日任务；指定任务即使前置未完成也返回 0。
- `progress mark` 标为 `done` 必须有非空证据，且前置任务与阶段完成。
- `test` 只执行课程声明的具体 `learner_tests/*.py`；拒绝目录、绝对路径、路径穿越、通配符和其他 pytest 选项。
- `diagnose` 不再自动把任务标记完成；诊断是可选工具。
- `serve` 只允许绑定 `127.0.0.1`。

## 4. 校验规则

启动命令前校验：

- schema 版本、课程版本和 JSON 格式。
- 131 条 `source_catalog`，每个系列编号从 1 连续覆盖，且非 supplemental 模块的 `catalog_refs` 精确覆盖全部条目、不重复。
- 所有 ID 唯一，阶段和任务依赖图无环。
- 全小节无 `quiz` / `choices` / `answer_index`；`practice` 类型合法；`code` 小节必须有安全的 `.py` 文件名。
- `supplemental` 小节必须有 `supplemental_note`；`catalog_refs` 只能引用真实存在的来源 ID。
- 阶段覆盖全部任务；练习命令必须是具体 `learner_tests/*.py`。

校验失败直接报告路径与原因，退出码为 3；不读取备用课程、不修复数据、不迁移状态。

## 5. 写入与退出码

状态、草稿与笔记先写同目录临时文件，再原子替换正式文件。时间使用带时区 ISO 8601。未知字段保留，未知状态拒绝。`state_lock` 串行化所有写入。

| 退出码 | 含义 |
| --- | --- |
| 0 | 命令成功或练习通过 |
| 1 | 当前任务阻塞或练习失败 |
| 2 | 参数错误 |
| 3 | 课程或状态数据无效 |

工具自身用 `python -m pytest` 验证（只覆盖 `tool_tests/`）；用户练习只由 `learnctl test <exercise_id>` 按课程声明执行。

## 6. 本地工作台与 API

只允许绑定 `127.0.0.1`。工作台使用标准库 `ThreadingHTTPServer` 和 `learnctl/web/static/` 内的原生 HTML/CSS/JS；不依赖 Node、前端框架、CDN、数据库或外部服务。

核心端点：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/bootstrap` | 仪表盘、阶段、任务摘要、模块、选修项 |
| GET | `/api/tasks/{id}` | 任务知识卡、公共 practice、草稿、可编辑文件（不返回 validator） |
| POST | `/api/tasks/{id}/status` | 更新任务状态，沿用证据与前置校验 |
| POST | `/api/tasks/{id}/lesson-position` | 保存当前小节 |
| PUT | `/api/tasks/{id}/sections/{sid}/draft` | 原子保存草稿到 `.learn/lesson-submissions/` |
| POST | `/api/tasks/{id}/sections/{sid}/validate` | 运行本地校验；通过则幂等完成小节 |
| POST | `/api/env/action` | D01 固定动作：detect / create_venv / install / verify |
| GET/PUT | `/api/files` | 读取或原子保存当前任务白名单文件 |
| GET/PUT | `/api/notes/{task_id}` | 读取或保存任务笔记 |
| POST | `/api/modules/{id}/status`、`/api/options/{id}` | 模块状态与选修开关 |
| GET/POST | `/api/diagnostic/questions`、`/api/diagnostic/run` | 可选诊断 |
| POST | `/api/exercises/{id}/run` | 运行课程声明的练习 |
| GET | `/api/catalog` | 按系列与关键词筛选来源索引 |
| GET | `/api/ai/status` | provider/model/base_url/configured（不含 key） |
| POST | `/api/ai/session-key` | 设置本次服务内存 Key（不落盘/日志） |
| POST | `/api/ai/test` | 显式联网测试连接 |
| POST | `/api/ai/generate` | 用真实索引标题生成变式练习（严格 JSON） |
| POST | `/api/ai/review` | 评审当前可见内容（严格 JSON） |

写操作必须带当前 `Host`，若浏览器发送 `Origin` 也必须与当前本地地址一致。所有响应带 CSP、`X-Content-Type-Options` 与 `Referrer-Policy`。API 错误统一为 `{ "ok": false, "error": "..." }`。

文件白名单只来自当前任务 artifacts 与练习 `test_command` 声明的具体文件。目录型 artifact、`.learn`、绝对路径、路径穿越、通配符、符号链接越界均拒绝。

## 7. DeepSeek AI 助教边界

- 官方固定：`https://api.deepseek.com`，`POST /chat/completions`，`model=deepseek-chat`，Bearer 鉴权；使用 `urllib.request`，不引入 SDK。
- Key 优先服务器内存 session key，其次环境变量 `DEEPSEEK_API_KEY`；无 Key / 401 / 429 / 网络 / 超时 / 非 JSON / schema 错误都明确报错，无 fallback、不切换模型。
- Key 绝不写入磁盘 / progress / 日志；`GET /api/ai/status` 不返回 Key；前端用 password 输入框，仅保存到本次服务。
- 生成/评审提示词必须带当前小节 `catalog_refs` 的真实标题、`supplemental` 标记、目标、公开要求与完成状态；明确声明“索引仅代表标题知识范围，不代表视频正文”。
- 评审只发送当前可见练习内容、实践要求、相关索引标题与最近本地验证摘要（限长）；禁止发送其他文件、笔记、历史与环境变量。
- AI 只指导，不完成小节、不改代码；本地 validator 通过是完成小节的唯一依据。

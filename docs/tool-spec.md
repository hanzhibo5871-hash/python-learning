# learnctl 工具规格

## 1. 范围

`learnctl` 是一个 Python 3.11+ 的本地可视化学习工具，读取 `data/curriculum.json`，提供：

1. 4 阶段、29 任务、149 小节的真实实践路线（`code` / `json` / `text` / `command` / `env_action`，全部为输入型实践，没有任何选择题）。
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
  local_practice.py  编辑器作业路径、只创建缺失文件、磁盘文件验收
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

课程文件必须是 `schema_version: 3`，`curriculum_version: 3.0.0`。每个任务包含标题、学习目标、概念、前端对照、编码任务、产物、验收和至少 2 个小节；每个小节包含讲解、关键点、前端对照、示例、步骤与 `practice` 实践。`practice.kind` 只允许 `code` / `json` / `text` / `command` / `env_action`：

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

`tasks` 只使用 `todo`、`in_progress`、`done`；`modules` 与 `module_decisions` 只使用 `learn`、`practice`、`mastered`。当前课程为 curriculum 3.0.0 / schema 3：D01 → D02-D07 Python 语法 → D08-D17 常用开发 → D18-D24 真实项目 → D25-D29 AI / Agent。schema 1 或旧的 `courses` / `course_decisions` 直接报错，不自动迁移。读取旧课程版本时保留未知历史字段，但 D02-D28 的旧小节完成和旧 done 状态不能冒充 v3；D01 只在环境证据仍有效时保留。后端按任务与小节顺序门禁 validate/done，直接 URL 只能查看锁定说明。

## 3. CLI 契约

```powershell
python -m learnctl today [--json]
python -m learnctl lesson [TASK] [--json]
python -m learnctl practice prepare <TASK> <SECTION> [--json]
python -m learnctl practice check <TASK> <SECTION> [--json]
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

D07 起 `practice prepare` 原子创建缺失的正式作业文件，保留已有本地文件；首次创建使用课程起始内容，旧网页草稿保留供自行复制。`practice check` 只从声明路径读取磁盘文件，不接收任意路径；运行原有验证器，通过才登记小节完成，不覆盖源文件、不自动标记任务完成。缺失文件、前置未完成、验证期间文件变化均明确报错。连续项目使用原 `project_file`，其余文件置于 `learner_workspace/lessons/<TASK>/<SECTION>/`。

`GET /api/tasks/<TASK>/sections/<SECTION>/local-file` 读取当前本地作业；同路径 `POST` 准备文件；原 `POST .../validate` 使用 `{"source":"local_file"}` 时验收磁盘内容，忽略客户端 `content`。GET task 的 D07+ 小节返回 `local_file`，任务响应附项目根目录供编辑器定位。网页基础输入流程与历史记录保留。

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

任务页以“讲解与示例 / 动手练习”组织内容，D02–D09 包含 24 道独立草稿的离线加练（课程合计 149 小节）。基础必修题先验证顺序语句、stdin/stdout 和控制流，D04 开始要求函数。加练为 `optional: true`，不新增任务完成门槛，既有有效进度继续保留。

编辑停止 800ms 后自动保存草稿；切换前等待保存完成，保存失败展示后端错误并保留输入。验证成功和失败均持久化提交内容。`validate` 响应的 `learning_feedback` 为失败时的中文学习提示，仍保留真实 checks/stdout/stderr/exit_code。同一小节重复运行返回 409；小节验证、产物写入与进度证据在 `state_lock` 内串行执行。

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


### 全练习 AI 判题

验证/环境动作/实验/诊断/pytest HTTP 响应增加 `grading_token`。服务端凭据绑定本题、这份提交和真实本地结果；仅在进程内存保留 10 分钟、最多 128 份。`POST /api/ai/grade` 请求 `{ "grading_token": "...", "hint_level": 1 }`，提示等级为 1–3；旧 `/api/ai/review` 是别名。响应 `{ "ok": true, "feedback": {...} }`，包含 `analysis_version=2`、`requirements`（完整要求及状态/解释/引用）、`issues`（原因/依据/当前级提示）、`limitations`，以及兼容字段 `summary`、`reason`、`location`、`evidence`、`hint`、`hint_level`、`local_passed`、`advisory` 和 `conflict`。失败响应 `ok=false`，不伪造判题结论。

模型返回 `judgement`、`requirements`、`issues`、`limitations`；必要字段、类型和已有要求 ID 由服务器校验，遗漏要求标为待确认。展示证据由服务器从真实运行记录或已提供源码的准确行号回取，模型不能编造引用原文。无法核实、重复或超过四条的引用只省略该引用，并在分析边界中说明；没有可核实引用的要求标为待确认，保留原分析和提示。AI 文字作为复查建议展示，不再用正则逐句匹配输出或异常，文字偏差不阻断整份反馈。代码引用、公式及偶发答案片段按文本展示；敏感值先遮盖，不执行模型代码或 HTML。本地运行结果仍决定是否通过，AI 不修改学习记录。相同凭据的并发请求仍拒绝，三层提示复用一次缓存结果；网络失败可手动重试。

`POST /api/ai/variation-submit` 接收 `task_id`、`section_id`、`variation_id`、`content`，从服务器内存取得题意，返回语法检查与凭据。变式无可信行为测试，不计课程完成。命令不执行，Python 只编译检查语法。CLI `learnctl test <id> --ai` 用真实 pytest 输出及该次白名单测试文件进行同样的解析，保留本地退出码。未声明被测实现路径时明确不能定位实现源码，绝不根据 import 猜测并扫描其他文件。

配置 Key 后显式提交会自动联网判题。浏览器对编辑、切课、切题执行 AbortController 取消接收及版本失效检查；服务端已经发出的模型请求仍可能完成。未配置、API 错误、60 秒网络超时或协议无法识别均显示未完成 AI 判题；前端 65 秒终止接收。模型分析最多包含提交前 32768 字符，并明确截断标记。真实 API 质量与费用需单独验证，离线回归使用 mock。


正式作业多文件上下文只来自该小节 `workspace_deps`，当前编辑提交优先于磁盘同名文件；示例/补全/变式不继承原作业依赖。仅安全相对路径、UTF-8文本，拒绝隐藏配置、越界路径和链接。单文件最多32KiB、依赖合计64KiB；缺失、不可读、截断或验证期间改变的文件明确报告，不据此猜行号。上下文与证据仅在判题凭据内存记录中保留，不随下一题历史传递。`GET /api/ai/status` 的 `grading_analysis_version=2` 标识新版后端；已在运行的旧进程需由用户保存后安全重启，修改源码不会自动重启服务。


AI 判题校验修订：`grading_validation_revision=4` 标识宽松证据策略。引用无法核实时仍返回其余分析和渐进提示，AI 文字结论不再触发 `grading_evidence`。文字先遮盖敏感值，超长内容明确标注截断，前端统一转义为文本。必要协议解析、真实证据摘录、确定性测试权威和学习记录边界保持不变。

`GET /api/ai/grading-diagnostics` 返回最近失败的有界内存元数据：诊断编号、版本、分类、固定字段路径和规则名，最多 32 条、10 分钟过期。不含草稿、模型回复、密钥、grading_token 或私人配置。失败响应的 `diagnostic_id` 与该记录关联；该读取不调用模型、不写学习进度。

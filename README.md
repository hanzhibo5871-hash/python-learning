# learnctl

`learnctl` 是一个面向 Python 零基础学习者的本地学习工作台。它读取 `data/curriculum.json`（curriculum 3.0.0、schema 3），提供 4 阶段、29 任务、156 个教学与实践小节，其中包含 24 道离线加练题。先学习 D02-D07 基础语法，再学习 D08-D17 常用开发，随后从零制作 D18-D24 的 task-manager，最后进入 D25-D29 AI / Agent。所有练习均需自己输入，使用本地验证反馈修改；AI 助教为可选功能。

原始 131 个来源条目只保存在 `source_catalog` 中，作为知识范围标题索引；工具不会下载、抓取或播放来源，也不把打开来源作为完成条件。FastAPI、SQLite、asyncio、测试、配置/日志/CLI、JSON 工程实践与 DeepSeek API 等索引缺口以 `supplemental` 标记为真实开发补充，索引标题只作知识范围，不代表视频正文。

本轮 D05–D28 逐节审核与旧→新映射见 [课程审核清单](docs/course-audit.md)。D29 用离线模型讲只读工具、有限循环和可复核交付；新增任务不重置已有 v3 学习记录。

## 实践优先版：更少说明，更多可运行代码

全部 **29 个任务、156 个小节**使用短规则与独立作业布局；完整原理保留在折叠参考中。
新增 **115 张可运行的前置知识卡、230 道补全小练习**（含加练小节）。每道练习的参考输出实际执行验证，未修改起始代码不能直接通过。补全练习与正式作业有独立编辑器，运行示例不会覆盖你的答案，也不记为课程通关。

结果区区分 **测试输入、预期结果、实际返回值、print 输出、异常**。正确抛出题目要求的异常也算通过；程序仅退出成功不代表逻辑正确。D04 首次面积练习只练函数返回，D06 再给同一函数增加异常校验；D03 先提供 and/or/not 和 raise 的小例子。

本次保留原来的任务、小节 ID 和课程版本号，另记 `meta.practice_first_revision=2`，不会删除 `.learn`、已有草稿或项目产物。历史完成记录保留，不会把旧记录伪装成新练习也已验证；新增补全题可用于复习。

实验是本机 Python 进程，**不是安全沙箱**：临时目录、32 KiB 源码、5 秒和输出量限制只用于控制误操作；不要运行不可信代码或填写真实密钥。命令、HTML 和多文件片段不在这个按钮里执行。HTML/真实项目仍使用已有工作区与 D24 集成验收。

详见 [学习路径](docs/learning-path.md) 与 [实践优先版维护说明](docs/practice-first.md)。

## 最短启动

需要 Python 3.11 或更高版本。在 Windows 中双击仓库根目录的 `start_learning.bat`；也可以在项目根目录运行：

```powershell
python -m learnctl serve --open
```

打开 D01 后，先写一句你想用 Python 做什么，再按顺序点击“检测我的环境”“创建项目专用环境（.venv）”“安装学习工具与测试依赖”“检查环境是否准备完成”。每步查看页面报告，全部通过后在底部填写证据并标记 D01 完成。安装依赖可能需要联网。

## 常用命令

```powershell
python -m learnctl today --json
python -m learnctl lesson D02 --json
python -m learnctl progress
python -m learnctl progress mark D02 --status done --evidence "本地验证通过"
python -m learnctl progress module py-basics --status practice
python -m learnctl progress option langchain-cloud --enabled
python -m learnctl diagnose --json                # 可选工具，非主线前置
python -m learnctl test form                      # 运行课程声明的 learner_tests/*.py
python -m learnctl serve --open
```

任务状态为 `todo`、`in_progress`、`done`；知识模块状态为 `learn`、`practice`、`mastered`。任务改为 `done` 时必须提供证据，且全部前置任务和前置阶段已完成。小节验证通过才会记录完成，任务不会自动完成。

## 实践与验证

**基础完成后转入本地编辑器。** D01–D06 保留网页入门练习；D07 起正式作业改为编辑真实文件，网页提供讲解、复习和验证反馈。课程知识顺序、题目契约与历史进度保持不变，补全题不再作为后续课程的默认主流程。

用编辑器打开本项目目录，在终端激活项目环境（PowerShell：`.\.venv\Scripts\Activate.ps1`），然后：

```powershell
python -m learnctl practice prepare D07 D07-import
# 打开 learner_workspace/lessons/D07/D07-import/main.py，修改并保存
python -m learnctl practice check D07 D07-import
```

`prepare` 只创建缺失文件，已有文件不会覆盖；首次创建使用课程起始内容，旧网页草稿保留供自行复制。`check` 读取指定本地文件并运行原有验收，成功才记录小节完成；缺文件直接报错，不改用网页草稿。网页也可点击“准备本地作业文件”和“验证已保存文件并 AI 判题”。全部必修通过后，继续用 `progress mark` 或网页填写证据完成任务。

D07–D17、D25–D28 的独立作业在 `learner_workspace/lessons/<任务>/<小节>/`；带真实产物声明的 D18–D24 和 D29 使用原有 `learner_workspace/task-manager/`。后续小节直接编辑同一文件，验收只读取，不回写旧内容。函数文件只定义函数时直接运行没有输出是正常的；测试夹具由 `practice check` 提供，真实项目依赖必须由你按课程完成。

入门阶段建议每次完成一个小节：在“讲解与示例”中预测输出，再进入“动手练习”补全代码。D02/D03 先写顺序语句、判断和循环，D04 才开始系统编写函数。D07 起优先完成编辑器中的独立作业，需要时再展开示例、知识卡和补全题。JavaScript 对照收在可选说明里。

D02–D09 每个任务提供 3 道“加练”题：输入转换与小票、运费与循环、函数、购物车统计、异常边界、数据对象、UTF-8/JSON、命令行。加练保存独立草稿与完成记录，可重复验证，不增加主线完成门槛。工具会自动向 `input()` 提供题目约定的输入；在终端运行同一程序时需自己键入输入。

基础阶段的网页编辑器停止输入后自动保存，切换小节或任务会先等待保存；页面显示保存状态。支持 Ctrl+S 保存、Ctrl+Enter 验证。重置需要确认；验证失败会展示真实输出、期望值与实际值，以及常见 Python 错误的中文提示。通过后仍需自己填写任务完成证据。

每个小节都是输入型实践：

- `code`：写代码并运行本地验证（服务端私有 validator，检查函数与输出）。
- `json`：配置/API 契约，确定性解析校验。
- `text`：onboarding / 需求 / 复盘。
- `command`：只理解命令文本，绝不执行你输入的命令。
- `env_action`：D01 固定动作（检测环境 / 创建项目专用环境 / 安装依赖 / 最终检查）。

D01–D06 任务页提供 **保存草稿 / 运行并验证 / 重置为起始内容**。D07 起任务页提供本地文件准备与验证；验收结果同步到原有进度及 `.learn/lesson-submissions/`。失败保留文件，重复通过幂等。本地验证只在本机执行代码，服务仅绑定 `127.0.0.1`。

### 连续项目（D18-D24）

D18 到 D24 串联为一个真实对等交付项目（任务管理器 Task Manager），产物统一写入 `learner_workspace/task-manager/`，共 **15 个真实产物文件**：

- D18 需求与契约：`docs/requirements.md` + `contract.json`
- D19 工程配置：`pyproject.toml` + `taskproj/__init__.py` + `taskproj/config.py` + `taskproj/main.py` + 项目 `README.md`
- D20 数据库层：`taskproj/db.py`（SQLite CRUD，`D20-crud` 在 `D20-init` 基础上继续编辑同一文件）
- D21 API 层：`taskproj/api.py`（FastAPI 路由，`D21-errors` 在 `D21-routes` 基础上继续编辑同一文件）
- D22 测试：`tests/test_project.py` + `tests/test_api.py`
- D23 CLI 与网页：`taskproj/cli.py` + `taskproj/static/index.html`
- D24 交付与复盘：`docs/runbook.md` + `docs/review.md`（从零重建全部交付物 + 验收检查）

```text
learner_workspace/task-manager/
├── README.md
├── contract.json
├── pyproject.toml
├── docs/
│   ├── requirements.md
│   ├── runbook.md
│   └── review.md
├── taskproj/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── db.py
│   ├── api.py
│   ├── cli.py
│   └── static/
│       └── index.html
└── tests/
    ├── test_project.py
    └── test_api.py
```

**产物如何生成与继续编辑。** 先准备本节真实文件，在本地编辑器编写、保存，再用 `practice check` 或网页文件验证验收。多个小节涉及同一文件时继续编辑原文件；准备动作保留已有内容，验收不覆盖它。后续小节读取声明的真实依赖，缺文件则失败。任务页仍保留项目文件区，显示已声明文件及其创建状态。

**在编辑器终端运行项目。** 小节验收在学习工具根目录运行；真实项目命令则在 `learner_workspace/task-manager/` 下运行：

- 运行测试：`python -m pytest -q tests/test_project.py tests/test_api.py`
- 启动 API：`python -m uvicorn taskproj.api:app --reload` 后访问 `http://127.0.0.1:8000/`
- 使用 CLI：`python -m taskproj.cli add 买牛奶 && python -m taskproj.cli list`
- D24 标记完成时触发**项目验收**自动检查（文件完整性、pytest 通过、SQLite CRUD、FastAPI 路由、CLI 子命令），不通过则拒绝标记任务为 done。

**保存文件不等于完成小节。** 编辑器保存或网页文件区保存后，都须验证已保存文件；CLI 与网页使用同一个验证器和前置门禁。验证成功记录小节完成，D24 仍保留完整项目验收。

## 本地可视化工作台

```powershell
python -m learnctl serve --host 127.0.0.1 --port 8765 --open
```

工作台使用 Python 标准库 HTTP 服务和随包分发的原生 HTML/CSS/JS，不需要 Node、CDN、数据库、账号或联网。可以：

- 在仪表盘查看阶段进度、今日任务与知识模块。
- 打开任务页阅读课程、完成实践、保存草稿、运行本地验证、编辑白名单产物文件与笔记。
- 在**项目文件区**里直接编辑 `learner_workspace/task-manager/` 的真实产物文件（`保存项目文件` 经白名单接口原子写回），并在小节页看到“本节真实产物”提示与已落盘状态。
- 在来源索引中按系列和关键词检索 131 个真实标题。
- 从诊断页提交 D1-D5 答案（可选，非主线前置）。

## AI 助教（可选）

AI 助教默认且唯一的 provider 为 DeepSeek 官方 API（`https://api.deepseek.com`，`deepseek-chat`，Bearer 鉴权，`urllib` 实现，无 SDK）。无 Key 也能完成全部固定课程与本地验证。配置 Key 后，点击正式作业验证、补全练习运行、示例实验或环境动作会自动继续 AI 判题。页面会说明联网行为。

- Key 优先保存在本次服务内存，其次读取环境变量 `DEEPSEEK_API_KEY`；绝不写磁盘、不进日志。
- `GET /api/ai/status` 不返回 Key；前端用 password 输入框。
- 点击提交/运行发送当前题意、完整要求、本课教学规则、当前提交和本次真实运行证据。多文件作业仅读取本题声明的依赖；提交时保存内存快照，不扫描其他题目、笔记、历史或私密配置。未配置不发请求，页面明确显示 AI 未配置。AI 判题可能产生 DeepSeek API 费用。
- 判题覆盖全部 156 小节（含 24 道加练）、230 道补全题及示例实验。JSON、文本、命令说明、环境动作和项目作业均使用各自的本地验证结果。服务端提供短期判题凭据，拒绝客户端伪造的测试结果；不发送其他文件、笔记、历史、环境变量、私有 validator 或补全题参考代码。
- AI 针对当前作业逐项核对要求，给出本题专属的错误原因、代码/运行证据和渐进提示。提示词优先解析与引导，尽量不给完整答案；代码引用、公式或偶发答案片段不再导致整次反馈失败。所有模型文字按普通文本转义显示，不执行其中的代码或 HTML，敏感值继续遮盖。三层提示共用同一次分析，不重复调用模型。
- AI 不能覆盖客观测试失败，也不能撤销本地通过；冲突时以本地结果为准。AI 不改代码、不写完成记录。未配置、网络失败或超时不假装通过；异常协议和无法核实的引用/运行结论仍不展示。失败诊断只在内存保留最近 32 条的固定字段和规则名，10 分钟过期，不保存草稿、模型原文、密钥或判题凭据。
- 双击不重复提交；修改输入会使旧结果失效，切题/切课停止接收迟到结果。浏览器取消不能撤回服务端已发出的模型请求。凭据仅在服务内存中保存，10 分钟过期，最多 128 份；刷新后需重新运行，API Key 不落盘。
- 变式题有独立编辑器，按服务端保存的变式题意判题；只检查 Python/JSON 语法，不执行变式命令，没有可信行为测试时明确标注 AI 仅作建议，不计课程完成。
- 可选诊断页同样提供 AI 原因引导。旧 pytest API 返回 `grading_token`，可交给 `POST /api/ai/grade`；CLI 用 `python -m learnctl test <exercise_id> --ai` 显式启用（读取环境变量 Key），保留 pytest 退出码。仅分析本次测试输出，不扫描工作区代码。旧 `/api/ai/review` 对正式作业也要求该凭据；变式评审仍可按绑定 ID 提交。
- 当前课时助教默认简洁中文，先回答问题，必要时才给短代码；明确要求详细时再展开。课程目标、实践规则、前置卡片和起始代码由服务端按当前小节读取，不采信客户端伪造的课程正文。
- 提问会携带当前作业最多 8000 字符（D07 起读取已保存的本地文件）、本课时最近验证摘要，以及最近 3 轮（6 条）成功对话。历史按完整轮次保留，总计最多 12000 字符；不会读取其他文件或发送隐藏参考答案。
- 对话仅存在当前浏览器内存，按任务和小节隔离；刷新页面或清空对话可重新开始。失败问题保留在输入框供重试，不加入历史；重复点击不会重复请求，切换课时或清空后迟到的回答不会串入新会话。


## 数据与状态

```text
learnctl/                    CLI 与工作台源码
data/curriculum.json         schema 3、curriculum 3.0、131 条来源索引、4 阶段 29 任务 156 小节
docs/learning-path.md        4 阶段学习契约
docs/tool-spec.md            CLI、数据、API 与 AI 边界规格
tool_tests/                  learnctl 自身测试
learner_tests/               用户逐步创建的练习测试（不随工具提交）
.learn/progress.json         本地进度，首次写入时创建
.learn/lesson-submissions/   小节草稿（原子保存）
.learn/notes/                任务笔记
.learn/diagnostic-report.json 最近一次诊断报告
```

状态文件使用 schema 2。schema 1 或旧的 `courses` / `course_decisions` 直接报错，不做迁移；课程版本升级到 3.0.0 时，读取旧状态会保留未知字段、诊断、evidence、tests 等历史信息，但清空 D02-D28 的旧小节完成断言并将旧 done 降为 in_progress；D01 的有效环境证据可以保留。迁移只在内存执行，下一次正常保存才持久化。

`python -m pytest` 只运行 `tool_tests/`。`learnctl test` 只执行课程 JSON 声明的具体 `learner_tests/*.py` 文件，拒绝目录、其他路径、无目标命令和 pytest 额外选项；测试退出码原样返回。

工具实现的是本地工作台，不实现数据库服务、远程服务、来源抓取或自动答案；所有工具状态都在本地 JSON 中。

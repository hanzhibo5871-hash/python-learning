# learnctl

`learnctl` 是一个面向 Python 零基础学习者的本地学习工作台。它读取 `data/curriculum.json`（curriculum 3.0.0、schema 3），提供 4 阶段、28 任务、146 个教学与实践小节，其中包含 24 道离线加练题。先学习 D02-D07 基础语法，再学习 D08-D17 常用开发，随后从零制作 D18-D24 的 task-manager，最后进入 D25-D28 AI。所有练习均需自己输入，使用本地验证反馈修改；AI 助教为可选功能。

原始 131 个来源条目只保存在 `source_catalog` 中，作为知识范围标题索引；工具不会下载、抓取或播放来源，也不把打开来源作为完成条件。FastAPI、SQLite、asyncio、测试、配置/日志/CLI、JSON 工程实践与 DeepSeek API 等索引缺口以 `supplemental` 标记为真实开发补充，索引标题只作知识范围，不代表视频正文。

## 实践优先版：更少说明，更多可运行代码

全部 **28 个任务、122 个小节**使用短规则与独立作业布局；完整原理保留在折叠参考中。
新增 **39 张可运行的前置知识卡、124 道补全小练习**。每道练习的参考输出实际执行验证，未修改起始代码不能直接通过。补全练习与正式作业有独立编辑器，运行示例不会覆盖你的答案，也不记为课程通关。

结果区区分 **测试输入、预期结果、实际返回值、print 输出、异常**。正确抛出题目要求的异常也算通过；程序仅退出成功不代表逻辑正确。D04 首次面积练习只练函数返回，D06 再给同一函数增加异常校验；D03 先提供 and/or/not 和 raise 的小例子。

本次保留原来的任务、小节 ID 和课程版本号，另记 `meta.practice_first_revision=1`，不会删除 `.learn`、已有草稿或项目产物。历史完成记录保留，不会把旧记录伪装成新练习也已验证；新增补全题可用于复习。

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

零基础建议每次完成一个小节：在“讲解与示例”中预测输出，再进入“动手练习”补全代码。D02/D03 先写顺序语句、判断和循环，D04 才开始系统编写函数。JavaScript 对照收在可选说明里，不要求先懂前端。

D02–D09 每个任务提供 3 道“加练”题：输入转换与小票、运费与循环、函数、购物车统计、异常边界、数据对象、UTF-8/JSON、命令行。加练保存独立草稿与完成记录，可重复验证，不增加主线完成门槛。工具会自动向 `input()` 提供题目约定的输入；在终端运行同一程序时需自己键入输入。

编辑器停止输入后自动保存，切换小节或任务会先等待保存；页面显示保存状态。支持 Ctrl+S 保存、Ctrl+Enter 验证。重置需要确认；验证失败会展示真实输出、期望值与实际值，以及常见 Python 错误的中文提示。通过后仍需自己填写任务完成证据。

每个小节都是输入型实践：

- `code`：写代码并运行本地验证（服务端私有 validator，检查函数与输出）。
- `json`：配置/API 契约，确定性解析校验。
- `text`：onboarding / 需求 / 复盘。
- `command`：只理解命令文本，绝不执行你输入的命令。
- `env_action`：D01 固定动作（检测环境 / 创建项目专用环境 / 安装依赖 / 最终检查）。

任务页提供 **保存草稿 / 运行并验证 / 重置为起始内容** 三个按钮。草稿原子保存到 `.learn/lesson-submissions/`；验证失败保留草稿，重复通过幂等。本地验证只在本机执行代码，服务仅绑定 `127.0.0.1`，不会对外发送。

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

**产物如何生成与继续编辑。** 每个产物小节通过服务端本地验证后，其内容会被**原子写入**对应工作区文件（`原子落盘`，只在验证通过后写入，失败不覆盖）；后续小节读取已写入的真实文件作为依赖脚手架，不再使用隐藏参考实现。任务页会显示**项目文件区**面板，列出全部已声明文件及其创建状态：已创建文件可直接点开编辑，未创建文件也可打开空白编辑器。

**在网页上运行与验收。** 除了在课程小节里运行本地验证，你还可以在项目根目录 `learner_workspace/task-manager/` 下：

- 运行测试：`python -m pytest -q tests/test_project.py tests/test_api.py`
- 启动 API：`python -m uvicorn taskproj.api:app --reload` 后访问 `http://127.0.0.1:8000/`
- 使用 CLI：`python -m taskproj.cli add 买牛奶 && python -m taskproj.cli list`
- D24 标记完成时触发**项目验收**自动检查（文件完整性、pytest 通过、SQLite CRUD、FastAPI 路由、CLI 子命令），不通过则拒绝标记任务为 done。

**网页文件区的手动编辑只是继续编辑，不是完成依据。** 工作台的项目文件区提供 `保存项目文件` 按钮，通过后端白名单接口 `PUT /api/workspace/files/<path>` 把编辑器内容原子写回工作区文件。它只用于你在验证通过后继续打磨真实产物——手动保存**不会自动完成任何章节**；完成章节的唯一依据仍是服务端本地验证通过。未创建的文件也能打开空白编辑器保存，但工作台会提示你优先按课程章节完成验证以生成真实产物。

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

AI 助教默认且唯一的 provider 为 DeepSeek 官方 API（`https://api.deepseek.com`，`deepseek-chat`，Bearer 鉴权，`urllib` 实现，无 SDK）。无 Key 也能完成全部固定课程与本地验证。

- Key 优先保存在本次服务内存，其次读取环境变量 `DEEPSEEK_API_KEY`；绝不写磁盘、不进日志。
- `GET /api/ai/status` 不返回 Key；前端用 password 输入框。
- 只有你显式点击“测试连接 / 发送问题 / 生成变式练习 / 评审我的练习”才会联网。
- 评审只发送当前可见练习内容、实践要求、相关索引标题与最近本地验证摘要；不发送其他文件、笔记、历史与环境变量。
- AI 只指导，不改代码、不完成小节；本地 validator 通过才是完成小节的唯一依据。
- 当前课时助教默认简洁中文，先回答问题，必要时才给短代码；明确要求详细时再展开。课程目标、实践规则、前置卡片和起始代码由服务端按当前小节读取，不采信客户端伪造的课程正文。
- 提问会携带当前编辑器最多 8000 字符、本课时最近验证摘要，以及最近 3 轮（6 条）成功对话。历史按完整轮次保留，总计最多 12000 字符；不会读取其他文件或发送隐藏参考答案。
- 对话仅存在当前浏览器内存，按任务和小节隔离；刷新页面或清空对话可重新开始。失败问题保留在输入框供重试，不加入历史；重复点击不会重复请求，切换课时或清空后迟到的回答不会串入新会话。


## 数据与状态

```text
learnctl/                    CLI 与工作台源码
data/curriculum.json         schema 3、curriculum 3.0、131 条来源索引、4 阶段 28 任务 146 小节
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

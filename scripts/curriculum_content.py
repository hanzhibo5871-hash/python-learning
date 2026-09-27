# -*- coding: utf-8 -*-
"""learnctl 新课程内容数据。

本文件是 data/curriculum.json 的内容来源：由 scripts/build_curriculum.py 装配后生成。
内容规范：
- 全部 section 使用 practice（code/json/text/command/env_action），没有任何选择题。
- catalog_refs 只能引用 data/curriculum.json 中真实存在的 source_catalog id。
- 索引缺口（FastAPI/SQLite/asyncio/测试/配置/日志/CLI/JSON 工程实践/DeepSeek API 等）
  的 section 与 module 必须 supplemental=True 并给出 supplemental_note。
"""

from __future__ import annotations

from typing import Any


def _section(
    sid: str,
    title: str,
    refs: list[str],
    practice: dict[str, Any],
    explanation: list[str],
    key_points: list[str],
    bridge: str,
    example: str,
    steps: list[str],
    *,
    supplemental: bool = False,
    note: str | None = None,
    example_language: str = "python",
) -> dict[str, Any]:
    section: dict[str, Any] = {
        "id": sid,
        "title": title,
        "catalog_refs": refs,
        "explanation": explanation,
        "key_points": key_points,
        "frontend_bridge": bridge,
        "example": {"language": example_language, "code": example},
        "steps": steps,
        "practice": practice,
    }
    if supplemental:
        section["supplemental"] = True
        section["supplemental_note"] = note or "本节为真实开发补充：原 131 条来源索引标题未覆盖本节主题，不得把索引标题当作视频正文。"
    return section


def code(
    sid: str,
    title: str,
    refs: list[str],
    instructions: str,
    starter: str,
    expected: str,
    scenario: str,
    examples: list[str],
    hints: str,
    key_points: list[str],
    bridge: str,
    example: str,
    steps: list[str],
    *,
    file_name: str = "main.py",
    supplemental: bool = False,
    note: str | None = None,
    project_file: str | None = None,
    workspace_deps: list[str] | None = None,
) -> dict[str, Any]:
    explanation: list[str] = [
        "本节围绕“" + title + "”讲解：" + "；".join(key_points) + "。",
        "动手完成练习并观察运行结果，是理解这些概念最可靠的方式；验证失败时按提示与示例逐条排查。",
    ]
    practice: dict[str, Any] = {
        "kind": "code",
        "file_name": file_name,
        "scenario": scenario,
        "instructions": instructions,
        "starter_content": starter,
        "input_examples": [{"label": f"示例 {i + 1}", "value": item} for i, item in enumerate(examples)],
        "expected_behavior": expected,
        "hints": hints,
    }
    if project_file is not None:
        practice["project_file"] = project_file
    if workspace_deps is not None:
        practice["workspace_deps"] = workspace_deps
    return _section(sid, title, refs, practice, explanation, key_points, bridge, example, steps, supplemental=supplemental, note=note)


def _simple(
    kind: str,
    sid: str,
    title: str,
    refs: list[str],
    scenario: str,
    instructions: str,
    expected: str,
    hints: str,
    examples: list[str],
    key_points: list[str],
    bridge: str,
    example: str,
    steps: list[str],
    *,
    starter: str = "",
    supplemental: bool = False,
    note: str | None = None,
    project_file: str | None = None,
    workspace_deps: list[str] | None = None,
    example_language: str = "python",
) -> dict[str, Any]:
    explanation: list[str] = [
        "本节围绕“" + title + "”讲解：" + "；".join(key_points) + "。",
        "完成本节后，你应当能解释这些关键点；实践类练习由本地校验器给出确定性结果。",
    ]
    practice: dict[str, Any] = {
        "kind": kind,
        "scenario": scenario,
        "instructions": instructions,
        "starter_content": starter,
        "input_examples": [{"label": f"示例 {i + 1}", "value": item} for i, item in enumerate(examples)],
        "expected_behavior": expected,
        "hints": hints,
    }
    if project_file is not None:
        practice["project_file"] = project_file
    if workspace_deps is not None:
        practice["workspace_deps"] = workspace_deps
    return _section(
        sid, title, refs, practice, explanation, key_points, bridge, example, steps,
        supplemental=supplemental, note=note, example_language=example_language,
    )


def text_section(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _simple("text", *args, **kwargs)


def json_section(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _simple("json", *args, **kwargs)


def command_section(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _simple("command", *args, **kwargs)


def html_section(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("example_language", "html")
    return _simple("html", *args, **kwargs)


def project_section(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("example_language", "toml")
    return _simple("project", *args, **kwargs)


def env_action(sid: str, title: str, action: str, scenario: str, instructions: str, expected: str, hints: str) -> dict[str, Any]:
    practice: dict[str, Any] = {
        "kind": "env_action",
        "action": action,
        "scenario": scenario,
        "instructions": instructions,
        "starter_content": "",
        "input_examples": [],
        "expected_behavior": expected,
        "hints": hints,
    }
    return _section(
        sid,
        title,
        ["py-01", "py-03", "py-04", "py-05"],
        practice,
        ["环境是学习的前提：解释器版本、虚拟环境、包安装能力决定了后续每个任务能否真实运行。本节通过固定的检测与动作，把环境证据逐一落到你的项目目录，而不是依赖记忆。", "学习工具本身只在 127.0.0.1 本地运行，创建虚拟环境和安装依赖都是明确、可回放的命令；每一步完成前不会进入下一步。"],
        ["每次检测都读取当前真实状态", "固定动作不执行任意命令", "全部检查通过才完成环境章节"],
        "像前端确认 Node/npm 版本与 package-lock 一样，这里确认解释器、.venv 与依赖的真实状态。",
        "import sys\nprint(sys.executable)\nprint(sys.version_info[:2])",
        ["读取当前解释器路径", "对比主次版本是否 >= 3.11", "把结果当作后续所有任务的环境基线"],
    )


# --------------------------------------------------------------------------
# 模块（知识覆盖索引 + 真实开发补充）
# --------------------------------------------------------------------------

def _module(
    mid: str,
    title: str,
    topics: list[str],
    refs: list[str],
    *,
    supplemental: bool = False,
    note: str | None = None,
    optional_track_id: str | None = None,
) -> dict[str, Any]:
    module: dict[str, Any] = {
        "id": mid,
        "title": title,
        "topics": topics,
        "catalog_refs": refs,
        "default_status": "learn",
    }
    if optional_track_id is not None:
        module["optional_track_id"] = optional_track_id
    if supplemental:
        module["supplemental"] = True
        module["supplemental_note"] = note or "真实开发补充：原 131 条来源索引未覆盖本模块主题。"
    return module


PY_07 = [f"py-{i:02d}" for i in range(1, 8)]
PY_BASICS = [f"py-{i:02d}" for i in range(8, 29)]
PY_CONTROL = [f"py-{i:02d}" for i in range(29, 47)]
PY_FUNCTIONS = [f"py-{i:02d}" for i in range(47, 55)] + [f"py-{i:02d}" for i in range(68, 73)]
PY_COLLECTIONS = [f"py-{i:02d}" for i in range(55, 68)]
PY_FILES_ERRORS = [f"py-{i:02d}" for i in range(73, 84)]
PY_MODULES = [f"py-{i:02d}" for i in range(84, 88)]
LINUX = [f"linux-{i:02d}" for i in range(1, 20)]
AI_CONCEPTS = [f"ai-{i:02d}" for i in range(1, 6)]
AI_DEPLOY = [f"ai-{i:02d}" for i in range(6, 15)]
AI_APP_UI = [f"ai-{i:02d}" for i in range(15, 18)]
LANGCHAIN = [f"langchain-{i:02d}" for i in range(1, 6)]

MODULES: list[dict[str, Any]] = [
    _module("py-env", "Python 环境与工具链", ["解释器", "venv", "pip", "第一个程序", "IDE"], PY_07),
    _module("py-basics", "变量、类型与字符串", ["字面量", "变量", "类型转换", "运算符", "字符串与格式化"], PY_BASICS),
    _module("py-control", "条件与循环", ["if 分支", "while", "for", "range", "break 与 continue"], PY_CONTROL),
    _module("py-functions", "函数与作用域", ["函数定义", "参数", "返回值", "作用域", "lambda"], PY_FUNCTIONS),
    _module("py-collections", "数据容器", ["list", "tuple", "dict", "set", "切片", "推导式"], PY_COLLECTIONS),
    _module("py-files-errors", "文件与异常", ["文件编码", "读写", "异常概念", "异常捕获"], PY_FILES_ERRORS),
    _module("py-modules", "模块与包", ["导入语法", "自定义模块", "自定义包", "第三方包"], PY_MODULES),
    _module("linux-cli", "命令行基础", ["目录结构", "ls/cd", "文件操作", "查找与管道", "vim"], LINUX),
    _module("ai-concepts", "大模型概念与机制", ["大模型概念", "核心机制", "DeepSeek 与蒸馏"], AI_CONCEPTS),
    _module("ai-deploy", "本地模型部署", ["Ollama", "Windows/Mac/Linux 部署", "Chatbox", "Python 调用"], AI_DEPLOY),
    _module("ai-app-ui", "AI 应用界面", ["Streamlit API", "对话网页", "聊天机器人界面"], AI_APP_UI),
    _module("guide", "导学与学习路线", ["课程导学", "学习路线"], ["guide-01", "guide-02"]),
    _module("ending", "完结与复盘", ["课程完结"], ["ending-01"]),
    _module("langchain", "LangChain 与云模型选修", ["云架构", "LangChain", "APIKEY", "Streamlit 集成"], LANGCHAIN, optional_track_id="langchain-cloud"),
    _module("dev-path-json", "路径、编码与 JSON 工程实践", ["pathlib", "UTF-8", "json 读写"],
             [], supplemental=True,
             note="真实开发补充：原索引 py-73~py-80 仅覆盖文件读写，未覆盖 pathlib 路径对象、UTF-8 约定与 JSON 数据交换；这些是现代 Python 开发的常用能力。"),
    _module("dev-cli", "命令行程序与 argparse", ["argparse", "sys.argv", "退出码"],
             [], supplemental=True,
             note="真实开发补充：原索引 linux-01~linux-19 覆盖 shell 命令，未覆盖用 Python 编写命令行工具（argparse/退出码/子命令）。"),
    _module("dev-config-log", "配置、环境变量与日志", ["os.environ", ".env 解析", "logging"],
             [], supplemental=True,
             note="真实开发补充：原索引未覆盖应用配置（环境变量、.env 文件）与结构化日志（logging 模块）。"),
    _module("dev-http", "HTTP 与 FastAPI", ["urllib 客户端", "FastAPI 路由", "参数校验", "错误处理"],
             [], supplemental=True,
             note="真实开发补充：原索引未覆盖 HTTP 客户端编程与 FastAPI Web 框架；FastAPI 需要按官方文档安装，工具不会代为安装。"),
    _module("dev-testing", "单元测试与 API 测试", ["pytest", "mock", "测试隔离"],
             [], supplemental=True,
             note="真实开发补充：原索引未覆盖 pytest 单元测试与基于 mock 的 API 测试；pytest 已在开发依赖中。"),
    _module("dev-sqlite", "SQLite 标准库", ["sqlite3", "建表", "参数化 SQL", "事务"],
             [], supplemental=True,
             note="真实开发补充：原索引未覆盖数据库；本模块使用 Python 标准库 sqlite3，不需要额外数据库服务。"),
    _module("dev-asyncio", "asyncio 并发基础", ["async/await", "asyncio.run", "gather", "wait_for"],
             [], supplemental=True,
             note="真实开发补充：原索引未覆盖异步编程；本模块使用 Python 标准库 asyncio。"),
    _module("ai-api", "DeepSeek API 与提示词", ["DeepSeek API", "chat/completions", "提示词", "严格 JSON 输出"],
             [], supplemental=True,
             note="真实开发补充：原索引 ai-01~ai-05 介绍概念，未覆盖 DeepSeek 官方 API 的调用、鉴权与提示词工程；AI 功能始终由用户显式触发。"),
]

OPTIONAL_TRACKS: list[dict[str, Any]] = [
    {
        "id": "langchain-cloud",
        "title": "云模型与 LangChain 选修",
        "default_enabled": False,
        "enable_rule": "仅在用户明确选择云模型或 LangChain 时启用",
        "module_ids": ["langchain"],
        "affects_stage_completion": False,
        "affects_final_acceptance": False,
    }
]

# --------------------------------------------------------------------------
# 阶段
# --------------------------------------------------------------------------

STAGES: list[dict[str, Any]] = [
    {
        "id": "S1",
        "title": "真实环境与基础语法",
        "goal": "配置并验证本机 Python 开发环境，用真实程序掌握变量、类型、字符串、条件、循环、函数、容器、异常与模块组织，完成第一个业务程序。",
        "deliverable": "可复现的 .venv 环境、第一个商品表单清洗程序",
        "acceptance": ["环境检测全部通过", "D02 业务程序通过本地验证", "基础语法任务全部完成"],
        "prerequisites": [],
        "task_ids": ["D01", "D02", "D03", "D04", "D05", "D06", "D07"],
    },
    {
        "id": "S2",
        "title": "常用开发能力",
        "goal": "掌握路径与 JSON、命令行工具、配置与日志、HTTP 客户端、FastAPI、测试、SQLite 与 asyncio，形成独立开发真实功能的工具箱。",
        "deliverable": "一套覆盖文件/CLI/API/数据/并发的本地开发能力与对应验证",
        "acceptance": ["每个任务的核心函数通过本地验证", "能独立写一个 FastAPI 接口并配套测试", "SQLite 与 asyncio 有可运行示例"],
        "prerequisites": ["S1"],
        "task_ids": ["D08", "D09", "D10", "D11", "D12", "D13", "D14", "D15", "D16", "D17"],
    },
    {
        "id": "S3",
        "title": "真实普通项目",
        "goal": "从需求、契约、目录、配置、SQLite 数据层、FastAPI 接口、测试、CLI/网页演示到重建交付，独立做出一个可运行的本地任务管理项目。",
        "deliverable": "可运行、可测试、可重建的本地任务管理项目",
        "acceptance": ["项目可在新 venv 重建", "数据层与接口测试通过", "CLI 与网页演示可运行"],
        "prerequisites": ["S2"],
        "task_ids": ["D18", "D19", "D20", "D21", "D22", "D23", "D24"],
    },
    {
        "id": "S4",
        "title": "AI 应用",
        "goal": "掌握 DeepSeek 官方 API 的调用、鉴权、错误处理与提示词工程，完成一个可运行的 AI 应用项目，并用 mock 测试保证离线可验证。",
        "deliverable": "可运行、带 mock 测试的 AI 学习助手应用",
        "acceptance": ["DeepSeek 调用模块通过本地 mock 验证", "提示词包含真实索引标题与补充声明", "AI 应用可演示、可重建"],
        "prerequisites": ["S2"],
        "task_ids": ["D25", "D26", "D27", "D28"],
    },
]

# --------------------------------------------------------------------------
# 任务
# --------------------------------------------------------------------------

def _task(
    tid: str,
    stage: str,
    title: str,
    prereq: list[str],
    goal: str,
    modules: list[tuple[str, str]],
    concepts: list[str],
    bridge: str,
    coding: str,
    snippet: str,
    references: list[dict[str, str]],
    actions: list[str],
    artifacts: list[str],
    exercises: list[str],
    acceptance: list[str],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": tid,
        "stage_id": stage,
        "title": title,
        "prerequisites": prereq,
        "learning_goal": goal,
        "module_mapping": [{"module_id": mid, "relationship": rel} for mid, rel in modules],
        "concepts": concepts,
        "frontend_bridge": bridge,
        "coding_task": coding,
        "snippet": {"language": "python", "code": snippet},
        "references": references,
        "actions": actions,
        "artifacts": artifacts,
        "exercise_ids": exercises,
        "acceptance": acceptance,
        "lesson": sections,
    }


TASKS: list[dict[str, Any]] = []


# --------------------------------------------------------------------------
# S1
# --------------------------------------------------------------------------

TASKS.append(_task(
    "D01", "S1", "配置并验证你的 Python 开发环境",
    [],
    "配置本机 Python 开发环境并实时验证：解释器、项目根、.venv、pip、pytest 与可编辑安装全部就绪，为后续每个任务提供可复现的环境基线。",
    [("py-env", "depends_on")],
    ["解释器", "venv", "pip", "pytest", "可编辑安装"],
    "像前端确认 Node 版本、npm 与 lockfile 一样，这里把 Python 环境证据落成本地事实。",
    "运行环境检测，按需创建 .venv、安装开发依赖并运行环境验证，全部真实检查通过后完成本节。",
    "import sys\nprint(sys.executable)\nprint(sys.version_info[:2])",
    [{"title": "venv 官方文档", "url": "https://docs.python.org/3/library/venv.html"},
     {"title": "Python 安装指南", "url": "https://www.python.org/downloads/"}],
    ["完成 onboarding", "执行环境检测", "创建 .venv", "安装学习工具", "运行环境验证"],
    ["pyproject.toml", ".venv/"],
    [],
    ["当前 Python 版本 >= 3.11", "项目根存在 data/curriculum.json", ".venv 可创建且 pip 可用", "pytest 可在 .venv 导入", "learnctl 以可编辑方式安装到当前项目"],
    [
        text_section(
            "D01-onboarding", "今天要做什么、为什么",
            ["guide-01", "guide-02"],
            "首次进入 D01，你需要先理解学习路线和今天的目标，再动手配置环境。",
            "阅读本任务的说明和四个固定动作（检测、创建 .venv、安装、验证），用 2-4 句话写下：今天要配置什么、验证哪些能力、每步为什么需要。",
            "你的回答应覆盖环境配置的目标与步骤意义；建议包含“解释器、虚拟环境、pip、pytest”中的至少两个词。",
            "用你自己的话总结今天的任务，而不是照抄网页文字。",
            ["解释器与虚拟环境的关系", "pip 与 pytest 在环境里的角色"],
            ["环境是后续所有任务的前提", "检测让事实可见", "固定动作避免随意命令"],
            "前端项目先锁定 Node 版本再谈依赖；Python 同样先确认解释器与 venv。",
            "import sys\nprint(sys.version_info >= (3, 11))",
            ["写出今天的目标", "点出环境验证的价值", "说明每步的意义"],
        ),
        env_action(
            "D01-detect", "检测当前环境", "detect",
            "运行一次实时检测，查看当前解释器版本、项目根与 .venv 状态。",
            "点击“重新检测”。检测结果会显示：Python 可执行文件、版本、项目根、.venv 是否存在及其 pip/pytest 是否可用。",
            "返回当前环境的实时检测结果；检测成功且 Python 版本 >= 3.11 即通过本节。",
            "若版本不足 3.11，不要自动安装，按提示访问 python.org 或查看 Windows 官方安装指导。",
        ),
        env_action(
            "D01-create-venv", "创建 .venv 虚拟环境", "create_venv",
            "用当前解释器创建项目虚拟环境。",
            "点击“创建 .venv”。工具会执行：当前解释器 -m venv 项目/.venv。若 .venv 已存在，不会删除重建。",
            ".venv 创建成功且其 Python 可运行即通过本节。",
            "这一步隔离依赖，避免污染全局 Python。",
        ),
        env_action(
            "D01-install", "安装学习工具与测试依赖", "install",
            "把 learnctl 以可编辑方式安装到 .venv，并安装 pytest 等开发依赖。",
            "这是一个联网安装动作，需要二次确认。工具会执行：.venv 的 Python -m pip install -e \".[dev]\"。",
            "安装命令返回成功，且 .venv 中能导入 learnctl 与 pytest 即通过本节。",
            "安装需要网络；如果失败请检查网络，再重试。",
        ),
        env_action(
            "D01-verify", "运行环境验证", "verify",
            "用固定小程序与工具 smoke 验证整个环境。",
            "点击“运行环境验证”。工具会在 .venv 中执行固定小程序并检查 learnctl 可编辑安装是否指向当前项目。",
            "全部检查通过（版本、venv、pytest、可编辑安装）才通过本节。",
            "这是 D01 的最后一关：全部真实检查通过才算环境就绪。",
        ),
    ],
))

TASKS.append(_task(
    "D02", "S1", "第一个业务程序：商品表单清洗与含税金额",
    ["D01"],
    "用 Python 清洗前端表单的姓名、把价格转成 float 并计算含税金额，返回结构化 dict，同时覆盖空值、非法价格与异常。",
    [("py-basics", "depends_on")],
    ["变量", "字符串清洗", "类型转换", "返回值", "异常"],
    "前端表单拿到的是字符串；后端第一件事就是清洗与转换，这和你在前端做 trim/Number() 是同一件事。",
    "实现 clean_name、parse_price 与 process_form，把它们组合成可验证的业务程序。",
    'name = " 张三 "\nprice = "99.9"\ndata = {"name": name.strip(), "price": float(price)}\nprint(data)',
    [{"title": "内置类型官方文档", "url": "https://docs.python.org/3/library/stdtypes.html"}],
    ["清洗姓名", "转换价格", "计算含税金额", "处理异常"],
    ["exercises/form.py"],
    ["form"],
    ["姓名去掉首尾空白且非空", "价格字符串转 float", "含税金额正确", "空值与非法价格抛出明确异常"],
    [
        code(
            "D02-name", "变量与字符串清洗", ["py-10", "py-13", "py-16", "py-17"],
            "实现 clean_name(name: str) -> str：去掉首尾空白；若去掉后为空，抛出 ValueError('姓名不能为空')。",
            "def clean_name(name: str) -> str:\n    # 你的实现\n    ...",
            "clean_name(' 张三 ') 返回 '张三'；clean_name('   ') 抛出 ValueError。",
            "表单姓名可能带多余空格，甚至完全空白，必须清洗后校验。",
            ["clean_name(' 张三 ') -> '张三'", "clean_name('   ') -> ValueError"],
            "先 name.strip()，再判断空字符串。",
            ["字符串是不可变序列，strip() 返回新字符串", "先清洗再判断，顺序很重要", "校验失败用 raise 抛出异常"],
            "对应前端表单的 value.trim()，但 Python 需要显式赋值新字符串。",
            'name = " 张三 "\nclean = name.strip()\nprint(clean, bool(clean))',
            ["调用 str.strip()", "判断清洗后是否为空", "空则抛出 ValueError"],
        ),
        code(
            "D02-price", "类型转换与数值计算", ["py-12", "py-13", "py-15", "py-21"],
            "实现 parse_price(price) -> float：把字符串转成 float；无法转换时抛出 ValueError('价格必须是数字')。再实现 calculate_tax(price, rate=0.13) -> float，返回 round(price * rate, 2)。",
            "def parse_price(price: str) -> float:\n    # 你的实现\n    ...\n\ndef calculate_tax(price: float, rate: float = 0.13) -> float:\n    # 你的实现\n    ...",
            "parse_price('99.9') 返回 99.9；parse_price('abc') 抛出 ValueError；calculate_tax(100.0) 返回 13.0。",
            "表单提交的价格是字符串，必须在计算前完成类型转换并处理失败。",
            ["parse_price('99.9') -> 99.9", "parse_price('abc') -> ValueError", "calculate_tax(100.0) -> 13.0"],
            "float() 本身会抛 ValueError，捕获后转成自己的提示；金额用 round 保留两位。",
            ["float() 是类型转换函数，也是可能失败的调用", "失败时要给出业务含义明确的异常", "金额计算要处理浮点精度"],
            "对应前端的 parseFloat，但 Python 更严格地要求处理转换失败。",
            'price = float("99.9")\ntax = round(price * 0.13, 2)\nprint(price, tax)',
            ["调用 float() 转换", "捕获转换失败", "用 round 处理浮点精度"],
        ),
        code(
            "D02-form", "组合成完整业务函数", ["py-10", "py-50", "py-82"],
            "实现 process_form(name, price) -> dict：调用上面两个函数，返回 {\"name\": ..., \"price\": ..., \"rate\": 0.13, \"tax\": ..., \"amount\": ...}，其中 amount = round(price * (1 + rate), 2)。异常要能向上传递。",
            "def process_form(name: str, price: str) -> dict:\n    # 组合 clean_name / parse_price / calculate_tax\n    ...",
            "process_form(' 张三 ', '99.9') 返回 {\"name\": \"张三\", \"price\": 99.9, \"rate\": 0.13, \"tax\": 12.99, \"amount\": 112.89}；传入空名或非法价格会抛出 ValueError。",
            "一个函数串联清洗、转换与计算，让调用方只需要处理一个入口。",
            ["process_form(' 张三 ', '99.9') 返回含 name/price/tax/amount 的 dict", "process_form('', '10') 抛出 ValueError", "process_form('张三', 'abc') 抛出 ValueError"],
            "dict 是天然的业务返回值；先让各步骤分别通过，再组合。",
            ["函数组合让每一步可独立测试", "dict 作为统一返回结构", "异常逐层向上传递，不吞错"],
            "对应前端把表单数据整理成 payload 提交后端。",
            'def process_form(name, price):\n    return {"name": name.strip(), "price": float(price)}\n\nprint(process_form(" 张三 ", "99.9"))',
            ["组合两个函数", "构造业务 dict", "确认异常能向上传递"],
        ),
    ],
))

TASKS.append(_task(
    "D03", "S1", "条件与循环",
    ["D02"],
    "用 if/elif/else 处理分支，用 for/while 与 range 处理重复，理解 break 与 continue 的控制作用。",
    [("py-control", "depends_on")],
    ["if/elif/else", "for", "while", "range", "break", "continue"],
    "条件判断对应前端的 if/else 与 switch，循环对应数组的 map/filter 但更贴近底层。",
    "实现评分等级判断与求和、倒计时、查找等循环函数。",
    'for i in range(5):\n    if i % 2 == 0:\n        print(i)',
    [{"title": "控制流官方文档", "url": "https://docs.python.org/3/tutorial/controlflow.html"}],
    ["实现分支函数", "实现循环函数"],
    ["exercises/control.py"],
    [],
    ["分支边界正确", "循环结果正确", "break/continue 行为正确"],
    [
        code(
            "D03-grade", "条件分支与边界", ["py-29", "py-31", "py-33", "py-34"],
            "实现 score_level(score) -> str：90 及以上返回 '优秀'，75-89 返回 '良好'，60-74 返回 '及格'，0-59 返回 '不及格'；非数字或超出 0-100 抛出 ValueError。",
            "def score_level(score) -> str:\n    # 你的实现\n    ...",
            "score_level(95) == '优秀'，score_level(60) == '及格'，score_level(-1) 抛出 ValueError。",
            "评分规则是典型的分支业务，必须同时覆盖边界值。",
            ["score_level(95) -> '优秀'", "score_level(89) -> '良好'", "score_level(60) -> '及格'", "score_level(-1) -> ValueError"],
            "先判断类型与范围，再逐级比较；注意 60/75/90 的归属。",
            ["分支顺序决定边界归属", "先校验再比较避免意外", "isinstance(score, (int, float)) 判断类型"],
            "对应前端表单校验后渲染不同等级样式。",
            'def level(score):\n    if score >= 90:\n        return "优秀"\n    elif score >= 60:\n        return "及格"\n    return "不及格"',
            ["校验输入", "按阈值依次判断", "返回等级字符串"],
        ),
        code(
            "D03-loop", "循环、range 与中断", ["py-37", "py-40", "py-42", "py-46"],
            "实现：sum_even(n) -> int 返回 0..n 中偶数的和；countdown(n) -> list 返回 [n, n-1, ..., 0]；find_first(items, target) -> int 返回第一个等于 target 的下标，没有则返回 -1。",
            "def sum_even(n: int) -> int:\n    # 你的实现\n    ...\n\ndef countdown(n: int) -> list:\n    ...\n\ndef find_first(items: list, target) -> int:\n    ...",
            "sum_even(6) == 12（2+4+6），countdown(3) == [3,2,1,0]，find_first([1,2,3], 3) == 2，find_first([1,2], 9) == -1。",
            "循环是处理重复与查找的基础，break 用于提前终止。",
            ["sum_even(6) -> 12", "countdown(3) -> [3,2,1,0]", "find_first([1,2,3], 3) -> 2", "find_first([1,2], 9) -> -1"],
            "sum_even 用 range(n+1) 加 if；countdown 用 range(n, -1, -1)；find_first 用 enumerate 配合 return -1。",
            ["range 的 start/stop/step", "for + enumerate 同时取下标", "break 提前结束循环"],
            "对应前端 forEach 里手动找 index 的模式。",
            "def countdown(n):\n    return list(range(n, -1, -1))\n\nprint(countdown(3))",
            ["写 for 循环", "用 enumerate 取下标", "用 break/return 提前退出"],
        ),
    ],
))

TASKS.append(_task(
    "D04", "S1", "函数、参数与作用域",
    ["D03"],
    "掌握函数定义、默认参数、*args/**kwargs、返回值，以及局部变量与全局作用域的分隔。",
    [("py-functions", "depends_on")],
    ["def", "默认参数", "*args", "**kwargs", "return", "作用域"],
    "函数对应前端可复用的函数，但 Python 的参数与作用域规则更显式。",
    "实现带默认参数、可变参数与关键字参数的函数，并演示作用域。",
    'def greet(name, greeting="你好"):\n    return f"{greeting}，{name}"',
    [{"title": "函数官方文档", "url": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions"}],
    ["实现参数函数", "演示作用域"],
    ["exercises/functions.py"],
    [],
    ["默认参数生效", "可变参数拼接正确", "关键字参数转 dict", "作用域行为正确"],
    [
        code(
            "D04-params", "参数与返回值", ["py-47", "py-48", "py-49", "py-50", "py-69"],
            "实现：make_greeting(name, *, greeting='你好') -> str 返回 f\"{greeting}，{name}\"；join_all(*items) -> str 用 '、' 连接；describe(**kwargs) -> dict 原样返回 kwargs。",
            "def make_greeting(name, *, greeting='你好'):\n    # 你的实现\n    ...\n\ndef join_all(*items):\n    ...\n\ndef describe(**kwargs):\n    ...",
            "make_greeting('张三') == '你好，张三'；make_greeting('张三', greeting='早上好') == '早上好，张三'；join_all('a','b') == 'a、b'；describe(x=1) == {'x': 1}。",
            "位置参数、默认参数、仅限关键字参数、*args 与 **kwargs 各有分工。",
            ["make_greeting('张三') -> '你好，张三'", "join_all('a','b') -> 'a、b'", "describe(x=1) -> {'x': 1}"],
            "* 号后面的参数只能按关键字传；*args 收集元组，**kwargs 收集 dict。",
            ["默认参数让接口更宽容", "*args 收集位置参数为元组", "**kwargs 收集关键字参数为字典"],
            "对应前端剩余参数与 options 对象。",
            'def join_all(*items):\n    return "、".join(items)\n\nprint(join_all("a", "b"))',
            ["定义默认参数", "用 *args 收集", "用 **kwargs 收集"],
        ),
        code(
            "D04-scope", "作用域与返回值", ["py-43", "py-53", "py-52", "py-68"],
            "实现：make_counter() 返回一个函数，每次调用返回递增的数字（用 nonlocal）；calc_total(prices, discount=0) -> dict 返回 {\"subtotal\": 和, \"discount\": 折扣, \"total\": 折后}，金额保留两位。",
            "def make_counter():\n    count = 0\n    def inner() -> int:\n        nonlocal count\n        # 你的实现\n        ...\n    return inner\n\ndef calc_total(prices: list, discount: float = 0.0) -> dict:\n    # 你的实现\n    ...",
            "counter = make_counter(); counter() == 1，counter() == 2；calc_total([100, 50], 20) 返回 {\"subtotal\": 150.0, \"discount\": 20.0, \"total\": 130.0}。",
            "闭包依赖 nonlocal 修改外层变量；函数返回值是业务结果的标准出口。",
            ["make_counter() 每次 +1", "calc_total([100, 50], 20) 的 total == 130.0"],
            "nonlocal 声明后才能修改外部变量；round 保留两位小数。",
            ["nonlocal 修改闭包变量", "函数只通过返回值对外", "浮点金额统一 round"],
            "对应前端闭包与 useMemo 的返回值思路。",
            "def make_counter():\n    n = 0\n    def inner():\n        nonlocal n\n        n += 1\n        return n\n    return inner",
            ["定义闭包", "用 nonlocal 修改外层变量", "返回内部函数"],
        ),
    ],
))

TASKS.append(_task(
    "D05", "S1", "数据容器",
    ["D04"],
    "掌握 list、tuple、dict、set 的常用操作、切片与推导式，会按需选择容器。",
    [("py-collections", "depends_on")],
    ["list", "tuple", "dict", "set", "切片", "推导式"],
    "容器对应前端的数组与对象；Python 的 set/dict 语义更严格，切片是独有的便利。",
    "实现序列切片、字典聚合、集合去重与推导式函数。",
    'words = ["a", "b", "a"]\ncount = {w: words.count(w) for w in set(words)}\nprint(count)',
    [{"title": "数据结构官方文档", "url": "https://docs.python.org/3/tutorial/datastructures.html"}],
    ["实现序列与映射函数"],
    ["exercises/collections.py"],
    [],
    ["切片结果正确", "计数与去重正确", "推导式正确"],
    [
        code(
            "D05-sequence", "列表、元组与切片", ["py-55", "py-56", "py-57", "py-58", "py-59", "py-61"],
            "实现：first_last(seq) -> tuple 返回 (第一个, 最后一个)；reverse_slice(seq) -> list 用切片反转；middle(seq) -> list 返回去掉首尾后的列表。空序列抛出 ValueError。",
            "def first_last(seq):\n    # 你的实现\n    ...\n\ndef reverse_slice(seq):\n    ...\n\ndef middle(seq):\n    ...",
            "first_last([1,2,3]) == (1,3)；reverse_slice([1,2,3]) == [3,2,1]；middle([1,2,3,4]) == [2,3]。",
            "切片与下标是容器操作的基础；返回元组表达固定长度结果。",
            ["first_last([1,2,3]) -> (1,3)", "reverse_slice([1,2,3]) -> [3,2,1]", "middle([1,2,3,4]) -> [2,3]"],
            "seq[0] 与 seq[-1]；[::-1] 反转；[1:-1] 去首尾；先判断空。",
            ["下标与负下标", "切片 [start:stop:step]", "空序列先校验"],
            "对应前端 array[0] / array[array.length-1] / slice()。",
            "def first_last(seq):\n    if not seq:\n        raise ValueError(\"空序列\")\n    return (seq[0], seq[-1])",
            ["取首尾元素", "用切片反转", "去掉首尾"],
        ),
        code(
            "D05-mapping", "字典、集合与推导式", ["py-62", "py-63", "py-64", "py-66"],
            "实现：count_words(text) -> dict 统计每个词出现次数（按空格切分）；unique_keep_order(words) -> list 去重并保持首次出现顺序；merge_scores(*dicts) -> dict 合并多个分数字典。",
            "def count_words(text: str) -> dict:\n    # 你的实现\n    ...\n\ndef unique_keep_order(words: list) -> list:\n    ...\n\ndef merge_scores(*dicts) -> dict:\n    ...",
            "count_words('a b a') == {'a': 2, 'b': 1}；unique_keep_order(['a','b','a']) == ['a','b']；merge_scores({'x':1},{'x':2,'y':3}) == {'x':2,'y':3}（后者覆盖）。",
            "dict 适合按键聚合，set 适合去重，推导式让转换表达更紧凑。",
            ["count_words('a b a') -> {'a': 2, 'b': 1}", "unique_keep_order(['a','b','a']) -> ['a','b']", "merge_scores({'x':1},{'x':2,'y':3}) -> {'x':2,'y':3}"],
            "计数用 dict.get(key, 0)+1；去重用 set 判断是否见过同时 list 保序；合并用 update。",
            ["dict.get 提供默认值", "set 判重 + list 保序", "update 合并字典"],
            "对应前端 reduce 做计数、Set 去重。",
            'def count_words(text):\n    out = {}\n    for w in text.split():\n        out[w] = out.get(w, 0) + 1\n    return out',
            ["按键聚合", "set 去重", "字典推导式"],
        ),
    ],
))

TASKS.append(_task(
    "D06", "S1", "异常处理",
    ["D05"],
    "掌握 try/except/else/finally、常见异常类型与自定义异常，写稳的代码。",
    [("py-files-errors", "depends_on")],
    ["try/except", "else/finally", "ValueError", "自定义异常"],
    "异常对应前端 try/catch，但 Python 用异常表达更多业务失败。",
    "实现安全除法、整数解析与带自定义异常的记录校验。",
    'try:\n    value = int(input())\nexcept ValueError:\n    print("不是整数")',
    [{"title": "异常官方文档", "url": "https://docs.python.org/3/tutorial/errors.html"}],
    ["实现安全函数", "定义自定义异常"],
    ["exercises/errors.py"],
    [],
    ["异常被正确捕获", "自定义异常携带信息", "finally 执行"],
    [
        code(
            "D06-safe", "捕获与处理", ["py-81", "py-82", "py-83"],
            "实现：safe_divide(a, b) 返回 a/b，除零时返回字符串 '不能除以零'；read_int(value) 尝试 int(value)，失败返回 None。",
            "def safe_divide(a, b):\n    # 你的实现\n    ...\n\ndef read_int(value):\n    # 你的实现\n    ...",
            "safe_divide(6, 2) == 3.0；safe_divide(6, 0) == '不能除以零'；read_int('42') == 42；read_int('abc') is None。",
            "把可能失败的调用放进 try，明确告诉调用方失败形态。",
            ["safe_divide(6, 0) -> '不能除以零'", "read_int('42') -> 42", "read_int('abc') -> None"],
            "except ZeroDivisionError 与 except ValueError 分别捕获；except 后接 else/finally 组织清理逻辑。",
            ["异常类型精确匹配", "返回值约定失败形态", "finally 一定执行"],
            "对应前端 try/catch 并返回 null 的降级策略。",
            "def safe_divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return \"不能除以零\"",
            ["写 try/except", "捕获具体异常类型", "约定失败返回值"],
        ),
        code(
            "D06-custom", "自定义异常与校验", ["py-81", "py-82"],
            "定义 class InputError(ValueError)：pass；实现 validate_record(record) -> dict：name 为空抛 InputError('姓名不能为空')，age 非正数抛 InputError('年龄必须为正数')，否则返回原 dict。",
            "class InputError(ValueError):\n    pass\n\ndef validate_record(record: dict) -> dict:\n    # 你的实现\n    ...",
            "validate_record({'name': '张三', 'age': 20}) 返回原 dict；validate_record({'name': '', 'age': 20}) 抛 InputError；validate_record({'name': '张三', 'age': 0}) 抛 InputError。",
            "自定义异常让调用方可以精确捕获业务失败。",
            ["validate_record({'name': '张三', 'age': 20}) 原样返回", "空 name 抛 InputError", "age 0 抛 InputError"],
            "继承 ValueError 即可；校验失败时 raise InputError('中文消息')。",
            ["自定义异常继承基类", "业务校验集中在一处", "异常消息面向用户"],
            "对应前端抛出的业务错误对象。",
            "class InputError(ValueError):\n    pass\n\ndef validate(record):\n    if not record[\"name\"]:\n        raise InputError(\"姓名不能为空\")\n    return record",
            ["定义异常类", "编写校验逻辑", "抛出带消息的异常"],
        ),
    ],
))

TASKS.append(_task(
    "D07", "S1", "模块与包",
    ["D06"],
    "掌握 import、自定义模块、包结构、__main__ 守卫与标准库导入。",
    [("py-modules", "depends_on")],
    ["import", "自定义模块", "包", "__main__ 守卫", "标准库"],
    "模块对应前端拆分的 JS 文件，import 让代码可复用、可测试。",
    "写一个导入自定义模块的程序，并用 __main__ 守卫控制入口。",
    "from greetings import hello\nprint(hello(\"世界\"))",
    [{"title": "模块官方文档", "url": "https://docs.python.org/3/tutorial/modules.html"}],
    ["导入自定义模块", "使用 __main__ 守卫"],
    ["exercises/modules.py"],
    [],
    ["导入可用", "__main__ 守卫正确", "入口只在直接运行时执行"],
    [
        code(
            "D07-import", "导入自定义模块", ["py-84", "py-85"],
            "目录中已提供 greetings.py，其中定义 hello(name) -> str 返回 f\"你好，{name}\"。请写 main.py：从 greetings 导入 hello，调用 hello('世界') 并 print 结果。",
            "# 从 greetings 导入 hello，然后 print(hello(\"世界\"))\n# 你的实现\n...",
            "运行 main.py 输出“你好，世界”。",
            "import 让另一个文件里的函数可以直接复用。",
            ["运行 main.py 输出 '你好，世界'"],
            "注意导入路径：main.py 与 greetings.py 在同一目录时直接 from greetings import hello。",
            ["from ... import 导入具体函数", "模块名不加 .py", "同目录模块直接导入"],
            "对应前端 import { hello } from './greetings'。",
            "def hello(name):\n    return f\"你好，{name}\"",
            ["导入函数", "调用并输出", "确认运行结果"],
        ),
        code(
            "D07-main", "__main__ 守卫与包结构", ["py-85", "py-86"],
            "写 main.py：定义 run() -> str 返回 'ok'；用 if __name__ == '__main__': 守卫，在直接运行时调用 run() 并 print 结果；被 import 时不应自动打印。",
            "def run() -> str:\n    # 你的实现\n    ...\n\n# 你的守卫\n...",
            "直接运行 main.py 输出 'ok'；import main 后调用 main.run() == 'ok' 且 import 时不打印。",
            "__main__ 守卫让文件既可以是程序入口，也可以被安全导入。",
            ["直接运行输出 'ok'", "import main 不产生输出", "main.run() == 'ok'"],
            "if __name__ == '__main__': 下面写入口调用。",
            ["__name__ 在直接运行时是 '__main__'", "被导入时是模块名", "守卫保护入口逻辑"],
            "对应前端判断是否为主入口才挂载渲染。",
            "def run():\n    return \"ok\"\n\nif __name__ == \"__main__\":\n    print(run())",
            ["定义 run", "写 __main__ 守卫", "区分入口与导入"],
        ),
    ],
))

# --------------------------------------------------------------------------
# S2
# --------------------------------------------------------------------------

TASKS.append(_task(
    "D08", "S1".replace("S1", "S2"), "路径、UTF-8 与 JSON",
    ["D07"],
    "用 pathlib 处理路径，以 UTF-8 读写文件，用 json 完成数据交换。",
    [("dev-path-json", "depends_on"), ("py-files-errors", "knowledge_base")],
    ["pathlib", "read_text/write_text", "UTF-8", "json.loads/dumps"],
    "路径与数据文件是后端基本功；UTF-8 与 JSON 是前后端交换事实标准。",
    "实现读取 JSON 记录、统计并写回报告的函数。",
    'import json\nfrom pathlib import Path\n\ndata = json.loads(Path("records.json").read_text(encoding="utf-8"))',
    [{"title": "pathlib 官方文档", "url": "https://docs.python.org/3/library/pathlib.html"},
     {"title": "json 官方文档", "url": "https://docs.python.org/3/library/json.html"}],
    ["读取并统计", "写回报告"],
    ["automation/json_report.py"],
    [],
    ["读取 UTF-8 JSON", "统计正确", "报告可被 json.loads 读回"],
    [
        code(
            "D08-read", "读取与统计", ["py-73", "py-74", "py-75"],
            "目录中提供 records.json（UTF-8，内容为记录数组）。实现 load_records(path) -> list 读取并 json.loads；collect_stats(records) -> dict 返回 {\"count\": 条数, \"categories\": 去重后的分类列表}。",
            "def load_records(path) -> list:\n    # 你的实现\n    ...\n\ndef collect_stats(records: list) -> dict:\n    # 你的实现\n    ...",
            "load_records 读回列表；collect_stats 返回 count 与 categories。records.json 结构：{\"records\": [...]} 或数组。",
            "文件读写必须显式指定 UTF-8，避免不同系统的编码差异。",
            ["load_records('records.json') 返回列表", "collect_stats 的 count 与条数一致", "categories 不重复"],
            "用 Path(path).read_text(encoding='utf-8') 再 json.loads；读取失败时让 FileNotFoundError 自然抛出。",
            ["Path.read_text 显式 encoding", "json.loads 解析字符串", "统计结果结构清晰"],
            "对应前端 fetch JSON 后解析成对象。",
            'from pathlib import Path\nimport json\n\ndef load_records(path):\n    return json.loads(Path(path).read_text(encoding="utf-8"))',
            ["读取文件", "解析 JSON", "统计与去重"],
        ),
        code(
            "D08-write", "写回 JSON 报告", ["py-73", "py-77"],
            "实现 save_report(path, stats) -> None：把 stats 以 UTF-8、indent=2 写回 JSON 文件，并保证父目录存在。",
            "def save_report(path, stats) -> None:\n    # 你的实现\n    ...",
            "save_report 后文件可被 json.loads 读回且与传入一致。",
            "写文件要保证编码与目录，让后续步骤能直接读取。",
            ["写回后 json.loads 结果等于原 stats", "父目录自动创建"],
            "Path(path).parent.mkdir(parents=True, exist_ok=True) 后 write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')。",
            ["mkdir(parents=True) 创建目录", "ensure_ascii=False 保留中文", "indent=2 便于阅读"],
            "对应前端下载 JSON 文件的序列化。",
            'from pathlib import Path\nimport json\n\ndef save(path, data):\n    p = Path(path)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")',
            ["创建目录", "序列化 JSON", "写回文件"],
        ),
    ],
))

TASKS.append(_task(
    "D09", "S1".replace("S1", "S2"), "命令行工具",
    ["D08"],
    "用 argparse 编写命令行工具，处理参数、错误与退出码。",
    [("dev-cli", "depends_on"), ("linux-cli", "knowledge_base")],
    ["argparse", "sys.argv", "退出码", "--help"],
    "命令行工具是脚本与服务的基础入口，对应前端的 npm scripts。",
    "写一个带参数与校验的命令行程序。",
    'import argparse\n\nparser = argparse.ArgumentParser()\nparser.add_argument("--name", required=True)\nargs = parser.parse_args()',
    [{"title": "argparse 官方文档", "url": "https://docs.python.org/3/library/argparse.html"}],
    ["实现参数解析", "处理错误"],
    ["cli/greet.py"],
    [],
    ["参数生效", "缺少必填参数报错", "--help 可用"],
    [
        code(
            "D09-args", "argparse 参数解析", ["py-87", "linux-06"],
            "写 main.py：argparse 定义 --name（必填）与 --count（默认 1）。运行 python main.py --name 张三 --count 2 时打印两次“你好，张三”；--help 以退出码 0 输出帮助。",
            "import argparse\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser()\n    # 你的实现\n    ...\n\nif __name__ == \"__main__\":\n    main()",
            "python main.py --name 张三 --count 2 输出两行“你好，张三”；python main.py --help 退出码 0。",
            "argparse 自动生成帮助与错误消息，是命令行工具的标准做法。",
            ["--name 张三 --count 2 输出两行问候", "--help 退出码 0", "缺少 --name 退出码非 0"],
            "用 add_argument 定义参数，action 或 nargs 处理重复；type=int 做转换。",
            ["add_argument 定义参数", "type=int 转换", "parse_args 读取 sys.argv"],
            "对应前端 commander/yargs 的用法。",
            'import argparse\n\np = argparse.ArgumentParser()\np.add_argument("--name", required=True)\np.add_argument("--count", type=int, default=1)\nargs = p.parse_args()',
            ["定义参数", "读取参数", "输出结果"],
        ),
        code(
            "D09-errors", "参数错误与退出码", ["linux-06", "linux-15"],
            "扩展 main.py：--level 只允许 debug/info/warning，非法值由 argparse 报错；增加逻辑：count 必须 >= 1，否则打印错误并以退出码 2 退出。",
            "import argparse\nimport sys\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser()\n    parser.add_argument(\"--level\", choices=[\"debug\", \"info\", \"warning\"])\n    # 你的实现\n    ...\n\nif __name__ == \"__main__\":\n    main()",
            "python main.py --level nope 退出码 2 且 stderr 含“invalid choice”；count=0 时程序退出码 2 并输出中文错误。",
            "把参数校验交给 argparse，业务校验显式返回退出码。",
            ["--level nope 退出码 2", "count 非法时退出码 2"],
            "choices 参数直接限制取值；业务校验用 parser.error(...) 或 print + sys.exit(2)。",
            ["choices 限定枚举", "parser.error 统一报错", "非零退出码表达失败"],
            "对应命令行工具约定：非零退出码表示失败。",
            'parser.add_argument("--level", choices=["debug", "info", "warning"])\nargs = parser.parse_args()\nif args.count < 1:\n    parser.error("count 必须 >= 1")',
            ["限定取值", "业务校验", "返回非零退出码"],
        ),
    ],
))

TASKS.append(_task(
    "D10", "S1".replace("S1", "S2"), "配置与环境变量",
    ["D09"],
    "从环境变量与 .env 文件读取配置，提供默认值与类型转换。",
    [("dev-config-log", "depends_on")],
    ["os.environ", ".env", "默认值", "类型转换"],
    "配置不写死在代码里，对应前端的 .env 与 import.meta.env。",
    "实现读取环境变量与解析 .env 文件的两个函数。",
    'import os\n\ndef get(name, default):\n    return os.environ.get(name, default)',
    [{"title": "os.environ 官方文档", "url": "https://docs.python.org/3/library/os.html#os.environ"}],
    ["读取环境变量", "解析 .env"],
    ["config/env_config.py"],
    [],
    ["默认值生效", ".env 解析正确", "类型转换正确"],
    [
        code(
            "D10-env", "环境变量与默认值", ["linux-17", "py-10"],
            "实现：get_env(name, default=None) 读 os.environ，缺省返回 default；get_int_env(name, default) 转换 int，转换失败返回 default；get_bool_env(name, default) 把 'true'/'1' 视为 True。",
            "import os\n\ndef get_env(name, default=None):\n    # 你的实现\n    ...\n\ndef get_int_env(name, default):\n    ...\n\ndef get_bool_env(name, default):\n    ...",
            "get_env 返回环境变量；get_int_env('N', 5) 在未设置时返回 5；get_bool_env 解析布尔字符串。",
            "配置项经环境变量注入，便于在不同环境切换。",
            ["get_int_env('N', 5) 未设置时 -> 5", "get_bool_env('F','true') -> True", "get_env 返回字符串值"],
            "os.environ.get(name, default)；int() 用 try/except 兜底；bool 值手工映射字符串。",
            ["os.environ.get 提供默认", "int 转换失败兜底", "布尔字符串显式映射"],
            "对应前端的 process.env 与解析逻辑。",
            "import os\n\ndef get_int_env(name, default):\n    raw = os.environ.get(name)\n    try:\n        return int(raw)\n    except (TypeError, ValueError):\n        return default",
            ["读取环境变量", "类型转换", "失败兜底"],
        ),
        code(
            "D10-dotenv", "解析 .env 文件", ["linux-17", "py-74"],
            "实现 load_dotenv(path) -> dict：按行解析 KEY=VALUE，跳过空行与 # 注释，去掉首尾空白；重复键后者覆盖前者。",
            "def load_dotenv(path) -> dict:\n    # 你的实现\n    ...",
            "load_dotenv 返回键值 dict；文件不存在时返回空 dict。",
            ".env 是常见的本地配置载体；手写解析器必须处理注释与空白。",
            ["跳过注释与空行", "KEY=VALUE 拆分", "重复键后者覆盖"],
            "按行 split('=', 1)；rstrip() 处理行尾；用 with open 读取。",
            ["按行读取", "split('=', 1) 拆分", "跳过注释行"],
            "对应前端 dotenv 包的行为。",
            'def load_dotenv(path):\n    out = {}\n    try:\n        with open(path, encoding="utf-8") as f:\n            for line in f:\n                line = line.strip()\n                if not line or line.startswith("#"):\n                    continue\n                k, _, v = line.partition("=")\n                out[k.strip()] = v.strip()\n    except FileNotFoundError:\n        return {}\n    return out',
            ["读取文件", "过滤注释", "解析键值"],
        ),
    ],
))

TASKS.append(_task(
    "D11", "S1".replace("S1", "S2"), "日志",
    ["D10"],
    "用标准库 logging 输出结构化日志，配置级别、格式与文件输出。",
    [("dev-config-log", "depends_on")],
    ["logging", "级别", "Handler", "格式化"],
    "日志是排查线上问题的唯一线索，对应前端的 console 但可分级持久化。",
    "实现控制台日志与文件日志两个配置函数。",
    "import logging\n\nlogging.basicConfig(level=logging.INFO)\nlogging.info(\"服务已启动\")",
    [{"title": "logging 官方文档", "url": "https://docs.python.org/3/library/logging.html"}],
    ["控制台日志", "文件日志"],
    ["logging/app_log.py"],
    [],
    ["日志级别生效", "文件日志写入", "格式包含时间"],
    [
        code(
            "D11-basic", "控制台日志", ["py-15"],
            "写 main.py：配置 logging 输出到 stdout，级别 INFO，格式含级别名；main() 记录一条 INFO 日志“服务已启动”。运行 main.py 时 stdout 出现带 INFO 的日志行。",
            "import logging\nimport sys\n\ndef main():\n    # 配置 logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=\"%(levelname)s %(message)s\")\n    # 记录一条 INFO 日志：logging.info(\"服务已启动\")\n    ...\n\nif __name__ == \"__main__\":\n    main()",
            "运行 main.py 时 stdout 出现包含 INFO 与“服务已启动”的行。",
            "basicConfig 一次配置全局日志；级别过滤低于阈值的记录。",
            ["stdout 含 'INFO'", "stdout 含 '服务已启动'"],
            "basicConfig(level=..., stream=sys.stdout, format=...) 即可。",
            ["basicConfig 全局配置", "level 过滤级别", "format 定义输出格式"],
            "对应前端 logger 库的统一输出格式。",
            'logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(levelname)s %(message)s")\nlogging.info("服务已启动")',
            ["配置日志", "记录日志", "查看输出"],
        ),
        code(
            "D11-file", "文件日志", ["py-77", "py-15"],
            "实现 setup_file_logger(path, name='app') -> logging.Logger：创建 FileHandler 写入 path，格式含时间与级别名（format=\"%(asctime)s %(levelname)s %(message)s\"），级别 INFO，返回 logger。",
            "import logging\n\ndef setup_file_logger(path, name='app') -> logging.Logger:\n    # 你的实现\n    ...",
            "调用 setup_file_logger(tmp_path).info('写入日志') 后，文件中出现含 'INFO' 与 '写入日志' 的行。",
            "文件日志把运行痕迹持久化，方便事后排查。",
            ["文件包含 'INFO' 与 '写入日志'", "格式包含 asctime"],
            "FileHandler(path, encoding='utf-8') 配 Formatter，添加到 logger。",
            ["FileHandler 写文件", "Formatter 定义格式", "addHandler 绑定"],
            "对应前端把日志写到远端或本地文件的机制。",
            'handler = logging.FileHandler(path, encoding="utf-8")\nhandler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))\nlogger = logging.getLogger(name)\nlogger.addHandler(handler)\nlogger.setLevel(logging.INFO)',
            ["创建 FileHandler", "设置格式", "绑定到 logger"],
        ),
    ],
))

TASKS.append(_task(
    "D12", "S1".replace("S1", "S2"), "HTTP 客户端",
    ["D11"],
    "用 urllib.request 发起 GET/POST，解析 JSON 并处理错误与超时。",
    [("dev-http", "depends_on")],
    ["urllib.request", "GET/POST", "HTTPError", "超时"],
    "HTTP 客户端是前后端联调的镜像：一端发请求，一端响应 JSON。",
    "实现带错误处理的 GET 与 POST JSON 客户端。",
    'import json\nimport urllib.request\n\nwith urllib.request.urlopen(url) as r:\n    data = json.loads(r.read())',
    [{"title": "urllib.request 官方文档", "url": "https://docs.python.org/3/library/urllib.request.html"}],
    ["GET JSON", "POST JSON"],
    ["api/http_client.py"],
    [],
    ["GET 返回 dict", "POST 发送 JSON", "错误可识别"],
    [
        code(
            "D12-request", "GET 与错误处理", ["py-84", "py-87"],
            "实现 get_json(url) -> dict：用 urllib.request 发起 GET，json.loads 解析；状态非 200 时抛出 RuntimeError('HTTP 状态码: <code>')。再实现 safe_get_json(url) -> dict | None，出错时返回 None。",
            "import json\nimport urllib.request\nfrom urllib.error import HTTPError, URLError\n\ndef get_json(url) -> dict:\n    # 你的实现\n    ...\n\ndef safe_get_json(url) -> dict | None:\n    # 你的实现\n    ...",
            "get_json('http://127.0.0.1:<port>/ok') 返回 {'ok': True}；对返回 404 的地址抛 RuntimeError；safe_get_json 在失败时返回 None。",
            "真实联调最常见的错误是状态码与 JSON 解析失败，必须显式处理。",
            ["正常地址返回 dict", "404 抛 RuntimeError('HTTP 状态码: 404')", "safe_get_json 失败返回 None"],
            "urlopen 抛 HTTPError 时读取 e.code；URLError 表示连不上；timeout 参数设超时。",
            ["HTTPError.code 判断状态码", "URLError 区分网络错误", "timeout 防卡死"],
            "对应前端的 fetch 与状态码分支。",
            'def get_json(url):\n    try:\n        with urllib.request.urlopen(url, timeout=10) as r:\n            return json.loads(r.read())\n    except HTTPError as e:\n        raise RuntimeError(f"HTTP 状态码: {e.code}")\n    except URLError as e:\n        raise RuntimeError(f"网络错误: {e.reason}")',
            ["发起 GET", "解析 JSON", "处理错误"],
        ),
        code(
            "D12-post", "POST JSON", ["py-84", "py-87"],
            "实现 post_json(url, payload) -> dict：POST JSON 请求体，Content-Type: application/json，解析响应；错误处理同 get_json。",
            "import json\nimport urllib.request\n\ndef post_json(url, payload) -> dict:\n    # 你的实现\n    ...",
            "post_json('http://127.0.0.1:<port>/echo', {\"a\": 1}) 返回服务端回显的 JSON（含 {\"a\": 1}）。",
            "POST 需要设置方法、请求头与编码后的请求体。",
            ["发送 JSON 体", "Content-Type: application/json", "解析响应 dict"],
            "Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')。",
            ["Request 携带 data", "headers 声明 JSON", "method='POST'"],
            "对应前端的 fetch POST 与 JSON.stringify。",
            'req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")\nwith urllib.request.urlopen(req, timeout=10) as r:\n    return json.loads(r.read())',
            ["构造请求体", "声明请求头", "解析响应"],
        ),
    ],
))

TASKS.append(_task(
    "D13", "S1".replace("S1", "S2"), "FastAPI 基础",
    ["D12"],
    "用 FastAPI 定义路由，理解路径参数、查询参数与自动文档。",
    [("dev-http", "depends_on")],
    ["FastAPI", "路由", "路径参数", "查询参数", "自动文档"],
    "FastAPI 是当前主流的 Python Web 框架，对应前端熟悉的路由与 REST 约定。",
    "写一个带健康检查与路径参数的 FastAPI 应用。",
    'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/health")\ndef health():\n    return {"status": "ok"}',
    [{"title": "FastAPI 官方文档", "url": "https://fastapi.tiangolo.com/"}],
    ["健康检查", "路径参数", "查询参数"],
    ["api/app.py"],
    [],
    ["路由正确", "参数正确", "安装提示明确"],
    [
        code(
            "D13-app", "FastAPI 应用与健康检查",
            [],  # supplemental gap
            "写 app.py：from fastapi import FastAPI；创建 app；定义 GET /health 返回 {\"status\": \"ok\"}。",
            "from fastapi import FastAPI\n\napp = FastAPI()\n\n# 你的实现\n...",
            "app.py 中应存在 app 与 GET /health 路由。本工具只校验代码结构，真正的运行验证由你在 .venv 中执行 uvicorn app:app 完成。",
            "FastAPI 是真实开发补充；如果 .venv 尚未安装 fastapi，请先安装并确认用 .venv 运行学习工具。",
            ["存在 GET /health 路由", "返回 {\"status\": \"ok\"}"],
            "用 @app.get(\"/health\") 装饰一个返回 dict 的函数。",
            ["FastAPI() 创建实例", "@app.get 声明路由", "返回 dict 自动转 JSON"],
            "对应前端 Express 的路由写法。",
            '@app.get("/health")\ndef health():\n    return {"status": "ok"}',
            ["导入 FastAPI", "创建 app", "定义路由"],
            file_name="app.py",
            supplemental=True,
            note="真实开发补充：原 131 条来源索引未覆盖 FastAPI 框架；本节按官方文档安装与使用，工具不代为安装。",
        ),
        code(
            "D13-route", "路径参数与查询参数",
            [],  # supplemental gap
            "扩展 app.py：定义 GET /items/{item_id} 返回 {\"item_id\": item_id, \"q\": q}，其中 q 是查询参数（默认 None）；再定义 GET /items 返回 {\"items\": [], \"limit\": limit}，limit 默认 10。",
            "from fastapi import FastAPI\n\napp = FastAPI()\n\n# 定义 GET /items/{item_id}，参数 item_id: int、q: str | None = None\n# 定义 GET /items，参数 limit: int = 10\n# 你的实现\n...",
            "app 中应存在 GET /items/{item_id} 与 GET /items 两条路由，且带上述参数签名。",
            "路径参数用花括号声明并作为函数参数；查询参数直接写成默认参数。",
            ["GET /items/{item_id} 存在", "item_id: int 与 q 参数", "GET /items 带 limit 默认 10"],
            "函数参数即自动完成类型与校验；FastAPI 据此生成 OpenAPI 文档。",
            ["路径参数自动解析", "查询参数即默认参数", "类型注解即校验"],
            "对应前端路由里的 :id 参数。",
            '@app.get("/items/{item_id}")\ndef read_item(item_id: int, q: str | None = None):\n    return {"item_id": item_id, "q": q}',
            ["声明路径参数", "声明查询参数", "返回结构化 dict"],
            file_name="app.py",
            supplemental=True,
            note="真实开发补充：原索引未覆盖 Web 路由参数；本节约定按 FastAPI 官方文档编写。",
        ),
    ],
))

TASKS.append(_task(
    "D14", "S1".replace("S1", "S2"), "FastAPI 参数与错误处理",
    ["D13"],
    "用 pydantic 模型做请求体验证，用 HTTPException 处理错误。",
    [("dev-http", "depends_on")],
    ["pydantic", "HTTPException", "422", "404"],
    "后端必须把输入校验与错误响应做清楚，前端才拿得到稳定契约。",
    "写带 pydantic 模型与 HTTPException 的接口。",
    'from fastapi import FastAPI, HTTPException\nfrom pydantic import BaseModel\n\nclass Item(BaseModel):\n    name: str\n    price: float',
    [{"title": "FastAPI 请求体文档", "url": "https://fastapi.tiangolo.com/tutorial/body/"}],
    ["pydantic 模型", "HTTPException"],
    ["api/items.py"],
    [],
    ["模型字段正确", "404 处理正确", "校验错误可读"],
    [
        code(
            "D14-model", "pydantic 请求体模型",
            [],  # supplemental gap
            "写 app.py：定义 class Item(BaseModel) 含 name: str 与 price: float；定义 POST /items 接收 Item，返回 {\"name\": ..., \"price\": ..., \"amount\": round(price * 1.13, 2)}。",
            "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\nclass Item(BaseModel):\n    name: str\n    price: float\n\napp = FastAPI()\n\n# 你的实现\n...",
            "app 中应存在 Item 模型（name/price 字段）与 POST /items 路由。",
            "pydantic 模型声明请求体结构，FastAPI 自动校验并返回 422。",
            ["Item 有 name: str 与 price: float", "POST /items 存在", "amount 按 1.13 计算"],
            "用 BaseModel 子类声明字段；@app.post('/items') 接收 item: Item。",
            ["BaseModel 声明字段", "POST 接收模型", "自动校验返回 422"],
            "对应前端的 TypeScript interface + zod 校验。",
            'class Item(BaseModel):\n    name: str\n    price: float\n\n@app.post("/items")\ndef create_item(item: Item):\n    return {"name": item.name, "price": item.price, "amount": round(item.price * 1.13, 2)}',
            ["定义模型", "POST 路由", "返回计算结果"],
            file_name="app.py",
            supplemental=True,
            note="真实开发补充：原索引未覆盖 pydantic 与请求体校验。",
        ),
        code(
            "D14-errors", "HTTPException 错误处理",
            [],  # supplemental gap
            "扩展 app.py：在 GET /items/{item_id} 中，若 item_id 小于 1，raise HTTPException(status_code=404, detail='商品不存在')；并写一个独立函数 validate_price(price) -> float，price <= 0 时 raise HTTPException(status_code=422, detail='价格必须为正数')。",
            "from fastapi import FastAPI, HTTPException\n\napp = FastAPI()\n\ndef validate_price(price) -> float:\n    # 你的实现\n    ...\n\n@app.get(\"/items/{item_id}\")\ndef read_item(item_id: int):\n    # 你的实现\n    ...",
            "validate_price(-1) 抛 HTTPException(422)；item_id < 1 时 read_item 抛 HTTPException(404)。",
            "HTTPException 让业务失败映射为明确的 HTTP 状态码。",
            ["validate_price(0) 抛 422", "item_id < 1 抛 404", "正常价格返回浮点数"],
            "raise HTTPException(status_code=..., detail=...) 即可；detail 面向 API 调用方。",
            ["HTTPException 带状态码", "业务校验抛 HTTP 错误", "detail 提供可读消息"],
            "对应前端处理 4xx 响应。",
            'def validate_price(price):\n    if price <= 0:\n        raise HTTPException(status_code=422, detail="价格必须为正数")\n    return float(price)',
            ["抛 HTTPException", "设置状态码", "提供 detail"],
            file_name="app.py",
            supplemental=True,
            note="真实开发补充：原索引未覆盖 HTTP 错误处理。",
        ),
    ],
))

TASKS.append(_task(
    "D15", "S1".replace("S1", "S2"), "单元测试与 API 测试",
    ["D14"],
    "用 pytest 编写单元测试，用 mock 隔离外部依赖做 API 测试。",
    [("dev-testing", "depends_on")],
    ["pytest", "assert", "mock", "测试隔离"],
    "测试让改动可回归，对应前端 jest/vitest 的地位。",
    "为纯函数写 pytest 测试，为 HTTP 客户端写 mock 测试。",
    'def test_tax():\n    assert calculate_tax(100) == 13.0',
    [{"title": "pytest 官方文档", "url": "https://docs.pytest.org/"}],
    ["单元测试", "mock API 测试"],
    ["tests/test_utils.py"],
    ["test_utils"],
    ["测试通过", "mock 不联网", "边界覆盖"],
    [
        code(
            "D15-unit", "pytest 单元测试",
            [],  # supplemental gap
            "目录中已提供 tax.py，其中 calculate_tax(price) 返回 round(price * 0.13, 2)。写 test_tax.py：至少 3 个用例，覆盖正数、零与 0.5 精度，用 pytest 断言。",
            "from tax import calculate_tax\n\ndef test_tax_positive():\n    raise NotImplementedError(\"请补充断言\")",
            "python -m pytest -q test_tax.py 全部通过。",
            "单元测试直接验证函数行为，是回归的基石。",
            ["test_tax_positive 通过", "零值通过", "0.5 精度通过"],
            "assert calculate_tax(...) == 期望值；test_ 开头命名；pytest 自动收集。",
            ["test_ 前缀命名", "assert 断言", "pytest 收集执行"],
            "对应前端 describe/it/expect 的结构。",
            'from tax import calculate_tax\n\ndef test_tax_positive():\n    assert calculate_tax(100) == 13.0',
            ["导入被测函数", "编写断言", "运行 pytest"],
            file_name="test_tax.py",
            supplemental=True,
            note="真实开发补充：原索引未覆盖 pytest；pytest 已包含在开发依赖中。",
        ),
        code(
            "D15-mock", "mock 隔离的 API 测试",
            [],  # supplemental gap
            "目录中已提供 client.py，其 get_json(url) 使用 urllib.request。写 test_client.py：用 unittest.mock 替换 urlopen，断言 get_json 返回解析后的 dict，且全程不访问网络。",
            "from unittest import mock\nfrom client import get_json\n\ndef test_get_json_ok():\n    raise NotImplementedError(\"请用 mock 编写测试\")",
            "python -m pytest -q test_client.py 全部通过，且测试不发起真实网络请求。",
            "mock 把外部 HTTP 替换成确定性响应，让测试离线可跑。",
            ["测试通过", "使用 mock.patch", "断言返回 dict"],
            "mock.patch('urllib.request.urlopen', ...) 返回带 read() 的假对象；或 mock.patch.object(client.urllib.request, 'urlopen', ...)。",
            ["mock.patch 替换", "构造假响应对象", "断言解析结果"],
            "对应前端 mock fetch 的测试。",
            'from unittest import mock\nfrom client import get_json\n\ndef test_get_json_ok():\n    with mock.patch("urllib.request.urlopen") as m:\n        m.return_value.__enter__ = mock.Mock(return_value=m)\n        m.return_value.__enter__.return_value.read = mock.Mock(return_value=b\'{"ok": true}\')\n        assert get_json("http://x") == {"ok": True}',
            ["mock 替换 urlopen", "构造假响应", "离线断言"],
            file_name="test_client.py",
            supplemental=True,
            note="真实开发补充：原索引未覆盖 mock 测试；本测试使用标准库 unittest.mock。",
        ),
    ],
))

TASKS.append(_task(
    "D16", "S1".replace("S1", "S2"), "SQLite 标准库",
    ["D14"],
    "用标准库 sqlite3 建表、插入、查询与更新，使用参数化 SQL 防止注入。",
    [("dev-sqlite", "depends_on")],
    ["sqlite3", "CREATE TABLE", "参数化 SQL", "事务"],
    "本地数据持久化用 SQLite 即可，不需要单独数据库服务。",
    "实现建表与增删改查函数。",
    'import sqlite3\n\nconn = sqlite3.connect("tasks.db")\nconn.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT)")',
    [{"title": "sqlite3 官方文档", "url": "https://docs.python.org/3/library/sqlite3.html"}],
    ["建表", "增删改查"],
    ["database/tasks_db.py"],
    [],
    ["建表成功", "参数化 SQL", "CRUD 正确"],
    [
        code(
            "D16-create", "建表与连接",
            [],  # supplemental gap
            "实现 create_connection(path) -> sqlite3.Connection；init_db(conn) -> None：创建表 tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)。",
            "import sqlite3\n\ndef create_connection(path) -> sqlite3.Connection:\n    # 你的实现\n    ...\n\ndef init_db(conn) -> None:\n    # 你的实现\n    ...",
            "init_db 后 sqlite_master 中存在 tasks 表且列结构正确。",
            "SQLite 是文件数据库；表结构用 SQL 声明，列名与类型要明确。",
            ["表 tasks 存在", "包含 id/title/done 三列", "done 默认 0"],
            "conn.execute 执行 CREATE TABLE IF NOT EXISTS；用 sqlite_master 可查表结构。",
            ["sqlite3.connect 连接", "CREATE TABLE IF NOT EXISTS", "PRAGMA table_info 校验结构"],
            "对应前端的 schema 定义。",
            'def init_db(conn):\n    conn.execute("""\n        CREATE TABLE IF NOT EXISTS tasks (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            title TEXT NOT NULL,\n            done INTEGER NOT NULL DEFAULT 0\n        )\n    """)',
            ["连接数据库", "执行建表 SQL", "确认结构"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖数据库；本模块使用标准库 sqlite3，不需要额外数据库服务。",
        ),
        code(
            "D16-crud", "参数化增删改查",
            [],  # supplemental gap
            "实现：add_task(conn, title) -> int 插入并返回自增 id；list_tasks(conn) -> list 返回 [{id, title, done}]；toggle_task(conn, task_id) -> None 翻转 done；delete_task(conn, task_id) -> None。全部使用参数化 SQL（? 占位符）。",
            "def add_task(conn, title) -> int:\n    # 你的实现\n    ...\n\ndef list_tasks(conn) -> list:\n    ...\n\ndef toggle_task(conn, task_id) -> None:\n    ...\n\ndef delete_task(conn, task_id) -> None:\n    ...",
            "add_task 后 list_tasks 返回包含该任务；toggle 翻转 done；delete 移除；title 含单引号也能正确写入。",
            "参数化 SQL 把用户输入当作参数而不是拼进 SQL，是防注入的底线。",
            ["add_task 返回自增 id", "list_tasks 返回 dict 列表", "toggle 翻转 done", "标题含引号不报错"],
            "conn.execute('INSERT INTO tasks (title) VALUES (?)', (title,))；fetchall 后转 dict。",
            ["? 占位符传参", "commit 提交事务", "fetchall 读取结果"],
            "对应后端 ORM 的 create/read/update。",
            'def add_task(conn, title):\n    cur = conn.execute("INSERT INTO tasks (title) VALUES (?)", (title,))\n    conn.commit()\n    return cur.lastrowid',
            ["参数化 INSERT", "提交事务", "返回 id"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖 SQL 参数化与事务。",
        ),
    ],
))

TASKS.append(_task(
    "D17", "S1".replace("S1", "S2"), "asyncio 基础",
    ["D14"],
    "用 async/await 组织并发代码，理解 asyncio.run、gather 与 wait_for。",
    [("dev-asyncio", "depends_on")],
    ["async/await", "asyncio.run", "gather", "wait_for"],
    "异步让 IO 等待不阻塞整体，对应前端 Promise/async 的模型。",
    "实现异步聚合与超时控制函数。",
    "import asyncio\n\nasync def main():\n    results = await asyncio.gather(fetch(1), fetch(2))\n    return results",
    [{"title": "asyncio 官方文档", "url": "https://docs.python.org/3/library/asyncio.html"}],
    ["async 函数", "gather", "wait_for"],
    ["async/parallel.py"],
    [],
    ["异步函数返回正确", "gather 并发结果", "超时生效"],
    [
        code(
            "D17-async", "async 与 gather",
            [],  # supplemental gap
            "实现：async def fetch_item(n) -> int 返回 n（await asyncio.sleep(0) 模拟 IO）；async def run_all(n) -> list 用 asyncio.gather 并发获取 0..n-1；提供 main(n) 调用 asyncio.run(run_all(n)) 返回列表。",
            "import asyncio\n\nasync def fetch_item(n: int) -> int:\n    await asyncio.sleep(0)\n    # 你的实现\n    ...\n\nasync def run_all(n: int) -> list:\n    # 你的实现\n    ...\n\ndef main(n: int) -> list:\n    # 你的实现\n    ...",
            "main(4) == [0, 1, 2, 3]。",
            "gather 并发调度多个协程，结果顺序与传入顺序一致。",
            ["fetch_item(2) -> 2", "run_all(4) -> [0,1,2,3]", "main 用 asyncio.run 驱动"],
            "await asyncio.gather(*(fetch_item(i) for i in range(n)))。",
            ["async def 定义协程", "gather 并发", "asyncio.run 入口"],
            "对应前端 Promise.all。",
            "async def run_all(n):\n    return await asyncio.gather(*(fetch_item(i) for i in range(n)))",
            ["定义协程", "gather 并发", "run 驱动"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖异步编程；本模块使用标准库 asyncio。",
        ),
        code(
            "D17-timeout", "wait_for 超时控制",
            [],  # supplemental gap
            "实现：async def slow(n) -> int（await asyncio.sleep(0.5) 后返回 n）；async def fetch_with_timeout(n, timeout) -> int 用 asyncio.wait_for(slow(n), timeout)，超时抛出 asyncio.TimeoutError；提供 run(n, timeout) 用 asyncio.run 调用。",
            "import asyncio\n\nasync def slow(n: int) -> int:\n    await asyncio.sleep(0.5)\n    return n\n\nasync def fetch_with_timeout(n: int, timeout: float) -> int:\n    # 你的实现\n    ...\n\ndef run(n: int, timeout: float) -> int:\n    # 你的实现\n    ...",
            "run(3, 2.0) == 3（未超时）；run(3, 0.1) 抛出 asyncio.TimeoutError。",
            "wait_for 给协程加超时，防止外部调用无限等待。",
            ["run(3, 2.0) -> 3", "run(3, 0.1) 抛 TimeoutError"],
            "return await asyncio.wait_for(slow(n), timeout)。",
            ["wait_for 包装协程", "超时抛 TimeoutError", "run 驱动入口"],
            "对应前端 AbortController/超时。",
            "async def fetch_with_timeout(n, timeout):\n    return await asyncio.wait_for(slow(n), timeout)",
            ["wait_for 加超时", "捕获超时异常", "run 入口"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖异步超时。",
        ),
    ],
))

# --------------------------------------------------------------------------
# S3 本地任务管理项目
# --------------------------------------------------------------------------

TASKS.append(_task(
    "D18", "S1".replace("S1", "S3"), "需求与契约设计",
    ["D15", "D16"],
    "为一个本地任务管理项目写清需求、数据模型与 API 契约，作为后续实现的依据。",
    [("dev-testing", "depends_on"), ("dev-sqlite", "depends_on"), ("dev-http", "depends_on")],
    ["需求", "契约", "数据模型", "API 设计"],
    "先写契约再实现，对应前端先定接口再联调。",
    "写出需求说明与数据/API 契约。",
    '{"task": {"id": 1, "title": "写需求", "done": false}}',
    [{"title": "SQLite 官方文档", "url": "https://docs.python.org/3/library/sqlite3.html"}],
    ["写需求", "写契约"],
    ["taskproj/README.md", "taskproj/contract.json"],
    [],
    ["需求明确", "契约 JSON 合法", "覆盖核心实体与接口"],
    [
        text_section(
            "D18-requirements", "项目需求说明", [],
            "开始写项目前，先把需求说清楚：功能范围、边界与非目标。",
            "用 3-5 句话描述本地任务管理项目的功能：添加/列出/完成/删除任务、存储到 SQLite、提供 CLI 与网页两种入口、数据只留在本机。",
            "回答应覆盖任务的基本操作、存储方式、两种入口与本机边界。",
            "不需要设计文档格式，用通顺的中文描述即可。",
            ["增删改查任务", "SQLite 持久化", "CLI 与网页入口"],
            ["先定义范围再编码", "明确存储与本机边界", "两种入口共享同一套逻辑"],
            "对应前端先写 PRD/接口文档。",
            '需求：一个本地任务管理工具，支持添加、列出、完成、删除任务，数据存于 SQLite，提供 CLI 与网页两种入口，数据不离开本机。',
            ["写功能清单", "写存储方案", "写入口与边界"],
            project_file="docs/requirements.md",
            workspace_deps=[],
        ),
        json_section(
            "D18-contract", "数据与 API 契约", [],
            "用 JSON 定义任务数据模型与 API 契约。",
            "写出 JSON：包含 task 对象结构（id/title/done）与 endpoints 数组（每个含 method、path、description）。",
            "JSON 必须能解析，且包含键 task 与 endpoints，task 含 id/title/done 字段。",
            "契约是前后端共同遵守的接口约定。参考：GET /api/tasks、POST /api/tasks、PATCH /api/tasks/{id}/done、DELETE /api/tasks/{id}。",
            ["{\"task\": {\"id\": 1, \"title\": \"...\", \"done\": false}}", "endpoints 数组至少 4 项"],
            ["task 对象三字段", "endpoints 覆盖四个操作", "JSON 合法"],
            "对应前端 OpenAPI/接口文档。",
            '{\n  "task": {"id": 1, "title": "写需求", "done": false},\n  "endpoints": [\n    {"method": "GET", "path": "/api/tasks", "description": "列出任务"},\n    {"method": "POST", "path": "/api/tasks", "description": "新建任务"},\n    {"method": "PATCH", "path": "/api/tasks/{id}/done", "description": "标记完成"},\n    {"method": "DELETE", "path": "/api/tasks/{id}", "description": "删除任务"}\n  ]\n}',
            ["定义数据结构", "定义端点列表", "保持 JSON 合法"],
            project_file="contract.json",
            workspace_deps=[],
        ),
        text_section(
            "D18-readme", "项目 README", [],
            "给项目写一份可交付的 README：告诉别人这是什么、怎么安装、怎么运行。",
            "写 3-5 句话的 README：项目名称与一句话简介、安装命令（python -m venv .venv 与 pip install -e \".[dev]\"）、启动命令（uvicorn taskproj.api:app）与访问地址（http://127.0.0.1:8000）。",
            "回答应包含项目简介、安装命令与网页启动方式。",
            "README 是交付门面，写明安装与运行步骤才算可交付。",
            ["项目简介", "安装命令", "uvicorn 启动", "http://127.0.0.1:8000"],
            ["一句话介绍", "安装步骤", "运行命令"],
            "对应前端 README 的 Getting Started 段落。",
            '# 本地任务管理器\n\n一个本地任务管理工具，支持添加、列出、完成、删除任务，数据存于 SQLite。\n\n## 安装\n```\npython -m venv .venv\n.venv\\Scripts\\Activate.ps1\npython -m pip install -e ".[dev]"\n```\n\n## 启动网页\n```\nuvicorn taskproj.api:app --host 127.0.0.1 --port 8000\n```\n访问 http://127.0.0.1:8000',
            ["写项目名", "写安装命令", "写启动命令"],
            project_file="README.md",
            workspace_deps=[],
        ),
    ],
))

TASKS.append(_task(
    "D19", "S1".replace("S1", "S3"), "项目骨架与配置",
    ["D18"],
    "搭建包结构、读取配置（环境变量默认值）并准备入口。",
    [("dev-cli", "depends_on"), ("dev-config-log", "depends_on")],
    ["包结构", "配置", "环境变量", "入口"],
    "项目先立骨架与配置，再填业务，对应前端先搭目录与 env。",
    "实现 config.py 与 main.py 两个骨架文件。",
    "import os\nfrom pathlib import Path\n\ndef get_db_path():\n    return Path(os.environ.get(\"TASKPROJ_DB\", \"taskproj.db\"))",
    [{"title": "Python 包结构指南", "url": "https://docs.python.org/3/tutorial/modules.html#packages"}],
    ["实现配置", "实现入口"],
    ["taskproj/config.py", "taskproj/main.py"],
    [],
    ["配置读取环境变量", "入口可运行", "包结构存在"],
    [
        project_section(
            "D19-pyproject", "项目打包配置", [],
            "写 pyproject.toml，让项目可被 pip 安装并声明运行依赖。",
            "写出 pyproject.toml：含 [build-system]（requires 含 setuptools）、[project]（name 非空、version、requires-python 声明 >=3.11、dependencies 含 fastapi/uvicorn/pydantic）、[project.optional-dependencies] 的 dev 组含 pytest/httpx。",
            "TOML 必须能解析，且 project.name 非空、运行依赖与 dev 测试依赖齐全。",
            "pyproject.toml 是现代 Python 项目的元信息中心，pip install -e . 全靠它。",
            ["name 非空", "dependencies 含 fastapi/uvicorn/pydantic", "dev 组含 pytest/httpx"],
            ["[build-system] 声明构建后端", "[project] 声明元信息与依赖", "optional-dependencies.dev 放测试依赖"],
            "对应前端 package.json 的 dependencies/devDependencies。",
            '[build-system]\nrequires = ["setuptools>=68"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "taskproj"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = ["fastapi>=0.100", "uvicorn[standard]>=0.23", "pydantic>=2"]\n\n[project.optional-dependencies]\ndev = ["pytest>=8", "httpx>=0.24"]',
            ["写 build-system", "写 project 元信息", "写 dev 测试依赖"],
            project_file="pyproject.toml",
            workspace_deps=[],
        ),
        text_section(
            "D19-init", "包标记 __init__.py", [],
            "创建 taskproj/__init__.py，把目录声明成 Python 包。",
            "写一段包文档字符串：说明 taskproj 是一个“本地任务管理项目”的包，包含配置、数据层、接口与 CLI。",
            "回答应包含“任务管理”与包内职责说明，并保存到 taskproj/__init__.py。",
            "__init__.py 让 Python 把 taskproj 当作可导入的包；它同时是交付清单的一员。",
            ["本地任务管理", "配置/数据层/接口/CLI"],
            ["包标记文件", "说明包职责"],
            "对应前端包名与模块划分。",
            '"""本地任务管理项目包：包含配置、数据层、FastAPI 接口与 CLI。"""',
            ["写文档字符串", "说明职责"],
            project_file="taskproj/__init__.py",
            workspace_deps=[],
        ),
        code(
            "D19-config", "项目配置模块",
            [],  # supplemental gap
            "写 taskproj/config.py：get_db_path() -> Path，读取环境变量 TASKPROJ_DB，缺省返回 Path('taskproj.db')；get_int_env(name, default) 读取整数配置（参考 D10）。",
            "import os\nfrom pathlib import Path\n\ndef get_db_path() -> Path:\n    # 你的实现\n    ...\n\ndef get_int_env(name, default):\n    # 你的实现\n    ...",
            "设置 TASKPROJ_DB 后 get_db_path() 返回对应 Path；未设置返回 Path('taskproj.db')；get_int_env 失败兜底默认值。",
            "配置从环境变量注入，换环境不换代码。",
            ["TASKPROJ_DB 生效", "缺省 taskproj.db", "get_int_env 兜底"],
            "os.environ.get + Path 转换；int 转换用 try/except。",
            ["os.environ 读取", "Path 默认值", "类型转换兜底"],
            "对应前端 import.meta.env 的配置读取。",
            'def get_db_path():\n    return Path(os.environ.get("TASKPROJ_DB", "taskproj.db"))',
            ["读取环境变量", "返回 Path", "提供默认值"],
            file_name="taskproj/config.py",
            project_file="taskproj/config.py",
            workspace_deps=[],
        ),
        code(
            "D19-main", "项目入口",
            [],  # supplemental gap
            "写 taskproj/main.py：def main(argv=None) -> int 打印 '任务管理项目已启动' 并返回 0；用 __main__ 守卫调用。",
            "def main(argv=None) -> int:\n    # 你的实现\n    ...\n\nif __name__ == \"__main__\":\n    # 你的实现\n    ...",
            "python -m taskproj.main 输出“任务管理项目已启动”。",
            "入口文件只负责接线，业务逻辑留在其他模块。",
            ["运行输出 '任务管理项目已启动'", "main 返回 0"],
            "print 后 return 0；__main__ 守卫调用 main()。",
            ["main 返回退出码", "__main__ 守卫", "print 输出"],
            "对应前端的入口脚本。",
            'def main(argv=None):\n    print("任务管理项目已启动")\n    return 0\n\nif __name__ == "__main__":\n    raise SystemExit(main())',
            ["定义 main", "输出提示", "守卫调用"],
            file_name="taskproj/main.py",
            project_file="taskproj/main.py",
            workspace_deps=[],
        ),
    ],
))

TASKS.append(_task(
    "D20", "S1".replace("S1", "S3"), "SQLite 数据层",
    ["D19"],
    "实现项目的数据层：建表、增删改查，全部参数化 SQL。",
    [("dev-sqlite", "depends_on")],
    ["数据层", "建表", "参数化 SQL", "事务"],
    "数据层独立成模块，CLI 与网页共用同一套逻辑。",
    "实现 taskproj/db.py 的数据访问函数。",
    'def list_tasks(conn):\n    rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()\n    return [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]',
    [{"title": "sqlite3 官方文档", "url": "https://docs.python.org/3/library/sqlite3.html"}],
    ["建表初始化", "增删改查"],
    ["taskproj/db.py"],
    [],
    ["建表成功", "CRUD 正确", "参数化 SQL"],
    [
        code(
            "D20-init", "连接与建表",
            [],  # supplemental gap
            "写 taskproj/db.py：create_connection(path) -> sqlite3.Connection；init_db(conn) 创建 tasks 表（id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0）。本节先完成连接与建表，完整 CRUD 在下一节补齐后一起落盘。",
            "import sqlite3\n\ndef create_connection(path):\n    # 你的实现\n    ...\n\ndef init_db(conn):\n    # 你的实现\n    ...",
            "init_db 后 sqlite_master 存在 tasks 表，且 done 默认 0。",
            "数据层第一个能力是让数据库处于可用结构。",
            ["表 tasks 存在", "三列结构正确", "重复 init 不报错"],
            "CREATE TABLE IF NOT EXISTS 保证可重复初始化。",
            ["sqlite3.connect", "CREATE TABLE IF NOT EXISTS", "可重复执行"],
            "对应数据库迁移脚本的第一段 SQL。",
            "def init_db(conn):\n    conn.execute(\"CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)\")",
            ["连接", "建表", "确认可重复"],
            file_name="taskproj/db.py",
            workspace_deps=[],
            supplemental=True,
            note="真实开发补充：本节约为数据层铺垫，完整 CRUD 由 D20-crud 校验并落盘。",
        ),
        code(
            "D20-crud", "参数化增删改查",
            [],  # supplemental gap
            "扩展 taskproj/db.py：add_task(conn, title) -> int；list_tasks(conn) -> list（按 id 排序，done 转布尔）；complete_task(conn, task_id) -> None 把 done 置 1；delete_task(conn, task_id) -> None。全部参数化 SQL。本节通过后把完整 db.py 写入工作区。",
            "def add_task(conn, title) -> int:\n    # 你的实现\n    ...\n\ndef list_tasks(conn) -> list:\n    # 你的实现\n    ...\n\ndef complete_task(conn, task_id) -> None:\n    ...\n\ndef delete_task(conn, task_id) -> None:\n    ...",
            "add_task 后 list_tasks 返回 [{id, title, done: false}]；complete 后 done 为 true；delete 后消失；标题含引号安全。",
            "CRUD 是数据层核心，参数化 SQL 防止注入。",
            ["add_task 返回 id", "list_tasks 结构正确", "complete 置 1", "delete 移除"],
            "execute 用 ? 占位符；每次写操作后 commit。",
            ["INSERT/SELECT/UPDATE/DELETE", "? 占位符", "commit 提交"],
            "对应 ORM 的 create/read/update/delete。",
            'def add_task(conn, title):\n    cur = conn.execute("INSERT INTO tasks (title) VALUES (?)", (title,))\n    conn.commit()\n    return cur.lastrowid',
            ["插入", "查询", "更新与删除"],
            file_name="taskproj/db.py",
            project_file="taskproj/db.py",
            workspace_deps=["taskproj/__init__.py"],
        ),
    ],
))

TASKS.append(_task(
    "D21", "S1".replace("S1", "S3"), "API 与业务层",
    ["D20"],
    "用 FastAPI 暴露任务接口，接入数据层并处理错误。",
    [("dev-http", "depends_on"), ("dev-sqlite", "depends_on")],
    ["FastAPI", "路由", "请求体", "错误处理"],
    "接口层把数据层能力暴露成 HTTP，对应前端调用的后端接口。",
    "实现 taskproj/api.py 的 FastAPI 应用。",
    'from fastapi import FastAPI, HTTPException\nfrom pydantic import BaseModel',
    [{"title": "FastAPI 官方文档", "url": "https://fastapi.tiangolo.com/"}],
    ["列表接口", "新建接口", "错误处理"],
    ["taskproj/api.py"],
    [],
    ["路由覆盖四个操作", "模型正确", "错误返回 4xx"],
    [
        code(
            "D21-routes", "任务接口路由",
            [],  # supplemental gap
            "写 taskproj/api.py：class TaskIn(BaseModel) 含 title: str；class Task(BaseModel) 含 id/title/done；app 提供 GET / 返回网页页面（返回 FileResponse 或 HTML 字符串，可先用占位内容）、GET /health 返回 {\"status\": \"ok\"}、GET /api/tasks（调用 list_tasks）、POST /api/tasks（add_task）。本节先完成路由，网页内容在 D23 完善。",
            "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\nclass TaskIn(BaseModel):\n    title: str\n\nclass Task(BaseModel):\n    id: int\n    title: str\n    done: bool\n\napp = FastAPI()\n# 你的实现\n...",
            "app 中存在 GET /、GET /health、GET /api/tasks 与 POST /api/tasks 路由，且 POST 使用 TaskIn。",
            "接口层薄薄一层，把 HTTP 请求转成数据层调用；网页入口也只是一个普通路由。",
            ["TaskIn 有 title", "GET / 存在", "GET /health 存在", "GET/POST /api/tasks 存在"],
            "GET / 返回 FileResponse 或 HTML 字符串；/health 固定返回状态；其余路由调用数据层。",
            ["pydantic 模型", "网页与健康路由", "数据层路由"],
            "对应前端调用的 REST 接口，健康检查对应探活端点。",
            '@app.get("/health")\ndef health():\n    return {"status": "ok"}\n\n@app.get("/api/tasks")\ndef read_tasks():\n    conn = create_connection(get_db_path())\n    return list_tasks(conn)',
            ["定义模型", "定义网页/健康路由", "接入数据层"],
            file_name="taskproj/api.py",
            workspace_deps=["taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py"],
            supplemental=True,
            note="真实开发补充：本节约为接口层铺垫，完整 api.py（含错误处理）由 D21-errors 校验并落盘。",
        ),
        code(
            "D21-errors", "完成与错误处理",
            [],  # supplemental gap
            "扩展 taskproj/api.py：PATCH /api/tasks/{task_id}/done 调用 complete_task；DELETE /api/tasks/{task_id} 调用 delete_task；task_id 不存在时抛 HTTPException(404, '任务不存在')；title 为空时 POST 返回 422。本节通过后把完整 api.py 写入工作区。",
            "from fastapi import HTTPException\n\n# 你的实现\n...",
            "存在 PATCH/DELETE 路由；title 为空时抛 422；删除不存在任务时抛 404。",
            "错误要映射成明确的 HTTP 状态码，前端才好处理。",
            ["PATCH/DELETE 路由存在", "空 title 抛 422", "不存在任务抛 404"],
            "用一个带参校验的函数（如 def get_task_or_404(task_id)）统一处理 404。",
            ["HTTPException(404)", "校验抛 422", "路由覆盖完成/删除"],
            "对应后端 REST 的错误约定。",
            'def get_task_or_404(task_id):\n    conn = create_connection(get_db_path())\n    rows = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchall()\n    if not rows:\n        raise HTTPException(status_code=404, detail="任务不存在")\n    return conn',
            ["抛 404", "校验 422", "完善路由"],
            file_name="taskproj/api.py",
            project_file="taskproj/api.py",
            workspace_deps=["taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py"],
        ),
    ],
))

TASKS.append(_task(
    "D22", "S1".replace("S1", "S3"), "测试与验收",
    ["D21"],
    "为数据层写单元测试，为接口客户端写 mock 测试，构成项目回归防线。",
    [("dev-testing", "depends_on")],
    ["pytest", "fixture", "mock", "回归"],
    "测试保证改动不破坏既有功能，对应前端 CI 中的单测。",
    "实现项目数据层测试与 API mock 测试。",
    'def test_add_and_list(tmp_path):\n    conn = sqlite3.connect(tmp_path / "t.db")\n    init_db(conn)\n    add_task(conn, "测试")\n    assert list_tasks(conn)[0]["title"] == "测试"',
    [{"title": "pytest fixtures 文档", "url": "https://docs.pytest.org/en/stable/fixture.html"}],
    ["数据层测试", "接口测试"],
    ["tests/test_project.py", "tests/test_api.py"],
    ["test_project", "test_api"],
    ["测试通过", "mock 不联网", "覆盖边界"],
    [
        code(
            "D22-db", "数据层单元测试",
            [],  # supplemental gap
            "工作区中已有 taskproj/db.py（D20 落盘）。写 tests/test_project.py：用 tmp_path fixture 建临时库，覆盖 add/list/complete/delete 与含引号标题。本节通过后把测试文件写入工作区。",
            "import sqlite3\nfrom taskproj.db import init_db, add_task, list_tasks, complete_task, delete_task\n\ndef test_add_and_list(tmp_path):\n    raise NotImplementedError(\"请补充断言\")",
            "python -m pytest -q test_project.py 全部通过。",
            "数据层测试用临时库，不污染真实数据。",
            ["test_add_and_list 通过", "complete 翻转", "引号标题安全"],
            "tmp_path 是 pytest 内置 fixture；每个用例独立临时目录。",
            ["tmp_path fixture", "参数化 SQL 测试", "覆盖全部 CRUD"],
            "对应后端 repository 测试。",
            'def test_add_and_list(tmp_path):\n    conn = sqlite3.connect(tmp_path / "t.db")\n    init_db(conn)\n    add_task(conn, "测试")\n    assert list_tasks(conn)[0]["title"] == "测试"',
            ["建临时库", "执行 CRUD", "断言结果"],
            file_name="test_project.py",
            project_file="tests/test_project.py",
            workspace_deps=["taskproj/__init__.py", "taskproj/db.py"],
        ),
        code(
            "D22-api", "接口 TestClient 测试",
            [],  # supplemental gap
            "工作区中已有 taskproj/api.py（D21 落盘）。写 tests/test_api.py：用 fastapi.testclient.TestClient 覆盖 GET /health、GET /api/tasks、POST、PATCH 完成、DELETE，以及 404（不存在的任务）与 422（空标题）。本节通过后把测试文件写入工作区。",
            "from fastapi.testclient import TestClient\nfrom taskproj.api import app\n\ndef test_health():\n    raise NotImplementedError(\"请用 TestClient 编写测试\")",
            "python -m pytest -q tests/test_api.py 全部通过，且不访问网络。",
            "TestClient 让接口测试在离线环境稳定可跑，覆盖状态码与错误路径。",
            ["health 断言通过", "CRUD 断言通过", "404/422 覆盖"],
            "TestClient(app) 后调用 .get/.post/.patch/.delete；临时库通过 TASKPROJ_DB 环境变量隔离。",
            ["TestClient 请求", "断言状态码", "覆盖 404/422"],
            "对应前端对 API 层的 mock 测试。",
            'from fastapi.testclient import TestClient\nfrom taskproj.api import app\n\ndef test_health():\n    assert TestClient(app).get("/health").status_code == 200\n\ndef test_crud():\n    client = TestClient(app)\n    assert client.post("/api/tasks", json={"title": "x"}).json()["done"] is False',
            ["TestClient 调用", "断言结果", "保持离线"],
            file_name="tests/test_api.py",
            project_file="tests/test_api.py",
            workspace_deps=["taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py", "taskproj/api.py"],
        ),
    ],
))

TASKS.append(_task(
    "D23", "S1".replace("S1", "S3"), "CLI 与网页演示",
    ["D22"],
    "为项目写 CLI，并给出网页演示的运行方式。",
    [("dev-cli", "depends_on"), ("dev-http", "depends_on")],
    ["argparse", "子命令", "网页演示"],
    "CLI 与网页共用数据层，是复用架构的直接体现。",
    "实现 taskproj/cli.py 并描述网页演示。",
    'python -m taskproj.cli add "买牛奶"',
    [{"title": "argparse 官方文档", "url": "https://docs.python.org/3/library/argparse.html"}],
    ["CLI 子命令", "网页演示"],
    ["taskproj/cli.py"],
    [],
    ["CLI 可运行", "数据写入真实库", "演示说明完整"],
    [
        code(
            "D23-cli", "命令行子命令",
            [],  # supplemental gap
            "写 taskproj/cli.py：argparse 子命令 add（title 必填）、list、done（task_id）、rm（task_id）；list 打印每行“id. title [done]”；操作读写 TASKPROJ_DB 指向的数据库。本节通过后把 cli.py 写入工作区。",
            "import argparse\nimport sqlite3\nfrom taskproj.db import create_connection, init_db, add_task, list_tasks, complete_task, delete_task\n\ndef main(argv=None):\n    # 你的实现\n    ...\n\nif __name__ == \"__main__\":\n    raise SystemExit(main())",
            "设置 TASKPROJ_DB 指向临时库后：add 写入、list 打印、done/rm 生效。",
            "CLI 复用数据层，说明业务逻辑与界面分离。",
            ["add 后 list 可见", "done 标记完成", "rm 删除"],
            "add_subparsers(dest='command')；每个子命令 add_argument；按 command 分发。",
            ["子命令分发", "复用数据层", "print 列表输出"],
            "对应前端脚手架命令与后端接口复用同一模型。",
            'parser = argparse.ArgumentParser()\nsub = parser.add_subparsers(dest="command", required=True)\nadd = sub.add_parser("add")\nadd.add_argument("title")\nargs = parser.parse_args(argv)\nif args.command == "add":\n    conn = create_connection(get_db_path()); init_db(conn); add_task(conn, args.title)',
            ["定义子命令", "读取数据库", "分发处理"],
            file_name="taskproj/cli.py",
            project_file="taskproj/cli.py",
            workspace_deps=["taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py"],
        ),
        html_section(
            "D23-html", "网页页面与前端逻辑", [],
            "写 taskproj/static/index.html：一个真实可用的任务管理网页，用原生 fetch 调后端接口完成列表、新增、完成、删除。",
            "写出完整 HTML：含 <html>/<body> 与 <script>；页面用 fetch('/api/tasks') 拉取并渲染任务列表（createElement/innerHTML）；提供输入框与新增按钮（POST /api/tasks）；每个任务有完成按钮（PATCH /api/tasks/{id}/done）与删除按钮（DELETE /api/tasks/{id}）。",
            "HTML 结构完整、包含原生 fetch 调用与列表/新增/完成/删除四类交互。",
            "网页只是数据层与接口的另一个消费者，复用同一套 API。",
            ["fetch 调用 /api/tasks", "列表渲染", "新增/完成/删除按钮"],
            ["原生 fetch 调用接口", "用 DOM 渲染列表", "按钮触发对应方法"],
            "对应前端页面直接调用后端 REST 接口。",
            'fetch("/api/tasks").then(r => r.json()).then(tasks => {\n  const list = document.getElementById("list");\n  tasks.forEach(t => {\n    const li = document.createElement("li");\n    li.innerHTML = t.title;\n    list.appendChild(li);\n  });\n});',
            ["写页面结构", "写 fetch 渲染", "写新增/完成/删除"],
            project_file="taskproj/static/index.html",
            workspace_deps=[],
        ),
    ],
))

TASKS.append(_task(
    "D24", "S1".replace("S1", "S3"), "重建交付与复盘",
    ["D23"],
    "从全新 venv 重建项目、演示并复盘，验证项目可交付。",
    [("dev-cli", "depends_on"), ("dev-config-log", "depends_on")],
    ["重建", "演示", "复盘"],
    "交付标准是“别人拿到就能跑”，对应前端一条命令启动。",
    "写出重建命令序列并完成复盘。",
    'python -m venv .venv\n.venv\\Scripts\\Activate.ps1\npython -m pip install -e ".[dev]"\npython -m pytest',
    [{"title": "虚拟环境指南", "url": "https://docs.python.org/3/library/venv.html"}],
    ["重建命令", "复盘"],
    ["docs/runbook.md", "docs/review.md"],
    [],
    ["命令序列可重建", "复盘覆盖交付点"],
    [
        command_section(
            "D24-runbook", "重建命令序列", ["py-03", "py-87"],
            "写出从零重建项目并验证的命令序列（不执行），保存到 docs/runbook.md。",
            "依次写出：创建 .venv、安装依赖（pip install -e \".[dev]\"）、运行项目测试（python -m pytest）与启动网页（uvicorn taskproj.api:app --host 127.0.0.1 --port 8000）四条命令。",
            "命令文本能被解析且依次包含 venv、install、pytest、uvicorn 四类关键动作。",
            "本练习只校验命令内容，不会执行你输入的命令。",
            ["python -m venv .venv", "python -m pip install -e \".[dev]\"", "python -m pytest", "uvicorn taskproj.api:app"],
            ["按顺序写命令", "覆盖安装与测试", "覆盖启动"],
            "对应前端一行 npm install && npm run build 的可重建脚本。",
            'python -m venv .venv\n.venv\\Scripts\\Activate.ps1\npython -m pip install -e ".[dev]"\npython -m pytest\nuvicorn taskproj.api:app --host 127.0.0.1 --port 8000',
            ["列重建命令", "列验证命令", "列启动命令"],
            project_file="docs/runbook.md",
            workspace_deps=[],
        ),
        text_section(
            "D24-review", "项目复盘", ["ending-01"],
            "完成重建与演示后，复盘整个项目，保存到 docs/review.md。",
            "用 3-5 句话复盘：项目交付了什么、数据层与接口如何复用、重建过程是否顺利、下一步可以改进什么。",
            "回答应覆盖项目产物、复用点、重建结果与改进方向。",
            "复盘是学习闭环的一部分，不是可选任务。",
            ["项目产物", "复用架构", "改进方向"],
            ["写交付内容", "写复用方式", "写改进建议"],
            "对应前端项目结束后的 retrospective。",
            '项目交付了可运行的本地任务管理工具；数据层被 CLI 与网页复用；重建验证顺利；下一步可以加提醒功能。',
            ["写产物", "写复用", "写改进"],
            project_file="docs/review.md",
            workspace_deps=[],
        ),
    ],
))

# --------------------------------------------------------------------------
# S4 AI 应用
# --------------------------------------------------------------------------

TASKS.append(_task(
    "D25", "S1".replace("S1", "S4"), "DeepSeek API 调用",
    ["D12", "D14"],
    "用标准库 urllib 直连 DeepSeek 官方 API，掌握鉴权、请求与错误处理。",
    [("ai-api", "depends_on"), ("dev-http", "depends_on")],
    ["DeepSeek API", "Bearer 鉴权", "chat/completions", "错误处理"],
    "AI 能力通过 HTTP API 提供，与调用任何 JSON 服务一样，只是多了鉴权头。",
    "实现调用 chat/completions 的客户端函数。",
    'import json\nimport urllib.request\n\nurl = "https://api.deepseek.com/chat/completions"\nheaders = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}',
    [{"title": "DeepSeek API 文档", "url": "https://api-docs.deepseek.com/"}],
    ["基础调用", "错误处理"],
    ["ai/deepseek_client.py"],
    [],
    ["Bearer 鉴权", "返回内容正确", "错误可识别"],
    [
        code(
            "D25-chat", "chat/completions 调用",
            [],  # supplemental gap
            "实现 call_chat(api_key, messages, *, base_url='https://api.deepseek.com') -> str：POST {base_url}/chat/completions，请求体含 model='deepseek-chat'、messages、stream=False；Bearer 鉴权；返回 choices[0].message.content。",
            "import json\nimport urllib.request\n\ndef call_chat(api_key: str, messages: list, *, base_url: str = \"https://api.deepseek.com\") -> str:\n    # 你的实现\n    ...",
            "向本地 mock 服务发送请求时，返回 mock 服务给出的 content，且请求带 Bearer <api_key>。",
            "本工具用本地 mock 服务校验你的客户端代码，全程不访问真实 DeepSeek。",
            ["返回 mock 的 content", "Authorization 为 Bearer <key>", "请求体含 model 与 messages"],
            "构造 Request(data=json.dumps(...).encode('utf-8'), headers=..., method='POST')；urlopen 读响应后 json.loads。",
            ["POST 请求构造", "Bearer 鉴权头", "解析 choices[0].message.content"],
            "对应前端带 Authorization 头调用 AI 网关。",
            'def call_chat(api_key, messages, *, base_url="https://api.deepseek.com"):\n    body = json.dumps({"model": "deepseek-chat", "messages": messages, "stream": False}).encode("utf-8")\n    req = urllib.request.Request(f"{base_url}/chat/completions", data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")\n    with urllib.request.urlopen(req, timeout=60) as r:\n        data = json.loads(r.read())\n    return data["choices"][0]["message"]["content"]',
            ["构造请求", "发送请求", "解析响应"],
            supplemental=True,
            note="真实开发补充：原索引 ai-01~ai-05 仅介绍概念，未覆盖官方 API 调用；调用只在你显式点击时发生。",
        ),
        code(
            "D25-errors", "API 错误处理",
            [],  # supplemental gap
            "扩展 call_chat 支持错误处理：定义 class ApiError(RuntimeError) 带 status_code 属性；状态非 200 时抛 ApiError('API 错误', status_code)，网络错误抛 ApiError('网络错误', None)；响应非 JSON 抛 ApiError('响应不是 JSON', None)。",
            "class ApiError(RuntimeError):\n    def __init__(self, message, status_code=None):\n        super().__init__(message)\n        self.status_code = status_code\n\n# 扩展 call_chat：\n...",
            "mock 返回 401 时抛 ApiError 且 status_code == 401；返回非 JSON 时抛 ApiError。",
            "AI 服务会返回 401/429/5xx，客户端必须给出可识别的错误。",
            ["401 -> ApiError(status_code=401)", "非 JSON -> ApiError", "正常请求返回 content"],
            "捕获 HTTPError（e.code）、URLError、json.JSONDecodeError，统一转 ApiError。",
            ["捕获 HTTPError", "捕获 URLError", "统一转 ApiError"],
            "对应前端把 AI 网关错误翻译成可读消息。",
            'except urllib.error.HTTPError as e:\n    raise ApiError("API 错误", e.code)\nexcept urllib.error.URLError as e:\n    raise ApiError("网络错误")',
            ["捕获状态码", "捕获网络错误", "统一异常"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖 API 客户端错误模型。",
        ),
    ],
))

TASKS.append(_task(
    "D26", "S1".replace("S1", "S4"), "提示词与索引驱动",
    ["D25"],
    "把真实索引标题写进提示词作为出题边界，并安全解析模型的严格 JSON 输出。",
    [("ai-api", "depends_on")],
    ["提示词", "索引边界", "严格 JSON", "解析安全"],
    "AI 输出不稳定，提示词要约束结构，解析端要处理噪声。",
    "实现提示词构造与 JSON 解析两个函数。",
    'def build_prompt(titles, goal, instructions):\n    return f"标题范围：{titles}\\n目标：{goal}\\n要求：{instructions}"',
    [{"title": "DeepSeek 提示词文档", "url": "https://api-docs.deepseek.com/"}],
    ["构造提示词", "解析 JSON"],
    ["ai/prompt.py"],
    [],
    ["提示词含真实标题", "JSON 解析健壮", "声明索引边界"],
    [
        code(
            "D26-prompt", "索引驱动的提示词",
            [],  # supplemental gap
            "实现 build_prompt(catalog_titles, goal, instructions, completed) -> str：把 catalog_titles 的标题逐个列入“知识范围标题”段，说明“索引仅代表标题知识范围，不代表视频正文”，并附上目标、要求与已完成状态。",
            "def build_prompt(catalog_titles: list[str], goal: str, instructions: str, completed: bool) -> str:\n    # 你的实现\n    ...",
            "返回字符串包含所有 catalog_titles、短语“索引仅代表标题知识范围”以及 goal/instructions/completed。",
            "索引只做知识范围边界，不能声称看过视频正文。",
            ["包含所有传入标题", "包含'索引仅代表标题知识范围'", "包含 goal 与 completed"],
            "用 f-string 拼接标题列表；把边界声明写成固定句子。",
            ["f-string 拼接", "标题逐条列出", "声明索引边界"],
            "对应前端把产品上下文注入 prompt。",
            'def build_prompt(titles, goal, instructions, completed):\n    scope = "；".join(titles)\n    return f"知识范围标题：{scope}\\n索引仅代表标题知识范围，不代表视频正文。\\n目标：{goal}\\n要求：{instructions}\\n已完成：{completed}"',
            ["列出标题", "写边界声明", "附上目标"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖提示词工程；索引标题只作为知识范围边界。",
        ),
        code(
            "D26-parse", "严格 JSON 解析",
            [],  # supplemental gap
            "实现 parse_ai_json(text) -> dict：从文本中定位第一个以 { 开头、以 } 结尾的 JSON 片段并 json.loads；找不到或解析失败抛 ValueError。",
            "import json\n\ndef parse_ai_json(text: str) -> dict:\n    # 你的实现\n    ...",
            "parse_ai_json('前缀 {\"a\": 1} 后缀') 返回 {'a': 1}；parse_ai_json('没有JSON') 抛 ValueError。",
            "模型输出常夹带说明文字，解析必须定位真实 JSON。",
            ["前缀+JSON 提取成功", "纯 JSON 成功", "无 JSON 抛 ValueError"],
            "用 find('{') 与 rfind('}') 切片后再 json.loads。",
            ["定位花括号", "切片提取", "json.loads 校验"],
            "对应前端解析 LLM 输出的容错处理。",
            'def parse_ai_json(text):\n    start = text.find("{")\n    end = text.rfind("}")\n    if start == -1 or end == -1 or end <= start:\n        raise ValueError("没有 JSON")\n    return json.loads(text[start:end + 1])',
            ["定位片段", "切片", "解析校验"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖模型输出解析。",
        ),
    ],
))

TASKS.append(_task(
    "D27", "S1".replace("S1", "S4"), "AI 应用项目",
    ["D26"],
    "把客户端、提示词与解析组合成一个 AI 学习助手流程，并做成可运行应用。",
    [("ai-api", "depends_on"), ("ai-app-ui", "knowledge_base")],
    ["组合流程", "可运行应用", "mock 验证"],
    "AI 应用 = 客户端 + 提示词 + 解析 + 界面，复用前三者完成业务。",
    "实现 send_message 与 review_submission 两个核心流程函数。",
    'def review_submission(api_key, submission, rubric, *, base_url):\n    prompt = build_prompt(...)\n    content = call_chat(api_key, [{"role": "user", "content": prompt}], base_url=base_url)\n    return parse_ai_json(content)',
    [{"title": "DeepSeek 聊天补全文档", "url": "https://api-docs.deepseek.com/"}],
    ["消息封装", "评审流程"],
    ["ai/assistant.py", "ai/app.py"],
    [],
    ["消息结构正确", "评审返回四字段", "mock 离线可验证"],
    [
        code(
            "D27-client", "消息封装与严格输出",
            [],  # supplemental gap
            "实现 send_message(api_key, prompt, *, base_url) -> dict：组装 [{role: 'user', content: prompt}] 调用 call_chat，把返回内容交给 parse_ai_json 解析成 dict。",
            "from deepseek_client import call_chat\nfrom prompt import parse_ai_json\n\ndef send_message(api_key: str, prompt: str, *, base_url: str) -> dict:\n    # 你的实现\n    ...",
            "向本地 mock 服务发送时返回解析后的 dict；mock 返回非 JSON 时抛 ApiError。",
            "客户端负责把模型文本转成结构化数据。",
            ["返回 dict", "解析成功", "非 JSON 抛 ApiError"],
            "messages = [{'role': 'user', 'content': prompt}]；call_chat 后 parse_ai_json。",
            ["组装消息", "调用客户端", "解析结构"],
            "对应前端把 AI 响应映射成对象。",
            'def send_message(api_key, prompt, *, base_url):\n    messages = [{"role": "user", "content": prompt}]\n    content = call_chat(api_key, messages, base_url=base_url)\n    return parse_ai_json(content)',
            ["组装消息", "调用 API", "解析输出"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖 AI 应用客户端封装。",
        ),
        code(
            "D27-flow", "评审流程",
            [],  # supplemental gap
            "实现 review_submission(api_key, submission, rubric, catalog_titles, *, base_url) -> dict：用 build_prompt 构造提示词，调用 send_message，返回必须包含 summary/strengths/issues/next_steps 四键（缺失时抛 ValueError）。",
            "from prompt import build_prompt\n\ndef review_submission(api_key, submission, rubric, catalog_titles, *, base_url) -> dict:\n    # 你的实现\n    ...",
            "mock 服务返回四键 JSON 时，review_submission 返回该 dict；返回缺少键的 JSON 时抛 ValueError。",
            "评审流程把学习内容发给模型，但只在你显式点击时发生。",
            ["返回四键 dict", "缺失键抛 ValueError", "提示词包含目录标题"],
            "先 build_prompt，再 send_message，最后校验四键并转成业务结构。",
            ["组合函数", "校验输出结构", "缺失键报错"],
            "对应前端把产品数据组装成 AI 请求。",
            'data = send_message(api_key, prompt, base_url=base_url)\nif not {"summary", "strengths", "issues", "next_steps"} <= data.keys():\n    raise ValueError("评审输出缺少字段")\nreturn data',
            ["构造提示词", "发送请求", "校验输出"],
            supplemental=True,
            note="真实开发补充：原索引未覆盖 AI 应用业务流程。",
        ),
    ],
))

TASKS.append(_task(
    "D28", "S1".replace("S1", "S4"), "测试与交付复盘",
    ["D27"],
    "用 mock 为 AI 客户端写离线测试，并完成项目复盘与重建说明。",
    [("dev-testing", "depends_on"), ("ai-api", "depends_on")],
    ["mock 测试", "离线验证", "复盘"],
    "AI 功能必须可离线测试，这是把 AI 应用做稳的关键。",
    "实现 AI 客户端 mock 测试与交付复盘。",
    'from unittest import mock\nfrom ai_client import send_message\n\ndef test_send_message():\n    with mock.patch("urllib.request.urlopen") as m:\n        ...',
    [{"title": "unittest.mock 文档", "url": "https://docs.python.org/3/library/unittest.mock.html"}],
    ["mock 测试", "复盘"],
    ["ai/test_ai_client.py"],
    ["test_ai_client"],
    ["测试离线通过", "复盘完整"],
    [
        code(
            "D28-test", "AI 客户端 mock 测试",
            [],  # supplemental gap
            "目录中已提供 ai_client.py（含 call_chat 与 send_message）。写 test_ai_client.py：mock urllib.request.urlopen，覆盖正常返回、HTTP 401 抛 ApiError、非 JSON 抛 ApiError 三个用例，全程离线。",
            "from unittest import mock\nfrom ai_client import call_chat, ApiError\n\ndef test_call_chat_ok():\n    raise NotImplementedError(\"请用 mock 编写测试\")\n\ndef test_call_chat_401():\n    raise NotImplementedError(\"请用 mock 编写测试\")\n\ndef test_call_chat_bad_json():\n    raise NotImplementedError(\"请用 mock 编写测试\")",
            "python -m pytest -q test_ai_client.py 全部通过且不访问网络。",
            "AI 测试用 mock 替换网络，让 CI 与离线环境都能稳定回归。",
            ["三个用例通过", "401 抛 ApiError", "非 JSON 抛 ApiError"],
            "HTTPError 用 mock.Mock(spec=urllib.error.HTTPError) 或 raise urllib.error.HTTPError(url, 401, 'x', {}, None)。",
            ["mock urlopen", "构造 HTTPError", "断言异常类型"],
            "对应前端对 AI 接口层的 mock 测试。",
            'def test_call_chat_ok():\n    with mock.patch("urllib.request.urlopen") as m:\n        m.return_value.__enter__ = mock.Mock(return_value=m)\n        m.return_value.__enter__.return_value.read = mock.Mock(return_value=b\'{"choices": [{"message": {"content": "hi"}}]}\')\n        assert call_chat("k", [{"role": "user", "content": "hi"}], base_url="http://x") == "hi"',
            ["mock 网络", "断言正常返回", "断言异常"],
            file_name="test_ai_client.py",
            supplemental=True,
            note="真实开发补充：原索引未覆盖 AI 客户端 mock 测试。",
        ),
        text_section(
            "D28-review", "AI 应用复盘", ["ending-01", "ai-03"],
            "完成 AI 应用后复盘交付点。",
            "用 3-5 句话复盘：应用提供了什么能力、AI 调用如何被隔离（mock 可测）、提示词如何限定索引边界、如何重建与演示。",
            "回答应覆盖应用能力、测试隔离、提示词边界与重建方式。",
            "AI 应用的稳是“可离线测试”与“显式触发”换来的。",
            ["应用能力", "mock 隔离", "索引边界", "重建演示"],
            ["写能力", "写测试隔离", "写提示词边界", "写重建方式"],
            "对应前端交付 AI 功能后的上线复盘。",
            '应用提供学习评审；AI 调用封装在 client 层，测试用 mock 离线完成；提示词声明索引只是标题范围；重建用 venv + install 即可演示。',
            ["写能力", "写隔离", "写边界", "写重建"],
        ),
    ],
))

# --------------------------------------------------------------------------
# 练习（可选验收）
# --------------------------------------------------------------------------

EXERCISES: list[dict[str, Any]] = [
    {
        "id": "form",
        "task_id": "D02",
        "test_command": "python -m pytest -q learner_tests/test_form.py",
        "offline": True,
    },
    {
        "id": "test_utils",
        "task_id": "D15",
        "test_command": "python -m pytest -q learner_tests/test_utils.py",
        "offline": True,
    },
    {
        "id": "test_project",
        "task_id": "D22",
        "test_command": "python -m pytest -q learner_tests/test_project.py",
        "offline": True,
    },
    {
        "id": "test_api",
        "task_id": "D22",
        "test_command": "python -m pytest -q learner_tests/test_api.py",
        "offline": True,
    },
    {
        "id": "test_ai_client",
        "task_id": "D28",
        "test_command": "python -m pytest -q learner_tests/test_ai_client.py",
        "offline": True,
    },
]

# --------------------------------------------------------------------------
# 诊断（可选工具，非主线前置）
# --------------------------------------------------------------------------

DIAGNOSTICS: list[dict[str, Any]] = [
    {
        "id": "D0",
        "title": "Python 环境",
        "critical_cases": ["python_version", "venv_create", "pip_in_venv"],
        "modules": ["py-env"],
        "decision": {"pass": "mastered", "partial": "practice", "fail": "learn"},
    },
    {
        "id": "D1",
        "title": "语法迁移",
        "critical_cases": ["convert_input", "format_output"],
        "modules": ["py-basics"],
        "decision": {"pass": "mastered", "partial": "practice", "fail": "learn"},
    },
    {
        "id": "D2",
        "title": "控制流",
        "critical_cases": ["filter_loop", "boundary_case"],
        "modules": ["py-control"],
        "decision": {"pass": "mastered", "partial": "practice", "fail": "learn"},
    },
    {
        "id": "D3",
        "title": "函数与容器",
        "critical_cases": ["transform_dicts", "group_and_count"],
        "modules": ["py-functions", "py-collections"],
        "decision": {"pass": "practice", "partial": "learn", "fail": "learn"},
    },
    {
        "id": "D4",
        "title": "文件与工程化",
        "critical_cases": ["read_utf8", "missing_path_error"],
        "modules": ["py-files-errors", "py-modules"],
        "decision": {"pass": "practice", "partial": "learn", "fail": "learn"},
    },
    {
        "id": "D5",
        "title": "命令行",
        "critical_cases": ["navigate_files", "pipe_and_redirect"],
        "modules": ["linux-cli"],
        "decision": {"pass": "mastered", "partial": "practice", "fail": "practice"},
    },
]

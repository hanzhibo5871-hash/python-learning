"""Build the checked-in curriculum v3 data from the previous catalog and project contract.

The lesson table below is intentionally explicit: it is the source of truth for the
sequence, titles, exercises and project files. Teaching copy is assembled from each
lesson's own objective/syntax/operation rather than copied from an AI response.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beginner_drills import add_beginner_drills, align_beginner_contracts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "curriculum.json"


def core_specs() -> dict[str, list[dict[str, Any]]]:
    raw = {
        "D02": [
            ("execution", "程序如何执行：语句、缩进块与注释", "读懂 Python 3 从上到下执行语句，并用缩进表达代码块。", "顶层语句按顺序执行；冒号开启代码块，后续必须统一缩进；# 后内容是注释。"),
            ("names", "变量命名、赋值与动态类型", "理解名字绑定对象，而不是把变量看成固定类型的盒子。", "name = value 绑定对象；type() 查看精确类型；isinstance() 检查继承关系。"),
            ("numbers", "int、float、算术与比较", "用整数和浮点数完成计算，并读懂比较表达式的布尔结果。", "+、-、*、/、//、%、** 产生不同数值；== 比值，is 不用来比较普通数字。"),
            ("bool-none", "bool、None 与真值", "区分 False、None、空容器和非空值在条件中的含义。", "if value 使用真值；value is None 专门判断 None；bool(value) 可显式观察转换。"),
            ("strings", "字符串字面量、索引切片与不可变性", "读写字符串中的位置和片段，并理解字符串不能原地修改。", "s[i] 取单个字符，s[start:stop:step] 切片；修改要创建新字符串。"),
            ("string-methods", "字符串方法与 f-string", "用 strip、split、join 等方法清洗文本，并安全插入变量。", "方法返回新值；f'{name}: {value}' 在运行时格式化表达式结果。"),
        ],
        "D03": [
            ("if", "if、elif、else 与边界", "根据条件选择一条执行路径，并把边界值写成明确规则。", "if 条件: 开启分支；elif 可继续判断；else 处理剩余情况。"),
            ("match", "基础 match/case", "用 match 表达有限的结构匹配，同时知道何时 if 更清楚。", "match value: 下接 case 模式；case _ 是兜底，不等同于任意复杂条件。"),
            ("for", "for 遍历与 range", "逐项处理可迭代对象，并用 range 生成整数序列。", "for item in iterable:；range(stop)、range(start, stop, step) 的终点不包含。"),
            ("while", "while 条件循环与终止", "让循环由状态变化自然结束，避免死循环。", "while condition: 每轮重新判断；循环体必须改变最终会影响 condition 的状态。"),
            ("break-continue", "break、continue 与控制流", "在搜索和过滤中提前结束或跳过当前轮，而不破坏循环结构。", "break 结束最近一层循环；continue 跳到下一轮条件判断。"),
            ("enumerate-zip", "enumerate、zip 与并行遍历", "同时获得序号，或把两组数据按位置配对。", "enumerate(items, start=0) 生成序号和值；zip 在最短输入处停止。"),
            ("comprehension", "列表、集合与字典推导式", "把简单的遍历和过滤写成可读的推导式。", "[expr for item in source if condition]；结果容器由外层括号决定。"),
        ],
        "D04": [
            ("def-return", "函数定义、调用与 return", "把重复逻辑封装成可命名、可测试的函数。", "def name(parameters) -> return_type:；return 立即结束函数，省略时返回 None。"),
            ("default-keyword", "默认参数与关键字参数", "用默认值减少重复传参，并用关键字提升调用可读性。", "默认参数必须放在无默认参数之后；调用时可写 name(value=...)。"),
            ("varargs", "*args、**kwargs 收集与解包", "处理数量可变的位置参数和关键字参数。", "*args 收集 tuple，**kwargs 收集 dict；调用时的 * 与 ** 是解包。"),
            ("scope", "局部作用域与 LEGB", "理解函数内部名字的查找顺序，避免误改外部变量。", "Local、Enclosing、Global、Builtins 依次查找；函数赋值默认创建局部名字。"),
            ("global-nonlocal", "global、nonlocal 与闭包状态", "明确什么时候需要修改外层绑定，并看见闭包保存的状态。", "global 指向模块级名字；nonlocal 指向最近的外层函数绑定。"),
            ("lambda", "lambda 与 key 函数", "用短小 lambda 表达一次性计算，并知道复杂逻辑应回到 def。", "lambda parameters: expression 只能有一个表达式；sorted(items, key=lambda x: ...) 常见。"),
            ("type-hints", "类型标注与 Callable", "用标注表达输入输出契约，同时知道 Python 运行时不会自动强制类型。", "name: str -> str；list[int]、dict[str, int] 和 Callable 描述容器与函数。"),
        ],
        "D05": [
            ("list-tuple", "list、tuple、索引切片与修改", "按顺序保存数据，并选择可变 list 或不可变 tuple。", "list.append/insert/pop 修改原对象；tuple 创建后不能赋值。"),
            ("dict-set", "dict、set 的创建与增删改", "用 dict 建立键值关系，用 set 表示无重复集合。", "d[key] 读写字典；set.add/discard 修改集合；字典键必须可哈希。"),
            ("mutability", "可变性、引用别名与复制", "观察两个名字指向同一 list 的后果，并用 copy 得到独立外层对象。", "b = a 是同一对象；b = a.copy() 只复制一层；嵌套数据还要理解浅复制。"),
            ("unpacking", "序列解包与字典解包", "用解包减少索引噪音，并识别数量不匹配错误。", "a, b = pair；first, *middle, last = values；{**left, **right} 合并字典。"),
            ("traversal", "嵌套容器遍历与安全访问", "逐层读取真实业务数据，避免把键、值和元素混为一谈。", "for key, value in mapping.items()；链式访问前先确认容器形状。"),
            ("comprehensions", "多种推导式的过滤与转换", "根据输入和输出类型选择 list/set/dict 推导式，并保持可读。", "推导式的表达式先计算，再按条件保留；复杂嵌套应拆成普通循环。"),
            ("iterators-generators", "迭代器协议与生成器 yield", "理解 next 如何逐步取值，并用生成器延迟产生结果。", "iter(obj) 得到迭代器；next(it) 可能抛 StopIteration；yield 暂停并保存局部状态。"),
        ],
        "D06": [
            ("exception-types", "常见异常类型与原因", "从异常类型反推错误位置，而不是用一个宽泛 except 掩盖问题。", "ValueError 是值不合适；TypeError 是类型/参数不合适；KeyError 和 IndexError 指向访问边界。"),
            ("try-except", "try/except 精确捕获", "把可恢复的输入错误转成用户能理解的反馈。", "try 包含可能失败的语句；except SomeError 只捕获预期异常。"),
            ("else-finally", "else、finally 的执行时机", "区分成功分支和必做清理，保证文件等资源被释放。", "else 只在 try 无异常时执行；finally 无论成功失败都会执行。"),
            ("raise", "raise、异常链与输入校验", "主动拒绝不符合业务规则的输入，并保留底层原因。", "raise ValueError('...')；raise NewError(...) from exc 建立异常链。"),
            ("custom", "自定义异常与业务语义", "用异常类区分领域错误，让调用者能精确处理。", "class InputError(ValueError): pass；自定义异常仍可继承已有异常类型。"),
            ("with", "with 与上下文管理器", "用 with 管理文件等资源，理解进入和退出阶段的清理保证。", "with expression as target:；退出时自动调用上下文管理器的 __exit__。"),
        ],
        "D07": [
            ("import", "import、from import 与命名空间", "把功能拆到模块，并理解导入后名字来自哪个命名空间。", "import module；from module import name；as 只改变当前文件中的别名。"),
            ("package", "包、__init__.py 与相对导入", "组织多文件代码，区分包标记、绝对导入和相对导入。", "目录含 __init__.py 即可作为传统包；from .module import name 只在包上下文使用。"),
            ("main", "__name__ 守卫与可导入入口", "让文件既能被测试导入，又能作为命令行入口运行。", "if __name__ == '__main__': 只在直接执行该文件时运行。"),
            ("stdlib", "标准库查找与组合使用", "用 pathlib、json、datetime 等标准库完成小功能，不重复造轮子。", "标准库模块先 import，再用清晰的函数边界组合；查文档确认参数而不是猜。"),
            ("class-instance", "类、实例、属性与方法", "把相关状态和行为放在对象中，并理解 self 指向当前实例。", "class Name:；方法首参数 self；Name() 创建实例并拥有独立属性。"),
            ("inheritance", "继承、super 与方法重写", "读懂基础继承，并判断组合是否比继承更合适。", "class Child(Parent):；super() 调父类实现；重写方法要保持可替换契约。"),
            ("dataclass", "dataclass、字段默认值与标注", "用 dataclass 减少样板代码，同时为数据对象声明字段。", "@dataclass 自动生成 __init__/repr；可变默认值要用 field(default_factory=...)。"),
        ],
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for task_id, items in raw.items():
        result[task_id] = [
            {"id": f"{task_id}-{slug}", "title": title, "objective": objective, "syntax": syntax}
            for slug, title, objective, syntax in items
        ]
    return result


def common_specs() -> dict[str, list[dict[str, Any]]]:
    raw: dict[str, list[tuple[str, str, str, str]]] = {
        "D08": [
            ("pathlib", "路径对象与目录遍历", "用 Path 表达跨平台路径并筛选文件。", "Path /、glob、suffix 和 relative_to 组合出可测试的路径操作。"),
            ("utf8", "UTF-8 文本读写与编码边界", "用明确编码读写中文文本。", "read_text/write_text 显式 encoding='utf-8'，避免依赖系统默认编码。"),
            ("json-read", "JSON 读取与类型检查", "把 JSON 外部数据转换成受检查的 Python 结构。", "json.loads/load 负责解析，解析后仍要检查 list/dict 和字段类型。"),
            ("json-report", "统计并写回 JSON 报告", "从记录计算报告并稳定地写出 JSON。", "json.dump 的 ensure_ascii、indent 和 sort_keys 影响可读性与可重复性。"),
        ],
        "D09": [("parser", "argparse 基本参数", "把命令行字符串解析成结构化参数。", "ArgumentParser、add_argument、parse_args 组成最小 CLI。"), ("subcommands", "子命令与参数分派", "让一个入口承载多个清晰动作。", "add_subparsers 和 set_defaults 把命令映射到处理函数。"), ("errors", "参数错误与退出码", "让错误出现在 stderr 并用非零退出码告知调用者。", "parser.error 会退出；业务失败要保持稳定的 exit code。"), ("entry", "可执行入口与命令行回归", "从子进程观察真实命令行为。", "__main__ 守卫、sys.argv 与 subprocess 共同构成可回归入口。"),],
        "D10": [("env", "环境变量读取与默认值", "不把环境相关值写死在代码中。", "os.environ.get 读取字符串；默认值必须明确写在配置边界。"), ("convert", "配置类型转换与错误", "把字符串配置转换为 int/bool 并处理非法值。", "转换失败要有明确策略，不能把任意非空字符串当 True。"), ("dotenv", ".env 文件解析", "用小而清晰的解析器读取本地配置文件。", "逐行处理空行、注释、等号和首尾空白，不执行文件内容。"), ("config", "组合成 Settings 配置对象", "用一个配置对象传递稳定的运行参数。", "dataclass 把字段、默认值和来源集中起来，环境变量优先级要可解释。"),],
        "D11": [("logger", "logger、级别与传播", "建立可复用且不会重复输出的 logger。", "getLogger、setLevel、propagate 和 handler 数量共同决定日志路径。"), ("format", "formatter 与结构化上下文", "让日志包含定位问题需要的时间、级别和名称。", "Formatter 的格式字符串决定每条记录的可读字段。"), ("stream", "控制台 handler 与错误级别", "区分正常信息与需要关注的警告/错误。", "StreamHandler 和 level 组合决定控制台看到什么。"), ("file", "文件日志与资源关闭", "把重要运行记录持久化到文件并清理 handler。", "FileHandler 需要明确编码和关闭时机，测试要使用临时目录。"),],
        "D12": [("request", "urllib 请求对象与 GET", "构造可检查的 GET 请求并解析响应。", "Request、urlopen、response.read 和 json.loads 是基本链路。"), ("response", "状态码、响应体与 JSON 错误", "把 HTTP 和数据格式错误分成不同原因。", "HTTPError/URLError 与 JSONDecodeError 需要分别处理并保留上下文。"), ("post", "POST JSON 与 Content-Type", "把 Python 数据编码成 UTF-8 JSON 发送。", "data=json.dumps(...).encode('utf-8')，Content-Type 必须是 application/json。"), ("timeout", "timeout、网络错误与测试边界", "控制等待时间并让网络客户端可离线测试。", "timeout 作为参数传入；mock opener 才是单测中的网络边界。"),],
        "D13": [("app", "FastAPI app 与健康检查", "创建最小可运行 Web 应用。", "FastAPI()、装饰器路由和 JSON 返回值构成最小接口。"), ("route", "路径参数与查询参数", "让 URL 中的数据进入类型明确的函数参数。", "路径模板和函数参数名称对应，查询参数可提供默认值。"), ("response", "响应模型与状态码", "把 API 输出契约写进模型和状态码。", "response_model 和 status_code 让客户端知道返回结构。"), ("lifecycle", "应用生命周期与依赖函数", "在启动/关闭时管理资源，并让依赖可替换。", "lifespan 负责生命周期，Depends 负责请求范围依赖。"),],
        "D14": [("model", "Pydantic 请求体校验", "让非法输入在进入业务逻辑前被拒绝。", "BaseModel 字段、类型和约束自动生成 422。"), ("service", "路由与业务函数分离", "让业务规则可以不依赖 HTTP 单独测试。", "路由负责协议，service 负责判断和数据操作。"), ("errors", "HTTPException 与错误契约", "让不存在和冲突有稳定状态码。", "HTTPException(status_code, detail) 是显式的 API 错误边界。"), ("deps", "依赖注入与可替换数据源", "用依赖覆盖把测试和运行数据源分开。", "Depends 和 app.dependency_overrides 让同一接口使用不同存储。"),],
        "D15": [("assert", "pytest 测试函数与断言", "用小测试锁定成功、边界和异常行为。", "以 test_ 开头的函数由 pytest 收集，assert 表达期望。"), ("fixture", "fixture、tmp_path 与隔离", "为测试提供可重复且互不污染的资源。", "fixture 返回准备好的对象，tmp_path 提供临时目录。"), ("mock", "mock 隔离 HTTP", "不联网也能验证客户端调用协议。", "patch 替换边界对象，assert_called_once_with 检查调用。"), ("api", "TestClient API 回归", "把 HTTP 请求作为测试输入验证完整路由。", "TestClient 发送请求并检查 status_code 和 JSON。"),],
        "D16": [("connect", "sqlite3 连接与关闭", "建立临时数据库连接并明确资源边界。", "sqlite3.connect、row_factory 和 close 组成连接生命周期。"), ("schema", "建表、主键与默认值", "用幂等建表准备稳定数据结构。", "CREATE TABLE IF NOT EXISTS、PRIMARY KEY 和 DEFAULT 形成约束。"), ("crud", "参数化 SQL 增删改查", "用参数绑定实现安全 CRUD。", "问号占位符和参数 tuple 分离 SQL 结构与数据。"), ("transaction", "事务、回滚与资源边界", "理解 commit/rollback 如何保护一组操作。", "成功 commit，异常 rollback，finally 负责关闭连接。"),],
        "D17": [("coroutine", "async 函数、await 与 asyncio.run", "运行第一个可等待函数并理解暂停点。", "async def 定义协程，await 等待结果，asyncio.run 创建运行入口。"), ("gather", "gather 并发聚合与顺序", "同时等待多个 IO 任务并收集结果。", "asyncio.gather 返回顺序与传入 awaitable 顺序一致。"), ("timeout", "wait_for 超时与取消", "给异步操作设置时间边界并处理取消。", "asyncio.wait_for 超时会取消内部任务并抛 TimeoutError。"), ("boundary", "异步错误边界与测试", "覆盖成功、异常、超时而不依赖真实服务。", "异步测试要明确事件循环入口和 cleanup。"),],
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for task_id, items in raw.items():
        result[task_id] = [{"id": f"{task_id}-{slug}", "title": title, "objective": objective, "syntax": syntax} for slug, title, objective, syntax in items]
    return result


def project_specs() -> dict[str, list[dict[str, Any]]]:
    raw = {
        "D18": [
            ("scope", "需求边界与用户故事", "把四个用户故事和非目标写清楚。", "requirements", "docs/requirements.md", []),
            ("acceptance", "验收清单与运行场景", "把用户故事拆成可观察的成功和失败场景。", "requirements", "docs/requirements.md", []),
            ("data-contract", "数据模型与 JSON 契约", "定义 Task 字段、done 表示和错误响应结构。", "contract", "contract.json", ["docs/requirements.md"]),
            ("api-contract", "API 路由契约与验收映射", "定义 CRUD 路径、输入输出和状态码。", "contract", "contract.json", ["contract.json"]),
        ],
        "D19": [
            ("pyproject", "打包配置与测试命令", "只写项目元数据、运行依赖和 pytest dev 依赖。", "pyproject", "pyproject.toml", ["docs/requirements.md", "contract.json"]),
            ("package", "包目录与 __init__.py", "创建包标记和公开版本常量。", "package", "taskproj/__init__.py", ["pyproject.toml"]),
            ("config", "配置模块与数据库路径", "从环境变量和默认值得到数据库路径。", "config", "taskproj/config.py", ["taskproj/__init__.py"]),
            ("main", "项目入口", "写最小可导入入口并说明它与 API/CLI 的关系。", "main", "taskproj/main.py", ["taskproj/config.py"]),
            ("readme", "README 启动说明", "把从零安装、测试和启动命令写给下一位开发者。", "readme", "README.md", ["taskproj/main.py"]),
        ],
        "D20": [
            ("connection", "连接生命周期与建表", "实现连接、row_factory 和幂等建表。", "db", "taskproj/db.py", ["taskproj/config.py"]),
            ("create-list", "新增与列表查询", "实现参数化新增和稳定排序列表。", "db", "taskproj/db.py", ["taskproj/db.py"]),
            ("update-delete", "完成与删除", "实现完成和删除并区分未知 ID。", "db", "taskproj/db.py", ["taskproj/db.py"]),
            ("db-tests", "数据层回归与事务", "先在临时目录中为真实数据层设计 CRUD 和事务测试。", "project-test", None, ["taskproj/__init__.py", "taskproj/db.py"]),
        ],
        "D21": [
            ("app", "FastAPI app 与 lifespan", "创建 app、连接依赖和健康检查。", "api", "taskproj/api.py", ["taskproj/db.py", "taskproj/config.py"]),
            ("schema", "Task 输入输出模型", "根据 contract 定义请求和响应模型。", "api", "taskproj/api.py", ["taskproj/api.py", "contract.json"]),
            ("crud-routes", "CRUD 路由与错误", "分步接入列表、新增、完成、删除路由。", "api", "taskproj/api.py", ["taskproj/api.py", "taskproj/db.py"]),
            ("static", "静态首页挂载与错误边界", "挂载网页目录并保留显式业务错误；完整首页在 D23 分步完成。", "api", "taskproj/api.py", ["taskproj/api.py"]),
        ],
        "D22": [
            ("db-fixtures", "数据层 fixture 与隔离", "把临时 DB fixture 接入已有 CRUD 测试并落成项目测试文件。", "project-test", "tests/test_project.py", ["taskproj/db.py"]),
            ("api-tests", "API TestClient 基础回归", "覆盖健康、列表、新增、完成、删除。", "api-test", "tests/test_api.py", ["taskproj/__init__.py", "taskproj/api.py", "taskproj/db.py", "taskproj/config.py"]),
            ("api-errors", "API 错误与边界回归", "覆盖空标题、未知 ID 和错误 detail。", "api-test", "tests/test_api.py", ["taskproj/api.py", "taskproj/db.py", "taskproj/config.py", "tests/test_api.py", "contract.json"]),
            ("acceptance", "公开验收脚本与失败定位", "把数据层、API 和契约检查串成可定位测试。", "api-test", "tests/test_api.py", ["taskproj/api.py", "taskproj/db.py", "taskproj/config.py", "tests/test_api.py", "tests/test_project.py"]),
        ],
        "D23": [
            ("cli-parser", "CLI 子命令与共享配置", "接入 argparse、add/list 和共享连接。", "cli", "taskproj/cli.py", ["taskproj/__init__.py", "taskproj/config.py", "taskproj/db.py"]),
            ("cli-mutate", "CLI 完成/删除与退出码", "接入 done/rm、未知 ID 和错误码。", "cli", "taskproj/cli.py", ["taskproj/cli.py", "taskproj/config.py", "taskproj/db.py"]),
            ("html-structure", "原生网页结构与可访问控件", "写列表、输入框和四类按钮的 HTML 骨架。", "html", "taskproj/static/index.html", ["contract.json"]),
            ("html-fetch", "fetch 渲染与 CRUD 交互", "分步接入 GET/POST/PATCH/DELETE 和 DOM 更新。", "html", "taskproj/static/index.html", ["taskproj/static/index.html", "taskproj/api.py"]),
        ],
        "D24": [
            ("rebuild", "从空目录重建与安装", "写出创建 venv、安装和跑测试的命令序列。", "runbook", "docs/runbook.md", ["README.md", "pyproject.toml"]),
            ("integrate", "API、CLI、网页集成演示", "记录三种入口的启动和预期结果。", "runbook", "docs/runbook.md", ["docs/runbook.md", "taskproj/api.py", "taskproj/cli.py"]),
            ("artifacts", "15 个真实产物核对", "对照契约清点文件、依赖链和验收输出。", "runbook", "docs/runbook.md", ["docs/runbook.md", "contract.json"]),
            ("review", "项目复盘与交付证据", "说明需求、失败修正、复用边界和下一步。", "review", "docs/review.md", ["docs/runbook.md"]),
        ],
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for task_id, items in raw.items():
        result[task_id] = [
            {"id": f"{task_id}-{slug}", "title": title, "objective": objective, "syntax": kind, "project_file": project_file, "workspace_deps": deps}
            for slug, title, objective, kind, project_file, deps in items
        ]
    return result


CORE_EXAMPLES: dict[str, list[tuple[str, str, str]]] = {
    "D02-execution": [("print('第一句')\nif True:\n    print('缩进块')", "第一句\n缩进块", "顶层 print 先执行；冒号后的代码块必须统一缩进四个空格。"), ("# 这行不会执行\nvalue = 2\nprint(value)", "2", "井号后的内容是给人看的注释，解释器只执行赋值和 print。")],
    "D02-names": [("value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))", "int\nTrue", "名字先绑定整数对象，type 观察精确类型，isinstance 检查是否属于某个类型体系。"), ("value = '七'\nprint(type(value).__name__)", "str", "同一个名字后来可以绑定字符串，这就是动态类型；它不等于没有类型。")],
    "D02-numbers": [("total = 7 // 2\nremainder = 7 % 2\nprint(total, remainder)", "3 1", "整除和取余分别回答商与余数，适合分页和周期计算。"), ("print(3 < 5)\nprint(0.1 + 0.2 == 0.3)", "True\nFalse", "比较表达式产生 bool；浮点数可能有二进制表示误差，不能盲信相等。")],
    "D02-bool-none": [("for value in [None, 0, '', [] , [1]]:\n    print(value is None, bool(value))", "True False\nFalse False\nFalse False\nFalse False\nFalse True", "is None 只判断 None，bool 则观察任意对象的真值。"), ("name = ''\nif not name:\n    print('需要输入')", "需要输入", "空字符串是假值，not 可以表达“没有输入”的分支。")],
    "D02-strings": [("text = 'Python'\nprint(text[0])\nprint(text[1:4])", "P\nyth", "索引取一个字符，切片的 stop 不包含在结果中。"), ("text = '猫'\nnew_text = text + '和狗'\nprint(text, new_text)", "猫 猫和狗", "字符串不可变；拼接得到新字符串，原来的 text 没有被原地改写。")],
    "D02-string-methods": [("raw = '  a,b  '\nparts = raw.strip().split(',')\nprint('|'.join(parts))", "a|b", "strip 先去首尾空白，split 再拆分，join 把多个字符串重新组合。"), ("name = '小林'\ncount = 3\nprint(f'{name} 有 {count} 个任务')", "小林 有 3 个任务", "f-string 在花括号中求值并转成文本，适合构造清晰消息。")],
    "D03-if": [("score = 89\nif score >= 90:\n    level = 'A'\nelif score >= 60:\n    level = 'B'\nelse:\n    level = 'C'\nprint(level)", "B", "分支按上到下检查，命中 elif 后不会继续执行后面的分支。"), ("age = 18\nprint('成人' if age >= 18 else '未成年')", "成人", "条件表达式适合很短的二选一；多步规则仍用普通 if 更易读。")],
    "D03-match": [("command = 'list'\nmatch command:\n    case 'list':\n        print('查看')\n    case 'add':\n        print('新增')\n    case _:\n        print('未知')", "查看", "case 按模式匹配值，case _ 是兜底分支。"), ("point = (0, 4)\nmatch point:\n    case (0, y):\n        print(y)", "4", "match 也能拆开元组结构；只用几个比较条件时 if 可能更直白。")],
    "D03-for": [("for number in range(1, 4):\n    print(number)", "1\n2\n3", "range 的 stop 不包含在序列中，所以 range(1, 4) 产生 1、2、3。"), ("total = 0\nfor value in [2, 5, 3]:\n    total += value\nprint(total)", "10", "for 从可迭代对象逐项取值，循环体负责处理当前项。")],
    "D03-while": [("remaining = 3\nwhile remaining:\n    print(remaining)\n    remaining -= 1", "3\n2\n1", "每轮开始重新判断条件，循环体必须改变 remaining 才能最终结束。"), ("answer = ''\nwhile answer != 'yes':\n    answer = 'yes'\nprint('继续')", "继续", "while 适合等待状态变化；真实输入场景还要为退出和异常设计边界。")],
    "D03-break-continue": [("for number in range(6):\n    if number == 2:\n        continue\n    if number == 5:\n        break\n    print(number)", "0\n1\n3\n4", "continue 跳过当前轮，break 结束最近一层循环。"), ("items = [3, 8, 4]\nfor item in items:\n    if item > 5:\n        print(item)\n        break", "8", "搜索到目标后 break 可以避免无意义的继续遍历。")],
    "D03-enumerate-zip": [("names = ['安', '博']\nfor index, name in enumerate(names, start=1):\n    print(index, name)", "1 安\n2 博", "enumerate 同时提供序号和值，start=1 让展示序号从一开始。"), ("for name, score in zip(['安', '博'], [90, 80]):\n    print(name, score)", "安 90\n博 80", "zip 按位置配对，在最短输入结束时停止。")],
    "D03-comprehension": [("squares = [n * n for n in range(4)]\nprint(squares)", "[0, 1, 4, 9]", "先遍历 n，再计算 n*n，最后组成新的 list。"), ("even = {n: n * n for n in range(5) if n % 2 == 0}\nprint(even)", "{0: 0, 2: 4, 4: 16}", "字典推导式同时写键和值；条件只保留偶数输入。")],
    "D04-def-return": [("def area(width, height):\n    return width * height\nprint(area(3, 4))", "12", "def 创建可调用的函数，return 把结果交给调用者并结束本次调用。"), ("def greet(name):\n    print('你好', name)\nprint(greet('林'))", "你好 林\nNone", "函数只 print 而没有 return 时，返回值是 None。")],
    "D04-default-keyword": [("def greet(name, prefix='你好'):\n    return f'{prefix}，{name}'\nprint(greet('林'))", "你好，林", "默认参数在调用者省略值时生效。"), ("def greet(name, prefix='你好'):\n    return f'{prefix}，{name}'\nprint(greet('林', prefix='早上好'))", "早上好，林", "关键字参数把值绑定到参数名，可读性比依赖位置更好。")],
    "D04-varargs": [("def total(*numbers):\n    return sum(numbers)\nprint(total(1, 2, 3))", "6", "*args 在函数内部是 tuple，适合收集数量不定的位置参数。"), ("def show(**options):\n    print(options)\nshow(color='blue', size=2)", "{'color': 'blue', 'size': 2}", "**kwargs 在函数内部是 dict，调用时可用 ** 解包字典。")],
    "D04-scope": [("value = '外层'\ndef read():\n    value = '局部'\n    return value\nprint(read(), value)", "局部 外层", "函数内赋值默认创建局部名字，不会自动改掉模块级 value。"), ("name = '模块'\ndef show():\n    print(name)\nshow()", "模块", "LEGB 查找会从局部、外层、全局到内置名字寻找引用。")],
    "D04-global-nonlocal": [("counter = 0\ndef add_global():\n    global counter\n    counter += 1\nadd_global()\nprint(counter)", "1", "global 明确允许函数重新绑定模块级名字。"), ("def make_counter():\n    value = 0\n    def step():\n        nonlocal value\n        value += 1\n        return value\n    return step\nstep = make_counter()\nprint(step(), step())", "1 2", "nonlocal 修改最近外层函数的绑定，闭包因此能保存状态。")],
    "D04-lambda": [("items = [('a', 3), ('b', 1)]\nprint(sorted(items, key=lambda item: item[1]))", "[('b', 1), ('a', 3)]", "lambda 适合表达一次性的短 key 函数。"), ("double = lambda number: number * 2\nprint(double(4))", "8", "lambda 只有一个表达式；复杂逻辑应改成有名字的 def。")],
    "D04-type-hints": [("def repeat(text: str, times: int) -> str:\n    return text * times\nprint(repeat('好', 2))", "好好", "标注表达输入输出契约，但 Python 运行时不会因此自动转换类型。"), ("from collections.abc import Callable\ndef apply(fn: Callable[[int], int], value: int) -> int:\n    return fn(value)\nprint(apply(lambda x: x + 1, 2))", "3", "Callable 描述函数形状，帮助读者和工具理解回调。")],
    "D05-list-tuple": [("items = ['a', 'b']\nitems.append('c')\nprint(items)", "['a', 'b', 'c']", "list 可变，append 会在原列表末尾增加元素。"), ("point = (3, 4)\nprint(point[0], point[1])", "3 4", "tuple 适合表示固定结构，创建后不能给某个位置重新赋值。")],
    "D05-dict-set": [("task = {'title': '买书', 'done': False}\ntask['done'] = True\nprint(task)", "{'title': '买书', 'done': True}", "dict 用键访问和更新值。"), ("tags = {'python', 'python', 'test'}\ntags.add('cli')\nprint(sorted(tags))", "['cli', 'python', 'test']", "set 自动去重，add 增加元素且不保证插入顺序。")],
    "D05-mutability": [("items = ['a']\nalias = items\nalias.append('b')\nprint(items)", "['a', 'b']", "赋值只复制引用，alias 和 items 指向同一个 list。"), ("items = ['a']\ncopy_items = items.copy()\ncopy_items.append('b')\nprint(items, copy_items)", "['a'] ['a', 'b']", "copy 产生新的外层列表；嵌套对象仍需考虑浅复制。")],
    "D05-unpacking": [("first, *middle, last = [1, 2, 3, 4]\nprint(first, middle, last)", "1 [2, 3] 4", "带星号的目标收集剩余元素。"), ("left = {'a': 1}\nright = {**left, 'b': 2}\nprint(right)", "{'a': 1, 'b': 2}", "** 在字典字面量中展开已有键值。")],
    "D05-traversal": [("scores = {'安': 90, '博': 80}\nfor name, score in scores.items():\n    print(name, score)", "安 90\n博 80", "items 返回键和值的配对，避免把字典键误当成完整记录。"), ("rows = [{'title': 'A'}, {'title': 'B'}]\nfor row in rows:\n    print(row['title'])", "A\nB", "嵌套数据要先确认每一层的容器形状再访问。")],
    "D05-comprehensions": [("values = [1, 2, 3, 4]\nprint([v * 10 for v in values if v % 2 == 0])", "[20, 40]", "列表推导式把转换和过滤放在同一条清晰规则里。"), ("print({word: len(word) for word in ['py', 'test']})", "{'py': 2, 'test': 4}", "字典推导式让输入元素同时生成键和值。")],
    "D05-iterators-generators": [("def numbers():\n    yield 1\n    yield 2\niterator = iter(numbers())\nprint(next(iterator), next(iterator))", "1 2", "yield 暂停函数并保存局部状态，next 每次恢复到下一个 yield。"), ("squares = (n * n for n in range(3))\nprint(list(squares))", "[0, 1, 4]", "生成器表达式延迟产生值，不必先创建完整列表。")],
    "D06-exception-types": [("try:\n    int('x')\nexcept ValueError as error:\n    print(type(error).__name__)", "ValueError", "异常类型说明失败原因；先捕获预期类型比裸 except 更安全。"), ("try:\n    {}['missing']\nexcept KeyError:\n    print('缺少键')", "缺少键", "KeyError 指向字典键不存在，而不是任意输入错误。")],
    "D06-try-except": [("try:\n    value = int('42')\nexcept ValueError:\n    value = 0\nprint(value)", "42", "try 放可能失败的语句，except 只处理调用者能恢复的异常。"), ("try:\n    int('x')\nexcept ValueError as error:\n    print(f'输入无效: {error}')", "输入无效: invalid literal for int() with base 10: 'x'", "把异常转成用户能理解的反馈，但不要丢掉类型和原因。")],
    "D06-else-finally": [("try:\n    value = int('4')\nexcept ValueError:\n    print('失败')\nelse:\n    print('成功', value)\nfinally:\n    print('清理')", "成功 4\n清理", "else 只在 try 成功时运行，finally 无论结果如何都运行。"), ("try:\n    raise RuntimeError('坏了')\nfinally:\n    print('释放资源')", "释放资源", "finally 适合关闭文件、连接等必须清理的资源。")],
    "D06-raise": [("def positive(value):\n    if value <= 0:\n        raise ValueError('必须为正数')\n    return value\nprint(positive(3))", "3", "raise 主动拒绝不符合业务规则的输入。"), ("try:\n    int('x')\nexcept ValueError as error:\n    raise RuntimeError('解析失败') from error", "（抛出 RuntimeError，并保留 __cause__）", "from 建立异常链，让上层知道业务错误来自哪个底层原因。")],
    "D06-custom": [("class InputError(ValueError):\n    pass\ntry:\n    raise InputError('姓名为空')\nexcept InputError as error:\n    print(type(error).__name__)", "InputError", "自定义异常继承 ValueError，调用者可以按领域语义捕获它。"), ("class AgeError(Exception):\n    pass\nprint(issubclass(AgeError, Exception))", "True", "异常类仍是普通类，可以表达比字符串消息更稳定的分支。")],
    "D06-with": [("from pathlib import Path\npath = Path('demo.txt')\nwith path.open('w', encoding='utf-8') as stream:\n    stream.write('你好')\nprint(path.read_text(encoding='utf-8'))\npath.unlink()", "你好", "文件句柄由 with 管理，即使中途异常也能执行关闭。"), ("from io import StringIO\nwith StringIO('hello') as stream:\n    print(stream.read())", "hello", "with 进入上下文并在离开时调用清理逻辑。")],
    "D07-import": [("import math\nprint(math.ceil(2.1))", "3", "import module 后通过模块命名空间访问成员。"), ("from pathlib import Path as P\nprint(P('a.txt').name)", "a.txt", "from import 直接取成员，as 只改变当前文件里的别名。")],
    "D07-package": [("# 包中的模块可以用绝对导入\nfrom pathlib import Path\nprint(Path('taskproj').name)", "taskproj", "包把多个模块组织成可复用的命名空间；相对导入要在包上下文运行。"), ("import json\ndata = json.loads('{\"ok\": true}')\nprint(data['ok'])", "True", "模块边界让功能可以独立导入和测试。")],
    "D07-main": [("def main():\n    print('直接运行')\nif __name__ == '__main__':\n    main()", "直接运行", "__name__ 守卫只在直接执行文件时调用入口，导入测试不会产生副作用。"), ("print(__name__)", "__main__（直接运行时）", "同一文件被导入时 __name__ 会变成模块名。")],
    "D07-stdlib": [("from datetime import date\nprint(date(2025, 1, 2).isoformat())", "2025-01-02", "标准库提供经过维护的通用能力，先查清 API 再组合。"), ("from pathlib import Path\nprint(Path('a.txt').suffix)", ".txt", "pathlib 等标准库对象比手写字符串拼路径更可靠。")],
    "D07-class-instance": [("class Task:\n    def __init__(self, title):\n        self.title = title\n    def label(self):\n        return self.title\ntask = Task('学习')\nprint(task.label())", "学习", "self 指向当前实例，每个 Task 可以保存自己的 title。"), ("class Counter:\n    def __init__(self):\n        self.value = 0\n    def inc(self):\n        self.value += 1\nc = Counter()\nc.inc()\nprint(c.value)", "1", "方法把状态和改变状态的行为放在同一个对象中。")],
    "D07-inheritance": [("class Animal:\n    def speak(self):\n        return '...'\nclass Dog(Animal):\n    def speak(self):\n        return super().speak() + '汪'\nprint(Dog().speak())", "...汪", "子类可以重写方法，并用 super 复用父类实现。"), ("class Base:\n    def __init__(self, name):\n        self.name = name\nclass Child(Base):\n    pass\nprint(Child('小林').name)", "小林", "没有重写时，子类实例可以继承父类初始化逻辑。")],
    "D07-dataclass": [("from dataclasses import dataclass\n@dataclass\nclass Point:\n    x: int\n    y: int\nprint(Point(1, 2))", "Point(x=1, y=2)", "dataclass 根据标注自动生成初始化和 repr，适合纯数据对象。"), ("from dataclasses import dataclass, field\n@dataclass\nclass Bag:\n    items: list[str] = field(default_factory=list)\nprint(Bag())", "Bag(items=[])", "可变默认值要用 default_factory，避免不同实例共享同一个 list。")],
}


# The explicit common/project tables are loaded before the shared normalizer below.
# Keep the early names structurally valid; later records extend the same mappings.
def _detail(
    explanation: list[str],
    js_bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, ...]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    return {
        "explanation": explanation,
        "js_bridge": js_bridge,
        "common_errors": [
            {"error": error, "symptom": symptom, "cause": cause, "fix": fix,
             "example": {"code": code, "symptom": symptom, "fix": fix}}
            for error, symptom, cause, fix, code in errors
        ],
        "guided_practice": {
            "goal": goal,
            "starter": starter,
            "steps": [
                {
                    "action": step[0] if len(step) == 2 else f"{step[0]}：{step[1]}",
                    "expected": step[-1],
                }
                for step in steps
            ],
            "check": check,
        },
        "input_examples": [{"label": label, "value": value, "expected": result} for label, value, result in inputs],
        "practice": {"instructions": instructions, "expected_behavior": expected, "starter_content": starter},
    }


def _manual_detail(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _detail(*args, **kwargs)


def _project_lesson(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _detail(*args, **kwargs)


def _explicit_dev(
    topic: str,
    explanation: list[str],
    bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, str]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    result = _detail(explanation, bridge, errors, goal, starter, steps, check, inputs, instructions, expected)
    result["topic"] = topic
    return result


NONCORE_TEACHING: dict[str, dict[str, Any]] = {}
PROJECT_TEACHING: dict[str, dict[str, Any]] = {}


NONCORE_TEACHING.update({
    "D14-model": _explicit_dev("Pydantic model", [
        "Pydantic BaseModel 把请求 JSON 转成带字段的 Python 对象，并按标注做类型和必填校验；模型描述的是输入边界而不是数据库表。",
        "缺字段、错误类型和额外字段是否允许，取决于字段声明。让 422 在 API 边界发生，比业务函数收到半成品 dict 更容易排查。",
        "测试发送真实 JSON，检查 model_dump 和错误 detail；不要在路由里手动把所有字符串转成目标类型。",
    ], "Pydantic 是运行时 schema，区别于只靠 TypeScript 编译期类型", [
        ("字段默认", "缺 title 仍通过", "title 有空字符串默认", "使用无默认 str", "class TaskIn(BaseModel): title: str = ''"),
        ("手动转换", "坏数字到业务层才报错", "字段声明成 str", "声明 priority: int", "priority = int(payload['priority'])"),
    ], "定义 TaskIn 并观察合法输入、默认值与 422。", "from pydantic import BaseModel\n\nclass TaskIn(BaseModel):\n    title: str\n    priority: int = 0\n", [
        ("合法", "TaskIn(title='买书')", "priority=0"), ("错误", "TaskIn(priority='bad')", "ValidationError"),
    ], "测试合法、省略默认、缺 title、坏 priority 四种输入。", [
        ("对象", "TaskIn(title='买书').model_dump()", "含 title/priority"), ("坏值", "TaskIn(priority='bad')", "ValidationError"),
    ], "定义 TaskIn(BaseModel)，title 必填、priority 为 int 默认 0；API 不手动吞 ValidationError。", "合法输入得到模型对象；错误输入得到字段位置明确的 422。"),
    "D14-service": _explicit_dev("service separation", [
        "路由负责 HTTP 输入输出，service 负责任务规则；分开后同一个业务函数可以被 CLI、测试和 API 复用。路由不应把 SQL、格式化和状态码混成一段。",
        "service 接收普通 Python 值或 repo 参数，返回明确结果/异常。依赖通过参数传入，测试可以用内存 fake 替换数据库。",
        "分别测试 service 业务结果和 route HTTP 映射，失败时能判断是规则错、序列化错还是状态码错。",
    ], "Express controller/service 分层与 Python 函数参数分离相同", [
        ("路由写规则", "service 无法复用", "全部逻辑在 endpoint", "抽出 create_task", "@app.post('/tasks')\ndef route(body): return db.insert(body)"),
        ("隐式全局 DB", "测试互相污染", "service 读取模块全局", "把 repo 作为参数", "DB = sqlite3.connect('app.db')"),
    ], "把 create_task 业务规则从 route 中抽出。", "def create_task(repo, title):\n    # 校验 title 并调用 repo\n    pass\n", [
        ("正常", "fake repo + create_task(repo, '买书')", "repo 收到一次 insert"), ("空标题", "create_task(repo, '   ')", "ValueError 且不写库"),
    ], "先独立调用 service，再用 route fake 依赖验证状态码；不连接真实数据库。", [
        ("服务", "create_task(repo, '买书')", "返回带 title 任务"), ("边界", "create_task(repo, '  ')", "ValueError"),
    ], "定义 create_task(repo, title)，先 strip/校验非空，再调用 repo.add；路由只负责映射 HTTP。", "业务函数可单测且空标题不写库；API 复用同一规则。"),
    "D14-errors": _explicit_dev("HTTPException", [
        "HTTPException 把业务失败转换成客户端能理解的 status_code 和 detail。404 表示资源不存在，422 表示输入不符合模型，二者不要都返回 500。",
        "异常应在边界产生：service 可以抛领域异常，route 再映射；不要把 traceback 或数据库连接信息放进 detail。",
        "测试检查正常、未找到和非法输入的状态码及 JSON 键。错误契约稳定后，前端只展示后端消息。",
    ], "FastAPI HTTPException 与 Express error middleware 都是统一错误映射", [
        ("返回 None", "客户端收到 200/null", "未找到没有分支", "raise HTTPException(404)", "return None"),
        ("泄漏 traceback", "响应含内部路径", "str(exc) 直接作为 detail", "使用固定安全消息", "raise HTTPException(500, detail=str(exc))"),
    ], "实现资源不存在的安全错误契约。", "from fastapi import HTTPException\n\ndef get_or_404(repo, task_id):\n    pass\n", [
        ("命中", "fake repo 返回任务", "返回任务"), ("未命中", "fake repo 返回 None", "status_code=404"),
    ], "用 fake repo 测试命中和未命中；检查 detail 不含内部异常。", [
        ("命中", "get_or_404(repo, 1)", "返回任务"), ("404", "get_or_404(empty_repo, 1)", "404/detail=任务不存在"),
    ], "定义 get_or_404(repo, task_id)，None 时 raise HTTPException(404, detail='任务不存在')，不要返回 null。", "命中返回结构，未命中稳定 404，不泄漏 traceback。"),
    "D14-deps": _explicit_dev("Depends", [
        "Depends 声明路由需要的协作者，FastAPI 在请求期间解析并注入。依赖可以返回数据库连接、配置或用户，路由不必知道创建细节。",
        "依赖函数是可替换边界：测试用 app.dependency_overrides 提供 fake，完成后清理 override，避免污染后续测试。",
        "依赖链的错误在请求前暴露；类型标注让读者知道路由收到什么对象，资源关闭则由生命周期负责。",
    ], "Depends 类似把 provider 注入 handler，而不是手动从全局单例读取", [
        ("直接全局", "测试不能隔离", "route 读取 DB 全局", "使用 Depends(get_repo)", "def route(): return DB.list()"),
        ("忘清 override", "后续测试继续用 fake", "override 未恢复", "finally 清空", "app.dependency_overrides[get_repo] = fake"),
    ], "用 Depends 注入可替换 repo。", "from fastapi import FastAPI, Depends\napp = FastAPI()\ndef get_repo(): return RealRepo()\n@app.get('/tasks')\ndef list_tasks(repo=Depends(get_repo)):\n    pass\n", [
        ("默认", "不 override 请求 /tasks", "调用默认依赖"), ("替换", "override get_repo 为 fake", "路由使用 fake"),
    ], "做一次默认请求和一次 override 请求，最后清空 dependency_overrides。", [
        ("依赖", "client.get('/tasks')", "返回 repo 数据"), ("替换", "app.dependency_overrides[get_repo] = lambda: fake", "响应来自 fake"),
    ], "定义 get_repo 并通过 Depends 注入；测试 override 后在 finally 清理，不能永久污染 app。", "路由不依赖具体全局实现，fake 可替换且清理完整。"),
    "D15-assert": _explicit_dev("pytest assert", [
        "pytest 会收集 test_ 开头的函数，普通 assert 失败时显示表达式和值。测试不是打印演示，而是对行为做可重复判断。",
        "一个测试围绕一个行为，输入和期望要具体；浮点、异常和集合分别需要合适断言，不能所有情况只写 truthy。",
        "先让失败测试暴露差异，再修改实现；pytest 的退出码是 CI 能否信任结果的重要反馈。",
    ], "pytest 的原生 assert 类似 Jest expect，但由 pytest 改写失败信息", [
        ("测试名错", "pytest 收集不到", "文件/函数不符合发现规则", "用 test_ 命名", "def check_add(): assert add(1,2)==3"),
        ("断言太弱", "错误实现也通过", "只 assert result", "断言精确值和边界", "assert result"),
    ], "写两个针对 add_tax 的确定性测试。", "def add_tax(price):\n    return price\n\ndef test_add_tax():\n    assert add_tax(100) == 113\n", [
        ("正常", "pytest -q", "测试通过"), ("失败反馈", "把实现改错后 pytest -q", "出现差异和非零退出"),
    ], "运行一次通过和一次故意失败，阅读 pytest 的断言差异。", [
        ("正常", "add_tax(100)", "113"), ("边界", "add_tax(0)", "0"),
    ], "定义 add_tax(price)，用 pytest 测试 100->113、0->0；测试名和断言必须可被 pytest 收集。", "pytest 退出码和断言结果与契约一致。"),
    "D15-fixture": _explicit_dev("pytest fixture", [
        "fixture 是测试准备和清理的函数，yield 前建立资源，yield 后释放。tmp_path 为每个测试提供独立临时目录，避免写入项目真实目录。",
        "fixture scope 越大越容易共享状态；初学阶段使用默认 function scope，让每个测试从空目录开始。",
        "第二个用例应看不到第一个用例创建的文件；失败时区分路径、编码和 fixture 注入问题。",
    ], "fixture 类似 Jest beforeEach/afterEach，但 yield fixture 直接表达资源生命周期", [
        ("固定 cwd", "测试互相覆盖文件", "写项目根", "使用 tmp_path", "Path('data.json').write_text('{}')"),
        ("fixture 无返回", "参数为 None", "缺 return/yield", "在 fixture 中返回资源", "@pytest.fixture\ndef data(): Path('x').touch()"),
    ], "用 tmp_path 测试文件写入与隔离。", "import pytest\n@pytest.fixture\ndef note_path(tmp_path):\n    return tmp_path / 'note.txt'\n\ndef test_write(note_path):\n    pass\n", [
        ("写读", "note_path.write_text('你好', encoding='utf-8')", "读回 你好"), ("隔离", "另一个测试查看 note_path.parent", "没有前一测试文件"),
    ], "运行两个测试并检查每个 tmp_path 独立；不使用真实 cwd。", [
        ("写读", "note_path.write_text('你好', encoding='utf-8')", "内容正确"), ("目录", "list(note_path.parent.iterdir())", "只看到当前测试文件"),
    ], "定义 note_path fixture 返回 tmp_path/'note.txt'，测试中文写读且不依赖 cwd；保持默认 function scope。", "每个测试拥有独立路径，资源在测试后可回收。"),
    "D15-mock": _explicit_dev("unittest.mock", [
        "Mock 用替身记录调用并返回固定值，patch 临时替换模块中真正查找的名称。它隔离网络和时钟，让测试只验证本地业务逻辑。",
        "patch 目标要写被测模块使用的路径，不是盲目写原始库路径；assert_called_once_with 能检查协议参数。",
        "mock 不应把所有实现都伪造掉，只替换不稳定边界；退出 with 后替换自动恢复。",
    ], "patch 与 Jest spyOn 类似，但 Python 目标遵循名称绑定位置", [
        ("patch 错目标", "真实网络仍调用", "patch 了原库路径", "patch 被测模块名称", "patch('urllib.request.urlopen')"),
        ("替换残留", "后续测试异常", "手动赋值未恢复", "使用 patch 上下文", "client.urlopen = Mock()"),
    ], "用 patch 隔离 fetch 的 opener。", "from unittest.mock import patch\n\ndef load_value():\n    # 调用模块内的 urlopen 替身\n    pass\n", [
        ("返回", "mock 返回固定 response", "解析固定 JSON"), ("调用", "assert_called_once_with", "URL/timeout 正确"),
    ], "运行成功和抛错两个 mock 测试；退出 patch 后确认名称恢复。", [
        ("成功", "with patch('client.urlopen') as open_mock", "解析固定值"), ("次数", "open_mock.assert_called_once()", "只调用一次"),
    ], "定义 load_value 并 patch 被测模块里的 urlopen；网络不可用时测试仍确定性通过。", "只替换网络边界，调用参数和 JSON 解析真实可断言。"),
    "D15-api": _explicit_dev("TestClient API", [
        "TestClient 在进程内把请求送到 FastAPI app，测试可观察 status_code、json 和 headers，不需要启动真实端口。",
        "API 输入应像真实客户端：json 参数是对象，路径/query 按 URL 编码；断言状态码和关键字段，不能只 assert response。",
        "错误响应要检查 detail 且不含 traceback；数据库依赖用 fixture/override 保持每例隔离。",
    ], "TestClient 类似 supertest/requests，但直接调用 ASGI app", [
        ("json 当 data", "服务收到错误 body", "调用 data 而非 json", "client.post(..., json=payload)", "client.post('/tasks', data={'title':'买书'})"),
        ("只断言 200", "错误状态未发现", "没有具体状态断言", "断言 201/404/422", "assert response"),
    ], "为 /health 与 /tasks 写状态码和 JSON 回归。", "from fastapi.testclient import TestClient\n\ndef test_health(app):\n    client = TestClient(app)\n    pass\n", [
        ("健康", "client.get('/health')", "200/status ok"), ("错误", "client.get('/missing')", "404"),
    ], "运行成功、创建和不存在路径三条 API 测试，固定依赖数据。", [
        ("健康", "client.get('/health')", "200"), ("创建", "client.post('/tasks', json={'title':'买书'})", "201/字段完整"),
    ], "使用 TestClient 测试 /health 和 /tasks，分别断言状态码、JSON 字段与错误 detail；不启动真实服务。", "API 测试离线完成，正常/错误契约清晰。"),
})


NONCORE_TEACHING.update({
    "D16-connect": _explicit_dev("sqlite connection", [
        "sqlite3.connect 创建连接对象，连接既管理事务也持有文件资源。:memory: 适合测试隔离，文件路径适合持久化，但两者都要 close。",
        "连接创建不等于表已存在；应用入口应明确 init_db 时机。关闭后不能继续 execute，也不能失败时偷偷换数据库。",
        "测试用内存库和 tmp_path 文件库检查连接、读写、关闭，不把固定 task.db 写进单测。",
    ], "sqlite connection 也有明确生命周期，需要显式 commit/close", [
        ("未 close", "Windows 文件无法删除", "连接持有句柄", "finally/with 关闭", "conn = sqlite3.connect(path)"),
        ("混用 DB", "测试读到旧数据", "共享固定文件", "tmp_path/:memory:", "sqlite3.connect('task.db')"),
    ], "实现 create_connection 和关闭边界。", "import sqlite3\n\ndef create_connection(path=':memory:'):\n    pass\n", [
        ("内存", "create_connection(':memory:')", "可 execute"), ("关闭", "conn.close(); conn.execute('select 1')", "明确失败"),
    ], "用内存库和 tmp_path 文件库各连接一次，finally 关闭。", [
        ("查询", "conn = create_connection(':memory:'); print(conn.execute('select 1').fetchone())", "(1,)"), ("关闭", "conn.close() 后执行查询", "ProgrammingError"),
    ], "定义 create_connection(path)，返回 sqlite3.Connection；数据源由调用者决定，不自动改用 cwd。", "连接和关闭边界可测试，路径策略透明。"),
    "D16-schema": _explicit_dev("sqlite schema", [
        "CREATE TABLE 描述关系结构，PRIMARY KEY 给行稳定身份，NOT NULL 防止必填字段为空，DEFAULT 让新行有初值。",
        "CREATE TABLE IF NOT EXISTS 让初始化可重复，但不会修改旧表；schema 变更要有迁移策略，不能每次请求 drop。",
        "用 PRAGMA table_info 检查真实列，再插入最小行观察 done 默认 0，而不是只检查 SQL 字符串。",
    ], "SQL schema 与 ORM model 都是数据契约，sqlite3 不会替你生成迁移", [
        ("重复建表", "第二次 OperationalError", "没有 IF NOT EXISTS", "使用幂等初始化", "CREATE TABLE tasks (...)"),
        ("默认错误", "done 比较异常", "缺少 DEFAULT 0", "声明 INTEGER NOT NULL DEFAULT 0", "done TEXT DEFAULT 'false'"),
    ], "建立可重复的 tasks 表并断言默认值。", "import sqlite3\n\ndef init_db(conn):\n    pass\n", [
        ("建表", "init_db(conn); PRAGMA table_info(tasks)", "有 id/title/done"), ("重复", "再次 init_db(conn)", "不报错"),
    ], "在内存库初始化两次，再插入只给 title 的记录并读取 done。", [
        ("列", "PRAGMA table_info(tasks)", "包含 id/title/done"), ("默认", "INSERT title='买书'; SELECT done", "0"),
    ], "定义 init_db(conn)，使用 CREATE TABLE IF NOT EXISTS，id 主键、title 非空、done 默认 0。", "建表幂等，列约束和默认 done 可被 SQL 验证。"),
    "D16-crud": _explicit_dev("sqlite CRUD", [
        "CRUD 把业务动作映射到 INSERT、SELECT、UPDATE、DELETE。参数值必须作为 execute 的第二个参数传入，而不是拼进 SQL 字符串。",
        "新增要 commit 并返回 id，查询转成稳定 dict，更新/删除报告是否命中；API 和 CLI 才能共享结果。",
        "测试覆盖引号标题、空列表、不存在 id 和重复调用，参数化 SQL 同时是安全和可测试的协议。",
    ], "sqlite 参数化查询与 Node 驱动的占位符原则相同，不能拼接用户输入", [
        ("SQL 拼接", "引号标题报错/注入", "f-string 拼 SQL", "使用 ? 参数", "conn.execute(f\"INSERT ... '{title}'\")"),
        ("忘 commit", "新连接看不到新增", "只 execute 未提交", "动作后 commit", "conn.execute(sql, params)"),
    ], "实现 add/list/toggle/delete 四个数据层动作。", "def add_task(conn, title):\n    pass\n\ndef list_tasks(conn):\n    pass\n", [
        ("新增", "add_task(conn, \"it's\")", "返回正 id"), ("列表", "list_tasks(conn)", "dict 含 title/done"),
    ], "在内存库完整运行 CRUD，再用含单引号标题验证参数化。", [
        ("新增", "add_task(conn, '买书')", "id>0"), ("安全", "add_task(conn, \"it's\")", "成功且标题完整"),
    ], "定义 add_task/list_tasks/toggle_task/delete_task，所有值参数化；不存在 id 返回明确结果。", "CRUD 可重复，特殊字符安全，列表结构稳定。"),
    "D16-transaction": _explicit_dev("sqlite transaction", [
        "事务把多个 SQL 动作组成全成或全撤销的单元。commit 固化修改，rollback 把未提交修改恢复到上一个边界。",
        "异常路径必须 rollback，finally 负责 close；如果 finally 无条件 commit，失败半成品就会被写入。",
        "测试在第二步故意抛异常，再查询确认第一步也没有留下；事务策略必须由数据层明确。",
    ], "事务回调与 JS ORM transaction 概念相同，但 sqlite3 需显式 commit/rollback", [
        ("异常仍 commit", "半条数据残留", "finally 调 commit", "except rollback", "try: insert_a(); insert_b()\nfinally: conn.commit()"),
        ("只 rollback", "资源泄漏", "异常路径缺 close", "finally 关闭", "except: conn.rollback()"),
    ], "实现失败即回滚的批量写入。", "def add_two(conn, first, second):\n    pass\n", [
        ("成功", "add_two(conn, 'A', 'B')", "两行存在"), ("失败", "第二个值触发异常", "两行都不存在"),
    ], "用查询计数验证成功与失败；失败 rollback，finally 关闭临时游标。", [
        ("成功", "add_two(conn, 'A', 'B')", "count=2"), ("回滚", "add_two(conn, 'A', bad)", "count 不增加"),
    ], "定义 add_two(conn, first, second)，成功 commit、异常 rollback；不要吞异常后返回成功。", "成功全量提交，失败没有半成品，资源路径可关闭。"),
    "D17-coroutine": _explicit_dev("async coroutine", [
        "async def 调用返回 coroutine，不会立即执行函数体；await 才把控制权交给事件循环并取得结果。同步函数不能直接 await。",
        "asyncio.run 负责创建和关闭一次事件循环，适合脚本边界；在已经运行的事件循环里再次 run 会报错。",
        "测试用短小 coroutine 和 asyncio.run 观察返回值，重点是执行时机和 await 链，而不是网络服务。",
    ], "Promise 需要 await，Python coroutine 同样惰性但由 asyncio event loop 调度", [
        ("忘 await", "得到 coroutine object/RuntimeWarning", "只调用 async 函数", "在 async 上下文 await", "result = fetch()"),
        ("嵌套 run", "RuntimeError event loop running", "在 async 函数内 asyncio.run", "直接 await", "async def outer(): return asyncio.run(inner())"),
    ], "定义 async fetch_value 并正确运行。", "import asyncio\n\nasync def fetch_value(value):\n    pass\n", [
        ("运行", "asyncio.run(fetch_value(3))", "返回 3"), ("时机", "创建 coroutine 后再 await", "执行发生在 await"),
    ], "用 asyncio.run 调用 coroutine；再写 async wrapper 用 await，不嵌套 run。", [
        ("值", "asyncio.run(fetch_value(3))", "3"), ("wrapper", "asyncio.run(wrapper())", "得到 awaited 值"),
    ], "定义 async fetch_value(value) 并在 async wrapper 中 await；脚本边界只用一次 asyncio.run。", "coroutine 被 await 执行，返回值准确且无未 await 警告。"),
    "D17-gather": _explicit_dev("asyncio.gather", [
        "gather 同时安排多个 awaitable，并按传入顺序返回结果；完成先后不一定等于结果顺序。并发适合互不依赖的等待任务。",
        "协程函数调用只是创建 coroutine，必须交给 gather/await；有依赖的第二步不能盲目并发。",
        "用 asyncio.sleep(0) 让出控制权并记录事件，分别观察执行交错和结果顺序。",
    ], "Promise.all 与 gather 都聚合并发任务，但 Python 返回列表顺序由参数决定", [
        ("未 await", "警告且无结果", "coroutine 没交给 gather", "await asyncio.gather", "tasks = [work(1), work(2)]"),
        ("误判顺序", "按完成顺序断言结果", "混淆执行与返回顺序", "按输入顺序断言", "assert results == [2, 1]"),
    ], "并发运行三个独立 coroutine 并保留输入顺序。", "import asyncio\n\nasync def run_all(values):\n    pass\n", [
        ("聚合", "asyncio.run(run_all([1, 2, 3]))", "返回 [1, 2, 3]"), ("空列表", "asyncio.run(run_all([]))", "返回 []"),
    ], "记录 coroutine 开始/结束，观察事件交错但结果顺序稳定。", [
        ("顺序", "asyncio.run(run_all([1, 2, 3]))", "结果按输入顺序"), ("并发", "每项 await asyncio.sleep(0)", "事件发生交错"),
    ], "定义 async run_all(values)，创建 coroutine 并 await asyncio.gather；不要用同步循环替代。", "所有结果返回且顺序与输入一致，任务都被 await。"),
    "D17-timeout": _explicit_dev("async timeout", [
        "asyncio.wait_for 给 awaitable 设置时间上限，超时会取消任务并抛 asyncio.TimeoutError。timeout 不是自动重试，也不应把超时当空结果。",
        "被取消的 coroutine 可能执行 finally 清理；调用者要决定传播还是转换成明确业务错误，不能遗留后台任务。",
        "用 asyncio.sleep 制造可控慢任务，分别测试足够和过短 timeout，整个测试离线且快速。",
    ], "AbortSignal.timeout 类似取消超时，二者都不等于 retry", [
        ("忘 await wait_for", "超时配置没生效", "只创建 wait_for coroutine", "await wait_for", "asyncio.wait_for(work(), 1)"),
        ("吞 timeout", "误以为成功", "except 返回 []", "保留明确超时错误", "except asyncio.TimeoutError: return []"),
    ], "控制慢 coroutine 的超时和取消。", "import asyncio\n\nasync def slow():\n    await asyncio.sleep(0.05)\n    return 'done'\n\nasync def run_with_timeout(seconds):\n    pass\n", [
        ("成功", "asyncio.run(run_with_timeout(1))", "done"), ("超时", "asyncio.run(run_with_timeout(0.001))", "TimeoutError"),
    ], "运行两种 timeout，检查慢任务被取消且没有后台 task。", [
        ("足够", "run_with_timeout(1)", "done"), ("太短", "run_with_timeout(0.001)", "明确超时失败"),
    ], "定义 run_with_timeout(seconds)，await asyncio.wait_for(slow(), timeout=seconds)；超时不得 fallback/retry。", "足够时间返回 done，太短明确失败且任务被取消。"),
    "D17-boundary": _explicit_dev("async errors", [
        "异步异常在 await 点重新抛出，try/except 必须包住 await 而不是只包住 coroutine 创建。gather 的异常策略也要由调用者明确。",
        "取消是重要边界，清理代码应放 finally，不能把取消吞成成功。错误消息不应包含秘密或内部连接信息。",
        "测试用立即抛错 coroutine 与取消场景验证路径，避免真实网络；结果区分成功、业务失败和取消。",
    ], "Promise rejection 要在 await/catch 边界处理，Python 也不能只 try 创建 coroutine", [
        ("try 范围错", "异常逃出处理器", "try 只包 coroutine()", "try 包 await", "try: task = fail()\nexcept ValueError: pass"),
        ("吞取消", "任务无法停止", "except BaseException 返回成功", "finally 清理后重新抛出", "except BaseException: return None"),
    ], "为异步失败和取消定义清晰结果。", "import asyncio\n\nasync def fail():\n    raise ValueError('bad input')\n\nasync def safe_call():\n    pass\n", [
        ("失败", "asyncio.run(safe_call())", "返回明确错误标签"), ("取消", "创建 task 后 cancel", "finally 执行且取消不被吞"),
    ], "分别运行失败 coroutine 和 cancel 场景，记录 finally 事件。", [
        ("错误", "asyncio.run(safe_call())", "得到 invalid-input"), ("取消", "task.cancel(); await task", "CancelledError 保留"),
    ], "定义 safe_call() 只捕获预期 ValueError；取消路径在 finally 清理后继续传播，不返回伪成功。", "预期异常得到稳定结果，取消完成清理且不被静默吞掉。"),
})


PROJECT_TEACHING: dict[str, dict[str, Any]] = {}


def _project_lesson(
    explanation: list[str],
    bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, str]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    return _manual_detail(explanation, bridge, errors, goal, starter, steps, check, inputs, instructions, expected)


PROJECT_TEACHING.update({
    "D18-scope": _project_lesson(
        ["这一节把 task-manager 的用户、动作和边界写进 docs/requirements.md。先明确“新增、查看、完成、删除”四个动作，再写哪些输入无效，后续 API、CLI 和网页都依赖这份共同语言。", "需求不是愿望清单，而是可以被验收的行为：例如空标题拒绝、完成状态可重复修改、删除不存在 id 有明确结果。每条规则都要能在后续测试中变成断言。", "编辑时只修改需求文件，不提前写 Python 实现。先让另一个人按文档复述一次流程，若无法判断状态码或输出，就回到本节补齐边界。"],
        "项目关系：requirements.md 是 D18-D24 的上游契约，不依赖实现文件；JS 经验只能帮助描述交互，验收仍以 Python 服务行为为准。",
        [("需求漏边界", "同一输入在 API/CLI 得到不同结果", "只写 happy path", "为每个动作补非法输入与预期", "新增任务：标题非空"), ("把实现写进需求", "改数据库后需求失去可读性", "文档混入函数名/SQL", "只记录用户可观察行为", "调用 db.insert(...)")],
        "把用户故事、输入约束和可观察验收写成一页需求。", "# docs/requirements.md\n# 先写用户故事与验收，不写实现代码\n", [("动作", "列出 add/list/complete/delete", "每个动作有输入和结果"), ("边界", "补空标题/不存在 id", "可判断接受或拒绝")],
        "打开 docs/requirements.md，用四个动作逐项检查输入、输出和失败反馈；不要创建额外实现文件。",
        [("新增", "标题='买书'", "得到一个可查询任务"), ("边界", "标题='   ' 或 id=999", "拒绝原因可被测试")],
        "编辑 docs/requirements.md：写用户故事、四个动作、空标题/不存在 id 边界，并给每条规则一个可观察验收结果。",
        "需求文件完整且能直接指导 contract、API、CLI、网页测试；没有把实现细节当验收。"),
    "D18-acceptance": _project_lesson(
        ["验收清单把 D18-scope 的文字变成运行场景，例如先创建任务、再列表确认、再完成、最后删除。场景顺序会成为 D24 从空 workspace 重建时的冒烟路径。", "每一步要写请求/命令、预期状态码或 stdout，以及失败时查看哪份证据。这样“功能似乎能用”会变成可重复的验收。", "本节只补 docs/requirements.md 的验收段，不写 API 实现；先用手工假设走一遍，发现缺字段就回到数据契约小节修正。"],
        "项目关系：本节继续修改 requirements.md，依赖 D18-scope 的用户故事；D19-D23 以后会把每个场景落实为真实命令。",
        [("只有成功列表", "删除/错误路径没有验收", "场景只包含 200", "加 400/404/422 预期", "GET /tasks -> 200"), ("预期不具体", "测试无法断言", "写“正常返回”", "写 JSON 字段/退出码", "结果：成功")],
        "将四个用户动作串成可执行验收场景。", "# requirements.md\n## 验收场景\n# 逐步补请求、结果和失败定位\n", [("主流程", "add -> list -> complete -> delete", "每步输出可观察"), ("错误", "空标题/不存在 id", "状态码或错误文本明确")],
        "按主流程和错误流程阅读清单，确认每一步都有操作、预期、失败排查。",
        [("主流程", "运行 add/list/complete/delete", "任务状态变化可验证"), ("错误流", "重复删除同一 id", "得到稳定 404/错误码")],
        "在 docs/requirements.md 加入主流程、错误流程、每步命令/请求和预期输出；不要写“应该正常”这种不可断言语句。",
        "验收清单能被 D24 runbook 直接复用，并覆盖成功与失败。"),
    "D18-data-contract": _project_lesson(
        ["contract.json 固定 task 的字段名、类型和默认值，避免 API、数据库和网页各自猜测。id 是整数身份，title 是非空字符串，done 是布尔状态。", "数据契约要区分输入与输出：创建请求不必携带 id，响应和列表需要 id。JSON 的 false/null 也必须按 JSON 规则写，不能混入 Python True/None 文本。", "保存后用 json.load 再验证字段，故意删字段或改类型观察失败。contract.json 不是装饰文档，它会被 D18-api-contract、D21 schema 和 D24 acceptance 引用。"],
        "项目关系：依赖 docs/requirements.md；本节产生 contract.json，后续 taskproj/api.py 和测试读取同一字段契约。",
        [("用 Python 字面量", "json.load 报解析错误", "写 True/None 或单引号", "使用 true/false/null 和双引号", "{'done': False}"), ("只写输出", "创建输入边界缺失", "没有区分 required", "补 input/output 字段约束", "{\"output\": {\"id\": 1}}")],
        "写出 API/数据库共用的 JSON 数据契约。", "{\n  \"task\": {\n    \"input\": {\"title\": \"string\"},\n    \"output\": {\"id\": 1, \"title\": \"string\", \"done\": false}\n  }\n}\n", [("解析", "python -m json.tool contract.json", "命令成功"), ("类型", "读取 input/output", "字段类型和必填项明确")],
        "用 json.tool 和 Python json.load 校验 contract.json；再复制一份故意改成单引号确认校验失败。",
        [("合法", "title='string', done=false", "JSON 可解析"), ("非法", "done='false'", "类型不符合契约")],
        "创建 contract.json：明确 task input/output 字段、title/id/done 类型、空标题和不存在 id 的错误契约；只使用标准 JSON。",
        "contract.json 可解析，字段可被后续模型、路由和 acceptance 直接引用。"),
    "D18-api-contract": _project_lesson(
        ["API 契约把需求动作映射到 HTTP method/path/status，例如 POST /api/tasks 创建、GET /api/tasks 列表。每条路线都要注明请求体和响应字段。", "契约先于 FastAPI 实现，可以提前发现路径重名、状态码冲突和错误 detail 不一致。把静态首页 GET / 也写进去，避免 D23 才发现没有网页入口。", "本节只在 contract.json 中增加 routes 与错误表，并用 json.tool 验证；不要把 Python 函数名当成对外 API 名称。"],
        "项目关系：依赖 requirements.md 与 contract.json 的数据字段；D21 api.py、D22 tests/test_api.py、D23 static/index.html 都按此路线表工作。",
        [("方法错", "客户端 POST 得到 405", "契约和实现 method 不一致", "固定 method/path 表", "GET /api/tasks 创建"), ("遗漏静态路由", "浏览器首页 404", "只写 JSON API", "加入 GET / 与静态文件验收", "routes: ['/api/tasks']")],
        "为 task CRUD 和静态首页建立可执行路由契约。", "# contract.json\n# 增加 routes 数组和 errors 对象\n", [("路由", "列出 GET/POST/PATCH/DELETE", "请求/响应清楚"), ("网页", "记录 GET /", "明确 index.html 入口")],
        "逐条读取 routes，核对 method、path、status、body；用 json.tool 检查文件结构。",
        [("创建", "POST /api/tasks {title}", "201 与 task"), ("缺失", "GET /api/tasks/999", "404/detail")],
        "在 contract.json 增加 CRUD 路由、201/404/422 错误与 GET / 静态入口，并保持字段引用与上一节一致。",
        "契约能直接生成 API 测试矩阵，D23 浏览器入口也有明确验收。"),
})
def _detail(
    explanation: list[str],
    js_bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, ...]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    """Store one lesson's teaching contract without deriving copy from its title."""
    return {
        "explanation": explanation,
        "js_bridge": js_bridge,
        "common_errors": [
            {
                "error": error,
                "symptom": symptom,
                "cause": cause,
                "fix": fix,
                "example": {"code": code, "symptom": symptom, "fix": fix},
            }
            for error, symptom, cause, fix, code in errors
        ],
        "guided_practice": {
            "goal": goal,
            "starter": starter,
            "steps": [
                {"action": step[0] if len(step) == 2 else f"{step[0]}：{step[1]}", "expected": step[-1]}
                for step in steps
            ],
            "check": check,
        },
        "input_examples": [{"label": label, "value": value, "expected": result} for label, value, result in inputs],
        "practice": {"instructions": instructions, "expected_behavior": expected, "starter_content": starter},
    }


# D02-D07 的内容是逐节写入的教学数据。这里不根据标题拼接解释、错误或输入，
# 这样审阅课程时可以直接看到每个 Python 概念的因果、边界和可运行练习。
CORE_TEACHING: dict[str, dict[str, Any]] = {
    "D02-execution": _detail(
        [
            "Python 解释器读取一个源文件时，先执行顶层语句，再进入被调用的函数。赋值、函数调用和条件语句都是有顺序的动作；同一行之前的名字若还没有绑定，运行到它时就会出现 NameError。",
            "冒号表示后面要跟一个代码块，代码块的边界由缩进决定。同一块中的语句必须对齐，通常用四个空格；取消块内语句的缩进或同一块缩进不一致才会产生缩进错误，单行使用三个空格本身不一定报错。",
            "注释从 # 开始到行尾，解释器不会执行它；它适合说明意图而不是掩盖代码。学习执行顺序时，可以在每个动作后打印标记，并故意改变缩进观察错误发生在哪里。",
        ],
        "JavaScript 用 {} 标记块、用分号分隔语句，而 Python 用冒号加一致缩进标记块；Python 没有 JS 那种依靠花括号恢复层级的写法。两者都从上到下执行，但 Python 的空白错误在解析阶段就会阻止程序启动。",
        [
            ("把块内语句缩进不一致", "运行即报 IndentationError", "同一代码块的缩进列不同，解析器无法确定层级", "统一使用四个空格，并让编辑器显示空白", "if ready:\n print('ok')\n  print('again')"),
            ("把注释当成可执行配置", "注释后的值没有生效，变量仍未定义", "# 后文本不会进入 Python 执行流程", "把需要执行的赋值写在注释外，再用注释解释原因", "# limit = 3\nprint(limit)"),
        ],
        "能观察一条语句接一条语句的执行顺序，并用统一四空格写出一个合法代码块。",
        "print('先执行')\nif True:\n    # 在块内补一条可观察语句\n    pass\n",
        [("把 print 放进 if 块", "运行输出两行且没有缩进错误"), ("在块外增加第二个 print", "第二个 print 无条件执行，输出顺序与源文件一致")],
        "运行文件并检查输出顺序；再把 if 后唯一的块内语句完全顶格，确认解释器报告 IndentationError，然后恢复四个空格。",
        [("合法块", "if True:\n    print('ready')", "ready"), ("执行顺序", "print('A')\nprint('B')", "A\nB")],
        "编写 main.py：先打印 START，再在 if True 块内打印 BLOCK，最后打印 END；保持四空格缩进，并保留一行解释每个阶段。",
        "运行输出严格为 START、BLOCK、END 三行；把块内缩进改错时验证应失败而不是静默跳过。",
    ),
    "D02-names": _detail(
        [
            "赋值语句不是把值塞进固定类型的盒子，而是让名字指向一个对象。执行 value = 7 后，value 指向 int 对象；再次执行 value = '七'，只是改变绑定，旧对象是否还存在由引用决定。",
            "每个对象仍然有自己的运行时类型。type(value) 适合观察精确类型，isinstance(value, int) 适合判断是否属于某个类型体系，例如 bool 是 int 的子类这一点会影响判断结果。",
            "命名要表达数据角色，不能使用关键字、空格或以数字开头。把绑定、类型和作用域分开理解，能解释为什么函数参数可以遮蔽外层同名变量，以及为什么未赋值名字会 NameError。",
        ],
        "JavaScript 变量也能在运行时换类型，但 let/const 描述的是绑定是否可重新赋值；Python 的变量名没有 const 关键字。Python 的 isinstance 更像面向对象层次判断，不能简单等同于 JS 的 typeof 字符串比较。",
        [
            ("把 isinstance 当成 type 名称比较", "isinstance(value, 'int') 报 TypeError", "第二个参数必须是类型或类型元组，不是字符串", "传入 int，或先使用 type(value).__name__ 做展示", "value = 3\nprint(isinstance(value, 'int'))"),
            ("使用关键字作为变量名", "解析时报 SyntaxError", "class、def、for 等词被 Python 保留为语法结构", "换成有意义的普通名词，如 class_name", "class = '初级'"),
        ],
        "能创建清晰名字，演示同名绑定不同类型，并用 type 与 isinstance 给出可观察证据。",
        "value = 7\n# 增加类型观察和一次合法的重新绑定\n",
        [("观察整数", "打印 type(value).__name__ 和 isinstance(value, int)", "得到 int 和 True"), ("重新绑定文本", "把 value 改成 '七' 后再次观察", "得到 str，说明绑定改变而不是类型缺失")],
        "运行两次绑定并检查输出；再把变量名改为关键字，确认错误来自语法而非业务逻辑。",
        [("整数", "value = 7\nprint(type(value).__name__)\nprint(isinstance(value, int))", "int\nTrue"), ("文本", "value = '七'\nprint(type(value).__name__)", "str")],
        "编写 main.py，定义 score = 88，打印它的类型和是否为 int；随后将 score 绑定到 '88'，再次打印类型并在注释中说明动态类型的含义。",
        "输出先显示 int/True，再显示 str；代码没有使用关键字变量名，并能解释名字绑定对象的变化。",
    ),
    "D02-numbers": _detail(
        [
            "int 表示整数，float 表示带小数的近似数；+、-、*、/、//、%、** 的结果类型和意义不同。尤其 / 总是产生浮点商，而 // 取整除结果，不能因为输入都是整数就混为一谈。",
            "比较表达式会产生 True 或 False。== 比较值，!=、<、<=、>、>= 表达顺序关系；is 比较对象身份，只应该用于 None 等单例判断，不应拿来替代数字相等。",
            "浮点数按二进制近似保存，0.1 + 0.2 可能不等于字面量 0.3。金额或严格边界要使用 Decimal 或明确的容差；写练习时同时覆盖零、负数、除数和余数边界。",
        ],
        "JavaScript 只有 Number 这一常用数值类型，整数/浮点的直觉不同于 Python 的 int/float 分离；JS 的 === 既比较值又比较类型，而 Python 的 == 负责值比较。Python 的 // 和 JS 没有直接同名运算符。",
        [
            ("把 / 当成整除", "7 / 2 得到 3.5 而不是 3", "单斜杠定义的是普通除法，结果通常是 float", "需要页数或商时使用 //，并为负数确认取整规则", "print(7 / 2)"),
            ("用 is 比较两个数字", "结果可能受对象缓存影响，语义不可靠", "is 比较身份而不是数值相等", "数字使用 ==，None 使用 is None", "a = 1000\nb = 1000\nprint(a is b)"),
        ],
        "能区分算术运算、值比较和身份比较，并为除零、负数和浮点近似选择合理处理。",
        "a = 7\nb = 2\n# 写出商、余数和一个边界比较\n",
        [("计算商余", "打印 a // b 与 a % b", "输出 3 和 1"), ("增加零除边界", "在 b == 0 时先打印提示，不直接执行除法", "程序不因 ZeroDivisionError 崩溃")],
        "用 7 和 2 输出商余，再处理 b=0；最后用 == 而非 is 检查一个计算结果。",
        [("商余", "print(7 // 2, 7 % 2)", "3 1"), ("比较", "print(3 < 5)\nprint(0.1 + 0.2 == 0.3)", "True\nFalse")],
        "定义 divide_parts(total, size)，返回商和余数；size 为 0 时返回清晰错误结果或抛出 ValueError，并用负数输入写一个边界调用。",
        "正常输入返回 (3, 1)；size=0 不执行非法除法；比较使用 ==/关系运算而非 is。",
    ),
    "D02-bool-none": _detail(
        [
            "bool 只有 True 和 False，但很多对象都能被转换为真值。None、0、0.0、空字符串、空 list/dict/set 通常是假值；非空容器即使里面有 0 也是真值。",
            "None 表示“没有对象/没有结果”，不是空字符串也不是数字零。判断它应写 value is None；如果只写 if value，就会把 None、空文本和 0 混在同一条路径。",
            "条件语句会调用对象的真值规则，and/or 还会短路并返回操作数本身。输入校验要先决定“缺失”和“空内容”是否相同，再选择 is None、not value 或显式比较。",
        ],
        "JavaScript 的 null/undefined 与 Python None 有相似的缺失语义，但 JS 的 falsy 集合还包含 NaN，Python 没有 undefined。Python 用 is None 判断单例，不能照搬 JS 的 == null 宽松比较。",
        [
            ("把空字符串当 None", "空字符串被误认为未提供对象", "'' 是 str，只是假值，不是 None", "缺失判断使用 is None，空内容判断另写 not text", "text = ''\nif text is None:\n    print('缺失')"),
            ("把列表内容当布尔值", "[0] 被判断为 False", "真值看容器是否为空，不看元素是否为零", "用 bool(items) 判断是否有元素，必要时再检查元素", "items = [0]\nprint(bool(items))"),
        ],
        "能区分缺失值、空值和非空值，写出不混淆 None 与假值的条件分支。",
        "value = None\n# 分别补充 None 判断和空字符串判断\n",
        [("缺失路径", "对 None 使用 is None", "输出“缺少姓名”之类的提示"), ("空容器路径", "对 [] 使用 bool 或 not", "输出“列表为空”，但不称它为 None")],
        "准备 None、''、[]、[0] 四个输入，分别打印 value is None 与 bool(value)，检查每一行含义。",
        [("缺失", "value = None\nprint(value is None, bool(value))", "True False"), ("有元素", "value = [0]\nprint(value is None, bool(value))", "False True")],
        "定义 describe_value(value)，对 None 返回 'missing'，对空字符串返回 'empty text'，对其他值返回 'present'；用 0 和 [0] 验证不能误判。",
        "None、空字符串、0、[0] 分别走符合语义的路径；函数没有把所有假值都写成 missing。",
    ),
    "D02-strings": _detail(
        [
            "字符串是由字符组成的不可变序列，单个索引用从 0 开始的位置，负索引从末尾倒数。切片的 stop 不包含在结果里，因此 text[1:4] 取的是位置 1、2、3。",
            "不可变意味着不能执行 text[0] = 'X'；它不意味着不能变换文本。strip、replace、切片和拼接都会创建新字符串，必须把结果保存到新名字或重新绑定原名字。",
            "转义序列让字符串表达换行、引号等字符，原始字符串 r'...' 可减少反斜杠转义。处理用户文本时要明确索引越界、空字符串和中文字符的边界，先观察长度再取位置。",
        ],
        "JavaScript 的 String 也不可变并支持索引/slice，但 JS 常用 slice 的参数和 Python 切片步长不同；Python 可写 text[::-1] 反转，JS 需要拆分、反转再合并。Python 的索引越界抛 IndexError，而 JS 常得到 undefined。",
        [
            ("原地修改字符", "报 TypeError: 'str' object does not support item assignment", "str 不提供按位置写入操作", "用切片/拼接建立新字符串并重新绑定", "text = 'cat'\ntext[0] = 'C'"),
            ("切片 stop 多取一位", "输出片段比预期长一个字符", "Python 切片右端是开区间", "把 stop 写成目标位置后一位，并用短字符串验证", "text = 'Python'\nprint(text[1:5])"),
        ],
        "能用索引和切片读取文本，解释不可变性，并用新字符串完成清洗或反转。",
        "text = ' Python '\n# 先观察长度，再完成一个不修改原值的切片\n",
        [("取片段", "打印 text[1:7]", "得到不含末尾空格的 Python"), ("证明不可变", "创建 reversed_text，不给 text 的索引赋值", "原 text 仍保留首尾空格")],
        "运行一个带首尾空格的字符串：输出切片、反转结果和原值；再把字符赋值语句放进注释，说明为什么不可行。",
        [("索引切片", "text = 'Python'\nprint(text[0])\nprint(text[1:4])", "P\nyth"), ("新字符串", "text = '猫'\nnew_text = text + '和狗'\nprint(text, new_text)", "猫 猫和狗")],
        "定义 transform_text(text)：去掉首尾空白后返回反转字符串；transform_text(' ab ') 必须是 'ba'，并证明原输入仍为 ' ab '。",
        "输入 ' ab ' 返回 'ba'，空字符串返回空字符串，函数不尝试原地修改 str。",
    ),
    "D02-string-methods": _detail(
        [
            "字符串方法通过点号调用，通常返回新字符串或新列表，而不是默默修改原字符串。strip 处理首尾空白，split 把一段文本拆成 list，join 则要求所有待连接元素都是 str。",
            "方法可以串联，但每一步的数据类型要跟得上：' a,b '.strip() 仍是 str，split(',') 后变成 list[str]，此时才能用 '|'.join(parts)。把中间结果打印出来能定位链式调用的错误。",
            "f-string 在运行时计算花括号里的表达式并转成文本，适合把名字、数量和格式放进消息。用户输入可能为空或含额外分隔符，清洗规则应明确是否保留空字段以及如何处理非字符串值。",
        ],
        "JavaScript 也有 trim、split、join 和模板字符串，但 Python 使用 f'...' 而不是反引号；Python join 是分隔符字符串的方法，调用形式与 JS 的数组 join 相反。",
        [
            ("忘记保存 strip 结果", "打印仍有首尾空格", "strip 返回新字符串，不改变原变量", "写成 text = text.strip() 或使用返回值继续处理", "text = ' hi '\ntext.strip()\nprint(repr(text))"),
            ("join 传入非字符串", "报 TypeError: sequence item ... expected str", "join 只连接字符串，整数不会自动转换", "先用 str(item) 转换，或明确格式化每个元素", "print(','.join(['a', 2]))"),
        ],
        "能把清洗、拆分、组合和格式化连成可解释的文本处理流程。",
        "raw = '  a,b  '\n# 逐步保存 cleaned、parts 和 message\n",
        [("拆分", "先 strip 再 split(',')，打印 parts", "得到 ['a', 'b']"), ("格式化", "用 join 和 f-string 生成一条消息", "输出不带首尾空格且包含数量")],
        "处理 '  a,b  '：输出 parts、用 | 连接，再用 f-string 说明共有几个字段；追加空输入时返回明确提示。",
        [("清洗", "raw = '  a,b  '\nparts = raw.strip().split(',')\nprint('|'.join(parts))", "a|b"), ("格式化", "name = '小林'\ncount = 3\nprint(f'{name} 有 {count} 个任务')", "小林 有 3 个任务")],
        "定义 format_tags(raw)：去除首尾空格、按逗号拆分、过滤空标签并返回用 ' / ' 连接的文本；空输入返回 '无标签'。",
        "' a,,b ' 返回 'a / b'，空输入返回 '无标签'，f-string 中的数量与实际标签数一致。",
    ),
    "D03-if": _detail(
        [
            "if 从上到下测试条件，第一条为真的分支执行后，其余 elif/else 不再执行。条件边界必须写清楚，例如成绩 60 是否算通过，不能靠分支排列让读者猜。",
            "elif 适合互斥的多段范围，else 表示前面条件都不成立。比较数字时要同时考虑最小值、最大值和类型错误；把复杂条件拆成有名字的布尔变量通常更容易调试。",
            "条件表达式适合很短的二选一，但不要把多层业务规则压成一行。先用几个边界输入画出路径，再把每条路径映射到明确返回值，避免遗漏负数、空文本或 None。",
        ],
        "JavaScript 和 Python 都有 if/else，但 JS 用括号和花括号，Python 用冒号和缩进；Python 没有强制三元写法，条件表达式写作 value_if_true if condition else value_if_false。",
        [
            ("把多个分支写成独立 if", "一个输入可能打印多个互斥结果", "独立 if 不会在命中后停止", "互斥范围使用 if/elif/else", "score = 95\nif score >= 60: print('及格')\nif score >= 90: print('优秀')"),
            ("忽略等号边界", "score=60 被判为不及格", "使用 > 而不是 >= 改变了规则", "先写边界表，再选择包含等号的比较符", "if score > 60:\n    result = '通过'"),
        ],
        "能把一组明确的业务条件翻译成互斥分支，并用边界值证明每条路径。",
        "score = 60\n# 补充优秀、通过和不通过三条路径\n",
        [("写边界", "分别测试 90、60、59", "三个输入各走唯一预期分支"), ("检查缺失", "为 None 或非数字输入加保护", "错误输入得到提示而非比较异常")],
        "运行 90、60、59 和一个非数字输入；逐行检查实际分支与规则表是否一致。",
        [("范围", "score = 89\nif score >= 90:\n    level = 'A'\nelif score >= 60:\n    level = 'B'\nelse:\n    level = 'C'\nprint(level)", "B"), ("二选一", "age = 18\nprint('成人' if age >= 18 else '未成年')", "成人")],
        "定义 classify_score(score)：90 以上返回 'A'，60–89 返回 'B'，0–59 返回 'C'，负数抛 ValueError；为 90、60、59、-1 写调用。",
        "四类输入分别得到 A、B、C 和明确 ValueError；每个数值只命中一条分支。",
    ),
    "D03-match": _detail(
        [
            "match/case 用模式描述值的形状或固定选项。它不是把一长串 if 自动变短：case 'list' 匹配字符串，case (x, y) 可以拆开元组，模式中的名字还会绑定匹配到的值。",
            "case 按书写顺序尝试，case _ 是兜底模式，必须放在最后。模式匹配适合命令、事件和结构化记录；如果条件是范围计算或多个独立布尔表达式，普通 if 往往更直白。",
            "结构模式可以带守卫，例如 case ('age', value) if value >= 18。要先明确输入可能是哪些类型，否则一个看似完整的 match 可能只处理字符串而把 list 或 None 静默落入兜底。",
        ],
        "JavaScript 的 switch 主要比较离散值，现代 JS 的解构需要另写逻辑；Python match 能匹配序列结构并绑定变量。Python 的 case _ 类似 default，但模式匹配还会改变局部绑定，不能只按 switch 的文本替换理解。",
        [
            ("把变量名当常量模式", "case status 可能匹配任意值或触发绑定错误", "小写名字在模式中通常表示捕获变量，不是已有常量", "固定值用字符串/数字或限定名称，并避免裸变量模式", "status = 'ready'\nmatch 'done':\n    case status: print('匹配')"),
            ("兜底 case 放在前面", "后续 case 永远不可达或解释器报模式错误", "_ 会匹配所有值", "把 case _ 放在最后并为未知值返回明确结果", "match value:\n    case _:\n        pass\n    case 'ok':\n        pass"),
        ],
        "能用固定值和结构模式处理有限事件，并为未知输入保留最后的兜底路径。",
        "command = 'list'\n# 增加 add 和未知命令的 case\n",
        [("增加固定 case", "为 add 返回新增提示", "list/add 各自只输出一条消息"), ("增加结构 case", "对 (0, y) 打印 y", "元组结构被拆开而不是按字符串比较")],
        "用 list、add、unknown 三个命令和一个元组坐标运行 match；确认兜底只处理未声明的值。",
        [("命令", "command = 'list'\nmatch command:\n    case 'list':\n        print('查看')\n    case 'add':\n        print('新增')\n    case _:\n        print('未知')", "查看"), ("结构", "point = (0, 4)\nmatch point:\n    case (0, y):\n        print(y)", "4")],
        "定义 command_label(value)：匹配 'list'、'add'、('task', title) 三种输入，其他值返回 '未知命令'；不要用一个裸变量 case。",
        "三种声明输入返回具体标签，未知字符串和 None 都走兜底；结构 case 能取出 title。",
    ),
    "D03-for": _detail(
        [
            "for 不按下标猜测循环次数，而是向可迭代对象逐项请求值。range(1, 4) 产生 1、2、3，stop 永远不包含；这条开区间规则适合表达长度和下标范围。",
            "循环变量在每轮被重新绑定，循环体应只处理当前值并维护必要的累积状态。遍历 list、tuple、字符串和字典时，得到的元素形状不同，字典默认遍历键。",
            "空序列不会执行循环体，因此累加器应在循环前设为中性值。遇到嵌套循环或复杂过滤时，先写普通 for 看清数据流，再考虑推导式或内置 sum 是否保持可读。",
        ],
        "JavaScript 的 for...of 也遍历值，传统 for 则遍历索引；Python 的 for 更直接地依赖 iterable 协议。Python range 是惰性的整数序列对象，不等于 JS 的数组，也不会包含 stop。",
        [
            ("range 终点多算一位", "循环输出 1、2、3、4", "range 的 stop 是开区间，若想 1 到 3 应写 range(1, 4)", "把上界写成最后值加一并用边界测试确认", "for n in range(1, 3):\n    print(n)"),
            ("把字典键当记录", "打印出 title/done 而不是对应值", "for item in mapping 默认只产生键", "使用 mapping.items() 或 mapping.values()", "task = {'title': 'A'}\nfor item in task:\n    print(item)"),
        ],
        "能用 for/range 完成遍历和累积，正确处理空输入以及 range 的开区间边界。",
        "numbers = [1, 2, 4, 5]\ntotal = 0\n# 用 for 只累加偶数\n",
        [("筛选偶数", "在循环体中判断 number % 2 == 0", "[1,2,4,5] 的总和为 6"), ("测试空列表", "把 numbers 改为 []", "total 仍为 0，循环体不执行也不报错")],
        "运行混合数字、空列表和含负数列表；打印每轮被累加的数字与最终总和。",
        [("range", "for number in range(1, 4):\n    print(number)", "1\n2\n3"), ("累加", "total = 0\nfor value in [2, 5, 3]:\n    total += value\nprint(total)", "10")],
        "定义 sum_even(numbers)：使用 for 遍历输入，只累加偶数；sum_even([1,2,4,5]) 为 6，空列表为 0。",
        "函数必须真正遍历输入并返回偶数和；不把输入改写为固定列表，空输入返回 0。",
    ),
    "D03-while": _detail(
        [
            "while 每次进入循环前重新计算条件，适合重复次数由状态决定的场景，例如等待用户输入或消费队列。和 for 不同，它不会自动推进任何变量，推进责任在循环体。",
            "一个可靠的 while 要有初始化、条件、状态变化和退出证据。若条件依赖 remaining，就必须在每轮减少 remaining；若读取输入，就要处理空输入、退出命令和输入异常。",
            "调试死循环时打印状态和迭代次数，先限制最大轮数保护程序。不要用 while True 掩盖没有退出条件的问题；只有在 break 条件清晰且可测试时才使用它。",
        ],
        "JavaScript 的 while 结构相似，也需要手动改变状态；Python 不使用 ++ 运算符，写 remaining -= 1。Python 的真值规则会直接决定 while 是否继续，空容器可以自然结束循环。",
        [
            ("忘记更新状态", "程序一直打印同一个值或超时", "条件变量没有变化，永远保持真值", "在循环体中明确更新，并加入最大迭代保护", "remaining = 3\nwhile remaining:\n    print(remaining)"),
            ("先更新再使用", "少处理一次输入或跳过最后一个值", "状态更新放在处理前改变了本轮数据", "先处理当前状态，再在末尾更新", "n = 3\nwhile n:\n    n -= 1\n    print(n)"),
        ],
        "能写出有初始化、状态变化和终止条件的 while，并能解释为什么循环一定会结束。",
        "remaining = 3\nwhile remaining:\n    print(remaining)\n    # 在这里减少状态\n",
        [("倒计数", "每轮打印 remaining 后减一", "输出 3、2、1 后停止"), ("空边界", "将 remaining 设为 0", "循环体不执行且程序继续")],
        "运行 remaining=3、0、-1 三种情况；为负数决定业务规则并避免意外无限循环。",
        [("倒计数", "remaining = 3\nwhile remaining:\n    print(remaining)\n    remaining -= 1", "3\n2\n1"), ("状态退出", "answer = ''\nwhile answer != 'yes':\n    answer = 'yes'\nprint('继续')", "继续")],
        "定义 countdown(start)：返回从 start 到 1 的列表；start<=0 返回空列表，并在实现中让循环状态每轮变化。",
        "countdown(3) 返回 [3,2,1]，countdown(0) 和 countdown(-1) 返回 []，没有死循环。",
    ),
    "D03-break-continue": _detail(
        [
            "continue 结束当前轮，直接进入下一轮；break 结束最近一层循环。它们改变的是控制流，不是循环变量本身，所以使用后仍要确认下次判断是否能推进。",
            "过滤时 continue 可以把异常或不需要的项提前跳过，搜索时 break 可以在找到目标后停止。二者都只影响最近一层循环，嵌套循环中要特别注意 break 并不会退出外层。",
            "过多的 break/continue 会隐藏业务路径。练习时为每个跳转写一个具体触发输入，并检查没有触发跳转、第一次触发和嵌套触发三种情况。",
        ],
        "JavaScript 也有 break/continue，作用范围同样是最近循环；Python 的 for/while 都支持它们，但不能把 continue 当成跳过整个函数，也不能用 break 替代函数 return。",
        [
            ("continue 后仍执行下面语句", "被跳过的数字仍打印出来", "continue 后本轮剩余语句不会运行", "把需要跳过的分支放在打印前，并用输出验证", "for n in range(3):\n    if n == 1: continue\n    print(n)"),
            ("嵌套循环 break 误解", "内层停止但外层仍继续，结果比预期多", "break 只结束最近一层循环", "用标志、函数 return 或重新设计外层控制流", "for row in rows:\n    for cell in row:\n        if cell: break"),
        ],
        "能在过滤和搜索中准确选择 continue 或 break，并说明跳转影响的循环层级。",
        "for number in range(6):\n    if number == 2:\n        # 跳过 2\n        continue\n    print(number)\n",
        [("过滤", "让 2 不打印", "输出中没有 2，其余数字仍按顺序出现"), ("搜索", "遇到 5 后 break", "找到目标后不再处理后续项")],
        "分别运行过滤和搜索两个循环，记录每个跳转的触发值；再用嵌套列表验证 break 只退出内层。",
        [("跳过和停止", "for number in range(6):\n    if number == 2:\n        continue\n    if number == 5:\n        break\n    print(number)", "0\n1\n3\n4"), ("搜索", "items = [3, 8, 4]\nfor item in items:\n    if item > 5:\n        print(item)\n        break", "8")],
        "定义 first_large(items, limit)：跳过 None，返回第一个大于 limit 的数字；没有找到返回 None，并用空列表测试。",
        "None 被跳过；找到第一个符合值立即停止；空列表和无匹配返回 None。",
    ),
    "D03-enumerate-zip": _detail(
        [
            "enumerate 把一个可迭代对象包装成 (index, value) 对，避免手写 range(len(items)) 再索引。start 只改变展示的起点，不会改变原序列。",
            "zip 把多个可迭代对象按位置组成元组，并在最短输入耗尽时停止。它不会自动报错提示长度不同，因此数据对齐是业务责任；必要时先比较长度或使用严格策略。",
            "解包循环变量时，左侧数量必须和产生的元组形状匹配。真实报表常需要序号、名称和分数同时展示，先打印一轮 zip 的结果，再决定输出格式和短输入处理。",
        ],
        "JavaScript 的 entries() 可以提供索引和值，Python enumerate 是更直接的迭代器；JS 的 zip 需要库或手动索引。Python zip 默认截断，不能假设它会补 null/None。",
        [
            ("手写 range(len()) 越界", "输入为空或变化时出现 IndexError", "索引范围和数据长度在修改后不同步", "优先使用 enumerate 直接取得序号和值", "for i in range(len(names) + 1):\n    print(names[i])"),
            ("zip 长度不一致未察觉", "最后一条数据被静默丢弃", "zip 在最短输入结束，不会自动补齐", "先校验长度，或明确记录截断行为", "print(list(zip(['a', 'b'], [1])))"),
        ],
        "能用 enumerate 获取展示序号，用 zip 配对数据，并能发现或解释长度不一致。",
        "names = ['安', '博']\nscores = [90, 80]\n# 用 enumerate 和 zip 分别完成两个输出\n",
        [("序号", "enumerate(names, start=1)", "输出 1 安、2 博"), ("配对", "zip(names, scores)", "输出姓名和对应分数")],
        "运行两组等长数据，再删掉一个 score；观察 zip 的输出并增加长度检查或明确的截断提示。",
        [("序号", "names = ['安', '博']\nfor index, name in enumerate(names, start=1):\n    print(index, name)", "1 安\n2 博"), ("配对", "for name, score in zip(['安', '博'], [90, 80]):\n    print(name, score)", "安 90\n博 80")],
        "定义 pair_scores(names, scores)：长度相同返回 [{'name':..., 'score':...}]，长度不同抛 ValueError；使用 enumerate 给结果加 position。",
        "等长输入按位置形成两条带 position 的记录；长度不一致不被静默截断。",
    ),
    "D03-comprehension": _detail(
        [
            "推导式把“遍历来源、计算结果、可选过滤”放进一个容器表达式。列表推导式产生 list，集合推导式去重，字典推导式同时写 key 和 value；外层括号决定结果容器。",
            "执行顺序仍是先取一个元素、判断 if、计算表达式，再放入结果。推导式不会改变原容器，但表达式中的可变操作仍可能产生副作用，所以不要把复杂业务塞进一行。",
            "推导式适合简单转换和过滤，超过一层嵌套或需要多个异常分支时应退回普通循环。边界要覆盖空输入、重复元素和条件全部不满足，确认结果类型符合后续代码。",
        ],
        "JavaScript 的 map/filter 可以组合完成类似转换，Set/对象也能去重或建映射；Python 推导式把循环语法放在括号内，不能照搬 JS 的箭头函数表达式。",
        [
            ("把 dict 写成 set 结构", "得到集合而不是键值映射", "缺少 key: value 形式，外层括号决定类型", "字典推导式明确写出 key 和 value", "print({word for word in ['py', 'py']})"),
            ("在推导式里做副作用", "结果难以预测或打印次数异常", "表达式调用 append 等改变外部状态，阅读顺序不清", "将副作用拆到普通 for，推导式只负责计算", "result = [items.append(x) for x in items]"),
        ],
        "能根据输出数据类型选择 list/set/dict 推导式，并在复杂逻辑时主动换回普通循环。",
        "values = [1, 2, 3, 4]\n# 生成偶数平方列表和一个字典映射\n",
        [("列表过滤", "保留偶数并计算平方", "得到 [4, 16]"), ("空输入", "把 values 改为 []", "得到空 list 而不是异常")],
        "分别写列表、集合和字典推导式，使用重复值与空输入；打印 type 和结果，确认去重和键值关系。",
        [("列表", "squares = [n * n for n in range(4)]\nprint(squares)", "[0, 1, 4, 9]"), ("字典", "even = {n: n * n for n in range(5) if n % 2 == 0}\nprint(even)", "{0: 0, 2: 4, 4: 16}")],
        "定义 summarize_numbers(values)，返回包含 even_squares(list)、unique(set)、by_value(dict) 三个键的字典；空输入也返回三个空容器。",
        "三种结果类型正确，重复输入只在 unique 中保留一次，复杂逻辑不依赖副作用。",
    ),
    "D04-def-return": _detail(
        [
            "def 语句创建函数对象并绑定到一个名字，函数体只有在调用时才执行。参数是调用者传入的局部名字，return 把一个值交给调用者并立即结束当前调用。",
            "没有 return 或只写 return 时，函数结果是 None；print 是输出副作用，不等于返回值。把计算和显示分开，函数才容易被测试、复用和组合。",
            "函数调用会建立新的局部执行帧，参数按位置或关键字绑定。调用者要满足参数数量和名称要求；边界输入应在函数内部明确返回结果或抛出有意义的异常。",
        ],
        "JavaScript 用 function 或箭头函数，Python 用 def 和缩进；两者都有 return，但 Python 函数省略 return 明确得到 None。Python 没有 JS 自动插入分号，缩进决定函数体范围。",
        [
            ("只 print 不 return", "调用者得到 None，后续计算失败", "print 只写输出流，不把值交还给调用者", "用 return 返回结果，是否打印交给调用者", "def area(w, h):\n    print(w * h)\nvalue = area(2, 3)"),
            ("return 后代码仍期待执行", "return 后的日志或清理没有发生", "return 立即离开当前函数", "把必要动作放在 return 前，或使用 finally 管理清理", "def f():\n    return 1\n    print('never')"),
        ],
        "能写出有输入、返回值和边界行为的函数，区分返回值与打印副作用。",
        "def area(width, height):\n    # 返回矩形面积\n    pass\n",
        [("正常调用", "实现 width * height 并 return", "area(3,4) 得到 12"), ("边界调用", "测试 0 和负数并决定规则", "规则明确，不把 None 静默当面积")],
        "调用函数并把返回值传给另一个 print；再写一个只 print 的对照函数，观察两者返回值差异。",
        [("返回值", "def area(width, height):\n    return width * height\nprint(area(3, 4))", "12"), ("None", "def greet(name):\n    print('你好', name)\nprint(greet('林'))", "你好 林\nNone")],
        "定义 rectangle_area(width, height)，返回面积；宽高必须是数字且不能为负数，非法输入抛 ValueError，并为 3*4、0、-1 写调用。",
        "rectangle_area(3,4)==12，零边长返回 0，负数抛 ValueError；函数返回值可被调用者继续使用。",
    ),
    "D04-default-keyword": _detail(
        [
            "默认参数在调用者省略对应实参时提供值，函数体看到的仍是普通局部参数。带默认值的参数必须放在无默认参数之后，否则调用绑定会产生 SyntaxError。",
            "关键字参数按参数名绑定，能让调用意图清晰并减少位置顺序错误。位置参数必须先于关键字参数；未知名称、重复传值和漏掉必需参数都会在调用阶段报 TypeError。",
            "默认值在函数定义时计算一次，因此不要用可变 list/dict 作为共享默认值。需要每次调用独立对象时，把 None 作为哨兵并在函数体内创建新容器。",
        ],
        "JavaScript 常用默认参数和对象参数模拟关键字参数，Python 原生支持 keyword-only/关键字调用。Python 的参数顺序规则更严格，不能把 `name=value` 放到位置参数前面。",
        [
            ("默认参数排在必需参数前", "定义阶段 SyntaxError", "调用绑定无法确定缺省位置", "把必需参数写在前面", "def greet(prefix='Hi', name):\n    pass"),
            ("可变默认值被调用共享", "第二次调用带有第一次的数据", "list 默认对象只创建一次", "使用 None 哨兵，在函数内建立新 list", "def add(x, bucket=[]):\n    bucket.append(x)\n    return bucket"),
        ],
        "能用默认值减少重复传参，用关键字提高可读性，并避开共享可变默认参数。",
        "def greet(name, prefix='你好'):\n    # 返回一条问候\n    pass\n",
        [("省略默认值", "greet('林')", "使用默认 prefix"), ("覆盖默认值", "用 prefix='早上好' 调用", "只改变这次调用，不影响下一次")],
        "分别使用位置、关键字、省略默认值和重复参数的调用；记录 TypeError 的原因而不是只记错误文本。",
        [("默认", "def greet(name, prefix='你好'):\n    return f'{prefix}，{name}'\nprint(greet('林'))", "你好，林"), ("关键字", "def greet(name, prefix='你好'):\n    return f'{prefix}，{name}'\nprint(greet('林', prefix='早上好'))", "早上好，林")],
        "定义 make_message(name, prefix='你好', suffix='!')，支持关键字覆盖；用 None 作为可选标签哨兵时确保每次调用不共享 list。",
        "省略值使用默认文本，关键字覆盖只影响当前调用，可选 list 在不同调用间互不污染。",
    ),
    "D04-varargs": _detail(
        [
            "*args 把多余的位置实参收集成 tuple，**kwargs 把多余的关键字实参收集成 dict。函数内部看到的是已经整理好的容器，顺序参数和命名参数的来源因此清晰可观察。",
            "调用时的 * 和 ** 是解包：把一个序列展开为位置参数，把一个映射展开为关键字参数。收集和解包方向相反，参数名冲突或容器形状不对会报 TypeError。",
            "可变参数适合日志、聚合和配置转发，但不是逃避设计契约的办法。函数仍应明确必需参数、允许的关键字和返回结构，边界要覆盖空 args、空 kwargs 和重复键。",
        ],
        "JavaScript 常用 rest/spread `...` 同时表示收集和展开；Python 分别使用 *args 与 **kwargs，并区分序列和映射。Python 的 kwargs 键必须是字符串标识符，调用时的重复参数会立即报错。",
        [
            ("把 kwargs 当 tuple", "尝试按位置访问或调用 append 失败", "**kwargs 收集的是 dict，不是 tuple", "使用 kwargs['name'] 或 kwargs.items()", "def show(**kwargs):\n    print(kwargs[0])"),
            ("解包类型不匹配", "传入 list 给 ** 时出现 TypeError", "** 要求 mapping，* 才接受 iterable", "按参数形状选择 * 或 **", "def f(**options):\n    return options\nf(**['a'])"),
        ],
        "能定义同时接收 args/kwargs 的函数，并用返回结构证明收集与解包的方向。",
        "def describe(*args, **kwargs):\n    # 返回两个参数容器\n    pass\n",
        [("收集位置", "传入 1、2 并观察 args", "args 是 (1, 2)"), ("收集关键字", "传入 name='林'", "kwargs 是 {'name': '林'}")],
        "用直接调用和 `values`/`options` 解包调用各一次；增加空调用，确认返回空 tuple 和空 dict。",
        [("位置参数", "describe(1, 2, name='林')", "args=(1,2)，kwargs 含 name"), ("空参数", "describe()", "args=()，kwargs={}")],
        "定义 describe(*args, **kwargs)，返回 {'args': args, 'kwargs': kwargs}；验证位置参数 tuple、关键字参数 dict 和空调用。",
        "describe(1,2,name='林') 的 args/kwargs 形状正确；空调用不报错；实现没有把 kwargs 转成 list。",
    ),
    "D04-scope": _detail(
        [
            "函数调用会创建局部作用域，函数内部赋值的名字默认是 Local；函数没有局部名字时，解释器依次查找 Enclosing、Global、Builtins，这就是 LEGB。",
            "读取外层变量不等于修改它。只要函数体对某名字赋值，编译器就把它视为局部；先读取后赋值会出现 UnboundLocalError，即使模块级已有同名变量。",
            "作用域让函数隔离临时状态，也会造成同名遮蔽。实践中优先通过参数传入依赖、通过 return 传出结果，只有明确需要共享状态时才使用 global/nonlocal。",
        ],
        "JavaScript 的词法作用域同样允许内层读取外层名字，但 Python 的 LEGB 查找和“函数内一旦赋值即局部”规则更显式；JS 的 var/let hoisting 不能用来解释 Python 的 UnboundLocalError。",
        [
            ("函数内赋值遮蔽全局", "读取时 UnboundLocalError", "编译器看到赋值就把 name 判定为局部", "通过参数传入，或明确声明 global（仅在确有必要时）", "count = 1\ndef show():\n    print(count)\n    count = 2"),
            ("误以为局部变量会泄漏", "函数外 NameError", "局部绑定只在函数调用帧存在", "return 结果，或在外层显式接收返回值", "def make():\n    hidden = 3\nmake()\nprint(hidden)"),
        ],
        "能用 LEGB 解释名字来源，避免依赖隐式全局，并通过参数/返回值传递状态。",
        "value = '外层'\ndef read():\n    # 创建一个局部 value 并返回\n    pass\n",
        [("局部遮蔽", "在 read 内绑定局部 value", "read() 返回局部值，外层 value 不变"), ("读取全局", "删除局部绑定后调用 show", "函数可读取全局但不自动修改它")],
        "运行局部遮蔽、读取全局、函数外访问局部三种例子；为每个名字标注 L/E/G/B 来源。",
        [("局部/外层", "value = '外层'\ndef read():\n    value = '局部'\n    return value\nprint(read(), value)", "局部 外层"), ("读取全局", "name = '模块'\ndef show():\n    print(name)\nshow()", "模块")],
        "定义 read_config(default)，优先返回局部参数而不是读取同名全局；用不同值证明调用之间没有共享临时局部状态。",
        "传入参数时返回参数值，未传入时使用明确默认；函数外不能直接访问内部临时名字。",
    ),
    "D04-global-nonlocal": _detail(
        [
            "global 声明让函数内的赋值重新绑定模块级名字；没有声明时，函数内 `counter += 1` 会被当作局部读写。global 改变的是模块共享状态，调用顺序会影响后续结果。",
            "nonlocal 只能出现在嵌套函数中，它指向最近一层外部函数的已有绑定。闭包返回 inner 后，外层函数已经结束，但 cell 会保留 value，因此同一个 step 可以记住前一次调用。",
            "共享状态很方便但难测试；优先把状态放进对象或显式参数，只有教学示例、模块计数器或闭包工厂需要时才使用 global/nonlocal。每个测试要建立新的闭包，避免实例之间串状态。",
        ],
        "JavaScript 闭包也能捕获并修改外层 let，但没有 global/nonlocal 这两个声明词；Python 必须用 nonlocal 明确“我要改外层绑定”。JS 模块作用域与 Python 模块全局都可能共享状态，但 Python 的 global 绑定规则更严格。",
        [
            ("忘记 nonlocal", "UnboundLocalError 或计数永远不变", "`value += 1` 先读后写，未声明时被判为局部", "在嵌套函数中声明 nonlocal value", "def make():\n    value = 0\n    def step():\n        value += 1\n        return value\n    return step"),
            ("闭包误用全局计数", "两个 counter 互相影响", "global 状态不属于某一个闭包实例", "将 value 放在工厂函数外层并声明 nonlocal", "counter = 0\ndef make():\n    def step():\n        global counter\n        counter += 1\n        return counter\n    return step"),
        ],
        "能解释 global 与 nonlocal 的绑定范围，并写出彼此独立、可重复测试的计数闭包。",
        "def make_counter():\n    value = 0\n    def step():\n        nonlocal value\n        # 补充一次递增并返回\n        pass\n    return step\n",
        [("闭包状态", "连续调用同一个 step 三次", "得到 1、2、3"), ("实例隔离", "再创建 second_counter", "它从 1 开始，不受第一个闭包影响")],
        "运行两个独立计数器，故意删除 nonlocal 看错误；确认没有使用模块级 counter 伪装闭包状态。",
        [("global", "counter = 0\ndef add_global():\n    global counter\n    counter += 1\nadd_global()\nprint(counter)", "1"), ("nonlocal", "def make_counter():\n    value = 0\n    def step():\n        nonlocal value\n        value += 1\n        return value\n    return step\nstep = make_counter()\nprint(step(), step())", "1 2")],
        "定义 make_counter() 返回 step，使用 nonlocal 保存计数；两个工厂调用必须互不影响，各自返回 1、2、3。",
        "同一闭包返回 [1,2,3]，第二个闭包也从 1 开始；代码含 nonlocal 且不依赖 global。",
    ),
    "D04-lambda": _detail(
        [
            "lambda 创建一个匿名函数，冒号右边只能是一个表达式，表达式的值就是返回值。它适合排序 key、短小映射或一次性回调，不适合承载多分支和副作用。",
            "sorted 的 key 函数接收每个元素并返回比较依据；lambda 可以直接取元组第二项或对象属性。先写出普通 def，再判断改成 lambda 后是否仍然能读懂。",
            "lambda 仍然遵守作用域和闭包规则，循环中捕获变化变量可能得到延迟绑定的意外结果。需要调试、注释或复用时，给函数一个名字通常更好。",
        ],
        "JavaScript 箭头函数也能写短回调，但 Python lambda 只能有一个表达式，不能包含赋值语句和多条语句。Python 的 sorted(key=...) 与 JS sort(compareFn) 的回调契约也不同：key 返回比较键，不返回比较结果。",
        [
            ("把 lambda 写成多条语句", "SyntaxError", "lambda 语法只接受一个表达式", "改用 def，或把表达式组合成清晰的单值计算", "double = lambda x: y = x * 2"),
            ("把 key 写成比较函数", "排序结果错误或 TypeError", "Python sorted 的 key 要返回每项的键值", "写 key=lambda item: item[1]", "sorted(items, key=lambda a, b: a[1] - b[1])"),
        ],
        "能用 lambda 表达短小 key 函数，并知道复杂逻辑何时必须改回 def。",
        "items = [('a', 3), ('b', 1)]\n# 按第二项排序，不写多语句 lambda\n",
        [("选择 key", "让 lambda 返回 item[1]", "b 排在 a 前"), ("改写 def", "把复杂表达式改成有名函数", "输出保持一致且更易调试")],
        "比较 lambda key 与普通 def key 的结果；增加空列表和相同 key 输入，确认排序稳定且不报错。",
        [("排序 key", "items = [('a', 3), ('b', 1)]\nprint(sorted(items, key=lambda item: item[1]))", "[('b', 1), ('a', 3)]"), ("简单计算", "double = lambda number: number * 2\nprint(double(4))", "8")],
        "定义 sort_tasks(tasks)，按每个字典的 priority 升序返回新列表；用 lambda 只提取 key，不在 lambda 中修改任务。",
        "priority 1 的任务排在 2 前；空列表返回空列表；原 tasks 顺序不被 sorted 原地修改。",
    ),
    "D04-type-hints": _detail(
        [
            "类型标注写在参数名后和返回箭头后，用来表达函数契约与阅读提示。它不会在普通 Python 运行时自动转换 '20' 为 20，也不会替你拒绝错误类型。",
            "list[int]、dict[str, int] 和 Callable[[int], str] 描述容器或回调的形状。标注应与真实 return 一致，否则静态工具会提示风险，但程序仍可能运行出不一致结果。",
            "类型标注的价值在边界处最明显：读者知道传入什么、得到什么，测试可以验证关键结果。遇到 Optional/None 时要把缺失路径写进标注和实现，而不是只在注释里说明。",
        ],
        "TypeScript 会在编译阶段检查类型并从类型系统生成错误，而 Python 标注默认只是运行时可读取的元数据；typing.get_type_hints 可以观察它，但不会代替验证。Python 的 `-> str` 与 JS 的返回类型注解不是同一执行机制。",
        [
            ("标注与返回值不一致", "静态检查提示返回 int，实际得到 None", "函数分支没有 return 或标注写错", "让所有路径返回声明类型，或改为 Optional", "def name() -> str:\n    print('林')"),
            ("把标注当自动转换", "format_user('林', '20') 仍按字符串运行", "Python 不因 annotation 自动转换参数", "在边界显式校验/转换，并测试错误类型", "def add(a: int, b: int) -> int:\n    return a + b\nprint(add('1', '2'))"),
        ],
        "能写出输入输出标注，使用 typing 工具观察标注，并明确标注不会替代运行时验证。",
        "def format_user(name: str, age: int) -> str:\n    # 返回姓名和年龄的文本\n    pass\n",
        [("写标注", "为 name、age 和 return 补全标注", "get_type_hints 能读到三项"), ("测结果", "调用林、20 并检查字符串", "返回文本含姓名和年龄")],
        "运行正确类型和错误类型两次；用 typing.get_type_hints 检查参数/返回标注，同时在实现中决定是否显式拒绝字符串年龄。",
        [("返回文本", "def repeat(text: str, times: int) -> str:\n    return text * times\nprint(repeat('好', 2))", "好好"), ("Callable", "from collections.abc import Callable\ndef apply(fn: Callable[[int], int], value: int) -> int:\n    return fn(value)\nprint(apply(lambda x: x + 1, 2))", "3")],
        "定义 format_user(name: str, age: int) -> str，返回 '姓名: 年龄'；用 get_type_hints 验证标注，并为负年龄决定明确错误。",
        "format_user('林',20)=='林: 20'，标注含 name/age/return；负年龄按实现契约拒绝或返回明确文本。",
    ),
    "D05-list-tuple": _detail(
        [
            "list 是有序且可变的序列，适合任务列表、结果集合等需要增删改的状态；tuple 也是有序序列，但创建后不能替换元素，适合固定坐标或返回多项结果。",
            "两者都支持索引和切片，切片会创建同类型的新序列。append、insert、pop 会改变 list 本身，而 tuple 不能调用这些修改操作；选择容器时要看数据是否需要原地变化。",
            "空容器、单元素 tuple 的语法有边界：() 是空 tuple，(1,) 才是单元素 tuple。遍历时不要把可变 list 当作固定记录，也不要为了“不可变”误以为 tuple 内部嵌套对象绝对不可变。",
        ],
        "JavaScript 的 Array 类似 Python list，但 JS 没有内建且语义完全对应的 tuple；Python tuple 的不可变性更适合表达固定结构。Python 切片会创建序列，JS slice 也会复制但不支持 Python 的 step。",
        [
            ("单元素 tuple 少逗号", "得到 int 而不是 tuple", "括号不是 tuple 标记，逗号才是", "写成 (value,)", "point = (3)\nprint(type(point).__name__)"),
            ("把 pop 当成只读", "原 list 少了一个元素", "pop 会修改 list 并返回被移除值", "需要保留原列表时先 copy 或使用切片", "items = ['a','b']\nlast = items.pop()"),
        ],
        "能根据可变性选择 list/tuple，正确使用索引、切片和增删操作。",
        "items = ['a', 'b']\npoint = (3, 4)\n# 对 list 修改，对 tuple 只读取\n",
        [("list 修改", "append 后打印 items", "得到三个元素"), ("tuple 读取", "打印 point 的两个位置", "输出 3 和 4，未尝试赋值")],
        "运行空 list、单元素 tuple 和普通 tuple；故意写 tuple[0] = 9 观察 TypeError，再用新 tuple 表达修改后的值。",
        [("list", "items = ['a', 'b']\nitems.append('c')\nprint(items)", "['a', 'b', 'c']"), ("tuple", "point = (3, 4)\nprint(point[0], point[1])", "3 4")],
        "定义 normalize_pair(values)：要求恰好两个元素，返回 tuple；输入 list 时不要修改原 list，长度错误抛 ValueError。",
        "['a','b'] 返回 ('a','b')，原 list 不变；空列表、三元素列表得到明确 ValueError。",
    ),
    "D05-dict-set": _detail(
        [
            "dict 用可哈希键映射到值，读取/更新写作 d[key]；set 只保存不重复的可哈希元素。dict 适合带名称的字段，set 适合去重、成员测试和集合运算。",
            "访问不存在的 dict 键会 KeyError，get 可以提供默认值；set.add 添加元素，discard 删除而不因不存在报错。列表不能作为键，因为它是可变且不可哈希的。",
            "容器的修改会影响所有指向同一对象的名字。遍历 dict 时默认得到键，遍历 set 没有稳定顺序；需要展示时排序，但不要把排序后的顺序误认为 set 的存储顺序。",
        ],
        "JavaScript object/Map 和 Set 能表达类似结构，但 Python dict 的 `d[key]` 缺键会抛 KeyError，JS 属性缺失常得到 undefined；Python set 也不承诺迭代顺序，不能按 Array 经验取下标。",
        [
            ("直接读取缺失键", "报 KeyError", "键不存在且代码没有默认策略", "用 get 或先判断 in，并决定缺失含义", "task = {}\nprint(task['title'])"),
            ("给 set 使用下标", "报 TypeError: 'set' object is not subscriptable", "set 无索引顺序，成员测试应使用 in", "用 value in tags 或转 sorted 后展示", "tags = {'py'}\nprint(tags[0])"),
        ],
        "能用 dict 建模字段、用 set 去重和测试成员，并处理缺键、删除不存在元素和无序展示。",
        "task = {'title': '买书', 'done': False}\ntags = {'python', 'python'}\n# 更新 task 并安全增删 tags\n",
        [("更新字段", "把 done 改为 True", "字典保留 title 并更新 done"), ("去重", "添加 cli 并 sorted 展示", "标签只出现一次且展示可预测")],
        "运行缺失键、重复标签、discard 未存在元素三个边界；用 get 提供默认标题，不把 set 当有序 list。",
        [("字典", "task = {'title': '买书', 'done': False}\ntask['done'] = True\nprint(task)", "{'title': '买书', 'done': True}"), ("集合", "tags = {'python', 'python', 'test'}\ntags.add('cli')\nprint(sorted(tags))", "['cli', 'python', 'test']")],
        "定义 summarize_tags(tags)，返回 {'unique': set(tags), 'count': len(set(tags))}；对重复标签、空列表和缺失输入策略写测试。",
        "重复标签被去重，count 等于唯一标签数；返回值同时是 dict 和 set，空列表得到空集合/0。",
    ),
    "D05-mutability": _detail(
        [
            "变量赋值通常只复制对象引用，不复制对象本身。执行 alias = items 后，alias.append 会通过同一个 list 改变 items；可以用 id 或 `alias is items` 观察它们确实是同一对象。",
            "list.copy() 创建新的外层 list，修改新列表不会改变原列表，但嵌套 list 仍共享内部对象，这就是浅复制。深层数据需要 copy.deepcopy 或明确重建结构，不能只看到外层不同就宣称完全独立。",
            "函数接收 list 时也接收引用，是否原地修改必须写进契约。输入式练习要同时检查返回值、原输入和身份关系，避免测试只看最终副本而漏掉副作用。",
        ],
        "JavaScript Array 赋值同样复制引用，`slice()` 常用于浅复制；Python 的 `is` 明确检查身份，`==` 只比较内容。两种语言都需要额外处理嵌套对象，不能把浅复制当深复制。",
        [
            ("把赋值当复制", "修改 alias 后原 list 也变化", "= 只建立第二个引用", "使用 copy() 或根据契约明确允许原地修改", "items = ['a']\nalias = items\nalias.append('b')"),
            ("浅复制遗漏嵌套", "修改 copied[0] 仍改变原嵌套元素", "copy 只复制外层容器", "使用 deepcopy 或逐层复制，并写嵌套测试", "a = [['x']]\nb = a.copy()\nb[0].append('y')"),
        ],
        "能通过身份和行为区分别名、浅复制与原对象，并写出不意外修改输入的函数。",
        "def copy_and_append(items):\n    # 复制外层后追加 new\n    pass\n",
        [("观察别名", "alias = items 后 append", "原 items 同步出现新元素"), ("观察复制", "copy_items.append", "原 items 不变，副本改变")],
        "运行一层 list 和嵌套 list；分别打印 `is`、`==` 和两个对象内容，说明哪些变化是预期副作用。",
        [("别名", "items = ['a']\nalias = items\nalias.append('b')\nprint(items)", "['a', 'b']"), ("复制", "items = ['a']\ncopy_items = items.copy()\ncopy_items.append('b')\nprint(items, copy_items)", "['a'] ['a', 'b']")],
        "定义 copy_and_append(items)，返回 (items, copied)，copied 用外层复制后追加 'new'；原 list 不得出现 'new'，并用两个实例检查身份。",
        "copy_and_append(['old']) 返回 (['old'], ['old','new'])，两个 list 内容符合预期且身份不同。",
    ),
    "D05-unpacking": _detail(
        [
            "序列解包按位置把 iterable 的元素绑定到多个名字，左侧目标数量必须匹配；星号目标收集剩余元素，因此 first, *middle, last 可以处理长度至少为两的序列。",
            "字典解包用 ** 把键值展开到新的字典字面量或函数调用中，后出现的同名键会覆盖前面的值。解包不会自动验证业务字段，合并前要明确覆盖是否允许。",
            "解包让代码表达数据结构，但会把数量错误提前变成 ValueError。边界测试要覆盖空序列、单元素、过长序列和重复字典键，确认错误是可理解的。",
        ],
        "JavaScript 的 destructuring 和 spread 与 Python 解包很相似，但 Python 的星号目标只能出现在合法赋值位置，字典 ** 只接受 mapping。Python 解包数量不匹配会 ValueError，不会静默得到 undefined。",
        [
            ("左侧数量不匹配", "报 ValueError: not enough/too many values", "序列元素数无法绑定到目标", "使用星号收集，或在解包前校验长度", "first, last = [1, 2, 3]"),
            ("误用单星号合并字典", "得到键序列或调用参数错误", "字典合并需要 **，单星号展开可迭代对象", "在字典字面量中使用 {**left, **right}", "left = {'a': 1}\nright = {*left}"),
        ],
        "能用序列/字典解包表达结构，并在长度和键覆盖边界处作出明确选择。",
        "values = [1, 2, 3, 4]\n# 解包首、中、尾并合并两个字典\n",
        [("星号收集", "写 first, *middle, last", "middle 为 [2,3]"), ("字典覆盖", "合并同名键并打印", "后一个字典的值按规则覆盖")],
        "运行长度 2、4、0 的序列解包；合并含同名键的两个字典并记录最终值来源。",
        [("序列", "first, *middle, last = [1, 2, 3, 4]\nprint(first, middle, last)", "1 [2, 3] 4"), ("字典", "left = {'a': 1}\nright = {**left, 'b': 2}\nprint(right)", "{'a': 1, 'b': 2}")],
        "定义 merge_task(defaults, overrides)，用字典解包合并配置并返回新 dict；同时定义 split_edges(values)，长度不足两项抛 ValueError。",
        "合并不修改原字典，overrides 的同名键生效；split_edges 对 [1,2,3] 返回首中尾，对短输入明确失败。",
    ),
    "D05-traversal": _detail(
        [
            "遍历嵌套容器前先确认每一层形状：是 dict、list 还是单个值。遍历 dict 默认拿 key，items() 才同时拿 key/value；遍历 list of dict 时，当前元素是记录 dict。",
            "链式访问 row['user']['name'] 假定每个键都存在，真实数据缺字段时会 KeyError。可以用 get、条件判断或数据校验把外部输入的不完整性转成可理解结果。",
            "循环是把结构化数据转成输出记录的过程，顺序、过滤和缺失策略都应可观察。练习不要只打印正常行，要放一条空记录或缺键记录，验证程序不会误把键名当内容。",
        ],
        "JavaScript 遍历 object 常用 Object.entries，Python 对应 dict.items；JS 缺属性通常给 undefined，Python 下标缺键会 KeyError。Python 访问嵌套 dict 没有可选链语法，需显式 get 或判断。",
        [
            ("直接遍历 dict 期待值", "输出 title/done 等键名", "dict 的默认迭代对象是键", "使用 items/values，按需要解包", "scores = {'安': 90}\nfor score in scores:\n    print(score)"),
            ("嵌套缺键未处理", "遇到 {} 报 KeyError", "外部记录不保证所有字段存在", "使用 get 默认值或先验证记录结构", "row = {}\nprint(row['title'])"),
        ],
        "能逐层读取 list/dict 数据，正确使用 items，并为缺失字段定义结果。",
        "scores = {'安': 90, '博': 80}\n# 遍历键和值并处理一条缺 title 记录\n",
        [("键值遍历", "使用 scores.items()", "输出姓名和分数"), ("缺失字段", "对 row.get('title','未命名')", "缺键记录仍产生可理解文本")],
        "运行两条完整记录和一条缺 title 记录；检查输出顺序和默认文本，不能让一个坏记录中断全部遍历。",
        [("字典", "scores = {'安': 90, '博': 80}\nfor name, score in scores.items():\n    print(name, score)", "安 90\n博 80"), ("嵌套", "rows = [{'title': 'A'}, {'title': 'B'}]\nfor row in rows:\n    print(row['title'])", "A\nB")],
        "定义 titles(rows)，遍历 list[dict] 返回标题列表；缺失 title 使用 '未命名'，空输入返回空列表，并保留原 rows 不变。",
        "完整记录返回对应标题，缺键变为 '未命名'，空列表返回 []；实现使用逐层读取而非打印键名。",
    ),
    "D05-comprehensions": _detail(
        [
            "列表、集合和字典推导式共享遍历结构，但结果类型决定语义：list 保留顺序和重复，set 去重，dict 用表达式产生键值。先写普通循环确认结果，再压缩成推导式。",
            "过滤条件放在 for 后，转换表达式放在最前。条件不满足时不产生结果；表达式若访问不存在字段或做除零，异常仍会发生，推导式不会自动吞掉错误。",
            "可读性是边界：一层转换过滤通常清晰，多层嵌套、多个条件和副作用会让调试困难。空输入、重复输入和全部过滤掉的输入都应返回正确的空容器。",
        ],
        "JavaScript 的 map/filter/reduce 往往把变换拆成链式回调，Python 推导式把循环和过滤放在一个表达式内。Python 集合推导式的去重与 JS Set 类似，但字典推导式不是普通 object 的直接语法替换。",
        [
            ("过滤条件写错位置", "结果包含不应保留的元素", "条件没有放在每个元素生成之前，或使用了错误变量", "先写循环核对变量，再写推导式", "[n * 10 for n in range(5) if n % 2]"),
            ("复杂推导式隐藏异常", "一条长表达式难以定位 KeyError", "多层访问和转换同时发生", "拆成步骤或普通循环，为每层数据加检查", "[row['user']['name'] for row in rows]"),
        ],
        "能为三种容器选择合适推导式，并保持转换、过滤和边界行为可读可测。",
        "values = [1, 2, 3, 4]\n# 写偶数乘十和单词长度映射\n",
        [("列表", "保留偶数并乘 10", "得到 [20,40]"), ("空结果", "用全为奇数的输入", "得到 [] 而不是 None")],
        "用普通循环先得到基准结果，再分别写 list/set/dict 推导式；对重复和空输入比较结果类型。",
        [("列表", "values = [1, 2, 3, 4]\nprint([v * 10 for v in values if v % 2 == 0])", "[20, 40]"), ("字典", "print({word: len(word) for word in ['py', 'test']})", "{'py': 2, 'test': 4}")],
        "定义 build_indexes(words)，返回 words 的长度映射和唯一小写词集合；忽略空词，输入可重复，结果不包含空字符串。",
        "重复词在 set 中只保留一次，dict 的键是原词/规范词且值为长度；空输入返回两个空容器。",
    ),
    "D05-iterators-generators": _detail(
        [
            "可迭代对象能被 iter() 转成迭代器，迭代器保存当前位置并由 next() 一次取一个值。取完后继续 next 会 StopIteration；for 正是自动处理这个协议的语法。",
            "生成器函数包含 yield，调用它时不会立即执行函数体，而是返回 generator；每次 next 才运行到下一个 yield，并暂停保留局部变量。因此它适合大文件、分页或无限序列。",
            "生成器只能消费一次，list(generator) 会把剩余值全部取完。不要把 `return list(...)` 当作生成器实现；练习应观察类型、惰性执行和 limit=0 等边界。",
        ],
        "JavaScript generator 也用 yield 和 next，但 Python 的 for/iter/next 协议与 JS iterator result 对象不同；Python 生成器直接产生值，结束时抛 StopIteration 而不是返回 `{done: true}` 给用户。",
        [
            ("用 return list 冒充生成器", "结果可迭代但一次性占用内存，类型是 list", "return 结束函数，没有 yield 暂停点", "在循环中逐项 yield，并用 inspect.isgenerator 检查", "def count_up_to(limit):\n    return list(range(limit))"),
            ("重复消费同一生成器", "第二次 list(generator) 得到 []", "生成器状态已经到结尾，不会自动重置", "每次需要遍历时重新调用生成器函数", "values = (n for n in range(2))\nprint(list(values))\nprint(list(values))"),
        ],
        "能区分 iterable、iterator 和 generator，并用 yield 延迟生成有限序列。",
        "def count_up_to(limit):\n    # 逐项 yield 0 到 limit-1\n    if False:\n        yield 0\n",
        [("惰性检查", "先调用 count_up_to，不立刻转 list", "得到 generator 对象"), ("消费序列", "用 list 或 next 取值", "3 产生 [0,1,2]，0 产生 []")],
        "分别用 inspect.isgenerator、next 和 list 验证类型/消费行为；再次消费同一对象并解释为什么为空。",
        [("yield", "def numbers():\n    yield 1\n    yield 2\niterator = iter(numbers())\nprint(next(iterator), next(iterator))", "1 2"), ("表达式", "squares = (n * n for n in range(3))\nprint(list(squares))", "[0, 1, 4]")],
        "定义 count_up_to(limit)，逐项 yield 0 到 limit-1；必须返回真正 generator，limit=0 返回空序列，不能一次性构造 list。",
        "list(count_up_to(3)) == [0,1,2]，inspect.isgenerator 为真，limit=0 不产生元素。",
    ),
    "D06-exception-types": _detail(
        [
            "异常对象携带类型和消息，类型通常比消息更稳定地表达失败原因。ValueError 表示类型对但值不合适，TypeError 表示操作与类型/参数不匹配，KeyError/IndexError 指向容器访问边界。",
            "解释器会在出错点创建异常并沿调用栈向上寻找处理者；如果没有匹配的 except，程序终止并打印 traceback。阅读最后一行异常类型和最靠近自己代码的栈帧，是定位错误的第一步。",
            "不要用裸 except 把所有异常变成“失败”。只捕获调用者能恢复的类型，保留原异常上下文；对不可恢复的编程错误让它继续暴露，测试才不会被静默错误欺骗。",
        ],
        "JavaScript 有 TypeError、RangeError 等异常，但 Python 的 KeyError/IndexError 更直接区分字典键和序列位置。两者都使用 try/catch 思路，但 Python 的 except 类型匹配和 traceback 读取方式不同。",
        [
            ("裸 except 掩盖错误", "真正的 NameError 被当成输入错误，程序继续错误运行", "except Exception/except 会捕获不该恢复的 bug", "先列出预期异常类型，其他异常继续抛出", "try:\n    print(missing)\nexcept:\n    print('输入错误')"),
            ("把 KeyError 当 IndexError", "except 分支没有执行，错误仍向上抛", "字典键访问和序列下标是不同边界", "分别捕获并给出对应字段/位置提示", "try:\n    {}['id']\nexcept IndexError:\n    pass"),
        ],
        "能从异常类型判断失败位置，精确捕获可恢复错误并保留不可恢复错误。",
        "try:\n    value = int('x')\nexcept ValueError as error:\n    # 打印异常类型和可理解提示\n    pass\n",
        [("值错误", "捕获 int('x') 的 ValueError", "输出 ValueError 和提示"), ("键错误", "单独处理缺失 dict 键", "不把它误报成索引错误")],
        "制造 ValueError、TypeError、KeyError、IndexError 四种错误；为每种选择一个准确 except，不使用裸 except。",
        [("值错误", "try:\n    int('x')\nexcept ValueError as error:\n    print(type(error).__name__)", "ValueError"), ("键错误", "try:\n    {}['missing']\nexcept KeyError:\n    print('缺少键')", "缺少键")],
        "定义 error_label(operation)，将 int('x')、缺失键、越界下标分别转换为三个稳定标签；其他异常不得被静默吞掉。",
        "三种预期异常得到对应标签；函数没有用裸 except 把 NameError/TypeError 伪装成输入错误。",
    ),
    "D06-try-except": _detail(
        [
            "try 块只应包含可能失败且需要恢复的最小语句，except 负责把特定异常转成返回值或用户反馈。把太多正常逻辑塞进 try 会让错误来源不清楚。",
            "`except ValueError as error` 可以读取异常对象；多个 except 按顺序匹配，子类异常应放在更具体的位置。处理后要决定返回默认值、再次 raise 还是记录并终止。",
            "输入解析常用 try/except，但不能把所有字符串都强行变成默认值。边界测试应区分合法数字、空文本、错误格式和真正的程序 bug，让错误反馈保持诚实。",
        ],
        "JavaScript try/catch 也包围可能失败的代码，但 Python 用多个 except 类型分支，且异常类是普通类层次。Python 没有 JS 的 catch 绑定语法，`as error` 才取得异常对象。",
        [
            ("try 范围过大", "错误提示无法判断哪一步失败", "文件读取、转换和业务计算混在一个 try", "缩小 try 到单个可恢复边界", "try:\n    data = read()\n    value = int(data)\n    save(value)\nexcept ValueError:\n    pass"),
            ("except 后继续使用未赋值变量", "出现 UnboundLocalError 或旧值污染", "异常路径没有初始化结果", "在 except 中明确返回/赋默认值", "try:\n    value = int(text)\nexcept ValueError:\n    pass\nprint(value)"),
        ],
        "能用最小 try 范围捕获准确异常，并让成功/失败路径都有明确结果。",
        "def parse(text):\n    try:\n        # 转换 text\n        pass\n    except ValueError:\n        return None\n",
        [("成功", "传入 '42' 返回 42", "调用者拿到 int"), ("失败", "传入 'x' 捕获 ValueError", "返回 None 而不是未绑定变量")],
        "运行成功、错误、空输入三条路径；在 except 中打印类型而不是异常后继续访问未赋值 result。",
        [("成功", "try:\n    value = int('42')\nexcept ValueError:\n    value = 0\nprint(value)", "42"), ("反馈", "try:\n    int('x')\nexcept ValueError as error:\n    print(f'输入无效: {error}')", "输出输入无效和异常原因")],
        "定义 parse_int(text)：合法整数返回 int，格式错误返回 None；只捕获 ValueError，并用 None/空文本边界调用。",
        "'42' 返回 42，'x' 和 '' 返回 None；其他编程错误不会被 try/except 静默吞掉。",
    ),
    "D06-else-finally": _detail(
        [
            "try 成功完成且没有异常时才执行 else，适合把依赖成功结果的后续动作放在这里；如果 try 失败，else 不运行。这样可以避免在解析失败时误保存半成品。",
            "finally 无论 try 成功、except 处理还是异常继续抛出都会运行，适合关闭文件、释放锁和记录清理事件。finally 中不要 return，否则可能覆盖原异常或原返回值。",
            "把资源生命周期和业务结果分开测试：成功路径应有 success 和 cleanup，失败路径应有 error 和 cleanup。只测试最终返回值会漏掉最重要的清理保证。",
        ],
        "JavaScript 也有 finally，执行时机相同；Python 的 else 是 try/except 特有的成功分支，JS 没有直接同名结构，不能用 else 代替 finally。",
        [
            ("把成功逻辑放 finally", "解析失败也写入成功记录", "finally 不表示成功，只表示必须执行", "成功后动作放 else，清理放 finally", "try:\n    int('x')\nfinally:\n    print('保存成功')"),
            ("finally return 吞异常", "调用者看不到原来的 RuntimeError", "finally 的 return 覆盖了待抛出的异常", "finally 只做清理，不返回业务值", "def f():\n    try:\n        raise ValueError('bad')\n    finally:\n        return None"),
        ],
        "能区分成功后动作和无条件清理，证明异常路径也执行 finally。",
        "def parse_number(text, events):\n    try:\n        value = int(text)\n        # 成功路径放在 else\n    except ValueError:\n        return None\n    finally:\n        events.append('finally')\n",
        [("成功", "传入 '7' 并观察 events", "返回 7 且 events 增加一次 finally"), ("失败", "传入 'x'", "返回 None 且仍增加一次 finally")],
        "运行成功、失败和 finally 中抛错三种情况；确认 finally 没有 return，也没有把失败报告成成功。",
        [("成功/清理", "try:\n    value = int('4')\nexcept ValueError:\n    print('失败')\nelse:\n    print('成功', value)\nfinally:\n    print('清理')", "成功 4\n清理"), ("异常清理", "try:\n    raise RuntimeError('坏了')\nfinally:\n    print('释放资源')", "释放资源后抛出 RuntimeError")],
        "定义 parse_number(text, events)：成功返回整数，失败返回 None；无论成功失败都追加一次 'finally'，并用两条调用验证。",
        "parse_number('7',[]) 返回 7 并记录 finally；parse_number('x',[]) 返回 None 仍记录 finally。",
    ),
    "D06-raise": _detail(
        [
            "raise 是程序主动拒绝不符合契约的输入，而不是让解释器偶然崩溃。异常消息应说明实际值违反了什么规则，调用者才能决定显示、重试或记录。",
            "捕获底层异常后可以抛出更有业务意义的新异常；`raise NewError(...) from exc` 保留 __cause__，traceback 能同时显示业务层和根因。裸 `raise` 只能在 except 内重新抛出当前异常。",
            "验证函数要先处理类型/范围边界，再执行计算。不要用返回字符串表示所有失败，否则调用者必须猜测字符串含义；选择异常类型和消息是一部分 API 契约。",
        ],
        "JavaScript 用 throw new Error 表达主动失败，Python 用 raise 加异常实例；Python 的 `from` 可以显式建立异常链，JS 通常需要手动设置 cause。",
        [
            ("raise 字符串", "运行时报 TypeError: exceptions must derive from BaseException", "Python 只能抛出 BaseException 子类实例", "使用 ValueError/自定义异常并写消息", "raise '输入错误'"),
            ("捕获后丢失根因", "日志只有业务错误，无法定位解析失败", "新异常没有 from 原异常", "使用 raise ... from error 保留链路", "try:\n    int('x')\nexcept ValueError:\n    raise RuntimeError('解析失败')"),
        ],
        "能主动验证规则、选择合适异常类型，并在转换异常时保留异常链。",
        "def positive(value):\n    if value <= 0:\n        # 抛出带原因的 ValueError\n        pass\n    return value\n",
        [("合法值", "positive(3)", "返回 3"), ("非法值", "positive(0)", "抛出包含规则的 ValueError")],
        "运行合法、零、负数和非数字输入；观察 traceback 的类型和消息，不要用字符串 return 伪装异常。",
        [("主动拒绝", "def positive(value):\n    if value <= 0:\n        raise ValueError('必须为正数')\n    return value\nprint(positive(3))", "3"), ("异常链", "try:\n    int('x')\nexcept ValueError as error:\n    try:\n        raise RuntimeError('解析失败') from error\n    except RuntimeError as outer:\n        print(type(outer.__cause__).__name__)", "ValueError")],
        "定义 require_nonempty(text)，空字符串和 None 抛 ValueError，非字符串抛 TypeError，合法文本返回去空白后的结果。",
        "合法文本返回清洗结果；None/空文本/非字符串分别是可区分的异常类型，消息说明具体契约。",
    ),
    "D06-custom": _detail(
        [
            "自定义异常是有名字的领域信号，通常继承 ValueError、LookupError 或 Exception。继承已有类型让调用者既能捕获具体异常，也能按更宽泛的类别处理。",
            "异常类可以很简单，只定义 class 和 pass；复杂时再添加字段。比起依赖消息字符串，异常类型能稳定支撑 `except TaskNotFound` 这样的分支。",
            "业务层应在合适边界抛出领域异常，入口层再把它转换成文本、HTTP 状态或退出码。测试要确认异常类型和消息，而不是只断言“发生了某种错误”。",
        ],
        "JavaScript 可以继承 Error 定义 DomainError，思路相似；Python 的异常继承链决定 except 匹配，不能只比较 `error.name` 字符串。",
        [
            ("自定义异常不继承异常类", "raise 时 TypeError", "只有 BaseException 子类才能被抛出", "继承 ValueError/Exception", "class InputError:\n    pass\nraise InputError()"),
            ("捕获顺序过宽", "具体异常分支永远不执行", "先捕获 Exception 把子类拦截了", "先写自定义异常，再写宽泛父类", "try:\n    raise InputError()\nexcept Exception:\n    pass\nexcept InputError:\n    pass"),
        ],
        "能定义带领域含义的异常类，并在调用边界按具体类型处理。",
        "class InputError(ValueError):\n    pass\n\ndef parse_name(value):\n    # 空值时抛 InputError\n    pass\n",
        [("声明异常", "让 InputError 继承 ValueError", "issubclass(InputError, ValueError) 为 True"), ("抛出捕获", "空姓名抛出并由调用者捕获", "输出稳定的异常类名")],
        "运行合法姓名、空姓名和非字符串姓名；分别捕获 InputError 与 ValueError，验证捕获顺序。",
        [("领域异常", "class InputError(ValueError):\n    pass\ntry:\n    raise InputError('姓名为空')\nexcept InputError as error:\n    print(type(error).__name__)", "InputError"), ("继承关系", "class AgeError(Exception):\n    pass\nprint(issubclass(AgeError, Exception))", "True")],
        "定义 InputError(ValueError) 和 parse_name(value)：空/空白姓名抛 InputError，调用者能精确捕获并保留消息。",
        "合法姓名返回清洗后的文本；空姓名抛 InputError，且 InputError 仍可被 ValueError 捕获。",
    ),
    "D06-with": _detail(
        [
            "with 把资源的进入和退出绑定到一个上下文管理器。文件对象进入 with 后可读写，离开代码块时自动 close；即使块内抛异常，退出逻辑仍会执行。",
            "`with open(path, encoding='utf-8') as stream` 同时表达资源、别名和编码。不要依赖垃圾回收或手写 close；异常发生在 read/write 中时，with 才能保证句柄释放。",
            "上下文管理器不只用于文件，也用于锁、数据库事务和临时修改。练习要检查返回内容、明确 UTF-8 编码和离开块后的资源状态，不能只看“文件存在”。",
        ],
        "JavaScript 没有完全对应的 with 资源协议，常用 try/finally 手动关闭；Python context manager 通过 __enter__/__exit__ 封装这套模式。Python 的 `with` 不能与 JS 的同名语法类比。",
        [
            ("忘记指定编码", "中文在不同系统出现乱码或 UnicodeDecodeError", "open 使用系统默认编码，环境差异改变结果", "读写明确写 encoding='utf-8'", "open(path).read()"),
            ("手动 close 遇异常未执行", "异常路径留下未关闭文件句柄", "close 写在可能抛错的语句之后且没有 finally", "用 with 管理文件，并让路径测试触发异常", "stream = open(path, encoding='utf-8')\ntext = stream.read()\nraise ValueError('bad')\nstream.close()"),
        ],
        "能用 with 读写 UTF-8 文件，并解释异常路径为何仍能完成资源清理。",
        "from pathlib import Path\n\ndef read_text(path):\n    # 用 with 和 UTF-8 返回文本\n    pass\n",
        [("准备文件", "创建含中文的临时文件", "文件有稳定 UTF-8 内容"), ("读取关闭", "调用 read_text 后检查返回值", "返回原文，句柄由 with 管理")],
        "创建含中文和换行的临时文件，调用 read_text；再让读取路径不存在，说明异常如何传播且不泄漏句柄。",
        [("内存流", "from io import StringIO\nwith StringIO('hello') as stream:\n    print(stream.read())", "hello"), ("文件", "from pathlib import Path\npath = Path('demo.txt')\nwith path.open('w', encoding='utf-8') as stream:\n    stream.write('你好')\nprint(path.read_text(encoding='utf-8'))\npath.unlink()", "你好")],
        "定义 read_text(path)，必须用 with 和 encoding='utf-8' 返回文件内容；用含中文文件及不存在路径验证成功和失败边界。",
        "中文原文完整返回；文件由 with 自动关闭；不存在路径得到明确 FileNotFoundError 或按契约转换。",
    ),
    "D07-import": _detail(
        [
            "import module 把模块对象绑定到当前命名空间，使用 module.name 访问成员；from module import name 只绑定指定成员。as 只是当前文件里的别名，不会改模块真实名称。",
            "导入会执行模块顶层代码并缓存到 sys.modules，因此模块不应在导入时启动服务或修改全局文件。把功能放进函数，导入只建立定义，测试才可安全复用。",
            "模块搜索路径由当前环境和 sys.path 决定。遇到 ModuleNotFoundError，先确认文件位置、包根目录和解释器环境，不要通过复制代码绕过导入问题。",
        ],
        "JavaScript 的 ES module import/export 也建立模块边界，但 Python 的 import 以文件/包和运行时 sys.path 为基础；Python `from` 导入的是绑定，不是 JS 的解构语法完全替代。",
        [
            ("循环导入", "ImportError: partially initialized module", "模块 A 顶层导入 B，B 又立即导入 A", "提取共享定义或把导入移到明确调用边界", "# a.py\nfrom b import value\n# b.py\nfrom a import value"),
            ("导入名被本地文件遮蔽", "导入了错误模块或缺少标准库成员", "文件名如 json.py 覆盖标准库 json", "避免与标准库/依赖同名并检查 module.__file__", "# json.py\nimport json\nprint(json.loads('{}'))"),
        ],
        "能区分模块对象、成员导入和别名，并让模块可被安全导入测试。",
        "import math\n# 用模块命名空间调用一个函数\n",
        [("模块导入", "调用 math.ceil", "得到 3"), ("成员别名", "from pathlib import Path as P", "P 创建路径对象且不影响 pathlib 名称")],
        "建立一个 helpers.py 导出 greet，main.py 分别用 import 和 from import 调用；确认导入模块不会自动打印无关副作用。",
        [("模块", "import math\nprint(math.ceil(2.1))", "3"), ("成员", "from pathlib import Path as P\nprint(P('a.txt').name)", "a.txt")],
        "编写 main.py：导入 pathlib.Path 和 math，定义 show_path(path) 返回后缀与向上取整结果；不要复制标准库实现。",
        "show_path('a.txt') 返回 '.txt'，math.ceil(2.1) 为 3；导入只使用合法模块和成员。",
    ),
    "D07-package": _detail(
        [
            "包是多个模块的目录边界，传统包通常包含 __init__.py；__init__.py 可以声明版本或公开名称，但不应塞入所有业务实现。包让导入路径表达职责层级。",
            "绝对导入从顶层包名开始，相对导入用点号指向当前包。相对导入要求模块作为包的一部分运行，直接 `python module.py` 可能没有父包上下文。",
            "包导入问题通常来自运行目录、PYTHONPATH 或包缺少标记文件。先从项目根目录运行模块并检查导入路径；不要在 main.py 中复制 helpers 的函数来“修复”导入。",
        ],
        "JavaScript 的目录和 package.json 也组织模块，但 Python 的 `from .helpers import greet` 依赖包上下文，不能直接按 JS 相对路径 import 的运行方式理解。",
        [
            ("直接运行相对导入文件", "ImportError: attempted relative import with no known parent package", "文件没有作为包模块运行", "从项目根用 python -m package.module，或在入口使用绝对导入", "from .helpers import greet\nprint(greet('世界'))"),
            ("漏掉 __init__.py", "包在预期环境中无法导入或路径含义不清", "目录没有传统包标记且运行环境不支持隐式命名空间", "创建空的 __init__.py 并从项目根验证", "from helpers import greet"),
        ],
        "能创建包目录、从模块导入函数，并用正确的包上下文运行入口。",
        "# main.py\nfrom helpers import greet\n# 打印 greet('世界') 的结果\n",
        [("建立模块", "在 helpers.py 定义 greet", "main 能导入而不复制函数"), ("运行入口", "从目录运行 main.py", "输出你好，世界")],
        "创建 helpers.py 与 main.py；从项目目录运行 main.py，并再用 `python -m` 方式说明包上下文差异。",
        [("包名", "from pathlib import Path\nprint(Path('taskproj').name)", "taskproj"), ("标准模块", "import json\ndata = json.loads('{\"ok\": true}')\nprint(data['ok'])", "True")],
        "在 main.py 从 helpers 导入 greet 并打印 greet('世界')；helpers.py 单独保存函数，不能复制函数体或使用路径穿越导入。",
        "main.py 运行输出 '你好，世界'，helpers.greet 可被独立导入；包目录有清晰导入边界。",
    ),
    "D07-main": _detail(
        [
            "同一个 .py 文件既可以被直接执行，也可以被别的模块导入。直接执行时 `__name__ == '__main__'`，导入时 __name__ 是模块的导入名；这是区分两种入口的可靠信号。",
            "把命令行动作放进 main()，再用守卫调用它，可以避免测试导入模块时立刻打印、写文件或启动服务。函数定义本身会被导入，但入口副作用只在直接运行时发生。",
            "__name__ 守卫不是装饰性模板：它决定副作用边界。测试应同时用子进程直接运行和 import 模块，分别检查输出/返回和没有额外输出。",
        ],
        "JavaScript 的 Node 入口常检查 require.main === module，ES module 还需比较 import.meta.url；Python 的 `__name__` 守卫是语言内建约定，不能写成 JS 的 require 判断。",
        [
            ("顶层直接调用 main", "导入模块时测试输出额外文字或修改文件", "调用没有放在 __name__ 守卫中", "保留定义，只有守卫内调用 main", "def main(): print('run')\nmain()"),
            ("拼写守卫字符串", "直接运行没有入口输出", "`__main__` 必须有两侧双下划线且是字符串", "写成 if __name__ == '__main__':", "if __name__ == 'main':\n    main()"),
        ],
        "能写可导入而无副作用的模块，并区分直接运行与导入测试。",
        "def main():\n    print('直接运行')\n\n# 补全 __name__ 守卫\n",
        [("定义入口", "把动作放入 main", "import 时只加载定义"), ("直接运行", "执行文件而非 import", "输出直接运行提示一次")],
        "使用子进程直接运行文件，再用 importlib 导入同一模块；记录两种情况下 __name__ 和 stdout 的差异。",
        [("直接运行", "def main():\n    print('直接运行')\nif __name__ == '__main__':\n    main()", "直接运行"), ("观察名字", "print(__name__)", "直接运行时为 __main__")],
        "定义 main() 打印一行并加 __name__ 守卫；直接运行输出一行，导入模块不应自动执行 main。",
        "子进程直接运行得到一行入口输出；导入不会产生入口副作用，守卫拼写准确。",
    ),
    "D07-stdlib": _detail(
        [
            "标准库是随 Python 提供、经过维护的模块集合。pathlib、json、datetime 等模块各自解决一类常见问题，先识别数据边界再选择 API，比手写字符串规则更可靠。",
            "导入模块后要阅读函数参数和返回类型：Path.suffix 返回后缀，json.loads 返回 Python 对象，date.isoformat 返回文本。标准库不会替你验证业务含义，解析后仍要做字段检查。",
            "使用标准库的练习应可离线、可重复、可测试。为路径使用临时目录，为日期固定样例，为 JSON 覆盖无效文本；不要因为 API 来自标准库就跳过错误边界。",
        ],
        "JavaScript 也有内建 API 和 npm 生态，但 Python 标准库模块通过 import 直接获得，API 返回的 Python 类型要按 Python 规则继续处理。不要把 JS Date/Path 字符串习惯直接当成 pathlib/date 对象。",
        [
            ("把 Path 当字符串拼接", "跨平台路径出现双分隔符或反斜杠问题", "字符串连接不知道当前系统路径规则", "使用 Path / 子路径并在边界转换为 str", "path = 'data' + '/' + 'a.txt'"),
            ("JSON 解析后不检查类型", "对 list 使用字典键，运行时报 TypeError", "JSON 文本可合法解析成任意顶层类型", "解析后先 isinstance 检查结构", "data = json.loads('[]')\nprint(data['title'])"),
        ],
        "能选择合适标准库 API，读懂返回类型，并为外部文本和路径写边界检查。",
        "from pathlib import Path\n# 用 Path 读取一个后缀，并用 date 输出 ISO 日期\n",
        [("路径", "打印 Path('a.txt').suffix", "得到 .txt"), ("日期", "创建固定 date 并 isoformat", "输出固定日期而非当前时间")],
        "组合 pathlib、json 或 datetime 完成一个小功能；输入路径和 JSON 都用临时/固定数据，不调用网络或当前随机时间。",
        [("日期", "from datetime import date\nprint(date(2025, 1, 2).isoformat())", "2025-01-02"), ("路径", "from pathlib import Path\nprint(Path('a.txt').suffix)", ".txt")],
        "定义 read_metadata(path)，用 pathlib 读取 UTF-8 JSON，确认顶层是 dict 且含 name 字符串；缺文件、无效 JSON、错误类型分别给出明确异常。",
        "合法文件返回 name；缺文件/解析失败/结构错误不会被混成一个静默空 dict，路径操作使用 Path。",
    ),
    "D07-class-instance": _detail(
        [
            "class 定义对象的共同结构和行为，调用 Name() 创建实例；__init__ 在创建时接收参数并把状态放到 self 上。self 不是关键字，而是约定的当前实例参数。",
            "实例属性存储在各自对象中，方法通过 self 读取/修改当前状态。把属性写成类属性会让实例意外共享值，尤其是 list/dict 等可变对象。",
            "类的职责是把紧密相关的数据和操作放在一起，不是把每个函数都包装成对象。练习要创建两个实例并分别修改，证明没有状态串线，再测试方法的边界输入。",
        ],
        "JavaScript class 也有 constructor、this 和方法，但 Python 方法必须显式写 self，实例属性要通过 self.title 绑定。Python 没有 JS 那种 this 自动注入，漏写 self 会在调用时出现参数错误。",
        [
            ("忘写 self", "调用方法时报 TypeError 参数数量不对", "实例方法的第一个参数接收当前对象", "定义方法时写 self，并用 self 访问属性", "class Task:\n    def label():\n        return 'x'"),
            ("把可变状态写成类属性", "两个实例共享同一 list", "类属性由所有实例读取同一个对象", "在 __init__ 中为每个实例创建 list", "class Bag:\n    items = []"),
        ],
        "能定义带实例状态和方法的类，并证明不同实例不会共享不该共享的属性。",
        "class Task:\n    def __init__(self, title):\n        self.title = title\n\n    def label(self):\n        # 返回当前任务标题\n        pass\n",
        [("实例状态", "创建两个不同 title 的 Task", "各自 label 返回自己的标题"), ("独立修改", "修改第一个 title", "第二个 title 保持不变")],
        "创建两个实例、修改其中一个并调用方法；再为 title 为空定义清晰行为，不要使用类级共享 list。",
        [("方法", "class Task:\n    def __init__(self, title):\n        self.title = title\n    def label(self):\n        return self.title\ntask = Task('学习')\nprint(task.label())", "学习"), ("计数器", "class Counter:\n    def __init__(self):\n        self.value = 0\n    def inc(self):\n        self.value += 1\nc = Counter()\nc.inc()\nprint(c.value)", "1")],
        "定义 Task 类，构造函数接收 title，label() 返回 title；创建两个实例并修改一个，证明实例状态独立。",
        "Task('学习').label() 为 '学习'；两个实例的 title 互不影响，方法包含 self。",
    ),
    "D07-inheritance": _detail(
        [
            "继承让子类获得父类的方法和属性，`class Child(Parent)` 建立 is-a 关系。子类可以直接复用父类实现，也可以重写同名方法改变某一行为。",
            "super() 用来调用父类实现，尤其常见于子类 __init__ 中先完成父类状态再添加自己的字段。重写方法时要保持输入输出契约，否则调用者按父类类型使用子类会出错。",
            "继承不是代码复用的唯一方式；如果两个对象只是“拥有”某个组件而不是“是一个”父类，组合更清楚。练习要覆盖继承默认行为、重写和 super 传参。",
        ],
        "JavaScript class extends/super 与 Python 继承概念相近，但 Python 的方法解析顺序、显式 self 和 super() 调用方式不同。不要把 JS 的原型链细节直接套到 Python 的 MRO。",
        [
            ("子类初始化漏 super", "父类属性不存在，方法调用 AttributeError", "重写 __init__ 后父类初始化不会自动执行", "在需要时调用 super().__init__(...)", "class Child(Parent):\n    def __init__(self, name):\n        self.extra = 1"),
            ("重写返回契约不一致", "调用者对结果做操作时报类型错误", "子类方法没有遵守父类约定", "保持参数/返回结构，或明确新的抽象边界", "class Dog(Animal):\n    def speak(self):\n        return None"),
        ],
        "能读懂基础继承、super 和方法重写，并判断是否应该使用组合。",
        "class Animal:\n    def speak(self):\n        return '...'\n\nclass Dog(Animal):\n    # 用 super 扩展父类结果\n    pass\n",
        [("继承默认", "让 Child 继承父类初始化", "子类实例能读取父类属性"), ("重写", "Dog.speak 调用 super", "输出父类结果加上汪")],
        "创建 Parent/Child，覆盖一个方法并在子类初始化中调用 super；测试父类实例、子类实例和多态调用。",
        [("重写", "class Animal:\n    def speak(self):\n        return '...'\nclass Dog(Animal):\n    def speak(self):\n        return super().speak() + '汪'\nprint(Dog().speak())", "...汪"), ("继承初始化", "class Base:\n    def __init__(self, name):\n        self.name = name\nclass Child(Base):\n    pass\nprint(Child('小林').name)", "小林")],
        "定义 Task 与 TimedTask：TimedTask 继承 Task，使用 super 初始化 title，重写 label 添加 deadline；保持父类 label 的基本含义。",
        "Task 与 TimedTask 都能返回标题，TimedTask 额外包含 deadline；父类初始化未被重复复制，super 调用有效。",
    ),
    "D07-dataclass": _detail(
        [
            "@dataclass 装饰器读取类字段标注，自动生成常用的 __init__、__repr__ 和比较方法。它适合主要保存数据的对象，但不会自动验证 int/str，也不会替你设计业务方法。",
            "字段写在类体中并带类型标注，构造函数参数顺序按字段顺序生成。可变默认值不能直接写 [] 或 {}，因为所有实例可能共享同一个对象；应使用 field(default_factory=list)。",
            "dataclass 的价值是减少样板而保持数据结构可见。先验证构造、字段访问和 repr，再加校验方法；不要为了教学练习在普通 Point 中塞一个无关的 __post_init__ 失败占位。",
        ],
        "JavaScript class 需要手写 constructor 和 toString，TypeScript interface 只描述结构而不生成运行时构造函数；Python dataclass 同时根据标注生成初始化和 repr，但标注不做运行时类型强制。",
        [
            ("用共享可变默认值", "两个 Point/Bag 实例修改同一 list", "类定义时 [] 只创建一次", "使用 field(default_factory=list)", "@dataclass\nclass Bag:\n    items: list[str] = []"),
            ("字段无标注", "dataclass 不把它当构造字段或工具提示缺失", "装饰器依靠 annotation 收集字段", "为每个数据字段写类型标注", "@dataclass\nclass Point:\n    x = 0\n    y = 0"),
        ],
        "能定义真正的数据类，访问字段并避免可变默认值共享，不把无关失败代码放进起始模板。",
        "from dataclasses import dataclass\n\n@dataclass\nclass Point:\n    x: int\n    y: int\n",
        [("构造字段", "创建 Point(2,3)", "x/y 可访问且 repr 包含字段值"), ("可变默认", "创建两个 Bag 并修改一个", "另一个 Bag 的 items 仍为空")],
        "运行 Point 构造、字段访问、repr 和两个 Bag 实例；故意使用 [] 默认值作为错误示例，不把它放进正式 starter。",
        [("Point", "from dataclasses import dataclass\n@dataclass\nclass Point:\n    x: int\n    y: int\nprint(Point(1, 2))", "Point(x=1, y=2)"), ("工厂默认", "from dataclasses import dataclass, field\n@dataclass\nclass Bag:\n    items: list[str] = field(default_factory=list)\nprint(Bag())", "Bag(items=[])")],
        "用 @dataclass 定义 Point(x:int,y:int)，再定义 Bag 的 list 字段并使用 default_factory；不要添加无关的 __post_init__ 失败逻辑。",
        "Point(2,3) 字段可访问且 repr 可读；两个 Bag 的 items 独立；starter 本身不包含无要求的 NotImplementedError。",
    ),
}


# 独立练习的输入不是教学示例的复制品，而是针对 practice.instructions 的
# 可运行调用。input_identifiers 是同一份练习契约的一部分，loader 会确认这些
# 名称确实出现在输入中，避免 UI 看似有示例、实际却无法开始练习。
CORE_INPUT_EXAMPLES: dict[str, list[dict[str, str]]] = {
    "D02-execution": [
        {"label": "完整输出", "value": "运行 main.py；源码依次打印 START、BLOCK、END", "expected": "stdout 恰好为 START、BLOCK、END 三行。"},
        {"label": "缩进边界", "value": "将 BLOCK 行完全取消缩进后运行 main.py", "expected": "解释器报告 IndentationError，程序无法执行。"},
    ],
    "D02-names": [
        {"label": "整数绑定", "value": "score = 88; print(type(score).__name__); print(isinstance(score, int))", "expected": "输出 int 和 True。"},
        {"label": "重新绑定", "value": "score = '88'; print(type(score).__name__); print(isinstance(score, int))", "expected": "输出 str 和 False，说明名字已指向新的对象。"},
    ],
    "D02-numbers": [
        {"label": "商余数", "value": "print(divide_parts(17, 5))", "expected": "得到 (3, 2) 或等价的商、余数结构。"},
        {"label": "除数边界", "value": "print(divide_parts(17, 0))", "expected": "得到明确错误结果或 ValueError，不出现静默的无穷计算。"},
    ],
    "D02-bool-none": [
        {"label": "缺失值", "value": "print(describe_value(None))", "expected": "输出 missing。"},
        {"label": "空文本", "value": "print(describe_value(''))", "expected": "输出 empty text，不能把空字符串误当作 None。"},
    ],
    "D02-strings": [
        {"label": "正常调用", "value": "print(transform_text(' ab '))", "expected": "输出 ba。"},
        {"label": "保持原值", "value": "original = ' ab '; print(transform_text(original)); print(original)", "expected": "依次输出 ba 和 ab（第二行保留原字符串的空格）。"},
    ],
    "D02-string-methods": [
        {"label": "逗号标签", "value": "print(format_tags(' py, test, , api '))", "expected": "输出 py / test / api。"},
        {"label": "空输入", "value": "print(format_tags('   '))", "expected": "输出 无标签，而不是多余分隔符。"},
    ],
    "D03-if": [
        {"label": "及格边界", "value": "print(classify_score(60))", "expected": "输出 B。"},
        {"label": "非法分数", "value": "print(classify_score(-1))", "expected": "抛出 ValueError，负数不会落入 C。"},
    ],
    "D03-match": [
        {"label": "命令", "value": "print(command_label('list'))", "expected": "输出 list 对应的说明。"},
        {"label": "结构模式", "value": "print(command_label(('task', '买书')))", "expected": "输出包含任务标题的说明。"},
    ],
    "D03-for": [
        {"label": "混合数字", "value": "print(sum_even([1, 2, 4, 5]))", "expected": "输出 6。"},
        {"label": "空列表", "value": "print(sum_even([]))", "expected": "输出 0，循环没有访问不存在的元素。"},
    ],
    "D03-while": [
        {"label": "倒数", "value": "print(countdown(3))", "expected": "输出 [3, 2, 1]。"},
        {"label": "非正数", "value": "print(countdown(0))", "expected": "输出 []，循环条件一开始就为假。"},
    ],
    "D03-break-continue": [
        {"label": "跳过空值", "value": "print(first_large([None, 2, 8, 10], 7))", "expected": "输出 8，None 被 continue 跳过。"},
        {"label": "没有命中", "value": "print(first_large([1, 3], 7))", "expected": "输出 None，遍历结束后没有伪造结果。"},
    ],
    "D03-enumerate-zip": [
        {"label": "配对", "value": "print(pair_scores(['A', 'B'], [90, 80]))", "expected": "得到两个带 name/score 的字典。"},
        {"label": "长度不一致", "value": "print(pair_scores(['A'], [90, 80]))", "expected": "抛出 ValueError，不静默丢掉多出的分数。"},
    ],
    "D03-comprehension": [
        {"label": "数字摘要", "value": "print(summarize_numbers([1, 2, 2, 3]))", "expected": "even_squares 为 [4]，unique 不重复且 by_value 可查长度。"},
        {"label": "空输入", "value": "print(summarize_numbers([]))", "expected": "三个结果均为空结构。"},
    ],
    "D04-def-return": [
        {"label": "面积", "value": "print(rectangle_area(3, 4))", "expected": "输出 12。"},
        {"label": "负数边界", "value": "print(rectangle_area(-1, 4))", "expected": "抛出 ValueError，函数不返回负面积。"},
    ],
    "D04-default-keyword": [
        {"label": "默认参数", "value": "print(make_message('林'))", "expected": "使用默认 prefix/suffix 生成问候。"},
        {"label": "关键字覆盖", "value": "print(make_message('林', prefix='早上好', suffix='。'))", "expected": "只替换指定的关键字参数。"},
    ],
    "D04-varargs": [
        {"label": "位置与关键字", "value": "print(describe(1, 2, name='林'))", "expected": "args 为 (1, 2)，kwargs 含 name。"},
        {"label": "空调用", "value": "print(describe())", "expected": "得到空 tuple 和空 dict，而不是缺少参数错误。"},
    ],
    "D04-scope": [
        {"label": "局部优先", "value": "default = '外层'; print(read_config('传入'))", "expected": "输出 传入，函数使用局部参数。"},
        {"label": "重复调用", "value": "print(read_config('A')); print(read_config('B'))", "expected": "两次结果分别为 A、B，不共享临时局部状态。"},
    ],
    "D04-global-nonlocal": [
        {"label": "闭包计数", "value": "counter = make_counter(); print(counter()); print(counter()); print(counter())", "expected": "输出 1、2、3。"},
        {"label": "两个闭包", "value": "a = make_counter(); b = make_counter(); print(a(), b(), a())", "expected": "输出 1 1 2，两个闭包状态彼此独立。"},
    ],
    "D04-lambda": [
        {"label": "按优先级", "value": "print(sort_tasks([{'title': 'B', 'priority': 2}, {'title': 'A', 'priority': 1}]))", "expected": "返回新列表，A 排在 B 前。"},
        {"label": "空任务", "value": "print(sort_tasks([]))", "expected": "输出 []，lambda 不会访问不存在的 priority。"},
    ],
    "D04-type-hints": [
        {"label": "格式化", "value": "print(format_user('林', 20))", "expected": "输出包含 林 和 20 的字符串。"},
        {"label": "检查标注", "value": "print(format_user.__annotations__)", "expected": "标注包含 name、age 和 str 返回值。"},
    ],
    "D05-list-tuple": [
        {"label": "二元列表", "value": "values = [1, 2]; print(normalize_pair(values)); print(values)", "expected": "返回 (1, 2)，原 list 仍为 [1, 2]。"},
        {"label": "长度边界", "value": "print(normalize_pair([1]))", "expected": "抛出 ValueError。"},
    ],
    "D05-dict-set": [
        {"label": "重复标签", "value": "print(summarize_tags(['py', 'py', 'test']))", "expected": "unique 为 {'py', 'test'}，count 为 2。"},
        {"label": "空标签", "value": "print(summarize_tags([]))", "expected": "unique 为空 set，count 为 0。"},
    ],
    "D05-mutability": [
        {"label": "复制追加", "value": "print(copy_and_append(['old']))", "expected": "原结果为 ['old']，复制结果为 ['old', 'new']。"},
        {"label": "检查引用", "value": "items = []; original, copied = copy_and_append(items); print(items is copied)", "expected": "输出 False，追加没有改变原 list 的身份。"},
    ],
    "D05-unpacking": [
        {"label": "合并配置", "value": "print(merge_task({'done': False}, {'title': '买书'}))", "expected": "得到同时含 done/title 的新 dict。"},
        {"label": "覆盖字段", "value": "print(merge_task({'title': '旧'}, {'title': '新'}))", "expected": "后面的 overrides 覆盖 title。"},
    ],
    "D05-traversal": [
        {"label": "标题列表", "value": "print(titles([{'title': 'A'}, {}, {'title': 'C'}]))", "expected": "输出 ['A', '未命名', 'C']。"},
        {"label": "空行", "value": "print(titles([]))", "expected": "输出 []。"},
    ],
    "D05-comprehensions": [
        {"label": "索引构建", "value": "print(build_indexes(['Py', 'py', '']))", "expected": "长度映射保留非空词，唯一集合为小写 py。"},
        {"label": "重复词", "value": "print(build_indexes(['api', 'api']))", "expected": "集合去重，但长度映射只保留一个键。"},
    ],
    "D05-iterators-generators": [
        {"label": "逐项生成", "value": "g = count_up_to(3); print(type(g).__name__); print(list(g))", "expected": "类型是 generator，列表为 [0, 1, 2]。"},
        {"label": "零上限", "value": "print(list(count_up_to(0)))", "expected": "输出 []，没有多生成一个 0。"},
    ],
    "D06-exception-types": [
        {"label": "转换错误", "value": "print(error_label('convert'))", "expected": "返回 int 转换失败对应的稳定标签。"},
        {"label": "未知操作", "value": "print(error_label('other'))", "expected": "未知异常不被静默吞掉，应得到明确失败。"},
    ],
    "D06-try-except": [
        {"label": "合法数字", "value": "print(parse_int('42'))", "expected": "输出 42。"},
        {"label": "格式错误", "value": "print(parse_int('x'))", "expected": "输出 None，只处理 ValueError。"},
    ],
    "D06-else-finally": [
        {"label": "成功路径", "value": "events = []; print(parse_number('7', events)); print(events)", "expected": "输出 7 和 ['finally']。"},
        {"label": "失败路径", "value": "events = []; print(parse_number('x', events)); print(events)", "expected": "输出 None 和 ['finally']，finally 仍执行。"},
    ],
    "D06-raise": [
        {"label": "合法文本", "value": "print(require_nonempty(' ok '))", "expected": "输出去除空白后的 ok。"},
        {"label": "空值", "value": "print(require_nonempty('   '))", "expected": "抛出 ValueError。"},
    ],
    "D06-custom": [
        {"label": "姓名校验", "value": "print(parse_name('林'))", "expected": "输出 林。"},
        {"label": "自定义错误", "value": "print(parse_name('   '))", "expected": "抛出 InputError，而不是模糊的普通 Exception。"},
    ],
    "D06-with": [
        {"label": "临时文件", "value": "from pathlib import Path; p = Path('note.txt'); p.write_text('你好', encoding='utf-8'); print(read_text(p))", "expected": "输出 你好，读取使用 UTF-8 并自动关闭文件。"},
        {"label": "不存在", "value": "print(read_text(Path('missing.txt')))", "expected": "抛出 FileNotFoundError，不改用其他 cwd 文件。"},
    ],
    "D07-import": [
        {"label": "路径与数学", "value": "print(show_path('report.txt'))", "expected": "结果包含 .txt 后缀和 math.ceil 的计算值。"},
        {"label": "嵌套路径", "value": "print(show_path('data/report.json'))", "expected": "Path 正确识别 .json，路径分隔符不靠字符串拼接。"},
    ],
    "D07-package": [
        {"label": "模块入口", "value": "运行 python main.py（main.py 从 helpers 导入 greet）", "expected": "输出 你好，世界。"},
        {"label": "导入来源", "value": "检查 main.py 中的 `from helpers import greet`", "expected": "greet 的实现只在 helpers.py 中出现一次。"},
    ],
    "D07-main": [
        {"label": "直接运行", "value": "运行 python main.py", "expected": "输出一行 main 的结果。"},
        {"label": "导入模块", "value": "运行 python -c \"import main\"", "expected": "导入不自动打印 main 的运行结果。"},
    ],
    "D07-stdlib": [
        {"label": "JSON 文件", "value": "print(read_metadata(Path('meta.json')))", "expected": "返回 name 字符串。"},
        {"label": "错误结构", "value": "print(read_metadata(Path('bad.json')))", "expected": "缺 name 或顶层非 dict 时明确失败。"},
    ],
    "D07-class-instance": [
        {"label": "实例方法", "value": "a = Task('学习'); print(a.label())", "expected": "输出 学习。"},
        {"label": "独立状态", "value": "a = Task('A'); b = Task('B'); a.title = '改过'; print(b.title)", "expected": "输出 B，b 不受 a 修改影响。"},
    ],
    "D07-inheritance": [
        {"label": "子类方法", "value": "print(TimedTask('学习', 30).label())", "expected": "输出同时包含标题和时长，且构造使用 super。"},
        {"label": "父类行为", "value": "print(Task('学习').label())", "expected": "父类仍返回基础标题，重写没有破坏父类。"},
    ],
    "D07-dataclass": [
        {"label": "Point", "value": "print(Point(2, 3).x, repr(Point(2, 3)))", "expected": "输出 2，repr 包含 Point(x=2, y=3)。"},
        {"label": "独立默认", "value": "a = Bag(); b = Bag(); a.items.append('x'); print(b.items)", "expected": "输出 []，default_factory 没有共享 list。"},
    ],
}

CORE_INPUT_IDENTIFIERS: dict[str, list[str]] = {
    "D02-execution": ["START", "BLOCK", "END"], "D02-names": ["score", "type", "isinstance"],
    "D02-numbers": ["divide_parts"], "D02-bool-none": ["describe_value", "None"],
    "D02-strings": ["transform_text"], "D02-string-methods": ["format_tags"],
    "D03-if": ["classify_score"], "D03-match": ["command_label"],
    "D03-for": ["sum_even"], "D03-while": ["countdown"],
    "D03-break-continue": ["first_large"], "D03-enumerate-zip": ["pair_scores"],
    "D03-comprehension": ["summarize_numbers"], "D04-def-return": ["rectangle_area"],
    "D04-default-keyword": ["make_message"], "D04-varargs": ["describe"],
    "D04-scope": ["read_config"], "D04-global-nonlocal": ["make_counter"],
    "D04-lambda": ["sort_tasks"], "D04-type-hints": ["format_user", "__annotations__"],
    "D05-list-tuple": ["normalize_pair"], "D05-dict-set": ["summarize_tags"],
    "D05-mutability": ["copy_and_append"], "D05-unpacking": ["merge_task"],
    "D05-traversal": ["titles"], "D05-comprehensions": ["build_indexes"],
    "D05-iterators-generators": ["count_up_to"], "D06-exception-types": ["error_label"],
    "D06-try-except": ["parse_int"], "D06-else-finally": ["parse_number"],
    "D06-raise": ["require_nonempty"], "D06-custom": ["parse_name"],
    "D06-with": ["read_text"], "D07-import": ["show_path"],
    "D07-package": ["helpers", "greet"], "D07-main": ["main"],
    "D07-stdlib": ["read_metadata"], "D07-class-instance": ["Task"],
    "D07-inheritance": ["TimedTask"], "D07-dataclass": ["Point", "Bag"],
}


# 每个示例都补充关键行、输出因果和边界说明。这里保留在构建器中，
# 而不是在 loader 中用重复句式“凑长度”，以便内容审阅可以逐节定位。
CORE_EXAMPLE_NOTES: dict[str, list[str]] = {
    "D02-execution": ["if True 的缩进行在条件成立时执行，所以先打印第一句，再打印缩进块。把唯一的块内语句完全顶格会在程序启动阶段得到 IndentationError。", "# 行不会执行，value = 2 先建立绑定，最后一行 print 才能输出 2。若删掉赋值而保留 print(value)，边界结果是 NameError。"],
    "D02-names": ["value = 7 先绑定整数，随后 type(value).__name__ 输出 int；名字绑定对象而不是固定类型盒子。把右侧改成未定义名字会在赋值时得到 NameError。", "value = '七' 重新绑定同一个名字，type(...).__name__ 因此输出 str。这个例子没有做数值转换；空字符串仍是 str，只是内容为空。"],
    "D02-numbers": ["7 // 2 得到整数商 3，7 % 2 得到余数 1，所以两行变量输出 3 1。除数改成 0 时会触发 ZeroDivisionError，应先定义输入边界。", "3 < 5 的结果是 True，而 0.1 + 0.2 == 0.3 常为 False，分别展示比较和浮点精度边界。若改用整数 1 + 2 == 3，结果会是 True。"],
    "D02-bool-none": ["name = '' 的真值是 False，not name 因而进入 if 并输出需要输入。把 name 改成非空文本时不会输出；None 与空字符串要按契约区分。", "循环分别打印 value is None 和 bool(value)，因此能看到 None、0、空文本、空列表与非空列表的差异。空容器是假值但不是 None，这是本例最重要的边界。"],
    "D02-strings": ["text[0] 读取第一个字符 P，text[1:4] 取位置 1、2、3，所以输出是 P 和 yth。切片右端不包含 4；若索引超出长度会抛 IndexError。", "text + '和狗' 创建新字符串，第二次 print 同时显示原 text 和 new_text，因此输出是猫 猫和狗。空字符串没有可读取的索引，应先检查长度。"],
    "D02-string-methods": ["name 和 count 被花括号中的表达式读取，f-string 因而输出小林 有 3 个任务。把 count 改成字符串仍能格式化，但计算前要明确类型。", "raw.strip() 去掉两端空白，split(',') 得到 a、b，join 用竖线重新连接，所以输出 a|b。没有逗号的文本会得到单元素列表，这是本例的边界。"],
    "D03-if": ["score = 89 先跳过 >=90，再命中 >=60，level 因而是 B。把分数改成 90 会命中 A，改成 59 会进入 else，这是分支边界。", "条件表达式先检查 age >= 18，age 为 18 时输出成人。age 改成 17 会选择未成年；这条语句只适合二选一。"],
    "D03-match": ["point = (0, 4) 匹配 case (0, y)，模式把第二个位置绑定到 y 并输出 4。point 改成 (1, 4) 时这个 case 不匹配，需提供其他分支才不会无输出。", "command = 'list' 命中第一个字面量 case，输出查看；'add' 会输出新增，其他值走 case _ 的未知。case _ 是兜底，不会把未知值改造成已知命令。"],
    "D03-for": ["range(1, 4) 的终点 4 不包含，所以循环依次输出 1、2、3。把 stop 改成 1 时循环为空，这是 range 的开区间边界。", "total 从 0 开始，for 依次把 2、5、3 加入，最终输出 10。列表为空时循环体不执行，total 仍为 0。"],
    "D03-while": ["answer 初始为空，while 条件成立后把它改为 yes，下一轮停止并输出继续。若循环体不更新 answer，就会无限循环；这正是状态循环的边界。", "remaining 每轮输出当前值再减一，依次输出 3、2、1；变成 0 后条件为假而结束。初始值为 0 时不会进入循环。"],
    "D03-break-continue": ["number == 2 时 continue 跳过 print，number == 5 时 break 结束循环，因此输出 0、1、3、4。若把 break 条件改成 4，4 也不会被打印。", "遍历 3、8、4 时第一次 item > 5 的 8 被打印，随后 break 停止搜索。把列表改成全不超过 5 的值时不会输出，调用者要定义未找到结果。"],
    "D03-enumerate-zip": ["zip 把安与 90、博与 80 按位置配对，所以两轮分别输出姓名和分数。两组列表长度不同时，zip 会在较短的一组结束时停止。", "enumerate(names, start=1) 给安、博编号 1、2，并同时提供 name。start 改成 0 会输出 0、1，序号只是展示值不会修改列表。"],
    "D03-comprehension": ["列表推导式逐个取 range(4) 的 n 并计算 n*n，输出 [0, 1, 4, 9]。range 为空时结果是空列表，不会执行表达式。", "字典推导式只保留偶数 n，并把 n 映射到 n*n，所以输出 {0: 0, 2: 4, 4: 16}。若过滤条件没有命中，结果是空字典。"],
    "D04-def-return": ["area(3, 4) 把两个实参绑定到 width、height，return 计算并交回 12。函数体只有调用时执行；传入缺少参数会得到 TypeError。", "greet 通过 print 输出你好 林，但没有 return，所以外层 print 又输出 None。函数打印和返回是两种不同的可观察结果。"],
    "D04-default-keyword": ["调用 greet('林', prefix='早上好') 用关键字覆盖默认 prefix，输出早上好，林。关键字名拼错会得到 TypeError，而不是静默使用默认值。", "省略 prefix 时使用定义处的默认值你好，输出你好，林。传入空字符串并不是省略参数，因此结果会保留空前缀。"],
    "D04-varargs": ["total(1, 2, 3) 把三个位置实参收集为 numbers tuple，再由 sum 得到 6。调用 total() 时 tuple 为空，sum 的结果是 0。", "show(color='blue', size=2) 把关键字实参收集为 dict 并打印 {'color': 'blue', 'size': 2}。调用者换一个关键字名，字典键也会随之变化。"],
    "D04-scope": ["show 没有局部 name，于是 LEGB 找到模块级 name='模块' 并输出模块。若在 show 内给 name 赋值，Python 会把它视为局部绑定，读取顺序就会改变。", "read 内的 value='局部' 遮蔽外层 value='外层'，所以 print 输出局部 外层。函数返回后局部绑定消失，外层变量仍保持外层。"],
    "D04-global-nonlocal": ["global counter 让 add_global 内的 counter += 1 重新绑定模块变量，所以 add_global() 后 print(counter) 输出 1。本例没有闭包；若删除 global，赋值前读取局部 counter 会报 UnboundLocalError。", "make_counter 返回的 step 用 nonlocal value 保存两次调用之间的数值，因此 print(step(), step()) 输出 1 2。本例不修改模块全局变量；重新创建闭包会得到独立的 value。"],
    "D04-lambda": ["double 是接收一个 number 并返回 number * 2 的匿名函数，double(4) 输出 8。lambda 只能写一个表达式；需要多步语句时应改用 def。", "sorted 的 key lambda 读取每个 tuple 的第二项，因此按 1、3 排序并输出 [('b', 1), ('a', 3)]。空列表会直接得到空列表。"],
    "D04-type-hints": ["repeat 的 str/int/str 标注描述参数和返回约定，repeat('好', 2) 仍由字符串乘法产生好好。标注不会自动把 '2' 转成整数，传入文本要另行校验。", "apply 的 Callable 标注说明 fn 接收 int 并返回 int，lambda x: x + 1 使结果为 3。传入不接受一个整数的函数会在调用时暴露错误。"],
    "D05-list-tuple": ["append('c') 直接修改原 list，所以 print 输出 ['a', 'b', 'c']。把 append 换成给 tuple 的位置赋值会触发 TypeError，因为 tuple 不可变。", "point 是固定的 tuple，point[0] 和 point[1] 分别输出 3、4。访问 point[2] 会得到 IndexError，位置边界要先确认长度。"],
    "D05-dict-set": ["set 字面量自动去掉重复的 python，add('cli') 再加入一个元素，sorted 后输出稳定的四个标签。set 没有索引，不能用 tags[0] 取值。", "task['done'] = True 用键更新 dict 的值，print 输出 done 为 True 的字典。访问不存在的键会得到 KeyError，需决定是否使用 get。"],
    "D05-mutability": ["alias = items 只建立第二个引用，alias.append('b') 通过同一个 list 修改 items，所以 print(items) 输出 ['a', 'b']。本例没有复制；若希望原列表不变，必须使用 copy 或其他明确的复制策略。", "items.copy() 创建新的外层 list，copy_items.append('b') 只改变副本，所以 print 输出 ['a'] ['a', 'b']。嵌套 list 仍可能共享内部对象，这是浅复制的边界。"],
    "D05-unpacking": ["{**left, 'b': 2} 把 left 的键值展开到新字典，再加入 b，所以输出包含 a=1、b=2。若右侧出现同名键，后写入的值会覆盖前值。", "first 和 last 接收首尾元素，*middle 收集中间的 2、3，所以输出 1 [2, 3] 4。列表少于两个元素时无法同时绑定首尾，会抛 ValueError。"],
    "D05-traversal": ["scores.items() 每轮提供 name 和 score 两个值，所以输出安 90、博 80。把 items 改成普通字典迭代只会得到键，解包数量就不再匹配。", "每个 row 都用 row['title'] 读取标题，因此输出 A、B。任一字典缺 title 会抛 KeyError，这是外部数据必须处理的边界。"],
    "D05-comprehensions": ["字典推导式把 py、test 分别映射到长度 2、4，所以输出 {'py': 2, 'test': 4}。输入出现重复词时，重复键只保留最后一次值。", "列表推导式先过滤偶数再乘 10，values 得到 [20, 40]。如果没有偶数，结果是空列表而不是包含 None 的列表。"],
    "D05-iterators-generators": ["numbers() 返回 generator，第一次和第二次 next 分别恢复到两个 yield，因此输出 1 2。第三次 next 会抛 StopIteration，说明迭代器已经耗尽。", "生成器表达式按需产生 0、1、4，list(squares) 才把它们收集成列表。再次消费同一个 generator 会得到空列表，因为它没有自动重置。"],
    "D06-exception-types": ["int('x') 的值格式不适合转换，except ValueError 输出异常类名 ValueError。把异常改成 {}['x'] 会得到 KeyError，异常类型应跟着失败操作判断。", "访问不存在的字典键进入 except KeyError，输出缺少键。访问存在键时不会进入处理分支，未知异常也不应被这个 except 吞掉。"],
    "D06-try-except": ["int('x') 抛 ValueError，except 把 error 插入 f-string，输出包含输入无效和 Python 的原因文本。传入对象类型不对时可能是 TypeError，不应假定所有失败都是 ValueError。", "int('42') 成功，所以 except 不执行，value 保留整数 42 并被 print 输出。若改成 int('x')，才会走 value = 0 的恢复分支；默认值的语义要写清。"],
    "D06-else-finally": ["int('4') 成功，else 输出成功 4，finally 无条件输出清理。把输入改成 x 时 else 不执行，但 finally 仍会输出清理。", "raise RuntimeError 立即抛出，finally 仍打印释放资源后异常继续向上传播。不要在 finally 中 return，否则可能覆盖原异常。"],
    "D06-raise": ["int('x') 产生 ValueError，from error 把它链接到新的 RuntimeError；本例没有正常输出，而是保留异常链供上层诊断。若输入合法，转换不会进入这个 raise。", "positive(3) 通过 value > 0 检查并返回 3，所以 print 输出 3。传入 0 或负数会得到消息为必须为正数的 ValueError。"],
    "D06-custom": ["InputError 继承 ValueError，raise 后被精确捕获，type(error).__name__ 输出 InputError。捕获 ValueError 也能接住它，但捕获普通字符串当然不行。", "AgeError 继承 Exception，所以 issubclass(AgeError, Exception) 输出 True。这个例子只检查继承关系，没有创建或抛出 AgeError 实例。"],
    "D06-with": ["path.open('w', encoding='utf-8') 在 with 内写入你好，退出代码块后 read_text 读回同样文本，因此输出是你好。with 负责关闭写入句柄；本例的边界是写入失败时也要执行退出清理。", "StringIO('hello') 进入 with 后 stream.read() 读取 hello，离开代码块时上下文管理器完成关闭。这里没有文件路径或 read_text 调用；若在退出后读取 stream，应观察资源已关闭的边界。"],
    "D07-import": ["import math 后通过 math.ceil(2.1) 访问模块成员，ceil 向上取整并输出 3。若写成 math.missing，会在运行时得到 AttributeError。", "from pathlib import Path as P 直接把 Path 绑定为本地别名，P('a.txt').name 输出 a.txt。as 只改变名字，不会改变 Path 对象的行为。"],
    "D07-package": ["json.loads 把 JSON 文本变成 dict，data['ok'] 读取布尔字段并输出 True。JSON 语法错误会抛 JSONDecodeError，不能当普通字典继续访问。", "Path('taskproj').name 从路径对象读取最后一段并输出 taskproj。这里展示的是可导入的模块成员；包目录不存在时，真实导入会失败而不会自动创建目录。"],
    "D07-main": ["直接运行文件时 __name__ 等于 '__main__'，守卫因此调用 main 并输出直接运行。被其他模块导入时守卫为假，main 不会自动执行。", "直接运行 print(__name__) 通常输出 __main__，导入同一文件时则会输出模块名。这个例子只观察绑定值，不包含入口函数调用。"],
    "D07-stdlib": ["date(2025, 1, 2).isoformat() 把日期格式化成稳定的 2025-01-02。构造非法月份会得到 ValueError，标准库不会悄悄修正日期。", "Path('a.txt').suffix 读取文件名最后的扩展名并输出 .txt。没有扩展名时 suffix 是空字符串，这是路径元数据的边界。"],
    "D07-class-instance": ["Task('学习') 构造实例，__init__ 把 title 保存到 self，task.label() 因而输出学习。另一个 Task 实例会有自己的 title 属性。", "Counter 的 __init__ 把 value 设为 0，inc 方法通过 self.value += 1 后使 print 输出 1。若忘记调用 inc，value 仍是 0。"],
    "D07-inheritance": ["Child 没有自己的 __init__，所以 Child('小林') 继承 Base 的初始化并输出 name 小林。若父类没有兼容的初始化签名，构造会抛 TypeError。", "Dog 重写 speak，并用 super().speak() 得到 ... 后拼接汪，输出 ...汪。去掉 super 调用则不会包含父类文本，重写契约会改变。"],
    "D07-dataclass": ["@dataclass 根据 Point 的 x/y 标注生成初始化方法和 repr，因此 Point(1, 2) 输出 Point(x=1, y=2)。本例只展示不可变默认字段的普通数据对象；传入缺少坐标会在构造时失败。", "field(default_factory=list) 为每个 Bag 实例单独创建 items，修改一个 Bag 后另一个仍为空。这里的关键边界是不能写 items=[] 共享同一个 list；dataclass 标注本身也不会自动做类型校验。"],
}


# Full per-example explanations.  The older topic notes above are retained for
# compatibility with the source table, but generated lessons use this exact
# code-indexed contract so one example can never borrow the other example's
# explanation.
CORE_EXAMPLE_EXPLANATIONS: dict[str, list[str]] = {
    "D02-execution": [
        "if True 的缩进行在条件成立时执行，所以先打印第一句，再打印缩进块。把唯一的块内语句完全顶格会在程序启动阶段得到 IndentationError。",
        "# 行不会执行，value = 2 先建立绑定，最后一行 print 才能输出 2。若删掉赋值而保留 print(value)，边界结果是 NameError。",
    ],
    "D02-names": [
        "value = 7 先绑定整数，type(value).__name__ 输出 int，isinstance 再输出它属于 int。把右侧改成未定义名字会在赋值时得到 NameError。",
        "value = '七' 重新绑定同一个名字，type(value).__name__ 因而输出 str。这个例子没有做数值转换；空字符串仍是 str，只是内容为空。",
    ],
    "D02-numbers": [
        "7 // 2 得到整数商 3，7 % 2 得到余数 1，所以输出是 3 1。除数改成 0 时会触发 ZeroDivisionError，应先定义输入边界。",
        "3 < 5 的结果是 True，而 0.1 + 0.2 == 0.3 常为 False，分别展示比较和浮点精度边界。改用整数 1 + 2 == 3 时结果会是 True。",
    ],
    "D02-bool-none": [
        "循环分别打印 value is None 和 bool(value)，所以能看到 None、0、空文本、空列表与非空列表的差异。空容器是假值但不是 None，这是本例的边界。",
        "name = '' 的真值是 False，not name 因而进入 if 并输出需要输入。把 name 改成非空文本时不会输出；None 与空字符串要按契约区分。",
    ],
    "D02-strings": [
        "text[0] 读取第一个字符 P，text[1:4] 取位置 1、2、3，所以输出是 P 和 yth。切片右端不包含 4；若索引超出长度会抛 IndexError。",
        "text + '和狗' 创建新字符串，第二次 print 同时显示原 text 和 new_text，因此输出是猫 猫和狗。空字符串没有可读取的索引，应先检查长度。",
    ],
    "D02-string-methods": [
        "raw.strip() 去掉两端空白，split(',') 得到 a、b，join 用竖线重新连接，所以输出 a|b。没有逗号的文本会得到单元素列表，这是本例的边界。",
        "name 和 count 被花括号中的表达式读取，f-string 因而输出小林 有 3 个任务。把 count 改成字符串仍能格式化，但计算前要明确类型。",
    ],
    "D03-if": [
        "score = 89 先跳过 >=90，再命中 >=60，level 因而是 B。把分数改成 90 会命中 A，改成 59 会进入 else，这是分支边界。",
        "条件表达式先检查 age >= 18，age 为 18 时输出成人。age 改成 17 会选择未成年；这条语句只适合二选一。",
    ],
    "D03-match": [
        "command = 'list' 命中第一个字面量 case，输出查看；'add' 会输出新增，其他值走 case _ 的未知。case _ 是兜底，不会把未知值改造成已知命令。",
        "point = (0, 4) 匹配 case (0, y)，模式把第二个位置绑定到 y 并输出 4。point 改成 (1, 4) 时这个 case 不匹配，需要其他分支处理。",
    ],
    "D03-for": [
        "range(1, 4) 的终点 4 不包含，所以循环依次输出 1、2、3。把 stop 改成 1 时循环为空，这是 range 的开区间边界。",
        "total 从 0 开始，for 依次把 2、5、3 加入，最终输出 10。列表为空时循环体不执行，total 仍为 0。",
    ],
    "D03-while": [
        "remaining 每轮输出当前值再减一，依次输出 3、2、1；变成 0 后条件为假而结束。初始值为 0 时不会进入循环。",
        "answer 初始为空，while 条件成立后把它改为 yes，下一轮停止并输出继续。若循环体不更新 answer，就会无限循环。",
    ],
    "D03-break-continue": [
        "number == 2 时 continue 跳过 print，number == 5 时 break 结束循环，因此输出 0、1、3、4。若把 break 条件改成 4，4 也不会被打印。",
        "遍历 3、8、4 时第一次 item > 5 的 8 被打印，随后 break 停止搜索。把列表改成全不超过 5 的值时不会输出，调用者要定义未找到结果。",
    ],
    "D03-enumerate-zip": [
        "names 配合 enumerate(start=1) 会输出 1 安、2 博，序号只是展示值不会修改列表。把 start 改成 0 会输出 0、1，这是编号边界。",
        "zip 把安与 90、博与 80 按位置配对，所以两轮分别输出姓名和分数。两组列表长度不同时，zip 会在较短的一组结束时停止。",
    ],
    "D03-comprehension": [
        "列表推导式逐个取 range(4) 的 n 并计算 n*n，输出 [0, 1, 4, 9]。range 为空时结果是空列表，不会执行表达式。",
        "字典推导式只保留偶数 n，并把 n 映射到 n*n，所以输出 {0: 0, 2: 4, 4: 16}。若过滤条件没有命中，结果是空字典。",
    ],
    "D04-def-return": [
        "area(3, 4) 把两个实参绑定到 width、height，return 计算并交回 12。函数体只有调用时执行；传入缺少参数会得到 TypeError。",
        "greet 通过 print 输出你好 林，但没有 return，所以外层 print 又输出 None。函数打印和返回是两种不同的可观察结果。",
    ],
    "D04-default-keyword": [
        "省略 prefix 时使用定义处的默认值你好，输出你好，林。传入空字符串并不是省略参数，因此结果会保留空前缀。",
        "调用 greet('林', prefix='早上好') 用关键字覆盖默认 prefix，输出早上好，林。关键字名拼错会得到 TypeError，而不是静默使用默认值。",
    ],
    "D04-varargs": [
        "total(1, 2, 3) 把三个位置实参收集为 numbers tuple，再由 sum 得到 6。调用 total() 时 tuple 为空，sum 的结果是 0。",
        "show(color='blue', size=2) 把关键字实参收集为 dict 并打印两个键值。调用者换一个关键字名，字典键也会随之变化。",
    ],
    "D04-scope": [
        "read 内的 value='局部' 遮蔽外层 value='外层'，所以 print 输出局部 外层。函数返回后局部绑定消失，外层变量仍保持外层。",
        "show 没有局部 name，于是 LEGB 找到模块级 name='模块' 并输出模块。若在 show 内给 name 赋值，Python 会把它视为局部绑定。",
    ],
    "D04-global-nonlocal": [
        "global counter 让 add_global 内的 counter += 1 重新绑定模块变量，所以 add_global() 后 print(counter) 输出 1。本例没有闭包；删除 global 会报 UnboundLocalError。",
        "make_counter 返回的 step 用 nonlocal value 保存两次调用之间的数值，因此 print(step(), step()) 输出 1 2。本例不修改模块全局变量，重新创建闭包会得到独立 value。",
    ],
    "D04-lambda": [
        "sorted 的 key lambda 读取每个 tuple 的第二项，因此按 1、3 排序并输出 [('b', 1), ('a', 3)]。空列表会直接得到空列表。",
        "double 是接收 number 并返回 number * 2 的匿名函数，double(4) 输出 8。lambda 只能写一个表达式，需要多步语句时应改用 def。",
    ],
    "D04-type-hints": [
        "repeat 的 str/int/str 标注描述参数和返回约定，repeat('好', 2) 由字符串乘法产生好好。标注不会自动把 '2' 转成整数，传入文本要另行校验。",
        "apply 的 Callable 标注说明 fn 接收 int 并返回 int，lambda x: x + 1 使结果为 3。传入不接受一个整数的函数会在调用时暴露错误。",
    ],
    "D05-list-tuple": [
        "append('c') 直接修改原 list，所以 print 输出 ['a', 'b', 'c']。把 append 换成给 tuple 的位置赋值会触发 TypeError，因为 tuple 不可变。",
        "point 是固定的 tuple，point[0] 和 point[1] 分别输出 3、4。访问 point[2] 会得到 IndexError，位置边界要先确认长度。",
    ],
    "D05-dict-set": [
        "task['done'] = True 用键更新 dict 的值，print 输出 done 为 True 的字典。访问不存在的键会得到 KeyError，需决定是否使用 get。",
        "set 字面量自动去掉重复的 python，add('cli') 再加入一个元素，sorted 后输出稳定的标签。set 没有索引，不能用 tags[0] 取值。",
    ],
    "D05-mutability": [
        "alias = items 只建立第二个引用，alias.append('b') 通过同一个 list 修改 items，所以 print(items) 输出 ['a', 'b']。本例没有复制；若希望原列表不变，必须使用 copy。",
        "items.copy() 创建新的外层 list，copy_items.append('b') 只改变副本，所以 print 输出 ['a'] ['a', 'b']。嵌套 list 仍可能共享内部对象，这是浅复制边界。",
    ],
    "D05-unpacking": [
        "first 和 last 接收首尾元素，*middle 收集中间的 2、3，所以输出 1 [2, 3] 4。列表少于两个元素时无法同时绑定首尾，会抛 ValueError。",
        "{**left, 'b': 2} 把 left 的键值展开到新字典，再加入 b，所以输出包含 a=1、b=2。若右侧出现同名键，后写入的值会覆盖前值。",
    ],
    "D05-traversal": [
        "scores.items() 每轮提供 name 和 score 两个值，所以输出安 90、博 80。把 items 改成普通字典迭代只会得到键，解包数量就不再匹配。",
        "每个 row 都用 row['title'] 读取标题，因此输出 A、B。任一字典缺 title 会抛 KeyError，这是外部数据的边界。",
    ],
    "D05-comprehensions": [
        "列表推导式先过滤偶数再乘 10，values 得到 [20, 40]。如果没有偶数，结果是空列表而不是包含 None 的列表。",
        "字典推导式把 py、test 分别映射到长度 2、4，所以输出 {'py': 2, 'test': 4}。输入出现重复词时，重复键只保留最后一次值。",
    ],
    "D05-iterators-generators": [
        "numbers() 返回 generator，第一次和第二次 next 分别恢复到两个 yield，因此输出 1 2。第三次 next 会抛 StopIteration，说明迭代器已经耗尽。",
        "生成器表达式按需产生 0、1、4，list(squares) 才把它们收集成列表。再次消费同一个 generator 会得到空列表，因为它没有自动重置。",
    ],
    "D06-exception-types": [
        "int('x') 的值格式不适合转换，except ValueError 输出异常类名 ValueError。把异常改成 {}['x'] 会得到 KeyError，异常类型应跟着失败操作判断。",
        "访问不存在的字典键进入 except KeyError，输出缺少键。访问存在键时不会进入处理分支，未知异常也不应被这个 except 吞掉。",
    ],
    "D06-try-except": [
        "int('42') 成功，所以 except 不执行，value 保留整数 42 并被 print 输出。若改成 int('x')，才会走 value = 0 的恢复分支。",
        "int('x') 抛 ValueError，except 把 error 插入 f-string，输出包含输入无效和 Python 的原因文本。传入对象类型不对时可能是 TypeError，不应假定所有失败都是 ValueError。",
    ],
    "D06-else-finally": [
        "int('4') 成功，else 输出成功 4，finally 无条件输出清理。把输入改成 x 时 else 不执行，但 finally 仍会输出清理。",
        "raise RuntimeError 立即抛出，finally 仍打印释放资源后异常继续向上传播。不要在 finally 中 return，否则可能覆盖原异常。",
    ],
    "D06-raise": [
        "positive(3) 通过 value > 0 检查并返回 3，所以 print 输出 3。传入 0 或负数会得到消息为必须为正数的 ValueError。",
        "int('x') 产生 ValueError，from error 把它链接到新的 RuntimeError；本例没有正常输出而是保留异常链供上层诊断。",
    ],
    "D06-custom": [
        "InputError 继承 ValueError，raise 后被精确捕获，type(error).__name__ 输出 InputError。捕获 ValueError 也能接住它，但捕获普通字符串不行。",
        "AgeError 继承 Exception，所以 issubclass(AgeError, Exception) 输出 True。这个例子只检查继承关系，没有创建或抛出 AgeError 实例。",
    ],
    "D06-with": [
        "path.open('w', encoding='utf-8') 在 with 内写入你好，退出代码块后 read_text 读回同样文本，因此输出是你好。with 负责关闭写入句柄；本例用 unlink 清理临时路径。",
        "StringIO('hello') 进入 with 后 stream.read() 读取 hello，离开代码块时上下文管理器完成关闭。这里没有文件路径；退出后再次读取应观察资源已关闭。",
    ],
    "D07-import": [
        "import math 后通过 math.ceil(2.1) 访问模块成员，ceil 向上取整并输出 3。若写成 math.missing，会在运行时得到 AttributeError。",
        "from pathlib import Path as P 直接把 Path 绑定为本地别名，P('a.txt').name 输出 a.txt。as 只改变名字，不会改变 Path 对象的行为。",
    ],
    "D07-package": [
        "Path('taskproj').name 从路径对象读取最后一段并输出 taskproj。这里是一个可复用模块成员的最小调用；真实包目录不存在时导入会失败。",
        "json.loads 把 JSON 文本变成 dict，data['ok'] 读取布尔字段并输出 True。JSON 语法错误会抛 JSONDecodeError，不能继续访问字段。",
    ],
    "D07-main": [
        "def main 定义入口，直接运行文件时 __name__ 等于 '__main__'，守卫因此调用 main 并输出直接运行。被导入时守卫为假，main 不会自动执行。",
        "直接运行 print(__name__) 通常输出 __main__，导入同一文件时则输出模块名。这个例子只观察绑定值，不包含入口函数调用。",
    ],
    "D07-stdlib": [
        "date(2025, 1, 2).isoformat() 把日期格式化成稳定的 2025-01-02。构造非法月份会得到 ValueError，标准库不会悄悄修正日期。",
        "Path('a.txt').suffix 读取文件名最后的扩展名并输出 .txt。没有扩展名时 suffix 是空字符串，这是路径元数据的边界。",
    ],
    "D07-class-instance": [
        "Task('学习') 构造实例，__init__ 把 title 保存到 self，task.label() 因而输出学习。另一个 Task 实例会有自己的 title 属性。",
        "Counter 的 __init__ 把 value 设为 0，inc 方法通过 self.value += 1 后使 print 输出 1。若忘记调用 inc，value 仍是 0。",
    ],
    "D07-inheritance": [
        "Dog 重写 speak，并用 super().speak() 得到 ... 后拼接汪，输出 ...汪。去掉 super 调用则不会包含父类文本，重写契约会改变。",
        "Child 没有自己的 __init__，所以 Child('小林') 继承 Base 的初始化并输出 name 小林。若父类没有兼容的初始化签名，构造会抛 TypeError。",
    ],
    "D07-dataclass": [
        "@dataclass 根据 Point 的 x/y 标注生成初始化方法和 repr，因此 Point(1, 2) 输出 Point(x=1, y=2)。传入缺少坐标会在构造时失败。",
        "field(default_factory=list) 为每个 Bag 实例单独创建 items，修改一个 Bag 后另一个仍为空。不能写 items=[] 共享同一个 list；标注本身也不会自动校验类型。",
    ],
}


def _dev_detail(
    explanation: list[str],
    bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, str]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    """Normalize hand-written common-development/project lesson data."""
    return _detail(explanation, bridge, errors, goal, starter, steps, check, inputs, instructions, expected)


# D08-D17 use explicit content records as well.  The three explanation paragraphs,
# error examples and practice inputs below are intentionally about the concrete API
# being taught; they are not generated from a section title.
DEV_TEACHING: dict[str, dict[str, Any]] = {
    "D08-pathlib": _dev_detail(
        [
            "Path 是表示路径的对象，不是带分隔符的普通字符串。`Path('data') / 'report.json'` 会按当前平台组合子路径，`.name`、`.suffix` 和 `.parent` 则提供结构化访问。",
            "Path.glob 会返回匹配的 Path 迭代结果，过滤时可以检查 `is_file()` 和后缀。相对路径依赖当前工作目录，所以库函数最好接收 root 参数，不要偷偷以 cwd 为基准。",
            "文件系统输入可能不存在、指向目录或越过项目根。先用 exists/is_file 判断，再用 relative_to 检查输出是否仍在允许目录内；测试应使用 tmp_path，而不是用户真实目录。",
        ],
        "JavaScript 的 path.join/resolve 返回字符串，Python pathlib 返回可继续操作的 Path 对象；不要把 `Path / name` 写成字符串加号，也不要假定斜杠在 Windows 上固定存在。",
        [("用字符串拼路径", "测试在另一平台出现路径分隔符或重复目录", "字符串连接没有路径语义", "用 Path 和 / 组合，并在边界转成 Path", "root = 'data' + '/' + 'a.txt'"), ("未检查 glob 结果类型", "把目录当文件 read_text 报 IsADirectoryError", "glob 同时可能匹配文件和目录", "过滤 `path.is_file()` 后再读取", "for path in Path('.').glob('*'):\n    print(path.read_text())")],
        "用 Path 组合路径、筛选文件并返回稳定的相对路径列表。",
        "from pathlib import Path\n\ndef list_json(root):\n    # 返回 root 下的 JSON 文件名\n    pass\n",
        [("建立 root", "把 root 转成 Path 并 glob('*.json')", "只找到 JSON 文件"), ("处理空目录", "传入空临时目录", "返回 []，不依赖当前工作目录")],
        "在临时目录创建一个 JSON、一个 TXT 和一个子目录；运行 list_json，确认只返回文件且排序稳定。",
        [("组合", "from pathlib import Path\nprint((Path('data') / 'a.txt').suffix)", ".txt"), ("筛选", "paths = [Path('a.json'), Path('a.txt')]\nprint([p.name for p in paths if p.suffix == '.json'])", "['a.json']")],
        "定义 list_json(root)，使用 Path.glob 和 is_file 返回按 name 排序的 JSON 文件名；不存在 root 时抛 FileNotFoundError。",
        "临时目录中只返回 JSON 文件名；子目录被排除；不存在根目录不会静默改用 cwd。",
    ),
    "D08-utf8": _dev_detail(
        [
            "文本文件是字节序列，encoding 决定字节如何还原成字符。UTF-8 能表示中文和常见 Unicode，但只有在读写两端都明确使用同一编码时，内容才可稳定往返。",
            "Path.read_text/write_text 是方便接口，但默认编码可能受平台设置影响。把 `encoding='utf-8'` 写进边界函数，能让调用者知道协议，也让测试不依赖开发机语言环境。",
            "编码错误与文件不存在是两种失败：前者说明字节解释不匹配，后者说明路径或生命周期有问题。测试应包含中文、换行、空文件和非法字节的处理策略。",
        ],
        "JavaScript 字符串通常以 UTF-16 代码单元表示，Python str 是 Unicode 文本，读写文件时必须显式选编码；不要把 JS 的字符串长度直觉直接套到 Unicode 字素边界。",
        [("依赖默认编码", "中文在不同机器乱码或抛 UnicodeDecodeError", "open/read_text 使用了系统默认值", "读写两端都声明 encoding='utf-8'", "Path('note.txt').write_text('你好')"), ("把 bytes 当 str", "调用 strip 或拼接时报 TypeError", "二进制读取返回 bytes，不能直接与 str 合并", "按协议 decode('utf-8') 或全程使用文本模式", "data = Path('note.txt').read_bytes()\nprint(data + '尾部')")],
        "实现一个显式 UTF-8 的文本往返函数，保留中文、换行和空文本。",
        "from pathlib import Path\n\ndef round_trip(path, text):\n    # 用 UTF-8 写入后读回\n    pass\n",
        [("写入中文", "使用 write_text(..., encoding='utf-8')", "读回内容与输入完全相同"), ("检查空文本", "传入 ''", "文件存在且返回空字符串")],
        "在临时目录分别写入中文、换行和空文本；用 read_bytes 观察 UTF-8 字节只是辅助，不要把 bytes 当作文本结果。",
        [("写读", "from pathlib import Path\np = Path('note.txt')\np.write_text('你好', encoding='utf-8')\nprint(p.read_text(encoding='utf-8'))", "你好"), ("空文件", "p.write_text('', encoding='utf-8')\nprint(repr(p.read_text(encoding='utf-8')))", "''")],
        "定义 round_trip(path, text)，用 Path 显式 UTF-8 写入并读回；不使用系统默认编码，返回值必须与 text 完全相同。",
        "中文、换行、空文本都能无损往返；函数没有把 bytes 或默认编码暴露给调用者。",
    ),
    "D08-json-read": _dev_detail(
        [
            "JSON 是文本格式，json.loads 接收字符串并返回 Python 对象：对象变 dict、数组变 list、true/null 分别变 True/None。解析成功不代表业务结构正确。",
            "读取外部 JSON 后应先判断顶层类型，再检查必需字段和字段类型。直接写 `data['name']` 会把结构错误留到更远处，使用小函数做契约校验能让错误靠近输入边界。",
            "JSONDecodeError 表示文本语法不合法，KeyError/TypeError 则可能表示结构不符合业务契约。练习应分开处理这几类错误，不能用一个空 dict 把坏数据伪装成成功。",
        ],
        "JavaScript JSON.parse 也只负责语法解析，不能保证字段存在；Python loads 返回 dict/list 等 Python 对象，不能继续使用 JS 的 undefined 检查方式。",
        [("解析后直接取字段", "合法 JSON 数组也会因字符串键报 TypeError", "JSON 顶层类型不一定是 object/dict", "先 isinstance(data, dict)，再检查字段", "data = json.loads('[]')\nprint(data['title'])"), ("把解析错误吞掉", "无效 JSON 变成空对象，后续误写报告", "except JSONDecodeError 返回默认值掩盖输入失败", "向调用者返回明确解析错误或结构错误", "try:\n    data = json.loads('{bad}')\nexcept json.JSONDecodeError:\n    data = {}")],
        "从 JSON 文本读取一个有 title 字段的 dict，并区分语法错误与结构错误。",
        "import json\n\ndef read_task(text):\n    # 解析并检查顶层结构\n    pass\n",
        [("解析对象", "使用 json.loads", "得到 dict"), ("检查字段", "验证 title 是非空字符串", "坏结构得到明确 ValueError")],
        "测试有效对象、有效数组、无效 JSON 和缺 title 四种输入；分别记录返回值或异常类型。",
        [("有效", "import json\ndata = json.loads('{\"title\": \"买书\"}')\nprint(data['title'])", "买书"), ("类型", "import json\ndata = json.loads('[1, 2]')\nprint(type(data).__name__)", "list")],
        "定义 read_task(text)，解析 JSON 后要求顶层 dict 且 title 为非空字符串；JSONDecodeError 不得静默转为空 dict。",
        "有效文本返回 title；无效语法和错误结构分别产生可识别失败，函数不凭空补齐字段。",
    ),
    "D08-json-report": _dev_detail(
        [
            "报告函数通常经历读取记录、聚合统计、构造结果和序列化四步。先明确输入记录的字段，再决定缺失字段是拒绝、跳过还是使用默认值，不能在 dump 时才发现数据形状错。",
            "json.dump 的 ensure_ascii、indent 和 sort_keys 影响文件是否易读、是否稳定。`sort_keys=True` 便于比较测试，ensure_ascii=False 能保留中文，但输出格式仍应由项目契约决定。",
            "写报告要使用临时文件或明确覆盖策略，避免在统计失败时留下半份结果。验证时同时读回 JSON、检查统计值和检查中文显示，确保序列化与业务结果一致。",
        ],
        "JavaScript JSON.stringify 的 replacer/space 与 Python dumps/dump 参数有相似作用；Python 的 ensure_ascii 默认会转义非 ASCII，不能假设输出一定直接显示中文。",
        [("统计前不校验字段", "缺 title 记录触发 KeyError 或错误计数", "聚合逻辑把外部记录当可信对象", "先校验/过滤并记录边界策略", "count = sum(1 for row in rows if row['done'])"), ("直接写正式文件", "中途异常留下截断 JSON", "写入目标文件不是原子过程", "先写临时文件，成功后替换，或明确测试目录", "with open(path, 'w', encoding='utf-8') as f:\n    json.dump(build_report(rows), f)")],
        "根据任务记录生成稳定 JSON 报告，包含总数、完成数和未完成数。",
        "import json\n\ndef write_report(rows, path):\n    # 统计后以稳定格式写出\n    pass\n",
        [("计算统计", "先构造 total/done/pending", "数字与输入记录一致"), ("写回读回", "dump 后再次 load", "JSON 可解析且中文不被错误改写")],
        "使用两条任务记录、空列表和缺 done 字段记录测试统计策略；检查文件不是空半成品。",
        [("稳定输出", "import json\nprint(json.dumps({'done': 1}, ensure_ascii=False, sort_keys=True))", "{\"done\": 1}"), ("缩进", "print(json.dumps({'title': '买书'}, ensure_ascii=False, indent=2))", "包含 title 与缩进的 JSON")],
        "定义 write_report(rows, path)，统计 total/done/pending，使用 ensure_ascii=False、indent=2、sort_keys=True 写 UTF-8 JSON，并可被再次 load。",
        "两条记录得到正确计数；空输入得到全零报告；输出 JSON 可读、稳定、含中文且不会在失败时写入伪报告。",
    ),
    "D09-parser": _dev_detail(
        [
            "argparse 把 argv 中的字符串转换成 Namespace，add_argument 描述选项名、类型、默认值和是否必需。解析器负责命令行语法，不应把业务数据库操作塞进参数声明。",
            "`type=int` 会在解析边界完成转换，`--verbose` 这类开关通常使用 action='store_true'。help 文本不是装饰，它决定用户能否知道默认值、输入格式和示例命令。",
            "命令行输入有缺失参数、未知选项和非法类型等失败。用 parse_args([...]) 做离线测试，确认成功 Namespace 以及失败时 stderr/退出码，而不是只测试手工 happy path。",
        ],
        "JavaScript 常用 minimist/commander 等库，Python argparse 自带帮助、类型转换和错误退出；不要把 `process.argv` 的字符串数组处理方式原样搬到 Namespace。",
        [("忘记 type=int", "业务函数收到 '3'，加法变成字符串拼接", "argparse 默认保留字符串", "在 add_argument 写 type=int 并测试 Namespace 类型", "parser.add_argument('--limit')\nargs = parser.parse_args(['--limit','3'])\nprint(args.limit + 1)"), ("把可选项写成必需", "用户不带 --verbose 也被拒绝", "required=True 与开关语义不匹配", "布尔开关使用 store_true 并提供默认 False", "parser.add_argument('--verbose', required=True, action='store_true')")],
        "定义 parse_args(argv)，把 --limit 转成 int、把 --verbose 转成 bool，并保留清晰 help。",
        "import argparse\n\ndef parse_args(argv):\n    # 建立 parser 并返回 Namespace\n    pass\n",
        [("声明参数", "加入 --limit type=int", "parse_args(['--limit','3']).limit == 3"), ("开关", "加入 --verbose", "不传为 False，传入为 True")],
        "用列表参数离线测试正常、缺值、非法数字和 --help；不要读取真实 sys.argv 让单测不可控。",
        [("解析", "import argparse\np = argparse.ArgumentParser()\np.add_argument('--limit', type=int, default=10)\nprint(p.parse_args(['--limit', '3']).limit)", "3"), ("开关", "p.add_argument('--verbose', action='store_true')\nprint(p.parse_args([]).verbose)", "False")],
        "定义 parse_args(argv)，支持 `--limit INTEGER` 默认 10 和 `--verbose` 开关；非法 limit 由 argparse 产生非零错误，不在业务层静默转换。",
        "正常 argv 得到正确 Namespace 类型；缺失/非法参数由 parser 明确拒绝，默认值可从 help 看见。",
    ),
    "D09-subcommands": _dev_detail(
        [
            "子命令把一个 CLI 的动作分成互不混淆的语法树，例如 `task add` 与 `task list`。add_subparsers 产生命令选择器，每个子解析器只声明自己需要的参数。",
            "set_defaults(func=...) 可以把解析结果直接分派到处理函数，但处理函数应接收 Namespace 并返回退出结果，不要在解析阶段执行数据库副作用。共享参数可以放在父解析器或显式复用函数中。",
            "无子命令、未知子命令和子命令缺参数都要有清晰反馈。测试用 argv 列表覆盖每个分支，检查 dispatch 选择正确函数以及未知命令不会落到默认的错误动作。",
        ],
        "JavaScript commander 的 command/action 与 argparse subparsers 目的相似，但 Python dispatch 常通过 Namespace 属性完成；不要把子命令字符串直接当函数名 eval。",
        [("子解析器没有 required", "空命令默默执行根处理函数", "未选择 subcommand 时 Namespace 没有动作", "设置 required=True 或显式检查 command", "sub = parser.add_subparsers(dest='command')\nargs = parser.parse_args([])"), ("共享参数重复不一致", "add/list 对 --db 的默认值不同", "每个子解析器手写了不同配置", "抽出 add_common_arguments 并测试两命令一致", "add.add_argument('--db', default='a.db')\nlist_p.add_argument('--db', default='b.db')")],
        "能建立 add/list 两个子命令，并将 Namespace 分派到不同处理函数。",
        "import argparse\n\ndef build_parser():\n    # 返回含 add/list 的 parser\n    pass\n",
        [("建立子命令", "调用 add_subparsers(dest='command')", "parse_args(['list']).command == 'list'"), ("分派", "为 add/list 设置不同 func", "dispatch 调用与命令对应的函数")],
        "测试 list、add、空命令、未知命令；记录每个命令得到的 Namespace 和退出行为。",
        [("选择", "p = argparse.ArgumentParser()\nsub = p.add_subparsers(dest='command')\nsub.add_parser('list')\nprint(p.parse_args(['list']).command)", "list"), ("参数", "add = sub.add_parser('add')\nadd.add_argument('title')\nprint(p.parse_args(['add','买书']).title)", "买书")],
        "定义 build_parser()，支持 list 和 add TITLE，并将 `args.func` 绑定到可测试处理函数；空/未知命令必须返回 parser 错误。",
        "list/add 分派正确；TITLE 作为字符串保留；空或未知命令有非零错误而非调用错误处理器。",
    ),
    "D09-errors": _dev_detail(
        [
            "命令行错误是用户输入协议的一部分，应写到 stderr 并返回非零退出码；成功输出写 stdout。argparse 的 parser.error 会统一格式化 usage、错误原因并以 SystemExit(2) 结束。",
            "业务错误和参数错误可以有不同退出码，但必须稳定。处理函数不要 catch SystemExit 后返回 0，否则 shell、测试和 CI 会误以为命令成功。",
            "测试错误时应捕获 SystemExit，检查 code、stderr 和没有污染 stdout。边界包括缺少位置参数、未知选项、非法枚举值以及目标不存在。",
        ],
        "Node CLI 通常手动写 console.error 和 process.exitCode；argparse 已经提供 stderr/退出码约定，但 Python 代码仍要避免把错误打印到 stdout。",
        [("错误打印到 stdout", "脚本管道把错误当成正常数据", "使用 print 默认写 stdout", "用 parser.error 或 print(..., file=sys.stderr)", "print('invalid input')\nraise SystemExit(2)"), ("错误后返回 0", "CI 绿色但命令实际失败", "except 后没有设置非零退出码", "让异常/SystemExit 传播或明确返回非零", "try:\n    parse()\nexcept ValueError:\n    print('bad')\n    return 0")],
        "让非法参数得到可预测 stderr 和非零退出码，成功路径保持干净 stdout。",
        "import argparse\n\ndef parse_or_error(argv):\n    # 参数失败交给 parser.error\n    pass\n",
        [("缺参数", "调用空 argv", "得到 SystemExit code=2 和 stderr"), ("成功", "调用合法 argv", "返回 Namespace 且不打印错误")],
        "捕获 parse_args 对缺参数、未知选项和非法整数的 SystemExit；分别检查 code、stderr 和 stdout。",
        [("parser error", "import argparse\np = argparse.ArgumentParser()\np.add_argument('title')\ntry:\n    p.parse_args([])\nexcept SystemExit as e:\n    print(e.code)", "2"), ("成功", "print(p.parse_args(['买书']).title)", "买书")],
        "定义 parse_or_error(argv)，缺少 TITLE/非法 --limit 时由 argparse 产生 code=2；成功路径返回 Namespace，不捕获成 0。",
        "错误路径 code 非零且信息在 stderr；成功路径得到结构化参数，stdout 不混入 usage/error 文本。",
    ),
    "D09-entry": _dev_detail(
        [
            "可执行入口是从 shell 到 Python 函数的边界：读取 argv、解析参数、调用 main、把返回值映射成退出码。把这些步骤放在 main() 中可以让导入测试不依赖真实命令行。",
            "`if __name__ == '__main__': raise SystemExit(main())` 让直接运行和导入行为分离。subprocess 测试能观察真实 stdout/stderr/returncode，比只调用内部函数更接近用户体验。",
            "入口测试要固定 cwd、环境和 argv，避免相对路径偶然成功。成功、未知命令和异常都要定义输出和退出码，尤其不能让 traceback 代替用户可读错误。",
        ],
        "Node 的 `require.main === module` 解决类似入口分离；Python 用 __name__ 守卫和 SystemExit 承载返回码，不能把 Node 的 process.argv[2] 索引规则直接复制。",
        [("导入时执行 CLI", "pytest 收集模块时就解析测试进程 argv", "顶层直接调用 main", "把调用放在 __name__ 守卫", "main()\n# module import 时立刻执行"), ("只测函数不测命令", "shell 下输出/退出码与单测不同", "入口包装丢失了真实 stderr/cwd", "加入 subprocess 回归，固定命令和 cwd", "assert main(['--bad']) is False")],
        "构造可直接运行且可被 import 的 CLI 入口，并用子进程锁定输出与退出码。",
        "import sys\n\ndef main(argv=None):\n    # 解析 argv 并返回整数退出码\n    pass\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
        [("函数入口", "main(argv) 返回 0/非零", "调用不读取外部 sys.argv"), ("子进程", "直接运行合法命令", "returncode 和 stdout 符合契约")],
        "用 subprocess 运行正常、错误和 help 命令；再 import 模块确认导入没有执行命令行。",
        [("守卫", "def main():\n    print('ok')\n    return 0\nif __name__ == '__main__':\n    raise SystemExit(main())", "直接运行输出 ok，退出 0"), ("argv", "def main(argv=None):\n    return 0 if (argv or []) == [] else 2\nprint(main([]))", "0")],
        "定义 main(argv=None) 和 __name__ 守卫；成功返回 0、参数错误返回 2，并用 subprocess 检查真正入口。",
        "直接运行和导入边界清晰；成功/失败 returncode 正确，导入不解析 pytest 的 argv。",
    ),
    "D10-env": _dev_detail(
        [
            "环境变量是进程启动时提供的字符串配置，`os.environ.get` 可以读取并给出默认值。它适合数据库路径、端口等部署差异，但不应把必需秘密写入源码或日志。",
            "环境变量不存在、存在但为空、存在但格式错误是三个不同状态。读取边界应明确优先级和是否允许空值，再把字符串转换成目标类型。",
            "测试配置时用 monkeypatch 或临时环境逐例恢复，避免一个测试污染下一个测试。不要把当前开发机环境当课程输入；函数最好接受 env 映射以便确定性验证。",
        ],
        "JavaScript process.env 同样全部是字符串；Python os.environ.get 的默认值也不会自动转换 int/bool。两者都不应把环境变量直接打印到日志，尤其是可能含秘密的值。",
        [("把非空字符串当 bool", "TASK_DEBUG='false' 仍被判断为 True", "bool('false') 为 True", "按 lower() 显式解析 true/false/1/0", "debug = bool(os.environ.get('TASK_DEBUG'))"), ("读取后泄露秘密", "日志/错误响应包含 token", "调试打印了完整环境变量", "只记录是否配置和安全字段，绝不输出值", "print(dict(os.environ))")],
        "实现读取环境变量并提供不泄密、可测试的默认策略。",
        "import os\n\ndef get_db_path(env=None):\n    # 从 env 或 os.environ 读取路径\n    pass\n",
        [("默认", "传入不含 TASKPROJ_DB 的映射", "返回 taskproj.db"), ("覆盖", "传入自定义路径", "返回自定义 Path/字符串且不打印环境")],
        "使用显式 env 映射测试缺失、空值和覆盖；检查函数不读取/输出无关 Key。",
        [("读取", "import os\nos.environ['APP_MODE'] = 'test'\nprint(os.environ.get('APP_MODE'))", "test"), ("默认", "print(os.environ.get('MISSING', 'default'))", "default")],
        "定义 get_setting(name, default, env=None)，优先读取 env 中非空值，否则返回 default；不得打印或持久化环境变量内容。",
        "覆盖值正确返回，缺失/空值使用明确默认；实现不输出 Key/环境全集。",
    ),
    "D10-convert": _dev_detail(
        [
            "环境变量和命令行参数进入 Python 时都是字符串，转换函数负责把它们变成 int、bool 等业务类型。转换失败不是默认成功，而是需要明确错误或 fallback 策略。",
            "布尔解析不能使用 bool(text)：'false'、'0' 和 'no' 都是非空字符串。应规范化大小写并列出允许集合，未知文本抛 ValueError，让配置错误尽早暴露。",
            "类型转换函数要保持纯净：给定同一字符串得到同一结果，不偷偷读取全局环境。测试覆盖大小写、空白、非法文本、负数和边界整数。",
        ],
        "JavaScript Number('') 会得到 0、Boolean('false') 会得到 true，这些隐式转换容易掩盖配置错误；Python 也不能依赖 bool(str)，应写显式解析表。",
        [("bool('false')", "错误配置被当成开启", "非空字符串真值为 True", "只接受明确 true/false 等文本", "print(bool('false'))"), ("int 失败后吞错", "端口变成默认值，部署问题难发现", "except ValueError 直接返回 0 没有说明原因", "在配置边界抛带字段名的 ValueError", "try:\n    port = int(text)\nexcept ValueError:\n    port = 0")],
        "实现安全的整数和布尔转换，并让非法配置在边界处失败。",
        "def parse_bool(text):\n    # 明确允许 true/false 文本\n    pass\n\ndef parse_port(text):\n    pass\n",
        [("布尔", "测试 TRUE、false、0", "大小写被规范化，0 按规则返回 False"), ("整数", "测试 1、65535、abc", "合法值返回 int，非法值抛 ValueError")],
        "对转换函数运行合法、空白、未知文本和数值边界；错误消息要带字段名或原值类别，不要打印秘密。",
        [("错误", "try:\n    print(int('abc'))\nexcept ValueError:\n    print('bad integer')", "bad integer"), ("布尔", "text = 'false'\nprint(text.strip().lower() in {'true','1','yes'})", "False")],
        "定义 parse_bool(text) 和 parse_port(text)：布尔只接受 true/1/yes 与 false/0/no，端口要求 1–65535，其他值抛 ValueError。",
        "合法文本返回对应类型；未知 bool 和越界端口明确失败，不把错误配置静默变成 0/True。",
    ),
    "D10-dotenv": _dev_detail(
        [
            ".env 是简单的本地键值文本，不是 Python 代码。解析器应逐行处理空行、# 注释、第一次等号、首尾空白和可选引号，绝不能 exec 文件内容。",
            "同名键的覆盖规则必须固定：通常后出现值覆盖前值，或环境变量优先于文件值。解析函数只负责文本到 dict，组合优先级放到 config 层，职责更容易测试。",
            "文件不存在可以按配置层契约返回空映射，但语法错误、缺少键名或不闭合引号应有明确处理。测试使用 tmp_path 创建真实 .env，覆盖中文值和等号出现在值中的情况。",
        ],
        "Node dotenv 库也把文件行解析成 process.env，但 Python 自己实现时不能使用 eval；两者都要防止值中的引号、# 和等号被错误截断。",
        [("用 split('=') 不限次数", "URL/token 中的后续等号被丢掉", "值本身可能含等号", "使用 split('=', 1)", "key, value = line.split('=')"), ("执行 .env", "任意命令被执行或秘密泄露", "把配置当 Python/ shell 脚本解释", "逐行纯文本解析，不调用 eval/exec/subprocess", "exec(Path('.env').read_text())")],
        "写一个不执行内容的 .env 解析器，正确处理注释、空行和带等号的值。",
        "from pathlib import Path\n\ndef load_dotenv(path):\n    # 逐行解析键值\n    pass\n",
        [("解析普通行", "处理 A=1", "得到 {'A':'1'}"), ("保留等号", "处理 URL=https://x?a=1", "值保留后续等号")],
        "用临时 .env 写入注释、空行、A=1、URL=https://x?a=1 和中文值；测试缺失文件按契约返回空 dict。",
        [("普通行", "line = 'A=1'\nkey, value = line.split('=', 1)\nprint(key, value)", "A 1"), ("带等号", "line = 'URL=https://x?a=1'\nprint(line.split('=', 1)[1])", "https://x?a=1")],
        "定义 load_dotenv(path)，忽略空行/注释，按第一次等号拆分并去除首尾空白；缺失文件返回 {}，不执行文件文本。",
        "普通、中文、带等号配置正确解析；缺失文件返回空 dict；任意 .env 内容都不会被执行。",
    ),
    "D10-config": _dev_detail(
        [
            "配置对象把来源、默认值和转换后的类型集中在一个边界，业务代码只接收 Settings，而不在每个函数里重复读取 os.environ。dataclass 适合表达这些稳定字段。",
            "构造配置时要固定优先级，例如显式参数 > 环境变量 > 默认值；每个字段都应在边界转换和校验。把 DATABASE_URL 这样的值保留为 Path/str，避免业务层猜类型。",
            "配置错误应在启动阶段失败，错误消息指出字段和规则但不泄露秘密。测试要传入自定义 env，检查默认、覆盖、类型转换和非法值的行为。",
        ],
        "TypeScript 常用 interface/env schema 描述配置，Python dataclass 同时可生成构造函数和 repr；不要让 repr/日志输出密码等敏感字段，必要时自定义 repr。",
        [("业务函数重复读环境", "测试无法隔离，运行时配置前后不一致", "每个函数各自读取 os.environ", "启动时构造一次 Settings 并传入", "def save():\n    path = os.environ.get('DB')"), ("配置未转换", "SQLite 接口收到字符串端口/布尔值", "Settings 字段仍是原始文本", "在 from_env 边界完成类型转换", "settings.debug = os.environ.get('DEBUG')")],
        "组合环境变量与默认值为可测试的 Settings 对象，并在构造时完成校验。",
        "from dataclasses import dataclass\n\n@dataclass\nclass Settings:\n    db_path: str\n    debug: bool\n",
        [("默认配置", "不传环境构造 Settings", "得到 documented defaults"), ("覆盖配置", "传入 DEBUG=true 和自定义 db_path", "字段类型分别为 bool/str")],
        "构造默认、覆盖、非法端口/布尔三种 Settings；打印安全字段时不要输出 token/password 的值。",
        [("对象", "from dataclasses import dataclass\n@dataclass\nclass Settings:\n    db_path: str = 'taskproj.db'\nprint(Settings())", "Settings(db_path='taskproj.db')"), ("优先级", "env = {'DB_PATH': 'x.db'}\nprint(env.get('DB_PATH', 'taskproj.db'))", "x.db")],
        "定义 Settings.from_env(env)，集中读取 DB_PATH、DEBUG、PORT，完成 bool/int 转换并在非法值时抛 ValueError；业务函数只接收 Settings。",
        "默认和环境覆盖按固定优先级生效；字段类型正确；非法配置在构造阶段失败且不泄露秘密。",
    ),
    "D11-logger": _dev_detail(
        [
            "logging logger 按名称组织记录，level 决定哪些记录被创建，handler 决定记录写向哪里。`logging.getLogger(__name__)` 让模块名称进入日志上下文，但不应每次函数调用都新增 handler。",
            "logger 会向父 logger 传播，root handler 可能再次输出同一条消息。库代码通常不配置全局 handler，应用入口统一配置；若模块自行配置，要控制初始化幂等性。",
            "日志级别不是 print 的替代：DEBUG 记录诊断、INFO 记录正常流程、WARNING/ERROR 记录需要处理的问题。测试应捕获记录内容和 handler 数量，确认重复调用 setup 不重复输出。",
        ],
        "JavaScript console.log 没有 Python logger 的层级/handler 模型；Python 日志应通过 logger/handler/propagate 控制路由，不能把每条记录都直接 print。",
        [("每次调用新增 handler", "同一日志出现两次/三次", "setup 在业务函数中反复 addHandler", "把 setup 做成幂等，先按 marker 检查 handler", "logger.addHandler(logging.StreamHandler())"), ("传播未关闭", "子 logger 与 root 各输出一次", "propagate=True 且两边都有 handler", "统一由 root 或子 logger 处理，明确 propagate", "child.addHandler(h)\nchild.propagate = True")],
        "配置一个可重复调用的模块 logger，产生日志但不重复输出。",
        "import logging\n\ndef get_logger():\n    # 返回配置后的 logger\n    pass\n",
        [("首次配置", "设置 level 和一个 handler", "INFO 记录可见"), ("重复配置", "再次调用 get_logger", "handler 数量不增加")],
        "用 pytest caplog 或临时 stream 调用 setup 两次；检查 logger 名称、级别、记录次数和 propagate。",
        [("取 logger", "import logging\nlogger = logging.getLogger('demo')\nlogger.setLevel(logging.INFO)\nlogger.info('ready')", "记录 ready"), ("级别", "logger.setLevel(logging.WARNING)\nlogger.info('hidden')", "INFO 不输出")],
        "定义 get_logger()，返回同名、幂等配置的 logger；重复调用不增加 handler，且 DEBUG/INFO/WARNING 级别符合说明。",
        "同一 logger setup 两次仍只有约定 handler 数；低于级别的记录被过滤，允许的记录不重复。",
    ),
    "D11-format": _dev_detail(
        [
            "Formatter 把 LogRecord 转成可读文本，常见字段有时间、级别、logger 名和消息。格式应服务于定位问题，不要把秘密、完整请求体或用户隐私无条件写入。",
            "日志消息的参数化写法 `logger.info('loaded %s', name)` 延迟格式化，适合级别过滤并避免不必要的字符串拼接。extra 可以添加结构化上下文，但字段名不能与 LogRecord 保留字段冲突。",
            "稳定日志格式便于测试和 grep，但时间戳会变化，所以断言应聚焦 level/name/message。为异常使用 logger.exception 才能保留 traceback，单纯 str(error) 会丢失调用位置。",
        ],
        "JavaScript 模板字符串会立即拼接文本，Python logging 参数化消息把格式化推迟到真正输出；两者都应先脱敏再记录。",
        [("格式字符串占位符不匹配", "日志格式化时报 TypeError 或字段缺失", "Formatter 的字段名与 LogRecord 不存在", "只使用标准字段或显式 extra", "logging.Formatter('%(request_id)s %(message)s')"), ("用 f-string 记录秘密", "日志保存 token/password", "格式化前没有脱敏且日志范围扩大", "只记录安全摘要/是否配置", "logger.info(f'token={token}')")],
        "配置包含时间、级别、名称和消息的 Formatter，并测试参数化消息和异常记录。",
        "import logging\n\ndef formatter():\n    # 返回稳定 Formatter\n    pass\n",
        [("设置格式", "使用 %(levelname)s/%(name)s/%(message)s", "记录包含关键字段"), ("异常", "在 except 中 logger.exception", "输出 traceback 而非只输出消息")],
        "用自定义 stream 捕获一条 INFO 和一条异常；断言关键字段存在，不断言易变时间文本。",
        [("格式", "import logging\nf = logging.Formatter('%(levelname)s:%(name)s:%(message)s')\nprint(f._fmt)", "格式包含 level/name/message"), ("参数化", "logger = logging.getLogger('demo')\nlogger.info('loaded %s', 'data')", "消息为 loaded data")],
        "定义 build_formatter()，格式包含时间、级别、logger 名和消息；用参数化日志记录名称，并在异常路径使用 logger.exception。",
        "日志格式可定位记录来源；参数化消息正确渲染；异常保留 traceback；敏感值没有进入输出。",
    ),
    "D11-stream": _dev_detail(
        [
            "StreamHandler 把记录写到一个文本流，默认常见是 stderr。handler 自己也有 level，可以让 logger 接收 DEBUG 但控制台只显示 WARNING 以上。",
            "多个 handler 的级别和 logger 级别共同决定输出，先经过 logger 过滤，再经过 handler 过滤。配置控制台时要明确 INFO 是否展示，以及格式化器是否已经附加。",
            "测试应使用 io.StringIO 注入流，不能依赖终端颜色或系统 stderr。执行完要移除/关闭临时 handler，避免污染其他测试和重复输出。",
        ],
        "JavaScript console 输出流由运行时控制，Python 可以把 StreamHandler 指向任意 file-like 对象，便于把日志边界注入测试。",
        [("把 handler level 设错", "DEBUG/INFO 全部消失或错误信息也被过滤", "handler level 高于/低于预期", "分别设置 logger 与 handler 并用三种级别测试", "handler.setLevel(logging.ERROR)\nlogger.info('ready')"), ("测试不清理 handler", "后续测试收到前一个测试的日志", "全局 logger 保留临时 handler", "finally 中 removeHandler/close", "logger.addHandler(stream_handler)\n# 缺少清理")],
        "将 logger 输出到可注入 stream，并验证级别过滤和清理。",
        "import io\nimport logging\n\ndef build_stream_logger():\n    # 返回 logger 与 stream\n    pass\n",
        [("注入流", "使用 io.StringIO 和 StreamHandler", "日志可从 stream.getvalue 读取"), ("级别", "分别记录 INFO/WARNING", "只出现契约允许的级别")],
        "测试 logger 的 INFO、WARNING、ERROR；结束后移除 handler，再次配置不出现历史内容。",
        [("handler", "import io, logging\nstream = io.StringIO()\nhandler = logging.StreamHandler(stream)\nprint(type(handler).__name__)", "StreamHandler"), ("级别", "handler.setLevel(logging.WARNING)\nprint(handler.level == logging.WARNING)", "True")],
        "定义 build_stream_logger()，返回 logger/stream，handler 为 StreamHandler；控制台只输出 WARNING 及以上并且重复 setup 不复制输出。",
        "输出流可断言且级别过滤正确；临时 handler 可清理；相同记录不会因传播重复出现。",
    ),
    "D11-file": _dev_detail(
        [
            "FileHandler 把日志持久化到文件，文件编码必须明确，尤其是中文消息。它本身持有文件资源，测试和应用关闭时要 flush/close，否则最后几条记录可能还没写入磁盘。",
            "文件日志路径属于配置边界，应由调用者传入临时目录或明确目录，不要在 import 时向项目根写 log。按模块设置 handler 时仍要防重复和控制 propagate。",
            "验证文件日志要先记录、刷新/关闭、再用 UTF-8 读取；同时覆盖异常记录和重复初始化。失败时要区分目录不存在、权限错误与日志格式问题。",
        ],
        "JavaScript 文件日志通常由 fs/第三方库管理，Python FileHandler 自带编码和轮转边界，但仍需显式关闭；不能把 console 输出当作文件落盘证据。",
        [("未指定 encoding", "中文日志乱码", "FileHandler 使用平台默认编码", "传入 encoding='utf-8'", "logging.FileHandler(path)"), ("handler 未关闭", "测试读文件缺最后一行或 Windows 无法删除", "文件句柄仍被 handler 持有", "flush 后 removeHandler/close，并在应用生命周期管理", "handler = logging.FileHandler(path)\nlogger.info('done')")],
        "把日志写进临时 UTF-8 文件并正确关闭 handler，验证内容和异常 traceback。",
        "import logging\n\ndef configure_file_logger(path):\n    # 返回 logger 和可关闭 handler\n    pass\n",
        [("写日志", "记录一条中文 INFO", "文件读回包含中文消息"), ("关闭", "移除并关闭 handler 后读取", "文件可完整读取/删除")],
        "在 tmp_path 配置 FileHandler，写正常与异常日志，关闭后读取 UTF-8 文件并确认 setup 两次不重复。",
        [("文件 handler", "import logging\nhandler = logging.FileHandler('demo.log', encoding='utf-8')\nprint(type(handler).__name__)\nhandler.close()", "FileHandler"), ("格式", "print(logging.Formatter('%(levelname)s %(message)s')._fmt)", "包含 level/message")],
        "定义 configure_file_logger(path)，使用 UTF-8 FileHandler 和稳定 Formatter；返回可关闭资源，重复调用不产生重复记录。",
        "文件包含完整中文日志和异常上下文；关闭后可读取/删除；未把秘密或重复记录写入文件。",
    ),
}

def _manual_detail(
    explanation: list[str],
    bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, str]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    return _detail(explanation, bridge, errors, goal, starter, steps, check, inputs, instructions, expected)


# D12-D17 的教学记录继续逐节说明真实 API、失败边界和离线练习；
# 不把 HTTP、FastAPI、SQLite、asyncio 统合成一个标题插值模板。
NONCORE_TEACHING: dict[str, dict[str, Any]] = {}


NONCORE_TEACHING.update({
    "D12-request": _manual_detail(
        [
            "urllib.request.Request 描述 URL、方法和请求头，urlopen 才是发生网络 I/O 的动作。把请求对象先构造出来，测试就能在不联网时检查协议形状。",
            "响应体通常是 bytes，文本协议要显式 decode；读取完还要关闭响应资源。GET 的查询条件通常编码在 URL，而不是偷偷改成请求体。",
            "本练习把 opener 作为参数注入，fake opener 可以记录 Request 并返回固定 bytes。学习重点是请求对象和资源生命周期，不是等待真实服务器。",
        ],
        "JavaScript fetch 返回 Promise<Response>，Python urllib 的 urlopen 返回同步响应对象；两者都要显式读取 body，但 Python 不会自动把 JSON 变成 dict。",
        [
            ("把 bytes 当 str", "拼接响应时报 TypeError", "read() 返回 bytes", "先 decode('utf-8') 再处理", "body = response.read() + '尾部'"),
            ("测试直接联网", "单测受 DNS/服务状态影响", "函数写死 urlopen", "注入 opener 并返回固定响应", "urlopen('https://example.invalid')"),
        ],
        "能构造并读取一个可测试的 GET 请求。",
        "from urllib.request import Request\n\ndef fetch_text(url, opener):\n    # 构造 Request 并读取文本\n    pass\n",
        [("检查请求", "让 fake opener 接收 Request", "method 为 GET 且 URL 未改变"), ("读取正文", "让 response.read 返回 UTF-8 bytes", "返回 str 并关闭响应")],
        "用 fake opener 测试 URL、GET 和中文响应，不访问真实网络。",
        [("GET", "fetch_text('/tasks', fake_open)", "得到解码文本"), ("中文", "fake response.read() 返回 '任务'.encode('utf-8')", "返回 '任务' 而不是 bytes")],
        "定义 fetch_text(url, opener)：创建 GET Request，调用 opener，并在 with 中读取 UTF-8 文本；测试必须使用 fake opener。",
        "请求字段准确，返回值是 str；测试调用一次且没有真实联网。",
    ),
    "D12-response": _manual_detail(
        [
            "HTTP 响应有状态码、headers 和 body 三层信息，200 不保证 body 是合法 JSON。客户端要先判断状态，再解码和 json.loads。",
            "JSONDecodeError 表示文本语法坏，HTTPError 表示协议状态失败；把二者都变成空 dict 会让上层误以为成功。",
            "fake response 能稳定覆盖合法 JSON、坏 JSON 和 404。练习保留失败原因，调用者才知道应修输入还是修服务。",
        ],
        "fetch 的 response.ok 常被误认为自动解析 JSON；urllib 需要手动检查 status、decode 和 loads。",
        [
            ("忽略状态", "404 被当成正常列表", "未检查 status", "先检查状态再解析", "return json.loads(response.read())"),
            ("吞解析错", "坏 JSON 变成 {}", "except 返回默认值", "保留解析错误或转换为明确异常", "except json.JSONDecodeError:\n    data = {}"),
        ],
        "区分状态码失败和 JSON 语法失败。",
        "def parse_response(response):\n    # 检查 status 后解析 JSON\n    pass\n",
        [("成功", "fake response status=200，body 为 b'{\"items\": []}'", "返回 dict"), ("坏 JSON", "status=200，body 为 b'{bad}'", "抛出可识别的解析错误")],
        "用三个 fake response 覆盖 200 合法 JSON、200 非法 JSON、404；断言每条路径的返回值或异常类型。",
        [("成功", "parse_response(Response(200, b'{\"ok\": true}'))", "返回 {'ok': True}"), ("状态", "parse_response(Response(404, b'{}'))", "明确 HTTP 失败")],
        "定义 parse_response(response)，先检查 status，再用 UTF-8 解码和 json.loads；HTTP 错误和坏 JSON 不得静默变成空对象。",
        "合法响应返回 Python dict；非 2xx 与坏 JSON 是可识别失败。",
    ),
    "D12-post": _manual_detail(
        [
            "POST JSON 需要把 Python 对象 dumps 成字符串，再 encode 成 UTF-8 bytes。Content-Type 告诉服务端 body 不是表单而是 JSON。",
            "Request 的 method、headers、data 必须一致；把 dict 直接塞进 data 或漏 Content-Type 都会让协议变形。",
            "注入 opener 后，测试可以还原 request.data 并检查中文、方法和头。不可序列化对象应在客户端边界失败，不能伪造成功。",
        ],
        "fetch 的 body 也需要 JSON.stringify 和 Content-Type；urllib 不会像某些 JS 客户端那样自动序列化 dict。",
        [
            ("dict 直传", "data 类型错误", "没有序列化", "dumps 后 encode", "Request(url, data={'title': '买书'}, method='POST')"),
            ("漏 Content-Type", "服务端可能返回 415", "没有声明 JSON 媒体类型", "设置 application/json", "Request(url, data=body, method='POST')"),
        ],
        "发送协议正确的 JSON POST。",
        "import json\nfrom urllib.request import Request\n\ndef post_json(url, payload, opener):\n    # 序列化并发送\n    pass\n",
        [("body", "fake opener 读取 request.data", "json.loads 可还原 payload"), ("header", "读取 method/headers", "POST 和 application/json")],
        "用 fake opener 检查中文 payload 的 bytes、method 和 Content-Type，不产生真实 HTTP 请求。",
        [("对象", "post_json('/tasks', {'title': '买书'}, fake_open)", "body 可还原原 dict"), ("非法", "post_json('/tasks', {'when': object()}, fake_open)", "序列化明确失败")],
        "定义 post_json(url, payload, opener)：json.dumps 后 UTF-8 编码，构造 POST Request 并只调用一次 opener；不能把 dict 直接作为 data。",
        "请求协议字段准确且中文可还原；不可序列化输入不会伪装成功。",
    ),
    "D12-timeout": _manual_detail(
        [
            "timeout 是一次网络操作的等待上限，不是重试次数。它必须传给真正执行 opener 的调用点，才能限制等待。",
            "TimeoutError、URLError 和 HTTPError 代表不同失败原因；练习只要求明确失败，不因网络失败偷偷重试或换服务地址。",
            "计数 fake opener 可以同时验证 timeout 值与只调用一次。测试完全离线，却能证明客户端的可靠性边界。",
        ],
        "AbortController 的超时也只是取消控制；Python timeout 同样不等于自动 retry。",
        [
            ("忘传 timeout", "慢服务持续阻塞", "调用点没有 timeout", "传入明确秒数", "urlopen(request)"),
            ("失败变空列表", "上层误以为成功", "except 返回 []", "保留网络错误或明确错误类型", "except Exception:\n    return []"),
        ],
        "传递 timeout 并坚持一次调用。",
        "from urllib.request import Request\n\ndef fetch_with_timeout(url, opener, timeout=2):\n    # timeout 传给 opener\n    pass\n",
        [("参数", "fake opener 记录 timeout", "值等于调用者传入值"), ("失败", "fake opener 抛 TimeoutError", "只调用一次并明确失败")],
        "用 fake opener 测试 timeout=3 和超时异常，不访问真实 URL，也不在 except 中重试。",
        [("定时", "fetch_with_timeout('/slow', fake_open, timeout=3)", "fake opener 收到 3"), ("异常", "fake_open 抛 TimeoutError", "失败且调用计数为 1")],
        "定义 fetch_with_timeout(url, opener, timeout=2)，仅调用 opener(request, timeout=timeout)；网络错误不 retry/fallback。",
        "timeout 原样传递；网络失败清晰返回且调用一次。",
    ),
})

NONCORE_TEACHING.update({
    "D17-coroutine": _manual_detail(
        ["async def 调用返回 coroutine，不会立即执行函数体；await 才把控制权交给事件循环并取得结果。同步函数不能直接 await。", "asyncio.run 负责创建和关闭一次事件循环，适合脚本边界；在已经运行的事件循环里再次 run 会报错。", "测试用短小 coroutine 和 asyncio.run 观察返回值，重点是执行时机和 await 链，而不是网络服务。"],
        "Promise 需要 await，Python coroutine 同样惰性但由 asyncio event loop 调度。",
        [("忘 await", "得到 coroutine object/RuntimeWarning", "只调用 async 函数", "在 async 上下文 await", "result = fetch()"), ("嵌套 run", "RuntimeError event loop running", "在 async 函数内 asyncio.run", "直接 await", "async def outer(): return asyncio.run(inner())")],
        "定义 async fetch_value 并正确运行。", "import asyncio\n\nasync def fetch_value(value):\n    # 让出一次控制权后返回 value\n    pass\n",
        [("运行", "asyncio.run(fetch_value(3))", "返回 3"), ("时机", "创建 coroutine 后再 await", "执行发生在 await")],
        "用 asyncio.run 调用 coroutine；再写 async wrapper 用 await，不嵌套 run。",
        [("值", "asyncio.run(fetch_value(3))", "3"), ("wrapper", "asyncio.run(wrapper())", "得到 awaited 值")],
        "定义 async fetch_value(value) 并在 async wrapper 中 await；脚本边界只用一次 asyncio.run。",
        "coroutine 被 await 执行，返回值准确且无未 await 警告。"),
    "D17-gather": _manual_detail(
        ["gather 同时安排多个 awaitable，并按传入顺序返回结果；完成先后不一定等于结果顺序。并发适合互不依赖的等待任务。", "协程函数调用只是创建 coroutine，必须交给 gather/await；有依赖的第二步不能盲目并发。", "用 asyncio.sleep(0) 让出控制权并记录事件，分别观察执行交错和结果顺序。"],
        "Promise.all 与 gather 都聚合并发任务，但 Python 返回列表顺序由参数决定。",
        [("未 await", "警告且无结果", "coroutine 没有交给 gather", "await asyncio.gather", "tasks = [work(1), work(2)]"), ("误判顺序", "按完成顺序断言结果", "混淆执行与返回顺序", "按输入顺序断言", "assert results == [2, 1]")],
        "并发运行三个独立 coroutine 并保留输入顺序。", "import asyncio\n\nasync def run_all(values):\n    # 用 gather 聚合\n    pass\n",
        [("聚合", "asyncio.run(run_all([1, 2, 3]))", "返回 [1, 2, 3]"), ("空列表", "asyncio.run(run_all([]))", "返回 []")],
        "记录 coroutine 的开始/结束，观察事件交错但结果顺序稳定。",
        [("顺序", "asyncio.run(run_all([1, 2, 3]))", "结果按输入顺序"), ("并发", "每个任务 await asyncio.sleep(0)", "事件发生交错")],
        "定义 async run_all(values)，创建 coroutine 并 await asyncio.gather；不要用同步循环替代。",
        "所有结果返回且顺序与输入一致，任务都被 await。"),
    "D17-timeout": _manual_detail(
        ["asyncio.wait_for 给 awaitable 设置时间上限，超时会取消任务并抛 asyncio.TimeoutError。timeout 不是自动重试，也不应把超时当空结果。", "被取消的 coroutine 可能执行 finally 清理；调用者要决定传播还是转换成明确业务错误，不能遗留后台任务。", "用 asyncio.sleep 制造可控慢任务，分别测试足够和过短 timeout，整个测试离线且快速。"],
        "AbortSignal.timeout 类似取消超时，二者都不等于 retry。",
        [("忘 await wait_for", "超时配置没生效", "只创建 wait_for coroutine", "await wait_for", "asyncio.wait_for(work(), 1)"), ("吞 timeout", "误以为成功", "except 返回 []", "保留明确超时错误", "except asyncio.TimeoutError: return []")],
        "控制慢 coroutine 的超时和取消。", "import asyncio\n\nasync def slow():\n    await asyncio.sleep(0.05)\n    return 'done'\n\nasync def run_with_timeout(seconds):\n    pass\n",
        [("成功", "asyncio.run(run_with_timeout(1))", "done"), ("超时", "asyncio.run(run_with_timeout(0.001))", "TimeoutError")],
        "运行两种 timeout，检查慢任务被取消且没有后台 task。",
        [("足够", "run_with_timeout(1)", "done"), ("太短", "run_with_timeout(0.001)", "明确超时失败")],
        "定义 run_with_timeout(seconds)，await asyncio.wait_for(slow(), timeout=seconds)；超时不得 fallback/retry。",
        "足够时间返回 done，太短明确失败且任务被取消。"),
    "D17-boundary": _manual_detail(
        ["异步异常在 await 点重新抛出，try/except 必须包住 await 而不是只包住 coroutine 创建。gather 的异常策略也要由调用者明确。", "取消是重要边界，清理代码应放 finally，不能把取消吞成成功。错误消息不应包含秘密或内部连接信息。", "测试用立即抛错 coroutine 与取消场景验证路径，避免真实网络；结果区分成功、业务失败和取消。"],
        "Promise rejection 要在 await/catch 边界处理，Python 也不能只 try 创建 coroutine。",
        [("try 范围错", "异常逃出处理器", "try 只包 coroutine()", "try 包 await", "try: task = fail()\nexcept ValueError: pass"), ("吞取消", "任务无法停止", "except BaseException 返回成功", "finally 清理后重新抛出", "except BaseException: return None")],
        "为异步失败和取消定义清晰结果。", "import asyncio\n\nasync def fail():\n    raise ValueError('bad input')\n\nasync def safe_call():\n    # 在 await 边界处理 ValueError\n    pass\n",
        [("失败", "asyncio.run(safe_call())", "返回明确错误标签"), ("取消", "创建 task 后 cancel", "finally 执行且取消不被吞")],
        "分别运行失败 coroutine 和 cancel 场景，记录 finally 事件。",
        [("错误", "asyncio.run(safe_call())", "得到 invalid-input"), ("取消", "task.cancel(); await task", "CancelledError 保留")],
        "定义 safe_call() 只捕获预期 ValueError；取消路径在 finally 清理后继续传播，不返回伪成功。",
        "预期异常得到稳定结果，取消完成清理且不被静默吞掉。"),
})

NONCORE_TEACHING.update({
    "D15-assert": _manual_detail(
        ["pytest 会收集 test_ 开头的函数，普通 assert 失败时显示表达式和值。测试不是打印演示，而是对行为做可重复判断。", "一个测试围绕一个行为，输入和期望要具体；浮点、异常和集合分别需要合适断言，不能所有情况只写 truthy。", "先让失败测试暴露差异，再修改实现；pytest 的退出码是 CI 能否信任结果的重要反馈。"],
        "pytest 的 assert 类似 Jest expect，但 Python 使用原生 assert 并由 pytest 改写失败信息。",
        [("测试名错", "pytest 收集不到", "文件/函数不符合发现规则", "用 test_ 命名", "def check_add(): assert add(1,2)==3"), ("断言太弱", "错误实现也通过", "只 assert result", "断言精确值和边界", "assert result")],
        "写两个针对 add_tax 的确定性测试。", "def add_tax(price):\n    return price\n\ndef test_add_tax():\n    assert add_tax(100) == 113\n",
        [("正常", "pytest -q", "测试通过"), ("失败反馈", "把实现改错后 pytest -q", "出现差异和非零退出")],
        "运行一次通过和一次故意失败，阅读 pytest 的断言差异。", [("正常", "add_tax(100)", "113"), ("边界", "add_tax(0)", "0")],
        "定义 add_tax(price)，用 pytest 测试 100->113、0->0；测试名和断言必须可被 pytest 收集。",
        "pytest 退出码和断言结果与契约一致。"),
    "D15-fixture": _manual_detail(
        ["fixture 是测试准备和清理的函数，yield 前建立资源，yield 后释放。tmp_path 为每个测试提供独立临时目录，避免写入项目真实目录。", "fixture scope 越大越容易共享状态；初学阶段使用默认 function scope，让每个测试从空目录开始。", "第二个用例应看不到第一个用例创建的文件；失败时区分路径、编码和 fixture 注入问题。"],
        "fixture 类似 Jest beforeEach/afterEach，但 yield fixture 直接表达资源生命周期。",
        [("固定 cwd", "测试互相覆盖文件", "写项目根", "使用 tmp_path", "Path('data.json').write_text('{}')"), ("fixture 无返回", "参数为 None", "缺 return/yield", "在 fixture 中返回资源", "@pytest.fixture\ndef data(): Path('x').touch()")],
        "用 tmp_path 测试文件写入与隔离。", "import pytest\n@pytest.fixture\ndef note_path(tmp_path):\n    return tmp_path / 'note.txt'\n\ndef test_write(note_path):\n    pass\n",
        [("写读", "note_path.write_text('你好', encoding='utf-8')", "读回 你好"), ("隔离", "另一个测试查看 note_path.parent", "没有前一测试文件")],
        "运行两个测试并检查每个 tmp_path 独立；不使用真实 cwd。", [("写读", "note_path.write_text('你好', encoding='utf-8')", "内容正确"), ("目录", "list(note_path.parent.iterdir())", "只看到当前测试文件")],
        "定义 note_path fixture 返回 tmp_path/'note.txt'，测试中文写读且不依赖 cwd；保持默认 function scope。",
        "每个测试拥有独立路径，资源在测试后可回收。"),
    "D15-mock": _manual_detail(
        ["Mock 用替身记录调用并返回固定值，patch 临时替换模块中真正查找的名称。它隔离网络和时钟，让测试只验证本地业务逻辑。", "patch 目标要写被测模块使用的路径，不是盲目写原始库路径；assert_called_once_with 能检查协议参数。", "mock 不应把所有实现都伪造掉，只替换不稳定边界；退出 with 后替换自动恢复。"],
        "patch 与 Jest spyOn 类似，但 Python 目标遵循名称绑定位置。",
        [("patch 错目标", "真实网络仍调用", "patch 了原库路径", "patch 被测模块名称", "patch('urllib.request.urlopen')"), ("替换残留", "后续测试异常", "手动赋值未恢复", "使用 patch 上下文", "client.urlopen = Mock()")],
        "用 patch 隔离 fetch 的 opener。", "from unittest.mock import patch\n\ndef load_value():\n    # 调用模块内的 urlopen 替身\n    pass\n",
        [("返回", "mock 返回固定 response", "解析固定 JSON"), ("调用", "assert_called_once_with", "URL/timeout 正确")],
        "运行成功和抛错两个 mock 测试；退出 patch 后确认名称恢复。",
        [("成功", "with patch('client.urlopen') as open_mock", "解析固定值"), ("次数", "open_mock.assert_called_once()", "只调用一次")],
        "定义 load_value 并 patch 被测模块里的 urlopen；网络不可用时测试仍确定性通过。",
        "只替换网络边界，调用参数和 JSON 解析真实可断言。"),
    "D15-api": _manual_detail(
        ["TestClient 在进程内把请求送到 FastAPI app，测试可观察 status_code、json 和 headers，不需要启动真实端口。", "API 输入应像真实客户端：json 参数是对象，路径/query 按 URL 编码；断言状态码和关键字段，不能只 assert response。", "错误响应要检查 detail 且不含 traceback；数据库依赖用 fixture/override 保持每例隔离。"],
        "TestClient 类似 supertest/requests，但直接调用 ASGI app。",
        [("json 当 data", "服务收到错误 body", "调用 data 而非 json", "client.post(..., json=payload)", "client.post('/tasks', data={'title':'买书'})"), ("只断言 200", "错误状态未发现", "没有具体状态断言", "断言 201/404/422", "assert response")],
        "为 /health 与 /tasks 写状态码和 JSON 回归。", "from fastapi.testclient import TestClient\n\ndef test_health(app):\n    client = TestClient(app)\n    pass\n",
        [("健康", "client.get('/health')", "200/status ok"), ("错误", "client.get('/missing')", "404")],
        "运行成功、创建和不存在路径三条 API 测试，固定依赖数据。",
        [("健康", "client.get('/health')", "200"), ("创建", "client.post('/tasks', json={'title':'买书'})", "201/字段完整")],
        "使用 TestClient 测试 /health 和 /tasks，分别断言状态码、JSON 字段与错误 detail；不启动真实服务。",
        "API 测试离线完成，正常/错误契约清晰。"),
    "D16-connect": _manual_detail(
        ["sqlite3.connect 创建连接对象，连接既管理事务也持有文件资源。:memory: 适合测试隔离，文件路径适合持久化，但两者都要 close。", "连接创建不等于表已存在；应用入口应明确 init_db 时机。关闭后不能继续 execute，也不能失败时偷偷换数据库。", "测试用内存库和 tmp_path 文件库检查连接、读写、关闭，不把固定 task.db 写进单测。"],
        "Node sqlite 驱动也有 connection 生命周期，Python sqlite3 需要显式 commit/close。",
        [("未 close", "Windows 文件无法删除", "连接持有句柄", "finally/with 关闭", "conn = sqlite3.connect(path)"), ("混用 DB", "测试读到旧数据", "共享固定文件", "tmp_path/:memory:", "sqlite3.connect('task.db')")],
        "实现 create_connection 和关闭边界。", "import sqlite3\n\ndef create_connection(path=':memory:'):\n    pass\n",
        [("内存", "create_connection(':memory:')", "可 execute"), ("关闭", "conn.close(); conn.execute('select 1')", "明确失败")],
        "用内存库和 tmp_path 文件库各连接一次，finally 关闭。",
        [("查询", "conn = create_connection(':memory:'); print(conn.execute('select 1').fetchone())", "(1,)"), ("关闭", "conn.close() 后执行查询", "ProgrammingError")],
        "定义 create_connection(path)，返回 sqlite3.Connection；数据源由调用者决定，不自动改用 cwd。",
        "连接和关闭边界可测试，路径策略透明。"),
    "D16-schema": _manual_detail(
        ["CREATE TABLE 描述关系结构，PRIMARY KEY 给行稳定身份，NOT NULL 防止必填字段为空，DEFAULT 让新行有初值。", "CREATE TABLE IF NOT EXISTS 让初始化可重复，但不会修改旧表；schema 变更要有迁移策略，不能每次请求 drop。", "用 PRAGMA table_info 检查真实列，再插入最小行观察 done 默认 0，而不是只检查 SQL 字符串。"],
        "SQL schema 与 ORM model 都是数据契约，sqlite3 不会替你生成迁移。",
        [("重复建表", "第二次 OperationalError", "没有 IF NOT EXISTS", "使用幂等初始化", "CREATE TABLE tasks (...)"), ("默认错误", "done 比较异常", "缺少 DEFAULT 0", "声明 INTEGER NOT NULL DEFAULT 0", "done TEXT DEFAULT 'false'")],
        "建立可重复的 tasks 表并断言默认值。", "import sqlite3\n\ndef init_db(conn):\n    pass\n",
        [("建表", "init_db(conn); PRAGMA table_info(tasks)", "有 id/title/done"), ("重复", "再次 init_db(conn)", "不报错")],
        "在内存库初始化两次，再插入只给 title 的记录并读取 done。",
        [("列", "PRAGMA table_info(tasks)", "包含 id/title/done"), ("默认", "INSERT title='买书'; SELECT done", "0")],
        "定义 init_db(conn)，使用 CREATE TABLE IF NOT EXISTS，id 主键、title 非空、done 默认 0。",
        "建表幂等，列约束和默认 done 可被 SQL 验证。"),
    "D16-crud": _manual_detail(
        ["CRUD 把业务动作映射到 INSERT、SELECT、UPDATE、DELETE。参数值必须作为 execute 的第二个参数传入，而不是拼进 SQL 字符串。", "新增要 commit 并返回 id，查询转成稳定 dict，更新/删除报告是否命中；API 和 CLI 才能共享结果。", "测试覆盖引号标题、空列表、不存在 id 和重复调用，参数化 SQL 同时是安全和可测试的协议。"],
        "sqlite 参数化查询与 Node 驱动的占位符原则相同，不能拼接用户输入。",
        [("SQL 拼接", "引号标题报错/注入", "f-string 拼 SQL", "使用 ? 参数", "conn.execute(f\"INSERT ... '{title}'\")"), ("忘 commit", "新连接看不到新增", "只 execute 未提交", "动作后 commit", "conn.execute(sql, params)")],
        "实现 add/list/toggle/delete 四个数据层动作。", "def add_task(conn, title):\n    pass\n\ndef list_tasks(conn):\n    pass\n",
        [("新增", "add_task(conn, \"it's\")", "返回正 id"), ("列表", "list_tasks(conn)", "dict 含 title/done")],
        "在内存库完整运行 CRUD，再用含单引号标题验证参数化。",
        [("新增", "add_task(conn, '买书')", "id>0"), ("安全", "add_task(conn, \"it's\")", "成功且标题完整")],
        "定义 add_task/list_tasks/toggle_task/delete_task，所有值参数化；不存在 id 返回明确结果。",
        "CRUD 可重复，特殊字符安全，列表结构稳定。"),
    "D16-transaction": _manual_detail(
        ["事务把多个 SQL 动作组成全成或全撤销的单元。commit 固化修改，rollback 把未提交修改恢复到上一个边界。", "异常路径必须 rollback，finally 负责 close；如果 finally 无条件 commit，失败半成品就会被写入。", "测试在第二步故意抛异常，再查询确认第一步也没有留下，事务策略必须由数据层明确。"],
        "事务回调与 JS ORM transaction 概念相同，但 sqlite3 需显式 commit/rollback。",
        [("异常仍 commit", "半条数据残留", "finally 调 commit", "except rollback", "try: insert_a(); insert_b()\nfinally: conn.commit()"), ("只 rollback", "资源泄漏", "异常路径缺 close", "finally 关闭", "except: conn.rollback()")],
        "实现失败即回滚的批量写入。", "def add_two(conn, first, second):\n    pass\n",
        [("成功", "add_two(conn, 'A', 'B')", "两行存在"), ("失败", "第二个值触发异常", "两行都不存在")],
        "用查询计数验证成功与失败；失败 rollback，finally 关闭临时游标。",
        [("成功", "add_two(conn, 'A', 'B')", "count=2"), ("回滚", "add_two(conn, 'A', bad)", "count 不增加")],
        "定义 add_two(conn, first, second)，成功 commit、异常 rollback；不要吞异常后返回成功。",
        "成功全量提交，失败没有半成品，资源路径可关闭。"),
})

NONCORE_TEACHING.update({
    "D13-app": _manual_detail(
        ["FastAPI() 创建 ASGI 应用，装饰器把 Python 函数注册成 HTTP 路由；返回 dict 会被框架编码为 JSON。", "健康检查只回答服务能否处理请求，不应在导入时连接真实数据库或启动端口。TestClient 在进程内调用 app，反馈更快也更稳定。", "本节的证据是 app 可导入、/health 返回 200 JSON、未知路径返回 404；每个结果都对应一条 HTTP 契约。"],
        "Express 用 app.get 注册处理器，FastAPI 用装饰器表达同一映射，并可从类型标注生成文档。",
        [("导入启动", "测试卡住或占端口", "import 时调用 uvicorn.run", "只暴露 app，把启动放入口", "uvicorn.run(app, port=8000)"), ("路径拼错", "GET /health 为 404", "装饰器路径写错", "用 TestClient 锁定路径", "@app.get('/heath')")],
        "创建可导入的 app 和健康路由。", "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    pass\n",
        [("导入", "from main import app", "得到 FastAPI 实例"), ("请求", "TestClient(app).get('/health')", "200 且 JSON 含 status")],
        "用 TestClient 请求 /health，不启动真实端口；再请求不存在路径确认 404。",
        [("健康", "client.get('/health')", "200/status=ok"), ("未知", "client.get('/missing')", "404")],
        "定义 app=FastAPI() 和 GET /health，返回 {'status': 'ok'}；禁止 import 副作用启动。",
        "app 可导入，健康检查 200，未知路径 404。"),
    "D13-route": _manual_detail(
        ["路径参数标识资源，如 /tasks/{task_id}；查询参数控制筛选，如 ?limit=10。FastAPI 依据类型标注转换，非法输入在函数体前得到 422。", "路径和查询参数不应手动从一个字符串切分；默认值写进签名，调用者不传时仍有确定行为。", "测试覆盖整数、缺省 limit 和非法类型。422 是输入契约反馈，不应在路由里 catch 成 200。"],
        "Express params/query 通常都是字符串，FastAPI 会按 Python 标注校验并生成 422。",
        [("未标 int", "加法 TypeError", "参数仍是 str", "声明 task_id: int", "def get_task(task_id): return task_id + 1"), ("查询无默认", "不传 limit 报错", "手动取缺失键", "声明 limit: int = 20", "def list_tasks(limit): return limit")],
        "实现路径与查询参数并观察 422。", "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/tasks/{task_id}')\ndef get_task(task_id: int):\n    return {'id': task_id}\n",
        [("路径", "client.get('/tasks/7')", "id 为整数 7"), ("非法", "client.get('/tasks/not-int')", "状态 422")],
        "请求整数/非法路径和带/不带 limit 的查询，记录状态和 JSON。",
        [("路径", "client.get('/tasks/7')", "200/id=7"), ("查询", "client.get('/tasks?limit=3')", "limit=3")],
        "定义 task_id:int 与 limit:int=20；非法输入由 FastAPI 422 拒绝，不在函数里静默转 0。",
        "正常值转换正确，缺省使用 20，非法类型 422。"),
    "D13-response": _manual_detail(
        ["response_model 描述成功响应字段，status_code 描述创建动作的协议结果；模型让返回值形状进入文档和运行时校验。", "输入模型与输出模型可以不同：创建只收 title，响应还含 id/done。Pydantic 模型比随意 dict 更早暴露字段遗漏。", "测试同时检查状态码、字段和错误响应；不要把内部异常对象直接交给客户端。"],
        "Express 需要手写 status/json，FastAPI 用 response_model 和 status_code 声明同一契约。",
        [("字段缺失", "响应校验失败", "返回 dict 不符合模型", "按模型构造结果", "return {'name': '买书'}"), ("创建 200", "客户端无法识别创建", "未设 201", "声明 status_code=201", "@app.post('/tasks')")],
        "定义 TaskOut 并返回 201。", "from pydantic import BaseModel\nclass TaskOut(BaseModel):\n    id: int\n    title: str\n    done: bool = False\n",
        [("模型", "TaskOut(id=1, title='买书')", "字段类型正确"), ("状态", "POST /tasks", "201 且有 id/title/done")],
        "用 TestClient 检查创建响应，并故意删必需字段观察响应校验失败。",
        [("模型", "TaskOut(id=1, title='买书').model_dump()", "done=False"), ("创建", "client.post('/tasks')", "201")],
        "定义 TaskOut(BaseModel)，POST 使用 response_model 和 status_code=201，返回完整字段。",
        "状态码和字段契约正确，多余内部字段不泄漏。"),
    "D13-lifecycle": _manual_detail(
        ["lifespan 适合启动一次、关闭一次的连接或资源：yield 前初始化，yield 后清理；它不是每个请求都重复执行的函数。", "Depends 表达请求级依赖，例如返回配置或连接。把应用级资源和请求级解析分开，资源生命周期才可预测。", "TestClient 上下文会触发 enter/exit；用事件列表检查 start、请求、stop 顺序，比只检查 200 更能验证清理。"],
        "Node startup/shutdown 类似 lifespan，Depends 类似可替换 provider。",
        [("无清理", "资源仍占用", "yield 后没有关闭", "在 yield 后清理", "async def lifespan(app): yield"), ("错误 Depends", "路由无法解析", "把 app.state 当默认值", "写依赖函数并 Depends", "def route(x=app.state.x): return x")],
        "验证 lifespan 和 Depends 的调用顺序。", "from contextlib import asynccontextmanager\nfrom fastapi import FastAPI, Depends\nevents=[]\n@asynccontextmanager\nasync def lifespan(app):\n    events.append('start'); yield; events.append('stop')\napp=FastAPI(lifespan=lifespan)\ndef get_value(): return 'ready'\n",
        [("进入", "with TestClient(app)", "events 先有 start"), ("退出", "退出上下文", "最后有 stop")],
        "用 TestClient 上下文请求 /state，断言依赖值和生命周期事件顺序。",
        [("依赖", "client.get('/state')", "value=ready"), ("清理", "退出 client 后查看 events", "最后为 stop")],
        "定义 lifespan 的 start/stop 与 Depends(get_value)；不在 import 时执行生命周期。",
        "初始化和清理各一次，依赖值进入响应。"),
    "D14-model": _manual_detail(
        ["Pydantic BaseModel 把请求 JSON 转成带字段的 Python 对象，并按标注做类型和必填校验；模型描述边界输入而不是数据库表。", "缺字段、错误类型和额外字段是否允许，取决于字段声明。让 422 在 API 边界发生，比业务函数收到半成品 dict 更容易排查。", "测试发送真实 JSON，检查 model_dump 和错误 detail；不要在路由里手动把所有字符串转成目标类型。"],
        "Pydantic 类似运行时 schema，区别于只靠 TypeScript 编译期类型。",
        [("字段默认", "缺 title 仍通过", "title 有空字符串默认", "使用无默认 str", "class TaskIn(BaseModel): title: str = ''"), ("手动转换", "坏数字到业务层才报错", "字段声明成 str", "声明 priority: int", "priority = int(payload['priority'])")],
        "定义 TaskIn 并观察 422。", "from pydantic import BaseModel\nclass TaskIn(BaseModel):\n    title: str\n    priority: int = 0\n",
        [("合法", "TaskIn(title='买书')", "priority=0"), ("错误", "TaskIn(priority='bad')", "ValidationError")],
        "测试合法、省略默认、缺 title、坏 priority 四种输入。",
        [("对象", "TaskIn(title='买书').model_dump()", "含 title/priority"), ("坏值", "TaskIn(priority='bad')", "ValidationError")],
        "定义 TaskIn(BaseModel)，title 必填、priority 为 int 默认 0；API 不手动吞 ValidationError。",
        "合法输入得到模型对象；错误输入得到字段位置明确的 422。"),
    "D14-service": _manual_detail(
        ["路由负责 HTTP 输入输出，service 负责任务规则；分开后同一个业务函数可以被 CLI、测试和 API 复用。路由不应把 SQL、格式化和状态码混成一段。", "service 接收普通 Python 值或 repo 参数，返回明确结果/异常。依赖通过参数传入，测试可以用内存 fake 替换数据库。", "分别测试 service 业务结果和 route HTTP 映射，失败时能判断是规则错、序列化错还是状态码错。"],
        "Express controller/service 分层与 Python 函数参数分离相同。",
        [("路由写规则", "service 无法复用", "全部逻辑在 endpoint", "抽出 create_task", "@app.post('/tasks')\ndef route(body): return db.insert(body)"), ("隐式全局 DB", "测试互相污染", "service 读取模块全局", "把 repo 作为参数", "DB = sqlite3.connect('app.db')")],
        "把 create_task 业务规则从 route 中抽出。", "def create_task(repo, title):\n    # 校验 title 并调用 repo\n    pass\n",
        [("正常", "fake repo + create_task(repo, '买书')", "repo 收到一次 insert"), ("空标题", "create_task(repo, '   ')", "ValueError 且不写库")],
        "先独立调用 service，再用 route fake 依赖验证状态码；不连接真实数据库。",
        [("服务", "create_task(repo, '买书')", "返回带 title 任务"), ("边界", "create_task(repo, '  ')", "ValueError")],
        "定义 create_task(repo, title)，先 strip/校验非空，再调用 repo.add；路由只负责映射 HTTP。",
        "业务函数可单测且空标题不写库；API 复用同一规则。"),
    "D14-errors": _manual_detail(
        ["HTTPException 把业务失败转换成客户端能理解的 status_code 和 detail。404 表示资源不存在，422 表示输入不符合模型，二者不要都返回 500。", "异常应在边界产生：service 可以抛领域异常，route 再映射；不要把 traceback 或数据库连接信息放进 detail。", "测试检查正常、未找到和非法输入的状态码及 JSON 键。错误契约稳定后，前端只展示后端消息。"],
        "Express error middleware 类似统一错误映射，FastAPI 用 HTTPException 与 validation handler。",
        [("返回 None", "客户端收到 200/null", "未找到没有分支", "raise HTTPException(404)", "return None"), ("泄漏 traceback", "响应含内部路径", "str(exc) 直接作为 detail", "使用固定安全消息", "raise HTTPException(500, detail=str(exc))")],
        "实现资源不存在的安全错误契约。", "from fastapi import HTTPException\n\ndef get_or_404(repo, task_id):\n    pass\n",
        [("命中", "fake repo 返回任务", "返回任务"), ("未命中", "fake repo 返回 None", "status_code=404")],
        "用 fake repo 测试命中和未命中；检查 detail 不含内部异常。",
        [("命中", "get_or_404(repo, 1)", "返回任务"), ("404", "get_or_404(empty_repo, 1)", "404/detail=任务不存在")],
        "定义 get_or_404(repo, task_id)，None 时 raise HTTPException(404, detail='任务不存在')，不要返回 null。",
        "命中返回结构，未命中稳定 404，不泄漏 traceback。"),
    "D14-deps": _manual_detail(
        ["Depends 声明路由需要的协作者，FastAPI 在请求期间解析并注入。依赖可以返回数据库连接、配置或用户，路由不必知道创建细节。", "依赖函数是可替换边界：测试用 app.dependency_overrides 提供 fake，完成后清理 override，避免污染后续测试。", "依赖链的错误在请求前暴露；类型标注让读者知道路由收到什么对象，资源关闭则由生命周期负责。"],
        "Depends 类似把 provider 注入 handler，而不是手动从全局单例读取。",
        [("直接全局", "测试不能隔离", "route 读取 DB 全局", "使用 Depends(get_repo)", "def route(): return DB.list()"), ("忘清 override", "后续测试继续用 fake", "override 未恢复", "finally 清空", "app.dependency_overrides[get_repo] = fake")],
        "用 Depends 注入可替换 repo。", "from fastapi import FastAPI, Depends\napp = FastAPI()\ndef get_repo(): return RealRepo()\n@app.get('/tasks')\ndef list_tasks(repo=Depends(get_repo)):\n    pass\n",
        [("默认", "不 override 请求 /tasks", "调用默认依赖"), ("替换", "override get_repo 为 fake", "路由使用 fake")],
        "做一次默认请求和一次 override 请求，最后清空 dependency_overrides。",
        [("依赖", "client.get('/tasks')", "返回 repo 数据"), ("替换", "app.dependency_overrides[get_repo] = lambda: fake", "响应来自 fake")],
        "定义 get_repo 并通过 Depends 注入；测试 override 后在 finally 清理，不能永久污染 app。",
        "路由不依赖具体全局实现，fake 可替换且清理完整。"),
})


CORE_PRACTICE_CONTRACTS: dict[str, dict[str, str]] = {
    "D02-execution": {
        "instructions": "请编写 main.py：先打印 START，再在 if True 块内打印 BLOCK，最后打印 END；必须使用四个空格缩进。",
        "expected_behavior": "直接运行 main.py 的 stdout 严格为 START、BLOCK、END 三行；缩进错误必须让验证失败。",
        "starter_content": "print('START')\nif True:\n    print('TODO')\nprint('END')\n",
        "starter_policy": "complete",
    },
    "D02-strings": {
        "instructions": "请定义 transform_text(text)：去掉首尾空白后返回反转字符串；例如 transform_text(' ab ') 应返回 'ba'，不要修改原字符串。",
        "expected_behavior": "transform_text(' ab ') == 'ba'，且原字符串仍为 ' ab '。",
        "starter_content": "def transform_text(text):\n    # 先完成 strip，再完成切片反转\n    raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
    "D03-for": {
        "instructions": "请定义 sum_even(numbers)：遍历输入序列，只累加偶数并返回总和；用一个空列表和一个混合数字列表自测。",
        "expected_behavior": "sum_even([1, 2, 4, 5]) == 6，且空列表返回 0。",
        "starter_content": "def sum_even(numbers):\n    total = 0\n    # 在这里用 for 遍历\n    return total\n",
    },
    "D04-varargs": {
        "instructions": "请定义 describe(*args, **kwargs)，返回 {'args': args, 'kwargs': kwargs}；分别用位置参数和关键字参数调用。",
        "expected_behavior": "describe(1, 2, name='林')['args'] == (1, 2)，kwargs['name'] == '林'。",
        "starter_content": "def describe(*args, **kwargs):\n    raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
    "D04-global-nonlocal": {
        "instructions": "请定义 make_counter()，用 nonlocal 保存计数并返回 step 函数；连续调用 step 应得到 1、2、3。",
        "expected_behavior": "同一个 step() 闭包连续三次返回 [1, 2, 3]，不能依赖全局变量。",
        "starter_content": "def make_counter():\n    value = 0\n    def step():\n        nonlocal value\n        raise NotImplementedError\n    return step\n",
        "starter_policy": "function_body",
    },
    "D05-mutability": {
        "instructions": "请定义 copy_and_append(items)，返回 (items, copied)，其中 copied 是外层复制后追加 'new' 的列表；调用后原列表不能出现 'new'。",
        "expected_behavior": "copy_and_append(['old']) == (['old'], ['old', 'new'])，证明引用和复制不同。",
        "starter_content": "def copy_and_append(items):\n    raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
    "D05-dict-set": {
        "instructions": "请定义 summarize_tags(tags)，返回 {'unique': set(tags), 'count': len(set(tags))}；用含重复标签的 list 验证。",
        "expected_behavior": "summarize_tags(['py', 'py', 'test'])['unique'] == {'py', 'test'}，count == 2。",
        "starter_content": "def summarize_tags(tags):\n    raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
    "D05-iterators-generators": {
        "instructions": "请定义 count_up_to(limit) 生成 0 到 limit-1；返回值必须是生成器/可迭代对象，逐项 yield 而不是一次性拼 list。",
        "expected_behavior": "list(count_up_to(3)) == [0, 1, 2]，并且 iter(count_up_to(3)) 是可迭代对象。",
        "starter_content": "def count_up_to(limit):\n    raise NotImplementedError\n    yield limit\n",
        "starter_policy": "function_body",
    },
    "D06-else-finally": {
        "instructions": "请定义 parse_number(text, events)：成功返回整数，失败返回 None；无论成功失败都向 events 追加 'finally'。",
        "expected_behavior": "两条路径都追加一次 finally，parse_number('7', events) == 7，parse_number('x', events) is None。",
        "starter_content": "def parse_number(text, events):\n    try:\n        raise NotImplementedError\n    finally:\n        events.append('finally')\n",
        "starter_policy": "function_body",
    },
    "D06-with": {
        "instructions": "请定义 read_text(path)，用 with 和 encoding='utf-8' 读取文件并返回文本；不要手动遗忘 close。",
        "expected_behavior": "给定含中文的临时文件后返回完全相同文本，文件句柄由 with 管理。",
        "starter_content": "from pathlib import Path\n\ndef read_text(path):\n    raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
    "D07-package": {
        "instructions": "请在 main.py 中从 helpers 模块导入 greet 并打印 greet('世界')；不要把 greet 函数复制到 main.py。",
        "expected_behavior": "直接运行 main.py 输出 '你好，世界'，证明模块导入和命名空间生效。",
        "starter_content": "from helpers import greet\nprint(greet('错误输入'))\n",
        "starter_policy": "complete",
    },
    "D07-class-instance": {
        "instructions": "请定义 Task 类：构造函数接收 title，实例方法 label() 返回 title；创建两个实例验证状态互不共享。",
        "expected_behavior": "Task('学习').label() == '学习'，两个实例的 title 独立。",
        "starter_content": "class Task:\n    def __init__(self, title):\n        self.title = title\n\n    def label(self):\n        raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
    "D07-dataclass": {
        "instructions": "请用 @dataclass 定义 Point，字段 x/y 为 int；Point(2, 3) 的字段可访问且 repr 包含类名和字段值。",
        "expected_behavior": "Point(2, 3).x == 2，Point(2, 3).y == 3，且 repr 可读。",
        "starter_content": "from dataclasses import dataclass\n\n@dataclass\nclass Point:\n    x: int\n    y: int\n",
    },
    "D04-type-hints": {
        "instructions": "请定义 format_user(name: str, age: int) -> str，返回包含姓名和年龄的文本；用 typing.get_type_hints 检查标注。",
        "expected_behavior": "format_user('林', 20) 返回包含“林”和“20”的字符串，并保留参数/返回值标注。",
        "starter_content": "def format_user(name: str, age: int) -> str:\n    raise NotImplementedError\n",
        "starter_policy": "function_body",
    },
}



def _explicit_dev(
    topic: str,
    explanation: list[str],
    bridge: str,
    errors: list[tuple[str, str, str, str, str]],
    goal: str,
    starter: str,
    steps: list[tuple[str, str]],
    check: str,
    inputs: list[tuple[str, str, str]],
    instructions: str,
    expected: str,
) -> dict[str, Any]:
    """Build a hand-written common-development lesson; topic is only metadata."""
    detail = _detail(explanation, bridge, errors, goal, starter, steps, check, inputs, instructions, expected)
    detail["topic"] = topic
    return detail


# D12-D17：每个小节的解释、错误、引导和独立输入都围绕自己的 API 契约。
# 这些记录故意不读取标题生成内容，方便审阅者逐节检查。
# Extend the already-defined common-development records with HTTP/async lessons.
NONCORE_TEACHING.update({
    "D12-request": _explicit_dev("urllib GET", [
        "Request 描述 URL、方法和请求头，urlopen 才是发生网络 I/O 的动作。把两步分开后，可以在不联网的测试中先检查请求协议。",
        "响应体通常是 bytes，文本协议要显式 decode；文件式 with 也提醒我们及时释放响应资源。GET 的查询条件通常编码在 URL，而不是偷偷改成请求体。",
        "练习把 opener 作为参数注入，fake opener 可以记录 Request 并返回固定 bytes。这样学习重点是请求对象和资源生命周期，而不是等待真实服务器。",
    ], "fetch 与 urllib", [("bytes 当 str", "拼接响应时报 TypeError", "read 返回 bytes", "decode UTF-8 后再处理", "body = response.read() + '尾部'"), ("直接联网测试", "测试受 DNS 影响", "函数写死 urlopen", "注入 opener", "urlopen('https://example.invalid')")], "能构造并读取一个可测试的 GET 请求。", "from urllib.request import Request\n\ndef fetch_text(url, opener):\n    pass\n", [("请求", "fake opener 记录 Request", "method 为 GET"), ("响应", "fake response.read 返回 UTF-8 bytes", "返回 str 并关闭响应")], "用 fake opener 测试 URL、GET 和中文响应，不访问真实网络。", [("GET", "fetch_text('/tasks', fake_open)", "得到解码文本"), ("中文", "fake response.read() 返回 '任务'.encode('utf-8')", "返回 '任务'")], "定义 fetch_text(url, opener)，创建 GET Request，调用 opener 并在 with 中读取 UTF-8 文本。", "请求字段准确，返回 str；测试调用次数为一次且无真实联网。"),
    "D12-response": _explicit_dev("HTTP response", [
        "响应有状态码、headers 和 body 三层信息，200 不保证 body 是合法 JSON。客户端要先判断状态，再解码和 loads。",
        "JSONDecodeError 表示文本语法坏，HTTPError 表示协议状态失败；把二者都变成空 dict 会让上层误以为成功。",
        "fake response 能稳定覆盖合法 JSON、坏 JSON 和 404。练习要求保留失败原因，调用者才知道应修数据还是修服务。",
    ], "urllib 响应", [("忽略状态", "404 被当正常列表", "未检查 status", "先检查状态", "return json.loads(response.read())"), ("吞解析错", "坏 JSON 变 {}", "except 返回默认值", "保留解析错误", "except json.JSONDecodeError: data = {}")], "区分状态码失败和 JSON 语法失败。", "def parse_response(response):\n    pass\n", [("成功", "Response(200, b'{\"items\": []}')", "返回 dict"), ("坏 JSON", "Response(200, b'{bad}')", "抛出解析错误")], "用 fake response 覆盖 200 合法/坏 JSON 和 404，不连接网络。", [("成功", "parse_response(Response(200, b'{\"ok\": true}'))", "返回 {'ok': True}"), ("状态", "parse_response(Response(404, b'{}'))", "明确 HTTP 失败")], "定义 parse_response(response)，先检查 status，再 UTF-8 解码并 json.loads；不 fallback 为空对象。", "合法响应返回 dict；非 2xx 与坏 JSON 是可识别失败。"),
    "D12-post": _explicit_dev("JSON POST", [
        "POST JSON 需要把 Python 对象 dumps 成字符串，再 encode 成 UTF-8 bytes。Content-Type 告诉服务端 body 不是表单而是 JSON。",
        "Request 的 method、headers、data 必须一致；把 dict 直接塞进 data 或漏 Content-Type 都会让协议变形。",
        "注入 opener 后，测试可以还原 request.data 并检查中文、方法和头。不可序列化对象应在客户端边界失败，不能伪造成功。",
    ], "urllib POST", [("dict 直传", "data 类型错误", "未序列化", "dumps 后 encode", "Request(url, data={'title': '买书'}, method='POST')"), ("漏 Content-Type", "服务端可能 415", "没有声明 JSON", "设置 application/json", "Request(url, data=body, method='POST')")], "发送协议正确的 JSON POST。", "import json\nfrom urllib.request import Request\n\ndef post_json(url, payload, opener):\n    pass\n", [("body", "fake opener 读取 data", "json.loads 可还原 payload"), ("header", "读取 method/headers", "POST 和 application/json")], "用 fake opener 检查中文 payload 的 bytes、method 和 Content-Type。", [("对象", "post_json('/tasks', {'title': '买书'}, fake_open)", "body 可还原原 dict"), ("非法", "post_json('/tasks', {'when': object()}, fake_open)", "序列化明确失败")], "定义 post_json(url, payload, opener)，dumps 后 UTF-8 encode，构造 POST Request 并只调用一次 opener。", "请求字段准确且中文可还原；不可序列化输入不会伪装成功。"),
    "D12-timeout": _explicit_dev("HTTP timeout", [
        "timeout 是一次网络操作的等待上限，不是重试次数。它必须传给真正执行 urlopen/opener 的调用点。",
        "TimeoutError、URLError 和 HTTPError 代表不同失败原因；课程练习只要求明确失败，不因网络失败偷偷重试或换地址。",
        "计数 fake opener 可以同时验证 timeout 值与只调用一次。测试因此完全离线，却能证明客户端的可靠性边界。",
    ], "urllib timeout", [("忘传 timeout", "慢服务持续阻塞", "调用点无 timeout", "传入秒数", "urlopen(request)"), ("失败变空列表", "上层误以为成功", "except 返回 []", "保留网络错误", "except Exception: return []")], "传递 timeout 并坚持一次调用。", "from urllib.request import Request\n\ndef fetch_with_timeout(url, opener, timeout=2):\n    pass\n", [("参数", "fake opener 记录 timeout", "等于调用者传入值"), ("失败", "fake opener 抛 TimeoutError", "只调用一次并明确失败")], "用 fake opener 测试 timeout=3 和超时异常，不访问真实 URL。", [("定时", "fetch_with_timeout('/slow', fake_open, timeout=3)", "fake 收到 3"), ("异常", "fake_open 抛 TimeoutError", "失败且计数为 1")], "定义 fetch_with_timeout(url, opener, timeout=2)，仅调用 opener(request, timeout=timeout)，不 retry/fallback。", "timeout 原样传递；网络失败清晰返回且调用一次。"),
    "D13-app": _explicit_dev("FastAPI app", [
        "FastAPI() 创建 ASGI 应用，装饰器把 Python 函数注册成 HTTP 路由。返回 dict 会被框架编码为 JSON。",
        "健康检查只回答服务能否处理请求，应该不依赖真实数据库。app 可以被 uvicorn 导入，也可以被 TestClient 在进程内调用。",
        "不要在 import 时启动服务器；TestClient 的状态码和 JSON 是本节最小可观察证据。",
    ], "Express app.get 对照 FastAPI decorator", [("导入启动", "测试卡住/占端口", "import 时 uvicorn.run", "只暴露 app", "uvicorn.run(app, port=8000)"), ("路径拼错", "GET /health 为 404", "装饰器路径错误", "用 TestClient 锁定路径", "@app.get('/heath')")], "创建可导入的 app 和健康路由。", "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    pass\n", [("导入", "from main import app", "得到 FastAPI"), ("请求", "TestClient(app).get('/health')", "200 且 status=ok")], "用 TestClient 请求 /health，不启动真实端口。", [("健康", "client.get('/health')", "200 与 status=ok"), ("未知", "client.get('/missing')", "404")], "定义 app=FastAPI() 和 GET /health，返回 {'status': 'ok'}；禁止 import 副作用启动。", "app 可导入，健康检查 200，未知路径 404。"),
    "D13-route": _explicit_dev("FastAPI route parameters", [
        "路径参数标识资源，如 /tasks/{task_id}；查询参数控制筛选，如 ?limit=10。FastAPI 依据类型标注完成转换，非法输入在函数体前得到 422。",
        "路径和查询参数不应手动从一个字符串切分；默认值写进签名，调用者不传时仍有确定行为。",
        "TestClient 要覆盖正常整数、缺省 limit 和非法类型。422 是输入契约反馈，不应在路由里 catch 成 200。",
    ], "Express params/query 都是字符串，FastAPI 会按标注校验", [("未标 int", "加法 TypeError", "参数仍为 str", "task_id: int", "def get_task(task_id): return task_id + 1"), ("查询无默认", "不传 limit KeyError", "手动取 query", "limit: int = 20", "def list_tasks(limit): return limit")], "实现路径与查询参数并观察 422。", "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/tasks/{task_id}')\ndef get_task(task_id: int):\n    return {'id': task_id}\n", [("路径", "client.get('/tasks/7')", "id=7"), ("非法", "client.get('/tasks/not-int')", "422")], "请求整数/非法路径和带/不带 limit 的查询，记录状态和 JSON。", [("路径", "client.get('/tasks/7')", "200/id=7"), ("查询", "client.get('/tasks?limit=3')", "limit=3")], "定义 task_id:int 与 limit:int=20；非法输入由 FastAPI 422 拒绝。", "正常值转换正确，缺省使用 20，非法类型 422。"),
    "D13-response": _explicit_dev("FastAPI response model", [
        "response_model 描述成功响应字段，status_code 描述创建等动作的协议结果。模型让返回值形状进入文档和运行时校验。",
        "输入模型与输出模型可以不同：创建只收 title，输出还含 id/done。Pydantic 模型比随意 dict 更早暴露字段遗漏。",
        "测试要同时检查状态码、字段和错误响应；不要把内部异常对象直接交给客户端。",
    ], "Express 需要手写 status/json，FastAPI 用模型声明", [("字段缺失", "响应校验失败", "返回 dict 不符合模型", "按模型构造", "return {'name': '买书'}"), ("创建 200", "客户端无法识别创建", "未设 status_code", "声明 201", "@app.post('/tasks')")], "定义 TaskOut 并返回 201。", "from pydantic import BaseModel\nclass TaskOut(BaseModel):\n    id: int\n    title: str\n    done: bool = False\n", [("模型", "TaskOut(id=1, title='买书')", "字段类型正确"), ("状态", "POST /tasks", "201 且有 id/title/done")], "用 TestClient 检查创建响应，并故意删必需字段观察失败。", [("模型", "TaskOut(id=1, title='买书').model_dump()", "done=False"), ("创建", "client.post('/tasks')", "201")], "定义 TaskOut(BaseModel)，POST 使用 response_model 和 status_code=201，返回完整字段。", "状态码和字段契约正确，多余内部字段不泄漏。"),
    "D13-lifecycle": _explicit_dev("FastAPI lifecycle", [
        "lifespan 适合启动一次、关闭一次的连接或资源：yield 前初始化，yield 后清理。它不是每个请求都重复执行的函数。",
        "Depends 表达请求级依赖，例如返回配置或连接。把应用级资源和请求级解析分开，资源生命周期才可预测。",
        "TestClient 上下文会触发 enter/exit；用事件列表检查 start、请求、stop 的顺序，比只检查 200 更能验证清理。",
    ], "Node startup/shutdown 类似 lifespan，Depends 类似可替换 provider", [("无清理", "资源仍占用", "yield 后没有 close", "在 yield 后清理", "async def lifespan(app): app.state.x=1; yield"), ("错误 Depends", "路由无法解析参数", "把 app.state 直接当默认值", "写依赖函数并 Depends", "def route(x=app.state.x): return x")], "验证 lifespan 和 Depends 的调用顺序。", "from contextlib import asynccontextmanager\nfrom fastapi import FastAPI, Depends\nevents=[]\n@asynccontextmanager\nasync def lifespan(app):\n    events.append('start'); yield; events.append('stop')\napp=FastAPI(lifespan=lifespan)\ndef get_value(): return 'ready'\n", [("进入", "with TestClient(app)", "events 先有 start"), ("退出", "退出上下文", "最后有 stop")], "用 TestClient 上下文请求 /state，断言依赖值和生命周期事件顺序。", [("依赖", "client.get('/state')", "value=ready"), ("清理", "退出 client 后查看 events", "最后为 stop")], "定义 lifespan 的 start/stop 与 Depends(get_value)；不在 import 时执行生命周期。", "初始化和清理各一次，依赖值进入响应。"),
})


def _project_detail(
    change: str,
    relation: str,
    run: str,
    instructions: str,
    expected: str,
    starter: str,
    inputs: list[tuple[str, str, str]],
    errors: list[tuple[str, str, str, str, str]],
) -> dict[str, Any]:
    """Project lessons keep file/dependency/run details as hand-written data."""
    return _detail(
        [change, relation, run],
        "JavaScript 经验可以帮助理解界面/HTTP，但本节先按真实 Python workspace 文件、命令和后端验收完成。",
        errors,
        instructions,
        starter,
        [("编辑本节产物", f"按契约修改目标文件：{instructions}", "只改变本节负责的文件，前序依赖仍可读取。"), ("运行验证", run, expected)],
        f"完成后运行：{run}；失败先比较前序依赖文件、路径和实际输出。",
        inputs,
        instructions,
        expected,
    )


# Extend the already-defined project records with the remaining project lessons.
PROJECT_TEACHING.update({
    "D18-scope": _project_detail(
        "把 task-manager 的用户、add/list/complete/delete 动作和输入边界写入 docs/requirements.md；需求必须是可验收行为而不是愿望。",
        "本节产物是后续 API、CLI、网页共同引用的上游边界，不写 Python 实现，也不提前创建数据库。",
        "用文本审阅逐条核对用户故事、空标题和不存在 id；失败时回到缺失的验收规则。",
        "编辑 docs/requirements.md，写四个用户故事、输入约束和每步可观察结果。",
        "需求文件能指导 contract、API、CLI 和测试；每条规则都有成功或失败证据。",
        "# docs/requirements.md\n# 写用户故事与验收，不写实现代码\n",
        [("主流程", "add -> list -> complete -> delete", "四步状态变化可观察"), ("边界", "空标题/不存在 id", "接受或拒绝规则明确")],
        [("需求漏边界", "实现之间行为不一致", "只写 happy path", "补每个动作的非法输入和结果", "新增任务：标题非空"), ("实现混入需求", "文档失去业务可读性", "写入函数名/SQL", "只记录用户可观察行为", "调用 db.insert(...)")],
    ),
    "D18-acceptance": _project_detail(
        "把需求写成可执行验收场景：创建后列表可见，完成后 done 改变，删除后不再出现，并列出空标题、重复删除等失败路径。",
        "继续修改 docs/requirements.md；D24 runbook 会复用这些步骤，后续测试要逐条变成断言。",
        "按主流程和错误流程模拟命令/请求，检查每一步有状态码、字段或 stdout；模糊的“正常返回”要补具体结果。",
        "在 docs/requirements.md 增加主流程、错误流程、操作、预期输出和失败定位。",
        "验收清单可直接转换成 API/CLI 测试矩阵，成功与失败都能复现。",
        "# requirements.md\n## 验收场景\n# 补请求、结果和错误定位\n",
        [("主流程", "add/list/complete/delete", "每步有输出"), ("错误流", "重复删除同一 id", "稳定 404/错误码")],
        [("只有成功列表", "错误路径没有验收", "只写 200", "补 400/404/422", "GET /tasks -> 200"), ("预期太虚", "测试无法断言", "写“正常返回”", "写 JSON 字段/退出码", "结果：成功")],
    ),
    "D18-data-contract": _project_detail(
        "创建 contract.json，固定 task 的 id/title/done 字段、类型和 input/output 区别；使用标准 JSON 的 true/false/null 和双引号。",
        "依赖 docs/requirements.md，产物会被 D18-api-contract、D21 schema、D22 tests 读取，不能各自猜字段。",
        "运行 python -m json.tool contract.json 与 json.load；再把 done 改成字符串，确认类型错误能被发现。",
        "创建 contract.json，明确 task input/output、title/id/done 类型、空标题和不存在 id 的错误契约。",
        "contract.json 可解析，字段能被模型、路由和 acceptance 直接引用。",
        "{\n  \"task\": {\"input\": {\"title\": \"string\"}, \"output\": {\"id\": 1, \"title\": \"string\", \"done\": false}}\n}\n",
        [("合法", "python -m json.tool contract.json", "解析成功"), ("边界", "done='false' 或缺 title", "契约明确拒绝")],
        [("Python 字面量", "json.load 报解析错误", "用了 True/None/单引号", "改成 JSON true/false/null/双引号", "{'done': False}"), ("只写输出", "创建输入不清楚", "没有 required input", "补 input/output 两侧", "{\"output\": {\"id\": 1}}")],
    ),
    "D18-api-contract": _project_detail(
        "在 contract.json 增加 CRUD routes、method/path/status/body 和 GET / 静态入口，把需求动作映射成可以请求的协议。",
        "依赖上一节字段契约；D21 api.py、D22 test_api.py、D23 static/index.html 都按同一张路由表工作。",
        "逐条读取 routes，核对 201/404/422 与 detail；若路径冲突，先修契约再写实现。",
        "在 contract.json 增加 GET/POST/PATCH/DELETE /api/tasks、错误表和 GET / 静态入口。",
        "契约能直接生成 API 测试矩阵，浏览器首页也有明确入口。",
        "# contract.json\n# 增加 routes 数组和 errors 对象\n",
        [("创建", "POST /api/tasks {title}", "201 与 task"), ("缺失", "GET /api/tasks/999", "404/detail")],
        [("方法错", "客户端得到 405", "契约和实现 method 不一致", "固定 method/path 表", "GET /api/tasks 创建"), ("遗漏静态路由", "浏览器首页 404", "只写 JSON API", "加入 GET / 验收", "routes: ['/api/tasks']")],
    ),
    "D19-pyproject": _project_detail(
        "配置 pyproject.toml 的项目元数据、Python 版本、taskproj 包和 pytest 测试路径，让安装与测试从空目录可重复。",
        "依赖 requirements.md/contract.json，配置是 D19-D24 的安装基础；字段名必须与真实目录一致。",
        "执行 python -m pip install -e . 与 python -m pytest --collect-only；失败先看 TOML 行号、包目录和依赖声明。",
        "编辑 pyproject.toml，声明 Python 版本、taskproj 包、pytest 测试路径和项目元数据。",
        "editable install 成功，taskproj 可导入，pytest 能发现 tests。",
        "[project]\nname = \"task-manager\"\nrequires-python = \">=3.11\"\n\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n",
        [("解析", "读取 pyproject.toml", "字段可读取"), ("安装", "python -m pip install -e .", "包可导入")],
        [("包名不一致", "import taskproj 失败", "name/目录不一致", "让 project 与包布局一致", "[project] name='task-manager'"), ("漏测试依赖", "空环境找不到 pytest", "只在 README 写依赖", "声明测试依赖", "pytest 只出现在 docs")],
    ),
    "D19-package": _project_detail(
        "创建 taskproj/__init__.py，让目录成为安全可导入的包；只放版本/说明，不在导入时打开数据库或启动服务。",
        "依赖 pyproject.toml；包根供 config.py、main.py、D20-D24 的模块导入使用。",
        "从项目根运行 python -c \"import taskproj\" 并比较导入前后文件树；没有 task.db 才算无副作用。",
        "创建 taskproj/__init__.py，只定义 __version__ 或包说明。",
        "包可导入、版本可观察，初始化无文件和网络副作用。",
        "# taskproj/__init__.py\n__version__ = \"0.1.0\"\n",
        [("导入", "python -c \"import taskproj\"", "成功"), ("版本", "print(taskproj.__version__)", "0.1.0")],
        [("缺 init", "包命令/相对导入失败", "目录没有包入口", "创建 __init__.py", "taskproj/\n  config.py"), ("导入副作用", "pytest 收集生成 DB", "init 执行 I/O", "只放常量", "Path('task.db').touch()")],
    ),
    "D19-config": _project_detail(
        "在 taskproj/config.py 集中数据库路径、默认值和可注入 env，D20 db.py 不再重复猜路径或依赖开发机环境。",
        "依赖 taskproj 包；D20 connection、D21 lifespan 和 README 都使用同一配置优先级。",
        "用空 env、非空 TASKPROJ_DB、空字符串三组输入运行函数；不得打印环境全集或秘密值。",
        "定义 database_path(env=None, root=None)，非空 TASKPROJ_DB 覆盖默认 taskproj.db，并返回 Path。",
        "配置优先级明确、路径稳定、无环境泄露。",
        "from pathlib import Path\n\ndef database_path(env=None, root=None):\n    pass\n",
        [("默认", "database_path({})", "得到 root/taskproj.db"), ("覆盖", "database_path({'TASKPROJ_DB':'custom.db'})", "使用 custom.db")],
        [("空值覆盖", "路径变成空 Path", "只判断 key 存在", "空值按未配置处理", "env={'TASKPROJ_DB': ''}"), ("泄露", "日志含配置值", "打印 os.environ", "只返回安全路径", "print(dict(os.environ))")],
    ),
    "D19-main": _project_detail(
        "在 taskproj/main.py 放可导入的 main(argv=None) 和 __name__ 守卫；入口读取配置/初始化并把成功、失败映射为整数退出码。",
        "依赖 config.py 与包布局；D20 会接入数据库实现，D24 runbook 复用 python -m taskproj.main。",
        "分别运行 python -m taskproj.main 与 python -c \"import taskproj.main\"，检查退出码和导入无副作用。",
        "定义 main(argv=None) 与 __name__ 守卫；成功返回 0，初始化失败返回非零并写安全 stderr。",
        "模块导入安全，直接运行有稳定退出码，后续数据层有调用点。",
        "def main(argv=None):\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
        [("导入", "python -c \"import taskproj.main\"", "无副作用"), ("运行", "python -m taskproj.main", "returncode=0")],
        [("import 建库", "pytest 导入生成 DB", "顶层执行 init_db", "把 I/O 放 main", "conn = create_connection()"), ("失败仍 0", "CI 误报成功", "except 返回 None", "返回非零整数", "except Exception: return None")],
    ),
    "D19-readme": _project_detail(
        "更新 README.md，说明 Python 版本、editable 安装、数据库路径、python -m taskproj.main 和 pytest 命令，成为空 workspace 的第一份导航。",
        "依赖 pyproject.toml/main.py；命令必须指向真实文件，D24 runbook 会复用这些步骤。",
        "在临时空目录按 README 顺序检查命令；失败归因到路径、安装或端口，不用修改说明掩盖代码问题。",
        "在 README.md 写安装、运行、测试、API/CLI 入口和数据库默认路径。",
        "零基础学员能按 README 安装并得到可解释的测试反馈。",
        "# task-manager\n\n## 安装\n\n## 运行\n\n## 测试\n",
        [("安装", "python -m pip install -e .", "与 pyproject 一致"), ("测试", "python -m pytest -q", "验收入口明确")],
        [("命令过时", "找不到入口", "沿用旧 app.py", "从真实包命令运行", "python app.py"), ("漏测试", "能跑但无法验收", "只写启动", "补 pytest -q", "python -m taskproj.main")],
    ),
})


# D20-D24 are deliberately file-oriented.  Each record names the real file being
# edited, the files it reads, and the command that proves the small change works.
PROJECT_TEACHING.update({
    "D20-connection": _project_detail(
        "在 taskproj/db.py 实现 create_connection、row_factory 和 init_db；使用 config.database_path 得到目标文件。",
        "依赖 taskproj/config.py 和 contract.json 的字段约定；后面的 CRUD 函数都复用本节连接和表结构，不重新猜路径。",
        "运行 python -c \"from taskproj.db import init_db; init_db(':memory:')\"，再用 sqlite_master 检查 tasks 表和列；失败先看连接是否关闭、SQL 是否幂等。",
        "编辑 taskproj/db.py：提供 create_connection(path)、init_db(conn)，设置 sqlite3.Row，创建 id/title/done 表且不在 import 时建库。",
        "同一内存库可重复 init_db；查询返回 Row，任务表的 id 自增、title 非空、done 默认 0。",
        "import sqlite3\n\ndef create_connection(path=':memory:'):\n    pass\n\ndef init_db(conn):\n    pass\n",
        [("建库", "conn=create_connection(':memory:'); init_db(conn)", "sqlite_master 能找到 tasks"), ("默认", "conn.execute(\"insert into tasks(title) values ('买书')\")", "done 为 0")],
        [("导入建库", "pytest 导入就出现 taskproj.db", "顶层调用 init_db", "把 I/O 放进函数/入口", "init_db(create_connection())"), ("重复建表失败", "第二次 init_db 报 table exists", "漏 IF NOT EXISTS", "使用幂等 DDL", "CREATE TABLE tasks (...)" )],
    ),
    "D20-create-list": _project_detail(
        "在 taskproj/db.py 增加 add_task 和 list_tasks；用 ? 参数绑定 title，列表按 id ASC 返回 dict/Row 可序列化数据。",
        "依赖 D20-connection 的 tasks 表和 Row 配置；D21 API、D23 CLI 都只调用这些数据层函数，不把 SQL 复制到入口。",
        "运行 python -m pytest -q tests/test_project.py -k 'create or list'；观察两条任务的 id 顺序和中文 title，失败先检查 commit 与参数 tuple。",
        "实现 add_task(conn, title) 与 list_tasks(conn)，拒绝空白标题，新增后 commit，列表稳定按 id 升序。",
        "add_task(' 买书 ') 保存明确标题；list_tasks 返回 id/title/done，插入顺序稳定且没有 SQL 字符串拼接。",
        "def add_task(conn, title):\n    pass\n\ndef list_tasks(conn):\n    pass\n",
        [("新增", "add_task(conn, '买书')", "返回 id=1"), ("列表", "list_tasks(conn)", "包含 title='买书' 且 done=False")],
        [("拼接 SQL", "引号标题导致 SQL 错误或注入", "把 title 拼进 SQL", "使用 ? 和参数 tuple", "f\"INSERT ... '{title}'\""), ("未提交", "同一连接外读不到新增行", "遗漏 conn.commit()", "写入后提交", "conn.execute(...)")],
    ),
    "D20-update-delete": _project_detail(
        "在 taskproj/db.py 增加 complete_task 和 delete_task；用 rowcount 区分真实更新/删除与未知 id，并让调用者得到可判断结果。",
        "依赖 create/list 的事务边界；D21 路由把 False 映射 404，D23 CLI 把 False 映射非零退出码。",
        "运行 python -m pytest -q tests/test_project.py -k 'complete or delete'，分别操作已存在和 999 id；失败先查看 rowcount 是否在 commit 前读取。",
        "实现 complete_task(conn, task_id) 和 delete_task(conn, task_id)，参数化 SQL，成功提交并返回 bool。",
        "已存在 id 完成后 done=True；未知 id 不写入、不误报成功；删除后列表不再包含该 id。",
        "def complete_task(conn, task_id):\n    pass\n\ndef delete_task(conn, task_id):\n    pass\n",
        [("完成", "complete_task(conn, 1)", "True 且 done=True"), ("未知", "delete_task(conn, 999)", "False，列表不变")],
        [("无条件成功", "不存在 id 也返回 True", "忽略 cursor.rowcount", "rowcount == 1 才成功", "conn.execute(...); return True"), ("先删后查", "删除结果不可判断", "没有读取 rowcount", "先保存 rowcount 再 commit", "conn.commit(); return cursor.rowcount")],
    ),
    "D20-db-tests": _project_detail(
        "创建 tests/test_project.py，把 D20 数据层的建表、CRUD、未知 id 和事务边界写成 pytest 断言。",
        "依赖真实 taskproj/db.py；fixture 使用 :memory: 或 tmp_path，每个测试独立，不能共享项目根目录 taskproj.db。",
        "运行 python -m pytest -q tests/test_project.py；先看失败断言中的返回值，再回到 db.py 修一处，禁止用放宽断言掩盖错误。",
        "创建 tests/test_project.py：fixture 初始化隔离连接，测试新增/列表/完成/删除和不存在 id 的确定性结果。",
        "至少四类行为有断言：字段、排序、状态变化、未知 id；测试单独运行和全量运行结果一致。",
        "import pytest\n\n@pytest.fixture\ndef db():\n    # 连接并初始化隔离数据库\n    pass\n\ndef test_task_crud(db):\n    pass\n",
        [("隔离", "pytest -q tests/test_project.py", "每例从空库开始"), ("边界", "complete_task(db, 999)", "断言 False")],
        [("固定数据库", "测试互相污染", "连接 taskproj.db", "fixture 使用 :memory:/tmp_path", "sqlite3.connect('taskproj.db')"), ("CRUD 断言过宽", "错误数据层仍通过", "只 assert result", "断言字段、状态和列表", "assert response")],
    ),
    "D21-app": _project_detail(
        "在 taskproj/api.py 创建 FastAPI app、lifespan 和 get_db 依赖；启动时初始化数据库，请求结束关闭连接。",
        "依赖 D20 的 create_connection/init_db 和 D19 config；D22 TestClient 通过 lifespan 验证启动/清理，不启动真实端口。",
        "运行 python -m pytest -q tests/test_api.py -k health；用 with TestClient(app) 观察 /health=200，失败先查依赖注入和 lifespan 是否传入 FastAPI。",
        "编辑 taskproj/api.py：声明 app=FastAPI(lifespan=lifespan)、GET /health 和可覆盖 get_db，禁止 import 时启动 uvicorn。",
        "TestClient 上下文可进入/退出；/health 返回 {'status':'ok'}，导入模块没有创建不可控的数据库文件。",
        "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    pass\n",
        [("导入", "from taskproj.api import app", "得到 FastAPI"), ("健康", "client.get('/health')", "200 与 status=ok")],
        [("import 启动", "测试卡住或端口被占用", "顶层 uvicorn.run", "只暴露 app", "uvicorn.run(app)"), ("连接不关", "Windows 无法清理临时 DB", "lifespan/依赖没有 close", "在 finally/yield 后关闭", "conn = create_connection(path)")],
    ),
    "D21-schema": _project_detail(
        "在 taskproj/api.py 按 contract.json 写 TaskIn/TaskOut；输入只收 title，输出包含 id/title/done，并保留 422 字段错误。",
        "依赖 contract.json 和 D21 app；D22 API 测试发送真实 JSON，D23 页面按输出字段渲染，不在前端重新猜类型。",
        "运行 python -m pytest -q tests/test_api.py -k 'validation or create'；发送缺 title、空 title、正常 title，比较 422/201 和 detail。",
        "定义 Pydantic 模型和字段约束，绑定 POST response_model/status_code；不在路由中把坏输入静默转成默认任务。",
        "正常 JSON 得到完整输出；缺字段或空白标题在业务写库前被拒绝，错误响应有稳定 detail。",
        "from pydantic import BaseModel\n\nclass TaskIn(BaseModel):\n    title: str\n\nclass TaskOut(BaseModel):\n    id: int\n    title: str\n    done: bool\n",
        [("正常", "TaskIn(title='买书')", "模型可用"), ("缺失", "POST /api/tasks {}", "422 且指出 title")],
        [("输出复用输入", "响应缺 id/done", "只返回 body", "使用 TaskOut 完整构造", "return body"), ("空白放行", "数据库出现空标题", "只校验字段存在", "strip 后拒绝空白", "title: str")],
    ),
    "D21-crud-routes": _project_detail(
        "在 taskproj/api.py 分步接入 GET/POST/PATCH/DELETE /api/tasks；路由只做模型、repo 调用和状态码映射。",
        "依赖 D20 CRUD 与 D21 schema；同一条 route 契约供 D22 TestClient 和 D23 fetch 使用，未知 id 必须统一 404。",
        "运行 python -m pytest -q tests/test_api.py -k 'tasks'，按创建、列表、完成、删除顺序执行；失败看响应状态、detail 和数据库行。",
        "实现四类路由：创建 201、列表 200、完成 200、删除 204/稳定响应；不存在 id raise HTTPException(404)。",
        "HTTP 状态码、JSON 字段、数据库状态和错误 detail 与 contract.json 一致；没有重复 SQL 或 traceback 泄漏。",
        "from fastapi import APIRouter\nrouter = APIRouter(prefix='/api')\n\n@router.get('/tasks')\ndef list_tasks():\n    pass\n",
        [("创建", "POST /api/tasks {'title':'买书'}", "201/task"), ("未知", "PATCH /api/tasks/999", "404/detail")],
        [("全返回 200", "客户端无法区分创建/失败", "没有状态码契约", "按 contract 设置 201/404", "return {'error': ...}"), ("绕过数据层", "API 与 CLI 行为不一致", "路由内直接 SQL", "只调用 db 函数", "conn.execute(...)")],
    ),
    "D21-static": _project_detail(
        "在 taskproj/api.py 挂载 taskproj/static 为 /，保留 /api 路由优先级；让 GET / 能找到后续 D23 的 index.html。",
        "依赖 FastAPI app 和目录结构；D23 继续编辑同一个 static/index.html，D24 从浏览器检查根路径而不是只测 JSON。",
        "运行 python -m pytest -q tests/test_api.py -k 'root or static'，确认 GET / 为 200/HTML、GET /api/tasks 仍返回 JSON；失败检查 mount 路径和目录存在性。",
        "创建 StaticFiles(directory='taskproj/static', html=True) 并 mount('/', ...)，先保留 API 路由注册；不要用静态首页吞掉 /api。",
        "根路径返回 HTML，API 路径继续命中 FastAPI；缺静态目录时错误在启动/测试中明确暴露。",
        "from fastapi.staticfiles import StaticFiles\n\n# app 已在本文件创建\n# app.mount('/', StaticFiles(directory='taskproj/static', html=True), name='static')\n",
        [("根路径", "client.get('/')", "HTML 200"), ("API", "client.get('/api/tasks')", "JSON 200")],
        [("先 mount /", "所有 API 变成 HTML/404", "静态路由遮蔽 API", "先注册 API 并检查顺序", "app.mount('/', static_app)"), ("cwd 假设", "换目录找不到 static", "使用相对 cwd", "以包文件位置构造路径", "directory='static'")],
    ),
    "D22-db-fixtures": _project_detail(
        "在 tests/test_project.py 把隔离 DB fixture 接到真实 CRUD，并将连接清理放进 fixture 的 yield 后半段。",
        "依赖 D20 db.py；D22 API fixture 会复用同一隔离原则，但每个测试仍应拥有独立数据和 override。",
        "运行 python -m pytest -q tests/test_project.py，连续重复两次；结果与临时目录无关且没有 taskproj.db 残留。",
        "完善 db fixture：创建 tmp_path 数据库、init_db、yield connection，finally close；测试不得读取当前工作目录。",
        "每个测试从空 tasks 表开始；异常测试结束后连接关闭，临时文件可删除。",
        "import pytest\n\n@pytest.fixture\ndef db(tmp_path):\n    conn = None\n    try:\n        yield conn\n    finally:\n        if conn:\n            conn.close()\n",
        [("空库", "len(list_tasks(db))", "0"), ("清理", "测试结束删除 tmp_path", "没有锁文件")],
        [("fixture scope 过大", "后一个测试看到前一个任务", "module/session 共享连接", "保持默认 function scope", "@pytest.fixture(scope='session')"), ("finally 缺失", "文件被锁或资源泄漏", "yield 后没有 close", "把 close 放 finally", "yield conn")],
    ),
    "D22-api-tests": _project_detail(
        "创建 tests/test_api.py，用 TestClient 覆盖 health、列表、新增、完成、删除的主流程，并用 app lifespan 上下文。",
        "依赖 D21 app/schema/routes 与 D20 db；测试通过 dependency_overrides 注入临时连接，不能启动 8784 或真实数据库。",
        "运行 python -m pytest -q tests/test_api.py；失败先按 status_code、response.json 和数据库状态定位，不把 assert response 当验收。",
        "建立 app/db fixture，使用 with TestClient(app) 请求真实路由；逐条断言状态码、字段和状态变化。",
        "API 测试离线稳定，主流程能证明创建数据最终被列表、完成、删除观察到。",
        "from fastapi.testclient import TestClient\n\ndef test_task_flow(app):\n    with TestClient(app) as client:\n        pass\n",
        [("健康", "client.get('/health')", "200"), ("主流程", "POST 后 GET/PATCH/DELETE", "每步状态和字段符合契约")],
        [("JSON 用 data", "422 或 body 为空", "client.post(data=...)", "使用 json=payload", "client.post('/api/tasks', data=payload)"), ("连接真实库", "测试顺序互相污染", "fixture 未覆盖 get_db", "override 并清理", "app.dependency_overrides[get_db] = real")],
    ),
    "D22-api-errors": _project_detail(
        "在 tests/test_api.py 增加空标题、缺字段、未知 id、重复删除的回归，锁定 422/404 和安全 detail。",
        "依赖 contract.json 的错误表和 D21 路由；前端只展示后端错误，测试因此检查真实 JSON 而不是猜测文字。",
        "运行 python -m pytest -q tests/test_api.py -k 'error or invalid or missing'；每个失败输入只断言约定字段和状态码。",
        "为每个边界构造请求与断言：验证不写库、detail 稳定且不含 traceback、重复删除不会伪造成功。",
        "错误路径状态码可预测，坏输入不会污染 tasks 表；错误信息只包含面向用户的安全内容。",
        "def test_invalid_task(client):\n    response = client.post('/api/tasks', json={'title': '   '})\n    assert response.status_code == 422\n",
        [("空白", "POST json={'title':'  '}", "422"), ("未知", "GET /api/tasks/999", "404/detail")],
        [("异常吞掉", "坏输入返回 200", "except Exception return {}", "保留 HTTPException/422", "return {}"), ("泄露内部信息", "detail 含文件路径/SQL", "直接 str(exc)", "使用固定安全 detail", "detail=str(exc)")],
    ),
    "D22-acceptance": _project_detail(
        "把 contract、数据层和 API 测试连成公开验收入口，确保从空临时数据库走完 task-manager 主流程。",
        "依赖 tests/test_project.py、tests/test_api.py 和前序文件；D24 会从空 workspace 重跑同一命令，不接受只在旧数据库上通过。",
        "运行 python -m pytest -q；失败按测试文件和第一条断言定位，先修根因再重跑全量。",
        "补充 acceptance 测试与 pytest 配置，覆盖 contract.json 可解析、15 个项目产物存在和 CRUD/API 主流程。",
        "公开命令一次通过，失败输出能定位到契约、数据层、API 或文件缺失，而不是隐藏在脚本中。",
        "def test_acceptance():\n    # 按 contract 与真实 workspace 逐项断言\n    pass\n",
        [("空库", "pytest -q --basetemp <tmp>", "从空临时目录通过"), ("全量", "python -m pytest -q", "无网络且全绿")],
        [("只测 happy path", "空标题/未知 id 回归缺失", "acceptance 没有错误矩阵", "补 422/404/事务断言", "assert response.status_code == 200"), ("硬编码 cwd", "换目录测试失败", "路径写死", "使用 tmp_path 和项目根定位", "Path('taskproj.db')")],
    ),
    "D23-cli-parser": _project_detail(
        "在 taskproj/cli.py 用 argparse 接入 add/list 子命令，复用 config.database_path 和 db 函数，入口支持 python -m taskproj.cli。",
        "依赖 D19 config、D20 db 和 D18 API/动作契约；CLI 的 stdout/exit code 与 API 状态含义相同但不是 HTTP。",
        "运行 python -m taskproj.cli --help、add 买书、list；失败先看 argparse 的 argv、数据库路径和 stdout 是否为稳定文本。",
        "定义 build_parser、main(argv=None) 和 add/list 子命令；解析后 dispatch 到函数，不在 import 时执行。",
        "--help 有子命令；add 输出新 id，list 输出 title/done；main 返回可用于 SystemExit 的整数。",
        "import argparse\n\ndef build_parser():\n    parser = argparse.ArgumentParser()\n    return parser\n\ndef main(argv=None):\n    return 0\n",
        [("帮助", "main(['--help'])", "显示 add/list"), ("解析", "main(['add', '买书'])", "进入 add handler")],
        [("直接读 sys.argv", "测试无法注入参数", "parser 与执行耦合", "main(argv=None) 显式传参", "sys.argv[1:]"), ("import 执行", "pytest 收集就打印帮助", "顶层 main()", "放在 __name__ 守卫", "main()")],
    ),
    "D23-cli-mutate": _project_detail(
        "在 taskproj/cli.py 增加 done/rm 子命令，复用数据层 rowcount 结果，把未知 id 转成 stderr 和非零退出码。",
        "依赖 D23 parser 和 D20 complete/delete；runbook 会把 CLI 与 API/网页做同一主流程比较。",
        "运行 python -m taskproj.cli done 1、rm 1、rm 999；检查 stdout、stderr 和 returncode，不能把错误打印到 stdout 后返回 0。",
        "实现 done/rm handler 和错误映射：成功返回 0，未知 id 返回 1 或契约规定非零，并清晰提示。",
        "CLI 成功改变数据库；未知 id 不静默成功，shell 能依靠退出码停止后续命令。",
        "def run_done(task_id):\n    pass\n\ndef run_remove(task_id):\n    pass\n",
        [("完成", "python -m taskproj.cli done 1", "returncode=0"), ("错误", "python -m taskproj.cli rm 999", "stderr 有提示且非零")],
        [("错误写 stdout", "管道把错误当数据", "print 默认 stdout", "使用 print(..., file=sys.stderr)", "print('not found')"), ("退出码 0", "脚本继续执行", "异常被吞掉", "返回非零并由入口 SystemExit", "except Exception: return 0")],
    ),
    "D23-html-structure": _project_detail(
        "编辑 taskproj/static/index.html，先完成可访问的标题、输入框、add/list/complete/delete 控件和空状态区域。",
        "依赖 contract.json 的字段和动作；D23-html-fetch 再在同一文件加入 fetch，不让 JS 经验替代 Python API 契约。",
        "用浏览器或静态检查确认每个控件有 label/id、按钮有 type、任务列表有可更新容器；失败看元素选择器和可访问名称。",
        "创建 HTML 骨架：h1、form/input、button、ul#tasks、空状态和错误区域；暂不把所有交互塞成一段脚本。",
        "页面结构能被键盘和测试定位；没有选择题，字段名与 API contract 一致。",
        "<!doctype html>\n<h1>Task manager</h1>\n<form id=\"add-form\"><label for=\"title\">标题</label><input id=\"title\" name=\"title\"></form>\n<ul id=\"tasks\"></ul>\n",
        [("结构", "document.querySelector('#add-form')", "表单存在"), ("空态", "没有任务时渲染 #empty", "用户知道列表为空")],
        [("无 label", "键盘用户无法理解输入", "只有 placeholder", "添加 for/id label", "<input placeholder='标题'>"), ("按钮默认提交", "点击完成刷新页面", "button 未写 type", "非表单按钮写 type=button", "<button>完成</button>")],
    ),
    "D23-html-fetch": _project_detail(
        "在 taskproj/static/index.html 分步加入 fetchTasks/addTask/toggleTask/deleteTask，让 DOM 与四条 API 路由同步。",
        "依赖 D21 API、contract.json 和上一节 DOM id；JS 只发送/展示后端结果，错误文字来自响应，不在前端另造业务规则。",
        "启动 uvicorn 后打开 /，执行新增、完成、删除并刷新；失败查看 Network method/path/body、响应状态和 DOM 更新顺序。",
        "实现 GET 初始加载、POST 表单、PATCH 完成、DELETE 删除；每个请求 await response.json 并处理非 2xx。",
        "页面能完成完整 CRUD；网络错误显示后端/浏览器可观察信息，按钮不会重复提交或把失败渲染成成功。",
        "async function loadTasks() {\n  const response = await fetch('/api/tasks');\n  if (!response.ok) throw new Error(await response.text());\n  return response.json();\n}\n",
        [("加载", "打开 /", "GET 列表并渲染"), ("新增", "填写标题提交", "POST 成功后列表出现任务")],
        [("未 await", "页面显示 Promise 或空列表", "直接渲染 fetch 返回值", "await response.json()", "const data = response.json()"), ("忽略 ok", "404 也显示成功", "只调用 json", "先检查 response.ok，保留后端错误", "return response.json()")],
    ),
    "D24-rebuild": _project_detail(
        "在 docs/runbook.md 写从空目录创建 venv、editable 安装、生成临时数据库和运行测试的顺序，不依赖开发机残留。",
        "依赖 README、pyproject 和 contract；这是一份 Python 工程重建证据，网页/CLI 只是后续入口，不可跳过安装和测试。",
        "复制命令到新的临时目录执行 python -m pytest -q；每一步记录命令、cwd、预期输出和失败排查路径。",
        "编辑 docs/runbook.md，按编号写 Python 3.11+、venv、pip install -e ., pytest、数据库和清理步骤。",
        "新环境可从零得到可导入包并跑过公开验收；命令中的文件和模块都真实存在。",
        "# 从空目录开始\npython -m venv .venv\npython -m pip install -e .\npython -m pytest -q\n",
        [("安装", "python -m pip install -e .", "包可导入"), ("验收", "python -m pytest -q", "测试通过")],
        [("跳过安装", "本机能跑换环境失败", "依赖只存在于全局", "runbook 明确 editable install", "python -m pytest -q"), ("cwd 错", "找不到 pyproject", "从错误目录执行", "每步标注项目根", "cd ..")],
    ),
    "D24-integrate": _project_detail(
        "在 docs/runbook.md 记录 API、CLI、网页三入口的启动/操作/预期输出，并指出同一 task 数据如何流过三层。",
        "依赖 D21 api.py、D23 cli.py/static/index.html 和 D22 acceptance；JS 交互只作展示，业务真相仍来自 Python API/SQLite。",
        "按 runbook 先跑 pytest，再启动 uvicorn，最后执行 CLI 与浏览器主流程；分别记录端口、stdout、HTTP 和 DOM 证据。",
        "补充三入口集成步骤：uvicorn taskproj.api:app、python -m taskproj.cli、浏览器 GET /；注明停止服务和临时 DB 清理。",
        "三种入口都能创建、列出、完成、删除同一类任务，异常路径能定位到 API/CLI/网页边界。",
        "# API\npython -m uvicorn taskproj.api:app\n# CLI\npython -m taskproj.cli list\n",
        [("API", "curl http://127.0.0.1:8000/api/tasks", "JSON 列表"), ("CLI", "python -m taskproj.cli list", "文本列表")],
        [("端口未停", "下一次启动 address in use", "runbook 没写 cleanup", "记录 Ctrl+C/进程清理", "uvicorn ... &"), ("三套规则", "入口结果不一致", "各入口重复业务逻辑", "共享 db/service/API 契约", "if cli_title: ...")],
    ),
    "D24-artifacts": _project_detail(
        "在 docs/runbook.md 按 contract 和课程产物清单核对 15 个真实文件、各文件责任、依赖关系和最后验证命令。",
        "依赖 D18-D23 的工作区文件；清单是交付证据，不是另一个模板项目，缺文件时必须回到对应小节补齐。",
        "运行 python -m pytest -q 并逐个 Test-Path/Path.exists 检查；记录缺失文件、错误路径和对应课程小节。",
        "写出 15 文件表：路径、由哪节创建/修改、被哪节使用、如何验证；同时列出不应提交的数据库/缓存文件。",
        "清单与真实 workspace 一致，15 个产物都能追溯到契约和测试，临时状态不会冒充交付文件。",
        "# docs/runbook.md\n| 文件 | 责任 | 验证 |\n| taskproj/db.py | SQLite 数据层 | pytest |\n",
        [("存在", "Path(path).exists()", "15 个路径均存在"), ("追溯", "查看 workspace_deps", "依赖链无断点")],
        [("清单虚构", "验收找不到文件", "手写路径未核对", "用 Path.exists 校验", "taskproj/database.py"), ("提交缓存", "环境相关数据污染", "把 taskproj.db 列为产物", "排除 DB/pycache", "git add taskproj.db")],
    ),
    "D24-review": _project_detail(
        "创建 docs/review.md，复盘需求到验收的证据、一次真实失败及修正、可复用边界和 Python 学习上的下一步。",
        "依赖 docs/runbook.md、tests 和 contract；复盘不是泛泛总结，要引用实际命令、错误输出类型和修正文件。",
        "运行最终 pytest、静态首页检查和 CLI smoke test，把通过命令与未解决风险写入 review.md；不把“已完成”当作证据。",
        "写 docs/review.md 的 evidence、failure/fix、tradeoffs、next steps 四段，引用真实文件和命令，不重复粘贴大段代码。",
        "读者能从复盘还原为什么这样分层、哪次失败暴露了边界、如何继续改进，并能区分已验证与风险。",
        "# docs/review.md\n## Evidence\n- python -m pytest -q\n## Failure and fix\n- 记录真实现象与文件修正\n",
        [("证据", "pytest -q", "记录通过数量/命令"), ("失败", "回看第一条失败", "写现象、原因、修正和复测")],
        [("只有感想", "无法复核交付", "没有命令/文件证据", "引用可重复验证", "项目很好"), ("隐藏风险", "下一位误以为无风险", "只写通过", "列出未覆盖项和边界", "全部完成")],
    ),
})


SECTION_EXAMPLES: dict[str, list[tuple[str, str]]] = {
    "D08-pathlib": [("from pathlib import Path\nroot = Path('workspace')\nfile = root / 'notes.txt'\nprint(file.name, file.suffix)", "notes.txt .txt"), ("from pathlib import Path\nroot = Path('tmp')\nroot.mkdir()\n(root / 'main.py').write_text('x = 1', encoding='utf-8')\n(root / 'readme.txt').write_text('docs', encoding='utf-8')\nprint([p.name for p in sorted(root.glob('*.py'))])", "['main.py']")],
    "D08-utf8": [("from pathlib import Path\np = Path('note.txt')\np.write_text('你好 🌱', encoding='utf-8')\nprint(p.read_text(encoding='utf-8'))", "你好 🌱"), ("from pathlib import Path\np = Path('note.txt')\np.write_text('第一行\\n第二行', encoding='utf-8')\nprint(len(p.read_text(encoding='utf-8').splitlines()))", "2")],
    "D08-json-read": [("import json\ndata = json.loads('{\"title\": \"买书\", \"done\": false}')\nprint(data['title'], data['done'])", "买书 False"), ("import json\ntry:\n    json.loads('{bad}')\nexcept json.JSONDecodeError:\n    print('JSON 无法解析')", "JSON 无法解析")],
    "D08-json-report": [("import json\nitems = [{'done': True}, {'done': False}, {'done': False}]\nreport = {'done': sum(item['done'] for item in items), 'open': sum(not item['done'] for item in items)}\nprint(json.dumps(report, sort_keys=True))", '{"done": 1, "open": 2}'), ("import json\nreport = {'done': 0, 'open': 0}\nprint(json.dumps(report, ensure_ascii=False, indent=2))", '{\n  "done": 0,\n  "open": 0\n}')],
    "D09-parser": [("import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--limit', type=int, default=20)\nprint(parser.parse_args(['--limit', '3']).limit)", "3"), ("import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('title')\nprint(parser.parse_args(['买书']).title)", "买书")],
    "D09-subcommands": [("import argparse\nparser = argparse.ArgumentParser()\nsub = parser.add_subparsers(dest='command', required=True)\nsub.add_parser('list')\nprint(parser.parse_args(['list']).command)", "list"), ("import argparse\nparser = argparse.ArgumentParser()\nsub = parser.add_subparsers(dest='command', required=True)\nadd = sub.add_parser('add')\nadd.add_argument('title')\nprint(parser.parse_args(['add', '买书']).title)", "买书")],
    "D09-errors": [("import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--count', type=int)\nprint(parser.parse_args(['--count', '2']).count)", "2"), ("import argparse\nparser = argparse.ArgumentParser()\ntry:\n    parser.parse_args(['--count', 'x'])\nexcept SystemExit as error:\n    print(error.code != 0)", "True")],
    "D09-entry": [("def main(argv=None):\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())\nelse:\n    print('import safe')", ""), ("def main(argv=None):\n    return 3\n\nprint(main([]))", "3")],
    "D10-env": [("import os\nprint(os.environ.get('TASKPROJ_MODE', 'dev'))", "dev"), ("import os\nos.environ['TASKPROJ_MODE'] = 'test'\nprint(os.environ.get('TASKPROJ_MODE'))", "test")],
    "D10-convert": [("def as_bool(value):\n    normalized = value.strip().lower()\n    if normalized in {'true', '1'}: return True\n    if normalized in {'false', '0'}: return False\n    raise ValueError(value)\nprint(as_bool('false'))", "False"), ("try:\n    print(int('not-a-number'))\nexcept ValueError:\n    print('配置整数无效')", "配置整数无效")],
    "D10-dotenv": [("from pathlib import Path\ndef read_env(path):\n    values = {}\n    for line in Path(path).read_text(encoding='utf-8').splitlines():\n        line = line.strip()\n        if line and not line.startswith('#'):\n            key, value = line.split('=', 1)\n            values[key.strip()] = value.strip()\n    return values\npath = Path('app.env')\npath.write_text('# local config\\nMODE=test\\n', encoding='utf-8')\ntry:\n    print(read_env(path))\nfinally:\n    path.unlink()", "{'MODE': 'test'}"), ("line = 'NAME=task=one'\nprint(line.split('=', 1))", "['NAME', 'task=one']")],
    "D10-config": [("from dataclasses import dataclass\n@dataclass\nclass Settings:\n    mode: str = 'dev'\n    port: int = 8000\nprint(Settings())", "Settings(mode='dev', port=8000)"), ("from dataclasses import dataclass\n@dataclass\nclass Settings:\n    mode: str\n    port: int\nprint(Settings('test', 9000).port)", "9000")],
    "D11-logger": [("import logging\nlogger = logging.getLogger('taskproj')\nlogger.handlers.clear()\nlogger.addHandler(logging.NullHandler())\nprint(len(logger.handlers))", "1"), ("import logging\nlogger = logging.getLogger('taskproj.once')\nlogger.handlers.clear()\nlogger.addHandler(logging.NullHandler())\nlogger.addHandler(logging.NullHandler())\nprint(len(logger.handlers))", "2")],
    "D11-format": [("import logging\nrecord = logging.LogRecord('taskproj', logging.INFO, '', 0, 'created %s', ('T1',), None)\nprint(logging.Formatter('%(levelname)s:%(name)s:%(message)s').format(record))", "INFO:taskproj:created T1"), ("import logging\nrecord = logging.LogRecord('taskproj', logging.ERROR, '', 0, 'failed', (), None)\nprint(logging.Formatter('%(levelname)s %(message)s').format(record))", "ERROR failed")],
    "D11-stream": [("import logging, io\nstream = io.StringIO()\nhandler = logging.StreamHandler(stream)\nhandler.setLevel(logging.WARNING)\nlogger = logging.getLogger('stream-demo')\nlogger.handlers.clear(); logger.propagate = False; logger.addHandler(handler); logger.setLevel(logging.INFO)\nlogger.info('hidden'); logger.warning('shown')\nprint(stream.getvalue().strip())", "shown"), ("import logging, io\nstream = io.StringIO()\nhandler = logging.StreamHandler(stream)\nlogger = logging.getLogger('level-demo')\nlogger.handlers.clear(); logger.propagate = False; logger.addHandler(handler)\nlogger.error('disk full')\nprint('disk full' in stream.getvalue())", "True")],
    "D11-file": [("import logging, tempfile\nfrom pathlib import Path\npath = Path(tempfile.mkstemp()[1])\nhandler = logging.FileHandler(path, encoding='utf-8')\nlogger = logging.getLogger('file-demo'); logger.handlers.clear(); logger.addHandler(handler); logger.warning('保存')\nhandler.close(); logger.removeHandler(handler)\nprint(path.read_text(encoding='utf-8').strip().endswith('保存'))", "True"), ("import logging, io\nstream = io.StringIO(); handler = logging.StreamHandler(stream)\nlogger = logging.getLogger('file-demo-2'); logger.handlers.clear(); logger.propagate = False; logger.setLevel(logging.INFO); logger.addHandler(handler); logger.info('one')\nprint(stream.getvalue().count('one'))", "1")],
    "D12-request": [("from urllib.request import Request\nrequest = Request('https://example.invalid/tasks', method='GET')\nprint(request.method, request.full_url)", "GET https://example.invalid/tasks"), ("from urllib.request import Request\nrequest = Request('https://example.invalid/tasks', headers={'Accept': 'application/json'})\nprint(request.get_header('Accept'))", "application/json")],
    "D12-response": [("import json\nstatus = 200\nbody = b'{\"items\": []}'\nif 200 <= status < 300:\n    print(json.loads(body.decode('utf-8')))", "{'items': []}"), ("import json\ntry:\n    json.loads(b'{bad}'.decode('utf-8'))\nexcept json.JSONDecodeError:\n    print('bad json')", "bad json")],
    "D12-post": [("import json\nfrom urllib.request import Request\nbody = json.dumps({'title': '买书'}, ensure_ascii=False).encode('utf-8')\nrequest = Request('https://example.invalid/tasks', data=body, method='POST', headers={'Content-Type': 'application/json'})\nprint(request.method, json.loads(request.data.decode('utf-8')))", "POST {'title': '买书'}"), ("import json\nbody = json.dumps({'done': False}).encode('utf-8')\nprint(body.decode('utf-8'))", '{"done": false}')],
    "D12-timeout": [("def fake_open(request, timeout):\n    return request.full_url, timeout\nprint(fake_open(type('Request', (), {'full_url': '/slow'})(), timeout=3))", "('/slow', 3)"), ("calls = []\ndef fake_open(request, timeout):\n    calls.append(timeout)\n    raise TimeoutError('slow')\ntry:\n    fake_open(None, 2)\nexcept TimeoutError:\n    print(len(calls))", "1")],
    "D13-app": [("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\nprint(health())", "{'status': 'ok'}"), ("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/version')\ndef version():\n    return {'version': 1}\nprint(version())", "{'version': 1}")],
    "D13-route": [("def get_task(task_id: int, limit: int = 20):\n    return {'id': task_id, 'limit': limit}\nprint(get_task(7, 3))", "{'id': 7, 'limit': 3}"), ("try:\n    int('not-int')\nexcept ValueError:\n    print('422 输入错误')", "422 输入错误")],
    "D13-response": [("from pydantic import BaseModel\nclass TaskOut(BaseModel):\n    id: int\n    title: str\n    done: bool = False\nprint(TaskOut(id=1, title='买书').model_dump())", "{'id': 1, 'title': '买书', 'done': False}"), ("from pydantic import BaseModel\nclass TaskOut(BaseModel):\n    id: int\n    title: str\nprint(TaskOut(id=1, title='买书').title)", "买书")],
    "D13-lifecycle": [("events = []\nevents.append('start')\ntry:\n    events.append('request')\nfinally:\n    events.append('stop')\nprint(events)", "['start', 'request', 'stop']"), ("from contextlib import contextmanager\n@contextmanager\ndef resource():\n    print('open')\n    try: yield\n    finally: print('close')\nwith resource(): print('use')", "open\nuse\nclose")],
    "D14-model": [("from pydantic import BaseModel\nclass TaskIn(BaseModel):\n    title: str\n    priority: int = 0\nprint(TaskIn(title='买书'))", "title='买书' priority=0"), ("from pydantic import BaseModel, ValidationError\nclass TaskIn(BaseModel):\n    title: str\ntry: TaskIn()\nexcept ValidationError: print('title required')", "title required")],
    "D14-service": [("def create_task(repo, title):\n    title = title.strip()\n    if not title: raise ValueError('empty')\n    return repo.add(title)\nprint(create_task(type('Repo', (), {'add': lambda self, x: x})(), ' 买书 '))", "买书"), ("try:\n    title = '  '.strip()\n    if not title: raise ValueError('empty')\nexcept ValueError as error:\n    print(error)", "empty")],
    "D14-errors": [("from fastapi import HTTPException\nerror = HTTPException(status_code=404, detail='任务不存在')\nprint(error.status_code, error.detail)", "404 任务不存在"), ("from fastapi import HTTPException\ntry: raise HTTPException(422, detail='标题不能为空')\nexcept HTTPException as error: print(error.status_code)", "422")],
    "D14-deps": [("def get_repo(): return 'real'\ndef list_tasks(repo): return repo\nprint(list_tasks(get_repo()))", "real"), ("fake = 'test'\ndef list_tasks(repo): return repo\nprint(list_tasks(fake))", "test")],
    "D15-assert": [("def add_tax(price): return price * 113 // 100\nassert add_tax(100) == 113\nprint('passed')", "passed"), ("def add_tax(price): return price * 113 // 100\nassert add_tax(0) == 0\nprint('zero covered')", "zero covered")],
    "D15-fixture": [("from pathlib import Path\nfrom tempfile import TemporaryDirectory\nwith TemporaryDirectory() as folder:\n    path = Path(folder) / 'note.txt'\n    path.write_text('你好', encoding='utf-8')\n    print(path.read_text(encoding='utf-8'))", "你好"), ("from pathlib import Path\nfrom tempfile import TemporaryDirectory\nwith TemporaryDirectory() as folder:\n    print(list(Path(folder).iterdir()))", "[]")],
    "D15-mock": [("from unittest.mock import Mock\nopener = Mock(return_value='ok')\nprint(opener('/tasks', timeout=2))\nopener.assert_called_once_with('/tasks', timeout=2)", "ok"), ("import sys\nfrom unittest.mock import patch\ndef measure(value):\n    return len(value)\nwith patch.object(sys.modules[__name__], 'measure', return_value=99):\n    print(measure('abc'))\nprint(measure('abc'))", "99\n3")],
    "D15-api": [("response = type('Response', (), {'status_code': 200, 'json': lambda self: {'status': 'ok'}})()\nprint(response.status_code, response.json())", "200 {'status': 'ok'}"), ("response = type('Response', (), {'status_code': 404, 'json': lambda self: {'detail': 'missing'}})()\nprint(response.status_code, response.json()['detail'])", "404 missing")],
    "D16-connect": [("import sqlite3\nconn = sqlite3.connect(':memory:')\nprint(conn.execute('select 1').fetchone())\nconn.close()", "(1,)"), ("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.close()\ntry: conn.execute('select 1')\nexcept sqlite3.ProgrammingError: print('closed')", "closed")],
    "D16-schema": [("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('create table tasks (id integer primary key, title text not null, done integer not null default 0)')\nprint(conn.execute(\"pragma table_info(tasks)\").fetchall()[1][1])", "title"), ("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('create table tasks (id integer primary key, done integer not null default 0)')\nconn.execute('insert into tasks default values')\nprint(conn.execute('select done from tasks').fetchone()[0])", "0")],
    "D16-crud": [("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('create table tasks (title text)')\nconn.execute('insert into tasks values (?)', ('买书',))\nprint(conn.execute('select title from tasks').fetchone()[0])", "买书"), ("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('create table tasks (title text)')\ncur = conn.execute('insert into tasks values (?)', ('a',))\nprint(cur.rowcount)", "1")],
    "D16-transaction": [("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('create table tasks (title text)')\ntry:\n    with conn:\n        conn.execute('insert into tasks values (?)', ('ok',))\n        raise ValueError('rollback')\nexcept ValueError: pass\nprint(conn.execute('select count(*) from tasks').fetchone()[0])", "0"), ("import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('create table tasks (title text)')\nwith conn: conn.execute('insert into tasks values (?)', ('saved',))\nprint(conn.execute('select count(*) from tasks').fetchone()[0])", "1")],
    "D17-coroutine": [("import asyncio\nasync def value(): return 3\nprint(asyncio.run(value()))", "3"), ("import asyncio\nasync def steps():\n    print('before')\n    await asyncio.sleep(0)\n    print('after')\nasyncio.run(steps())", "before\nafter")],
    "D17-gather": [("import asyncio\nasync def read(name):\n    await asyncio.sleep(0)\n    return name\nasync def main():\n    return await asyncio.gather(read('a'), read('b'))\nprint(asyncio.run(main()))", "['a', 'b']"), ("import asyncio\nasync def main(): return await asyncio.gather(asyncio.sleep(0, result=2), asyncio.sleep(0, result=1))\nprint(asyncio.run(main()))", "[2, 1]")],
    "D17-timeout": [("import asyncio\nasync def main():\n    return await asyncio.wait_for(asyncio.sleep(0, result='ok'), timeout=1)\nprint(asyncio.run(main()))", "ok"), ("import asyncio\nasync def main():\n    try: await asyncio.wait_for(asyncio.sleep(1), timeout=0)\n    except asyncio.TimeoutError: return 'timed out'\nprint(asyncio.run(main()))", "timed out")],
    "D17-boundary": [("import asyncio\nasync def work(): return 'done'\nprint(asyncio.run(work()))", "done"), ("import asyncio\nasync def work(): raise ValueError('bad')\ntry: asyncio.run(work())\nexcept ValueError as error: print(error)", "bad")],
    "D18-scope": [("# docs/requirements.md\n## 用户故事\n- Given 新建任务，When 查看列表，Then 列表显示该任务。", "requirements.md 记录 add -> list"), ("# docs/requirements.md\n## 输入边界\n- 空标题：拒绝并说明原因。\n- 未知 id：返回资源不存在。", "requirements.md 记录空标题与未知 id")],
    "D18-acceptance": [("## 场景：任务主流程\n1. POST /api/tasks {title}\n2. GET /api/tasks 能看到该任务\n3. PATCH /api/tasks/{id} 后 done=true\n4. DELETE 后列表不再出现", "四步场景可逐条验收"), ("## 失败场景\n| 输入 | 预期 |\n| 空标题 | 422 |\n| 未知 id | 404 |", "错误矩阵包含 422 与 404")],
    "D18-data-contract": [("{\n  \"task\": {\n    \"input\": {\"title\": \"string\"},\n    \"output\": {\"id\": \"integer\", \"done\": \"boolean\"}\n  }\n}", '{"task": {"input": {"title": "string"}, "output": {"id": "integer", "done": "boolean"}}}'), ("{\n  \"errors\": {\"missing\": 404, \"invalid\": 422}\n}", "JSON 错误码契约可解析")],
    "D18-api-contract": [("{\n  \"routes\": [\n    {\"method\": \"POST\", \"path\": \"/api/tasks\", \"status\": 201},\n    {\"method\": \"GET\", \"path\": \"/\", \"status\": 200}\n  ]\n}", "routes 固定 /api/tasks 与 /"), ("{\n  \"errors\": {\"missing\": 404, \"invalid\": 422}\n}", "错误契约固定 404 与 422")],
    "D19-pyproject": [("[project]\nname = \"task-manager\"\nrequires-python = \">=3.11\"", "项目元数据可解析"), ("[tool.pytest.ini_options]\ntestpaths = [\"tests\"]", "pytest 从 tests 发现用例")],
    "D19-package": [("# taskproj/__init__.py\n__version__ = '0.1.0'\n\n__all__ = ['__version__']", "package exports __version__"), ("# taskproj/__init__.py\n__version__ = '0.1.0'\n# Importing this module performs no database or network I/O", "import is side-effect free")],
    "D19-config": [("# taskproj/config.py\nfrom pathlib import Path\n\ndef database_path(env, root):\n    return root / env.get('TASKPROJ_DB', 'taskproj.db')", "default path is root/taskproj.db"), ("# taskproj/config.py\nfrom pathlib import Path\n\ndef database_path(env, root):\n    return root / env['TASKPROJ_DB']\n\n# An explicit environment value wins over the default", "TASKPROJ_DB controls the database path")],
    "D19-main": [("# taskproj/main.py\nfrom .api import app\n\ndef main(argv=None):\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())", "importable main with guarded entry point"), ("# taskproj/main.py\n\ndef main(argv=None):\n    # Return an exit status; the caller owns process termination\n    return 0", "main returns an integer status")],
    "D19-readme": [("# README.md\n# task-manager\n\npython -m pip install -e .\npython -m pytest -q", "安装、测试命令明确"), ("# README.md\n# 运行\npython -m taskproj.main\n\n# 默认数据库\ntaskproj.db", "入口和数据库路径明确")],
    "D20-connection": [("# taskproj/db.py\nimport sqlite3\n\ndef create_connection(path):\n    connection = sqlite3.connect(path)\n    connection.row_factory = sqlite3.Row\n    return connection", "create_connection owns connect and row_factory"), ("# taskproj/db.py\nSCHEMA = \"CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)\"\n\ndef init_db(connection):\n    connection.execute(SCHEMA)\n    connection.commit()", "init_db is repeatable and commits the schema")],
    "D20-create-list": [("# taskproj/db.py\ndef add_task(connection, title):\n    cursor = connection.execute('INSERT INTO tasks(title) VALUES (?)', (title,))\n    connection.commit()\n    return cursor.lastrowid", "add_task binds title and commits"), ("# taskproj/db.py\ndef list_tasks(connection):\n    rows = connection.execute('SELECT id, title, done FROM tasks ORDER BY id ASC')\n    return [dict(row) for row in rows]", "list_tasks returns stable ordered rows")],
    "D20-update-delete": [("# taskproj/db.py\ndef complete_task(connection, task_id):\n    cursor = connection.execute('UPDATE tasks SET done = 1 WHERE id = ?', (task_id,))\n    connection.commit()\n    return cursor.rowcount == 1", "complete_task reports whether one row changed"), ("# taskproj/db.py\ndef delete_task(connection, task_id):\n    cursor = connection.execute('DELETE FROM tasks WHERE id = ?', (task_id,))\n    connection.commit()\n    return cursor.rowcount == 1", "delete_task does not claim success for an unknown id")],
    "D20-db-tests": [("# tests/test_project.py\ndef test_add_and_list_tasks(db):\n    task_id = db.add_task('买书')\n    assert db.list_tasks() == [{'id': task_id, 'title': '买书', 'done': False}]", "pytest asserts the real data-layer shape"), ("# tests/test_project.py\ndef test_unknown_task_is_not_completed(db):\n    assert db.complete_task(999) is False\n    assert db.list_tasks() == []", "unknown ids leave the isolated database unchanged")],
    "D21-app": [("# taskproj/api.py\nfrom fastapi import FastAPI\n\napp = FastAPI(title='task-manager')\n\n@app.get('/api/health')\ndef health():\n    return {'status': 'ok'}", "GET /api/health returns the health contract"), ("# taskproj/api.py\nfrom contextlib import asynccontextmanager\n\n@asynccontextmanager\nasync def lifespan(app):\n    init_db()\n    yield\n    close_db()", "lifespan initializes before requests and closes afterward")],
    "D21-schema": [("# taskproj/api.py\nfrom pydantic import BaseModel\n\nclass TaskOut(BaseModel):\n    id: int\n    title: str\n    done: bool", "TaskOut fixes id/title/done response fields"), ("# taskproj/api.py\nfrom pydantic import BaseModel\n\nclass TaskIn(BaseModel):\n    title: str\n\n# POST /api/tasks validates TaskIn before writing", "TaskIn rejects missing title with the API validation contract")],
    "D21-crud-routes": [("# taskproj/api.py\n@app.post('/api/tasks', status_code=201)\ndef create_task(payload: TaskIn):\n    return service.create_task(payload)", "POST /api/tasks creates with status 201"), ("# taskproj/api.py\n@app.delete('/api/tasks/{task_id}', status_code=204)\ndef delete_task(task_id: int):\n    if not service.delete_task(task_id):\n        raise HTTPException(status_code=404, detail='任务不存在')", "DELETE maps an unknown id to 404")],
    "D21-static": [("# taskproj/api.py\nfrom fastapi.staticfiles import StaticFiles\n\napp.mount('/', StaticFiles(directory=PACKAGE_ROOT / 'static', html=True), name='static')", "GET / serves taskproj/static/index.html"), ("# taskproj/api.py\n@app.get('/api/tasks')\ndef list_tasks():\n    return service.list_tasks()\n\n# Register /api routes before the static mount", "API JSON routes remain distinct from the HTML mount")],
    "D22-db-fixtures": [("# tests/test_project.py\n@pytest.fixture\ndef db(tmp_path):\n    connection = sqlite3.connect(tmp_path / 'test.db')\n    init_db(connection)\n    yield connection\n    connection.close()", "each test receives a temporary database"), ("# tests/test_project.py\ndef test_fixture_is_empty(db):\n    assert db.list_tasks() == []\n\ndef test_fixture_isolated(db):\n    assert db.list_tasks() == []", "tests do not share task rows")],
    "D22-api-tests": [("# tests/test_api.py\ndef test_create_and_list(client):\n    created = client.post('/api/tasks', json={'title': '买书'})\n    assert created.status_code == 201\n    listed = client.get('/api/tasks')\n    assert listed.json()[0]['title'] == '买书'", "TestClient observes POST 201 then GET data"), ("# tests/test_api.py\ndef test_complete_task(client):\n    task_id = client.post('/api/tasks', json={'title': '学习'}).json()['id']\n    response = client.patch(f'/api/tasks/{task_id}', json={'done': True})\n    assert response.status_code == 200\n    assert response.json()['done'] is True", "PATCH changes done through the real route")],
    "D22-api-errors": [("# tests/test_api.py\ndef test_empty_title_is_rejected(client):\n    response = client.post('/api/tasks', json={'title': '  '})\n    assert response.status_code == 422\n    assert client.get('/api/tasks').json() == []", "422 rejects whitespace without a database row"), ("# tests/test_api.py\ndef test_unknown_id_is_not_found(client):\n    response = client.delete('/api/tasks/999')\n    assert response.status_code == 404\n    assert 'traceback' not in response.text", "404 exposes a safe detail for an unknown id")],
    "D22-acceptance": [("# tests/test_api.py\ndef test_public_acceptance(client):\n    created = client.post('/api/tasks', json={'title': '买书'})\n    assert created.status_code == 201\n    assert client.get('/api/tasks').status_code == 200", "public acceptance covers create and list"), ("# tests/test_api.py\ndef test_public_error_contract(client):\n    assert client.post('/api/tasks', json={}).status_code == 422\n    assert client.delete('/api/tasks/999').status_code == 404", "public acceptance locks 422 and 404")],
    "D23-cli-parser": [("# taskproj/cli.py\ndef build_parser():\n    parser = argparse.ArgumentParser(prog='taskproj')\n    sub = parser.add_subparsers(dest='command', required=True)\n    sub.add_parser('list')\n    return parser", "taskproj list is a required subcommand"), ("# taskproj/cli.py\nadd = sub.add_parser('add')\nadd.add_argument('title')", "taskproj add accepts a title argument")],
    "D23-cli-mutate": [("# taskproj/cli.py\ndef add_command(args, service):\n    task = service.add_task(args.title)\n    return {'stdout': f\"{task['id']} {task['title']}\\n\", 'returncode': 0}", "add returns shell output and code 0"), ("# taskproj/cli.py\ndef delete_command(args, service):\n    if not service.delete_task(args.task_id):\n        return {'stderr': '任务不存在\\n', 'returncode': 1}\n    return {'stdout': 'deleted\\n', 'returncode': 0}", "delete returns stderr and code 1 for an unknown id")],
    "D23-html-structure": [("<!-- taskproj/static/index.html -->\n<label for=\"title\">标题</label>\n<input id=\"title\" name=\"title\" required>\n<form id=\"task-form\"></form>\n<ul id=\"tasks\"></ul>", "index.html contains the task form and list"), ("<!-- taskproj/static/index.html -->\n<button type=\"submit\">新增</button>\n<button type=\"button\" data-action=\"complete\">完成</button>\n<button type=\"button\" data-action=\"delete\">删除</button>", "buttons expose add, complete, and delete actions")],
    "D23-html-fetch": [("// taskproj/static/index.html\nasync function loadTasks() {\n  const response = await fetch('/api/tasks');\n  if (!response.ok) throw new Error(await response.text());\n  return response.json();\n}", "browser GET /api/tasks renders the list"), ("// taskproj/static/index.html\nasync function deleteTask(id) {\n  const response = await fetch(`/api/tasks/${id}`, {method: 'DELETE'});\n  if (!response.ok) throw new Error(await response.text());\n}", "browser DELETE uses the backend error response")],
    "D24-rebuild": [("python -m venv .venv\npython -m pip install -e .\npython -m pytest -q", "从空环境安装并验收"), ("$ Test-Path pyproject.toml\nTrue\n$ Test-Path taskproj\nTrue", "项目配置和包目录均存在")],
    "D24-integrate": [("# API\npython -m uvicorn taskproj.api:app\n# CLI\npython -m taskproj.cli list\n# Browser\nGET /", "三种入口均有启动步骤"), ("# 主流程证据\nPOST -> GET -> PATCH -> DELETE", "四个动作顺序一致")],
    "D24-artifacts": [("| 文件 | 责任 |\n| taskproj/db.py | SQLite 数据层 |\n| taskproj/api.py | FastAPI 路由 |\n| taskproj/static/index.html | 网页入口 |", "三项文件责任可追溯"), ("$ Test-Path taskproj.db\nFalse\n$ Test-Path docs/runbook.md\nTrue", "数据库不属于交付产物，runbook 存在")],
    "D24-review": [("# Evidence\n- python -m pytest -q\n- python -m taskproj.cli list\n- GET /", "复盘引用三条真实证据"), ("## Failure and fix\n- 现象：GET /api/tasks 返回 404\n- 修正：补齐 route contract\n- 复测：passed", "失败、修正、复测均记录")],
}


SECTION_EXAMPLE_NOTES: dict[str, list[str]] = {
    "D08-pathlib": [
        "Path('/tmp') / 'notes.txt' 产生新的 Path 对象，斜杠连接不会改变原对象；suffix 只读取最后扩展名。把目录放进 tmp_path 后，glob('*.txt') 的结果可以稳定断言，换 cwd 也不会偷偷读到项目文件。",
        "relative_to(root) 只有在目标确实位于 root 下时才成功，越界路径会抛 ValueError；这正是边界，而不是应该吞掉的空列表。用 Path.exists 先区分“路径不存在”和“路径存在但不匹配”。",
    ],
    "D08-utf8": [
        "write_text(..., encoding='utf-8') 把中文按明确字节编码保存，read_text 使用同一编码才能还原原字符串；省略 encoding 会把结果交给机器默认设置。测试应同时读回中文和检查文件 bytes，避免只在本机通过。",
        "UTF-8 文件被 latin-1 或错误的本地编码读取时，可能出现乱码而不一定抛异常；因此“能打开”不是正确性的证据。用一个含中文和 emoji 的临时文件比较 round trip，才能看见编码契约。",
    ],
    "D08-json-read": [
        "json.loads 把文本解析成 dict/list 等 Python 对象，但不会替你保证字段存在；data['title'] 和 data.get('title') 对缺字段有不同语义。先捕获 JSONDecodeError，再按 isinstance 检查顶层形状。",
        "JSON 的 true、false、null 会分别变成 True、False、None；Python 字符串里的单引号字典不是合法 JSON。示例应故意传入缺 items 和坏逗号，观察解析错误与契约错误的区别。",
    ],
    "D08-json-report": [
        "统计报告先把记录按状态计数，再用 json.dump 写出普通 dict；sort_keys=True 让同一输入产生稳定文本，indent 便于审阅。报告中的 0 也要保留，因为它说明该类别已被检查。",
        "ensure_ascii=False 只影响中文的呈现，不改变 JSON 数据；写回前应通过临时路径避免覆盖输入。把空记录作为第二个输入，预期得到全为零的报告而不是缺字段。",
    ],
    "D09-parser": [
        "ArgumentParser 将 shell 的字符串参数转换为 Namespace，add_argument 的 dest/type/default 决定处理函数看到的值。parse_args(['--limit','3']) 是离线可重复的输入，不必启动真正命令。",
        "没有声明的参数会由 argparse 写入 stderr 并返回非零退出；这比业务函数收到一串未知字符串更早暴露用法错误。示例同时覆盖默认 limit 和显式 limit，检查 Namespace.limit 的整数类型。",
    ],
    "D09-subcommands": [
        "add_subparsers 把一个入口分成 add/list 等命令，set_defaults(func=...) 让解析结果携带明确分派目标。处理函数只接收已解析的 Namespace，避免再次手工切分 argv。",
        "子命令缺失或名称拼错时，parser 的 usage 和非零退出码是契约的一部分；不能默默选择 list。用两组 argv 比较 func 和参数，能证明分派不是靠 if 字符串猜测。",
    ],
    "D09-errors": [
        "parser.error 会把错误写到 stderr 并以非零状态结束，适合参数层失败；业务层失败也应保留非零返回，不把错误打印后继续返回 0。",
        "stdout 应只放可被管道消费的成功结果，stderr 放用法和失败提示；这个通道区别是 CLI 与普通 print 脚本的关键。子进程测试要分别读取两条流并断言 returncode。",
    ],
    "D09-entry": [
        "main(argv=None) 允许测试直接传入列表，__name__ 守卫只在 python -m 运行时调用 SystemExit；import 模块不应突然解析测试进程的 argv。",
        "subprocess.run 能观察真实入口的 stdout、stderr 和 returncode，补上只调用函数测试看不到的打包边界。把空 argv 与完整命令各跑一次，确认默认行为明确。",
    ],
    "D10-env": [
        "os.environ.get 返回字符串或默认值，读取配置时要把环境边界集中在一个函数中；不要让业务代码到处读 os.environ。空字符串是否算未配置必须写成规则并测试。",
        "环境变量只影响当前进程的配置快照，测试用 monkeypatch.setenv/delenv 可以还原状态；不要打印整个环境帮助调试。默认路径和显式路径各自应有确定输出。",
    ],
    "D10-convert": [
        "int('30') 成功而 int('三十') 抛 ValueError，配置转换应在边界捕获并给出字段名；把所有非空字符串直接当 True 会让 'false' 产生错误含义。",
        "布尔解析通常只接受 true/false 等明确集合，未知值应失败而不是猜测；整数还要检查范围。示例把合法、大小写和非法文本分别传入，比较返回值与异常。",
    ],
    "D10-dotenv": [
        ".env 解析应逐行处理空行、# 注释、第一次等号和两端空白，结果仍是字符串配置；不能用 exec/eval 把文件当 Python 执行。",
        "值里可能包含等号，所以 split('=', 1) 才不会截断；引号是否去除也要定规则。临时文件测试能证明读取的是指定路径而不是 cwd 下偶然存在的 .env。",
    ],
    "D10-config": [
        "Settings dataclass 把来源转换后的字段集中起来，构造时应明确默认值和覆盖优先级；业务函数只接收 Settings，不再重复读取环境。",
        "配置对象是数据契约，不是秘密日志容器；repr 或错误消息不应泄露敏感值。用空环境和覆盖环境构造两次，检查 database_path、debug 等字段类型。",
    ],
    "D11-logger": [
        "logging.getLogger('taskproj') 返回按名称复用的 logger，重复添加 handler 会使同一条记录打印两遍；初始化函数应做到幂等。",
        "logger.level、handler.level 和 propagate 共同决定记录去向，不能只调一个数字就假定结果。测试清空/隔离 handler 后记录一次，并断言捕获文本出现一次。",
    ],
    "D11-format": [
        "Formatter 把 LogRecord 的时间、级别、logger 名称和 message 组合成文本；%(message)s 是调用 logger.info 时传入的内容。",
        "格式字符串写错字段会在输出阶段报错，调用点不应自己拼时间和级别。用一条带 task_id 的记录检查格式包含字段且不重复渲染。",
    ],
    "D11-stream": [
        "StreamHandler 默认面向一个流，handler.setLevel 控制它接收的最低级别；logger 本身的级别过滤发生在更前面。分别记录 INFO 和 ERROR 才能看出配置差异。",
        "测试应使用 StringIO 或 caplog 捕获输出，不把日志写到真实终端作为断言；错误内容应保留事件而不是吞掉异常。调整 handler level 后，低级别记录应按契约消失。",
    ],
    "D11-file": [
        "FileHandler 会持有文件句柄，filename、encoding 和 formatter 必须显式设置；临时目录让测试不会污染仓库。",
        "测试结束要 removeHandler 并 close，否则 Windows 可能无法删除临时文件；重复初始化还会重复写入。读取文件并计算关键行次数，才能验证资源和格式都正确。",
    ],
    "D12-request": [
        "Request 只描述请求，opener 才执行 I/O；把 opener 作为参数传入后，fake opener 可以检查 URL、method 和 headers 而不访问网络。",
        "response.read() 通常返回 bytes，必须按 UTF-8 decode 后再交给字符串逻辑；with response 能保证资源释放。测试计数器应确认 opener 只被调用一次。",
    ],
    "D12-response": [
        "状态码、响应体和 JSON 语法是三层不同证据；200 仍可能携带坏 JSON，404 也不应被当成空列表。先检查状态，再 decode 和 loads，错误原因才可定位。",
        "JSONDecodeError 说明数据形状坏，HTTPError/非 2xx 说明协议失败；把两者统一成 {} 会制造假成功。fake response 的 200 合法、200 坏文本和 404 三组输入应得到不同结果。",
    ],
    "D12-post": [
        "POST JSON 要先 json.dumps，再 encode('utf-8')，Request 的 method 和 Content-Type 必须与 bytes body 一致；dict 不能直接作为可传输 body。",
        "fake opener 可解码 request.data 并检查中文、headers 和调用次数，所以不需要真实服务。object() 这类不可序列化值应抛出明确错误，而不是发送空 body。",
    ],
    "D12-timeout": [
        "timeout 是一次 opener 调用的等待上限，不是重试次数；它必须出现在真正执行网络操作的参数位置。fake opener 记录 timeout 就能离线验证传递。",
        "TimeoutError、URLError 和 HTTPError 保持各自原因，客户端不应因失败自动重试或换地址。计数测试确认网络错误只触发一次调用，符合可靠性边界。",
    ],
    "D13-app": [
        "FastAPI() 创建 ASGI 应用，@app.get('/health') 把函数注册为路由，返回 dict 后框架编码成 JSON；导入 app 不等于启动服务器。",
        "TestClient 在进程内调用路由，状态码和 JSON 是可重复证据；未知路径应保持 404。把 uvicorn.run 放进 __main__ 或外部命令，避免导入副作用。",
    ],
    "D13-route": [
        "路径参数来自 /tasks/{task_id}，查询参数来自 ?limit=3；类型标注让 FastAPI 在函数体前把可转换输入交给 int。",
        "非法路径参数的 422 是输入契约反馈，不应被 catch 成 200；缺省 limit 应由函数签名提供。TestClient 同时覆盖正常、缺省和非法三种 URL。",
    ],
    "D13-response": [
        "response_model 描述成功输出字段，status_code=201 说明创建完成；输入 TaskIn 和输出 TaskOut 可以有不同字段。",
        "返回 dict 缺少必需字段会触发响应校验问题，直接返回内部对象还可能泄露字段。测试应同时检查状态码、id/title/done 和错误响应。",
    ],
    "D13-lifecycle": [
        "lifespan 在 yield 前初始化、yield 后清理，TestClient 上下文会触发这两个阶段；它不是每个请求都重新创建连接。",
        "Depends 表达请求级协作者，app.state 适合保存应用级资源；事件列表记录 start、request、stop 的顺序，才能证明清理发生。",
    ],
    "D14-model": [
        "Pydantic BaseModel 在路由边界把 JSON 变成带字段的对象，缺 title 或 priority='bad' 会在业务逻辑前得到字段位置明确的 422。先看错误中的字段路径，再决定修请求还是修模型；不要在 service 里重复猜测类型。",
        "模型默认值与必填字段是不同契约；TaskIn(title='买书') 可以得到 priority=0，但不能把缺 title 猜成空字符串。",
    ],
    "D14-service": [
        "service 接收普通 Python 值和 repo 参数，路由只负责 HTTP 映射；因此空标题规则可以被 API、CLI 和单测共同调用。",
        "fake repo 能检查成功时只写一次，空白 title 时根本不写库；把数据库连接藏在全局会让这个边界无法隔离。",
    ],
    "D14-errors": [
        "HTTPException 的 status_code/detail 是客户端契约，资源不存在应是 404 而不是返回 200/null；内部 traceback 不属于 detail。",
        "service 领域异常与 route HTTP 映射要分层，测试要分别观察命中对象、404 状态和安全消息。这样前端无需自行解释错误。",
    ],
    "D14-deps": [
        "Depends 让 FastAPI 在请求期间调用 get_repo 并注入结果，路由签名直接表达它需要的协作者。测试 override 后应看到 fake repo 的返回值，并在用例结束时恢复覆盖，避免后续请求继续使用 fake。",
        "app.dependency_overrides 只应在测试期间替换依赖，finally 清空才能避免后续用例继续使用 fake；这比读取全局 DB 可控。",
    ],
    "D15-assert": [
        "pytest 收集 test_ 开头函数，assert add_tax(100) == 113 把输入和精确输出绑定起来；只 assert result 会让许多错误实现通过。",
        "让实现故意失败一次，pytest 的 diff 和非零退出码就是反馈；修回后再测 0 等边界，证明不是只对一个样例过拟合。",
    ],
    "D15-fixture": [
        "fixture 的 yield 前后分别建立和清理资源，tmp_path 为每个测试提供独立目录；测试不应写项目根目录的 data.json。",
        "默认 function scope 让第二个测试看不到第一个测试创建的文件；目录、编码和 fixture 返回值都应由断言观察，而不是靠人工检查。",
    ],
    "D15-mock": [
        "patch 必须替换被测模块真正查找的名称，Mock 返回固定 response 并记录调用；patch 退出后原名称自动恢复。",
        "assert_called_once_with 能验证 URL/timeout 协议，但不应把 JSON 解析逻辑也全部 mock 掉；保留本地业务代码才有测试价值。",
    ],
    "D15-api": [
        "TestClient 直接把 GET/POST 送到 ASGI app，不需要端口；json=payload 才会生成正确请求体，路径和 query 仍按真实 URL 输入。",
        "断言 response.status_code、json 字段和错误 detail，不能只写 assert response；fixture/override 让每例 API 数据隔离。",
    ],
    "D16-connect": [
        "sqlite3.connect(':memory:') 创建隔离数据库，文件路径则提供持久化；两种连接都要由调用者决定并最终 close。",
        "关闭后再次 execute 会得到 ProgrammingError，说明资源边界真实存在；测试不要共享固定 task.db，否则旧数据会改变结果。",
    ],
    "D16-schema": [
        "CREATE TABLE IF NOT EXISTS 让 init_db 可重复，PRIMARY KEY 提供 id，NOT NULL 和 DEFAULT 约束字段；它只保证表存在，不自动迁移旧结构。",
        "把 title 设为空或 done 省略后查询约束和默认值，能看到数据库而不是 Python if 在保护数据。schema 失败应在建表/插入处明确暴露。",
    ],
    "D16-crud": [
        "问号占位符把 SQL 结构和 title/id 数据分开，避免引号和注入改变语句；execute(sql, (value,)) 的 tuple 逗号很重要。",
        "INSERT/UPDATE/DELETE 后要按契约 commit 并检查 rowcount，SELECT 要把 Row 转成稳定输出。用中文、引号和不存在 id 测试，比只插入简单英文更可靠。",
    ],
    "D16-transaction": [
        "一组写操作要么一起 commit，要么异常时 rollback；finally 只负责 close，不应把事务失败伪装成成功。",
        "在第二个写操作故意 raise 后查询应看不到第一个未提交变化；这验证的是原子性，而不是单条 SQL 能否运行。",
    ],
    "D17-coroutine": [
        "async def 调用返回 coroutine 对象，只有 await 或 asyncio.run 才会执行函数体；直接 print(coro) 只会得到对象表示和警告。",
        "await 是协作式暂停点，asyncio.run 负责创建和关闭事件循环；同步入口不能反复嵌套 asyncio.run。用事件列表观察执行顺序。",
    ],
    "D17-gather": [
        "asyncio.gather 同时等待多个 awaitable，返回列表顺序仍按传入顺序而不是完成先后；这适合并发独立 IO。",
        "一个任务异常会影响 gather 的结果，return_exceptions=True 才会把异常作为结果收集；是否采用它必须是明确契约。",
    ],
    "D17-timeout": [
        "asyncio.wait_for 给 awaitable 设置时间上限，超时会取消内部任务并抛 TimeoutError；被取消的协程需要在 finally 清理。",
        "超时不是重试，测试用短 sleep 和计时事件即可证明取消发生；不要为了让测试通过把异常吞成 None。",
    ],
    "D17-boundary": [
        "异步边界测试要分别覆盖成功、业务异常和超时，并由 asyncio.run 或异步测试入口驱动；同步 assert 不能代替 await。",
        "fake async dependency 让测试不依赖真实服务，事件和异常类型是证据；清理任务后事件循环才不会留下 pending task。",
    ],
    "D18-scope": [
        "requirements.md 的用户故事描述添加、列表、完成、删除看到的行为，不写 SQL 或函数名；这让 API、CLI 和网页共享同一个目标。",
        "空标题和未知 id 也属于需求边界，后续测试必须能从文字找到对应断言；没有边界的“支持任务”无法验收。",
    ],
    "D18-acceptance": [
        "验收场景按 add→list→complete→delete 串起可观察状态，每一步都写请求/命令和结果；“正常返回”不足以成为断言。",
        "重复删除、空标题等失败场景提前写进清单，D22 测试和 D24 runbook 才不会只覆盖 happy path。每个失败场景还要写状态码、错误字段和排查证据，后续才能转成断言。",
    ],
    "D18-data-contract": [
        "contract.json 区分 input 的 title 与 output 的 id/title/done，JSON 使用 false/null 而不是 Python 的 False/None；json.tool 能先验证语法。",
        "字段类型和 required 规则会被 Pydantic、SQLite 和网页共同读取；改动 done 类型后应能在契约检查中看到失败。",
    ],
    "D18-api-contract": [
        "routes 表把用户动作映射成 method、path、body 和 status，POST /api/tasks 的 201 与 GET / 的静态入口都应明确写出。实现前逐条检查路径是否冲突，D22 测试和 D23 fetch 都从这张表取契约。",
        "契约先于 FastAPI 实现可以发现路径冲突和错误 detail 不一致；D22/D23 的测试与 fetch 直接使用这些路线。",
    ],
    "D19-pyproject": [
        "pyproject.toml 同时声明 project 元数据、requires-python、包布局和 pytest 发现路径；pip install -e . 是从空环境验证它的命令。",
        "项目名、包目录和测试路径必须互相一致，不能只在 README 里口头声明依赖；collect-only 可以先发现配置错误。",
    ],
    "D19-package": [
        "taskproj/__init__.py 让目录成为可导入包，版本常量是安全的公开信息；导入阶段不应创建数据库、读网络或启动服务。",
        "python -c 'import taskproj' 能证明包入口存在，检查导入前后的文件树还能证明没有隐藏副作用。若导入后出现数据库或缓存文件，说明 I/O 错误地放进了 __init__.py，应移到显式入口。",
    ],
    "D19-config": [
        "database_path 把 TASKPROJ_DB 的非空值与默认 taskproj.db 规则集中起来，并返回 Path；D20 连接层不再自己猜 cwd。",
        "空字符串不能被当成有效文件名，配置读取也不应打印环境全集；用三组 env/root 输入检查优先级和路径稳定性。",
    ],
    "D19-main": [
        "main(argv=None) 是可测试入口，if __name__ == '__main__' 才把返回码交给 SystemExit；导入 taskproj.main 不应执行初始化。",
        "直接 python -m taskproj.main 与 import 两种方式的副作用不同，分别运行才能证明模块边界和失败退出码。预期是导入不启动服务，直接运行返回可供 shell 判断的整数状态。",
    ],
    "D19-readme": [
        "README 的安装、数据库、测试和启动命令必须能在真实目录执行，命令中的 taskproj.main 不能继续指向旧 app.py。逐条复制命令到项目根运行，找不到文件时先修路径或安装说明，而不是改测试绕过。",
        "对下一位学习者来说，README 是从零开始的导航；用 python -m pytest -q 验收它列出的入口比只检查 Markdown 标题更有意义。",
    ],
    "D20-connection": [
        "create_connection 负责连接和 row_factory，init_db 负责幂等 DDL；导入 db.py 不应顺手生成 taskproj.db。",
        "在同一内存连接重复 init_db 并查询 sqlite_master，可以证明表结构和初始化时机；关闭连接后不能再执行 SQL。",
    ],
    "D20-create-list": [
        "add_task 用 ? 参数绑定 title，commit 后 list_tasks 按 id ASC 读取；这样包含引号或中文的标题仍是数据而不是 SQL。",
        "列表返回 id/title/done 的稳定形状，插入后立即查询能发现遗漏 commit；空白标题应在数据层拒绝而不是写入脏行。",
    ],
    "D20-update-delete": [
        "complete_task/delete_task 读取 cursor.rowcount，只有确实影响一行才返回 True；未知 id 不能伪造成功。",
        "完成应让 done 变为 True，删除应让后续列表看不到该行；这些状态变化是 D21 API 和 D23 CLI 共用的证据。",
    ],
    "D20-db-tests": [
        "tests/test_project.py 用 fixture 初始化隔离连接，并分别断言字段、排序、完成、删除和未知 id；它测试真实 db.py 而不是复制实现。",
        "故意让一个断言失败，pytest 的第一条差异能指向数据层行为；固定项目根数据库会让测试顺序改变结果。",
    ],
    "D21-app": [
        "FastAPI app、lifespan 和 get_db 把数据库资源接到请求边界，health 路由则不依赖真实任务数据。TestClient 进入上下文时应初始化一次，退出时关闭连接；普通导入不应触发生命周期。",
        "with TestClient(app) 会触发启动与清理，import taskproj.api 只应得到 app；这两个动作必须分别验证。",
    ],
    "D21-schema": [
        "TaskIn 与 TaskOut 从 contract.json 落成 Python 模型，创建输入不接收 id，输出必须含 id/title/done；模型错误在写库前被拒绝。",
        "发送 {}、空白 title 和正常 title 能分别观察 422 与 201；错误 detail 不应来自内部 traceback。",
    ],
    "D21-crud-routes": [
        "四条路由只编排模型、数据层和 HTTP 状态码，业务 SQL 仍在 db.py；这样 API、CLI 不会出现两套完成规则。",
        "创建、列表、完成、删除的状态和 JSON 应与 contract.json 一致，PATCH/DELETE 未知 id 统一 404；TestClient 主流程能串起证据。",
    ],
    "D21-static": [
        "StaticFiles(html=True) 让 GET / 找到 taskproj/static/index.html，但 API 路由仍应先注册并继续返回 JSON。分别请求根路径和 /api/tasks，前者应是 HTML，后者不能被静态挂载吞掉。",
        "从错误 cwd 启动时相对 static 路径可能失效，所以目录应依据包位置或项目根明确计算；root 和 /api 要分别请求。",
    ],
    "D22-db-fixtures": [
        "数据库 fixture 在 yield 前创建临时文件/内存库，在 finally 后关闭连接；每个测试都从空 tasks 表开始。",
        "连续运行同一个测试文件和删除 tmp_path 能暴露共享连接或未 close 问题，测试不应依赖已有 taskproj.db。若临时文件被锁或第二例看到旧任务，就回到 fixture 的 scope、yield 和 finally 检查。",
    ],
    "D22-api-tests": [
        "TestClient fixture 通过 dependency_overrides 注入隔离 db，with 上下文触发生命周期；API 测试因此无需真实端口。",
        "主流程每一步都断言 status_code、JSON 字段和状态变化，client.post 使用 json=payload 而不是 data 字符串。创建后的 id 必须能在下一次列表中出现，完成和删除还要观察 done 与列表变化。",
    ],
    "D22-api-errors": [
        "空标题/缺字段属于 422，未知 id/重复删除属于 404 或契约规定的失败；这些路径还应断言数据库没有脏写。",
        "错误 detail 面向用户且不含 SQL、文件路径和 traceback；前端展示后端返回内容，测试锁定这个边界。",
    ],
    "D22-acceptance": [
        "公开验收从空临时数据库检查 contract、数据层和 API，命令 python -m pytest -q 的退出码就是交付证据。它还应覆盖空标题和未知 id，确保失败路径没有被 happy path 掩盖。",
        "失败输出要能分辨文件缺失、schema、CRUD、路由和错误契约，不能只写一个宽泛的 end-to-end 断言。先定位第一条失败及其真实文件，再修复根因并重新运行公开命令。",
    ],
    "D23-cli-parser": [
        "build_parser 把 add/list 的 argv 解析成 Namespace，main(argv=None) 让测试无需修改 sys.argv；import cli 不应自动执行。",
        "--help、显式子命令和缺少子命令分别有明确输出/退出行为，数据路径仍从 config 进入 db，而不是 CLI 自己拼 SQL。解析结果应能被单测直接检查，真实子进程再验证模块入口和 stderr。",
    ],
    "D23-cli-mutate": [
        "done/rm 复用数据层的 bool 结果，把未知 id 写到 stderr 并返回非零；成功 stdout 才放任务结果或确认。",
        "subprocess 测试同时检查 returncode、stdout、stderr 和数据库状态，才能证明 shell 调用者能可靠编排操作。未知 id 的非零退出必须和成功输出分流，否则脚本会把失败继续传给下一步。",
    ],
    "D23-html-structure": [
        "index.html 先提供 label/input、表单、任务列表和空状态容器，元素 id 与 API 字段/动作契约对应；结构先于复杂脚本。",
        "button type、键盘顺序和可访问名称是可检查产物，不是装饰；静态回归应能找到新增、完成、删除控件。",
    ],
    "D23-html-fetch": [
        "fetch 链路按 GET/POST/PATCH/DELETE 与 API contract 对齐，await response.json 后才更新 DOM；Promise 本身不是任务列表。",
        "先检查 response.ok，非 2xx 时保留后端错误文本并停止成功渲染；浏览器 Network 面板能定位 method、path、body 和状态。",
    ],
    "D24-rebuild": [
        "runbook 从 venv、pip install -e . 到 pytest 按真实目录执行，证明项目不依赖当前机器的全局包或残留数据库。每个命令都应标注项目根和预期输出，复制到新目录仍能找到同样的包。",
        "每条命令都写 cwd、预期输出和失败排查，复制到新临时目录仍能复现；只写“运行项目”不能构成重建证据。",
    ],
    "D24-integrate": [
        "API、CLI 和网页使用同一 SQLite/业务契约，runbook 要记录 uvicorn、python -m taskproj.cli 和浏览器三种入口的操作结果。三者创建的任务应能互相看见，若结果不一致就检查共享 db/service 边界。",
        "集成过程还要记录 Ctrl+C、临时 DB 和端口清理；三入口结果不一致时回到共享 db/service 边界，而不是各自打补丁。",
    ],
    "D24-artifacts": [
        "15 个文件清单必须用真实 Path 存在性和 workspace_deps 核对，逐项说明创建小节、使用者和验证命令；taskproj.db/pycache 不属于交付产物。",
        "清单能把断裂依赖暴露出来，例如 API 引用了不存在的 static/index.html；它是证据索引，不是手写愿望列表。",
    ],
    "D24-review": [
        "review.md 引用 pytest、CLI smoke test 和静态页面检查的真实命令，并记录一次失败、原因、修正文件和复测结果。每条证据都要能由下一位开发者重新执行，而不是只相信文字结论。",
        "复盘还要区分已验证事实与未覆盖风险，说明为什么契约、SQLite、FastAPI、CLI 和原生页面这样分层，而不是只写项目感想。引用一次真实失败和复测命令，读者才能判断结论是否有证据。",
    ],
}

# These explanations are indexed beside SECTION_EXAMPLES, not by catalog order.
# Keeping them explicit prevents a lesson from inheriting the neighboring
# example's story when sections are reordered.
DEV_EXAMPLE_EXPLANATIONS: dict[str, list[str]] = {
    "D08-pathlib": [
        "Path('workspace') / 'notes.txt' 组合出一个路径对象，name 和 suffix 分别读取文件名与扩展名，所以输出 notes.txt .txt。相对路径仍受 cwd 影响；换到不存在的根目录时这里只是描述路径，不代表文件已经存在。",
        "root.glob('*.py') 只匹配 root 这一层的 Python 文件，列表推导式取 name 后排序，唯一结果是 main.py。没有匹配文件时结果应是 []，目录名也不应被误当成可读文件。",
    ],
    "D08-utf8": [
        "write_text 和 read_text 都显式使用 encoding='utf-8'，因此中文和 🌱 写入后可以原样读回并输出。若只省略一端的编码，结果可能依赖系统默认值；本例验证的是文本往返，不是字节长度。",
        "写入的字符串包含一个换行，read_text(...).splitlines() 把它分成第一行和第二行，所以 len 输出 2。空文本的 splitlines() 是空列表，不能把字符数直接当作行数。",
    ],
    "D08-json-read": [
        "json.loads 把合法 JSON 文本转换为 Python dict，data['title'] 和 data['done'] 读取两个字段，因此输出买书 False。JSON 的 false 会变成 Python 的 False；缺少 title 时按键访问会得到 KeyError。",
        "json.loads('{bad}') 在语法不合法时抛出 JSONDecodeError，except 只捕获这个明确类型并输出提示。坏 JSON 不能静默变成空字典，否则调用者会误以为数据有效。",
    ],
    "D08-json-report": [
        "两个 sum 分别统计 done 为真和为假的项目，json.dumps(sort_keys=True) 让输出键顺序稳定，因此得到 {\"done\": 1, \"open\": 2}。items 为空时两个计数都应为 0，不应除以项目数。",
        "空 report 通过 json.dumps(..., ensure_ascii=False, indent=2) 生成多行 JSON，缩进只改变展示，不改变字段值。若消费者要求单行传输，应去掉 indent，而不是手工删除换行。",
    ],
    "D09-parser": [
        "add_argument('--limit', type=int, default=20) 让 argparse 把命令行文本 '3' 转成整数 3，parse_args 后从 Namespace 读取 limit。省略选项会得到默认 20，传入非数字会由 argparse 拒绝。",
        "位置参数 title 没有前缀，parse_args(['买书']) 会把文本绑定到 args.title 并输出买书。缺少这个必填位置参数时解析失败，不能用默认标题掩盖输入缺失。",
    ],
    "D09-subcommands": [
        "add_subparsers(dest='command', required=True) 注册 list 子命令，解析 ['list'] 后 command 是字符串 list。未提供子命令会显示 argparse 错误并退出，required=True 正是在声明这个边界。",
        "add 子解析器额外声明 title 位置参数，所以 ['add', '买书'] 同时得到 command='add' 和 title='买书'。如果把 title 放到父解析器，list 也会被错误要求提供标题。",
    ],
    "D09-errors": [
        "--count 的 type=int 在解析阶段把 '2' 转换为整数，print(args.count) 因而输出 2。传入负数是否允许要由业务规则另行检查；type=int 只负责数字格式。",
        "传入 --count x 时，argparse 在 type=int 转换处触发 SystemExit，error.code 非零表示命令失败。捕获退出只适合测试；真实 CLI 应把错误留给用户并返回非零状态。",
    ],
    "D09-entry": [
        "main 返回 0，但 if __name__ == '__main__' 只在文件被直接执行时调用它，所以导入模块只打印 import safe。删除守卫会让导入产生输出或副作用，库代码就难以复用。",
        "subprocess 用当前 Python 执行 -c 'print(3)'，returncode 为 0 且 stdout.strip() 为 3，所以组合输出是 0 3。子进程失败时应同时检查 returncode 和 stderr，不能只看 stdout。",
    ],
    "D10-env": [
        "os.environ.get('TASKPROJ_MODE', 'dev') 在变量缺失时返回默认 dev，因此本例输出 dev。默认值只覆盖缺失，不会把显式空字符串自动变成 dev，空值规则需要单独定义。",
        "先把 TASKPROJ_MODE 写成 test，再用 get 读取，所以输出 test。环境变量本质是字符串；后续若需要布尔或整数，必须在配置边界显式转换。",
    ],
    "D10-convert": [
        "as_bool 先 strip/lower，再把 false 映射为 False，print 因而输出 False。输入 ' false ' 也会成功；未列入集合的文本应继续抛 ValueError，而不是猜测含义。",
        "int('not-a-number') 在转换处抛 ValueError，except 输出配置整数无效，说明错误被限定在格式失败。不能把所有配置异常都吞掉，否则缺失字段和权限问题会失去诊断信息。",
    ],
    "D10-dotenv": [
        "read_env 逐行 strip，跳过空行和 # 注释，再用 split('=', 1) 读取键和值，所以 app.env 中的 MODE 得到 test。值内部再有等号时仍会保留；文件内容不会被当成 Python 代码执行。",
        "split('=', 1) 只在第一个等号处分割 NAME=task=one，右侧完整保留 task=one。若不限制次数，右侧等号会造成 too many values to unpack。",
    ],
    "D10-config": [
        "Settings 的字段默认值在 dataclass 声明处定义，Settings() 因而产生 mode='dev'、port=8000。默认值属于配置契约；端口文本仍需在进入 dataclass 前转换为 int。",
        "显式传入 'test' 和 9000 后，.port 读取的是整数 9000，而不是默认值。参数位置顺序必须与字段一致；生产代码更适合用关键字避免错位。",
    ],
    "D11-logger": [
        "getLogger('taskproj') 返回命名 logger，clear 后只添加一个 NullHandler，所以 len(logger.handlers) 输出 1。NullHandler 不把库日志写到终端；真实应用应在入口决定输出位置。",
        "第二个例子明确添加了两个 NullHandler，handlers 长度因此输出 2，展示重复配置的可观察信号。生产 setup 应具有幂等性，不能因函数被调用两次就重复输出。",
    ],
    "D11-format": [
        "LogRecord 的消息模板是 created %s，参数 T1 由 Formatter 渲染，包含 levelname、name、message 后输出 INFO:taskproj:created T1。模板参数数量不匹配时格式化会失败，不能靠字符串拼接掩盖错误。",
        "第二个 LogRecord 的级别是 ERROR、消息是 failed，格式只请求 levelname 和 message，所以输出 ERROR failed。这里没有 name 字段；格式越简洁，日志上下文就越少，需按用途选择。",
    ],
    "D11-stream": [
        "handler 的级别设为 WARNING，logger.info('hidden') 被过滤而 logger.warning('shown') 写入 StringIO，所以最终只输出 shown。若把 handler 级别降到 INFO，hidden 也会出现。",
        "第二个 handler 把 logger.error('disk full') 写入 StringIO，检查 stream.getvalue() 包含 disk full 得到 True。测试流必须在用例结束时移除 handler，否则后续用例会收到这条记录。",
    ],
    "D11-file": [
        "FileHandler 使用临时路径和 UTF-8 写入中文保存，关闭并移除 handler 后读取文件，endswith('保存') 为 True。必须先 flush/close 再读取，Windows 上未关闭句柄还可能阻止删除临时文件。",
        "StringIO 作为 StreamHandler 的输出目标，logger.info('one') 只写一次，因此 count('one') 输出 1。若重复添加同一个用途的 handler，计数会变成 2，这正是初始化幂等性边界。",
    ],
    "D12-request": [
        "Request('https://example.invalid/tasks', method='GET') 只构造请求描述，不会发起网络连接，method 和 full_url 分别输出 GET、https://example.invalid/tasks。真正调用 urlopen 才会产生 I/O；单测应先检查对象字段。",
        "headers 中的 Accept 被 Request 保存，get_header('Accept') 读取出 application/json。请求头名称和值是协议字符串；缺少 Accept 不等于服务端一定返回 JSON。",
    ],
    "D12-response": [
        "status=200 落在 200 到 299 的范围内，body 先 decode 为 UTF-8 再由 json.loads 变成 dict，所以输出 {'items': []}。状态成功仍不保证 JSON 合法，解析失败必须保留为错误。",
        "b'{bad}' 解码后仍是非法 JSON，json.loads 抛 JSONDecodeError，except 输出 bad json。这里没有把坏响应改成空对象，因为那会掩盖服务端协议错误。",
    ],
    "D12-post": [
        "json.dumps 把 title 字典序列化，再 encode 成 UTF-8 bytes，Request 同时声明 POST 和 application/json，所以输出可还原的 POST 字典。data 必须是 bytes；直接传 dict 不是有效的 urllib 请求体。",
        "json.dumps({'done': False}) 后 decode 展示 JSON 文本，Python False 被编码为 JSON false，所以输出 {\"done\": false}。JSON 布尔值大小写固定，不能写成 Python 风格的 False。",
    ],
    "D12-timeout": [
        "fake_open 返回 request.full_url 和收到的 timeout，调用传入 3 后输出 ('/slow', 3)，证明超时参数到达真正的 I/O 边界。timeout 只是等待上限，不代表函数会自动重试。",
        "fake_open 记录 timeout=2 后抛出 TimeoutError，except 读取 calls 长度得到 1，证明只调用一次。网络失败不应被静默替换成空结果，否则调用者无法区分超时与空列表。",
    ],
    "D13-app": [
        "FastAPI 装饰器把 health 注册到 /health，但直接调用 health() 仍返回 {'status': 'ok'}，这是路由函数的业务结果。真实请求还会经过 FastAPI 的路径匹配和响应序列化，不能只凭函数调用证明路由可达。",
        "version 路由函数返回整数版本 1，直接调用的结果是 {'version': 1}。版本字段类型由响应契约决定；把数字写成字符串会改变客户端看到的 JSON 类型。",
    ],
    "D13-route": [
        "get_task(7, 3) 把位置实参绑定到 task_id 和 limit，返回字典中的 id=7、limit=3。HTTP 层若收到非整数文本，FastAPI 应在进入函数前返回 422，而不是让函数自行猜测。",
        "int('not-int') 抛 ValueError，except 把它转换成示意性的 422 输入错误。真实 FastAPI 校验会返回结构化 detail；业务代码不要把所有异常都伪装成输入错误。",
    ],
    "D13-response": [
        "TaskOut 为 done 提供 False 默认值，TaskOut(id=1, title='买书').model_dump() 因而得到完整三个字段。响应模型会把内部对象形状固定下来；缺少必填 id/title 时构造应失败。",
        "第二个 TaskOut 实例从模型属性 .title 读取买书，说明 Pydantic 模型既能校验输入也能提供属性访问。字段不存在时应得到明确 AttributeError，而不是返回任意键。",
    ],
    "D13-lifecycle": [
        "events 先记录 start，再进入 try 记录 request，finally 无论是否异常都追加 stop，所以列表是 start、request、stop。finally 适合资源清理；它不应吞掉请求异常。",
        "resource 在 yield 前打印 open，with 体打印 use，退出时 finally 打印 close，因此顺序是 open、use、close。上下文管理器的退出路径必须覆盖异常，否则资源会泄漏。",
    ],
    "D14-model": [
        "TaskIn 的 title 是必填、priority 默认 0，TaskIn(title='买书') 的表示包含 title='买书' priority=0。默认值只补 priority，不能补缺失 title；字段类型错误也应在模型边界被拒绝。",
        "调用 TaskIn() 缺少 title，Pydantic 抛 ValidationError，except 输出 title required。捕获后只展示面向用户的字段错误，不应把内部 traceback 当 API 响应。",
    ],
    "D14-service": [
        "create_task 先 strip 标题，再把非空文本交给 repo.add，所以输入两侧有空格时输出干净的买书。服务层依赖 repo 接口而不写 SQL；全是空白的标题应在提交前失败。",
        "'  '.strip() 得到空字符串，if not title 主动 raise ValueError('empty')，except 打印 empty。这个失败来自业务规则，不应被数据层静默改成一条空任务。",
    ],
    "D14-errors": [
        "HTTPException(status_code=404, detail='任务不存在') 保存了状态码和用户可读 detail，print 输出 404 任务不存在。错误对象不应包含 SQL、密钥或 traceback 等内部细节。",
        "显式 raise HTTPException(422, ...) 后被同类型 except 捕获，读取 status_code 输出 422。422 适合输入契约不满足的情况；未知资源应保持 404 语义。",
    ],
    "D14-deps": [
        "get_repo 返回 real，list_tasks 接收这个依赖并原样返回，所以输出 real。依赖函数应在边界创建资源，业务函数通过参数使用它，测试才能替换实现。",
        "fake='test' 被直接传给 list_tasks，结果输出 test，说明依赖可以被测试替身替换。替身只应提供本例需要的接口，不能让测试绕过业务断言。",
    ],
    "D15-assert": [
        "add_tax(100) 用整数 100 * 113 // 100 得到 113，assert 通过后才打印 passed。断言失败会在 print 之前抛 AssertionError，因此这不是“程序能运行”而是结果检查。",
        "同一函数输入 0 时整数算术结果仍是 0，assert 覆盖了零值边界并输出 zero covered。若实现错误地加固定费用，这个例子会立即失败。",
    ],
    "D15-fixture": [
        "TemporaryDirectory 提供隔离目录，代码在其中写入 note.txt，再用 UTF-8 读回中文并输出你好。with 退出后目录会清理；测试不能依赖项目根已有同名文件。",
        "新的 TemporaryDirectory 初始为空，Path(folder).iterdir() 转成列表后输出 []。若看到旧任务文件，说明 fixture 复用了共享目录或清理时机不正确。",
    ],
    "D15-mock": [
        "Mock 的 return_value 是 ok，调用 opener('/tasks', timeout=2) 输出 ok，assert_called_once_with 又验证了 URL 和 timeout 协议。Mock 只替代外部 opener，业务函数仍应执行真实的参数整理。",
        "patch.object 临时把本模块的 measure 替换为返回 99，所以 with 内输出 99；退出后真实 measure('abc') 恢复为 3。patch 应替换被测模块查找的名称，不能直接改写底层 builtins 造成递归或污染。",
    ],
    "D15-api": [
        "伪响应的 status_code 是 200，json() 返回 status=ok，所以输出 200 {'status': 'ok'}。测试同时观察状态和 JSON；只断言对象存在无法证明 API 契约。",
        "伪响应返回 404 和 detail=missing，读取 json()['detail'] 后输出 404 missing。错误响应也要检查字段形状，不能把非 2xx 当成功数据解析。",
    ],
    "D16-connect": [
        "内存连接执行 select 1 后 fetchone() 返回 (1,)，所以输出 (1,)，随后 close 释放资源。:memory: 数据库只属于这条连接，不能期待另一个连接看到同样的表。",
        "连接先 close，再 execute 会抛 sqlite3.ProgrammingError，except 输出 closed。关闭后的连接不可复用；实际项目应把 close 放在生命周期边界。",
    ],
    "D16-schema": [
        "CREATE TABLE 定义 title 后，pragma table_info(tasks).fetchone()[1] 读取第二列名称，输出 title。pragma 观察的是数据库真实 schema，不是 Python 字典猜出的字段。",
        "done 声明 DEFAULT 0，insert default values 后查询得到整数 0，说明默认值由 SQLite 写入。若把默认写成字符串，读取类型和 API 契约都会改变。",
    ],
    "D16-crud": [
        "insert 使用问号占位符并传入中文买书，SELECT 读回同一标题，说明数据作为参数而不是 SQL 文本拼接。标题含引号时仍应走同一参数路径，不能改用 f-string。",
        "execute 返回的 cursor.rowcount 在插入一行后是 1，所以输出 1。rowcount 只能说明本次语句影响的行数；不存在 id 的更新不能伪造成功。",
    ],
    "D16-transaction": [
        "with conn 里的 insert 尚未提交就 raise，异常离开上下文后事务回滚，查询 count 输出 0。这个结果证明前一条写入也被撤销，而不是只忽略了异常。",
        "正常离开 with conn 会提交 insert，随后 count 输出 1。事务边界必须由代码明确管理；把 commit 放在每条 SQL 后会失去原子性。",
    ],
    "D17-coroutine": [
        "async def value 调用后需要由 asyncio.run 驱动，协程返回 3 并输出 3。直接调用 value() 只会得到 coroutine 对象，不执行函数体并可能产生未 await 警告。",
        "steps 在 await 前打印 before，await asyncio.sleep(0) 让出控制权后再打印 after，所以顺序是 before、after。await 是执行边界；忘记 await 时 after 不会按预期发生。",
    ],
    "D17-gather": [
        "gather 传入 read('a')、read('b')，虽然协程可并发调度，结果列表仍按传入顺序输出 ['a', 'b']。任务完成先后不应被误当成返回列表顺序。",
        "两个 sleep 的结果分别是 2 和 1，gather 按传入位置返回 [2, 1]。若其中一个协程抛异常，默认 gather 会失败；是否收集异常必须由契约决定。",
    ],
    "D17-timeout": [
        "wait_for 给立即完成的 sleep 设置 timeout=1，协程返回 ok，asyncio.run 输出 ok。timeout 是上限而不是延迟，成功路径不应被包装成异常。",
        "sleep(1) 的等待超过 timeout=0，wait_for 抛 asyncio.TimeoutError，except 返回 timed out。超时只取消本次等待，不代表可以自动重试或返回假数据。",
    ],
    "D17-boundary": [
        "work 正常返回 done，asyncio.run 驱动协程后 print 输出 done。成功路径仍应在异步入口运行，不能用同步调用假装完成 await。",
        "第二个 work 主动 raise ValueError('bad')，try/except 捕获后打印 bad，说明业务异常可以穿过异步边界到调用者。不要用 broad except 把未知异常静默吞掉。",
    ],
}


# Project examples are file/command evidence, not claims that a fragment can
# run without the preceding workspace.  The target is explicit so the UI and
# validator can distinguish those fragments from runnable Python snippets.
PROJECT_EXAMPLE_TARGETS: dict[str, str] = {
    "D18-scope": "docs/requirements.md",
    "D18-acceptance": "docs/requirements.md",
    "D18-data-contract": "contract.json",
    "D18-api-contract": "contract.json",
    "D19-pyproject": "pyproject.toml",
    "D19-package": "taskproj/__init__.py",
    "D19-config": "taskproj/config.py",
    "D19-main": "taskproj/main.py",
    "D19-readme": "README.md",
    "D20-connection": "taskproj/db.py",
    "D20-create-list": "taskproj/db.py",
    "D20-update-delete": "taskproj/db.py",
    "D20-db-tests": "tests/test_project.py",
    "D21-app": "taskproj/api.py",
    "D21-schema": "taskproj/api.py",
    "D21-crud-routes": "taskproj/api.py",
    "D21-static": "taskproj/api.py",
    "D22-db-fixtures": "tests/test_project.py",
    "D22-api-tests": "tests/test_api.py",
    "D22-api-errors": "tests/test_api.py",
    "D22-acceptance": "tests/test_api.py",
    "D23-cli-parser": "taskproj/cli.py",
    "D23-cli-mutate": "taskproj/cli.py",
    "D23-html-structure": "taskproj/static/index.html",
    "D23-html-fetch": "taskproj/static/index.html",
    "D24-rebuild": "docs/runbook.md",
    "D24-integrate": "docs/runbook.md",
    "D24-artifacts": "docs/runbook.md",
    "D24-review": "docs/review.md",
}


def _example_contract(section_id: str, syntax: str) -> dict[str, Any]:
    number = int(section_id[1:3]) if section_id.startswith("D") and section_id[1:3].isdigit() else 0
    if 8 <= number <= 17:
        return {"source_kind": "python", "runnable": True}
    target_path = PROJECT_EXAMPLE_TARGETS.get(section_id)
    if not target_path:
        return {"source_kind": "python", "runnable": True}
    if syntax == "contract":
        source_kind = "json_fragment"
    elif syntax == "html":
        source_kind = "javascript" if section_id == "D23-html-fetch" else "html_fragment"
    elif syntax == "runbook":
        source_kind = "command"
    else:
        source_kind = "file_fragment"
    return {"source_kind": source_kind, "runnable": False, "target_path": target_path}


# AI 阶段的两个离线示例逐节对应请求、解析、组合与测试，不调用真实模型。
AI_EXAMPLES = {
    "D25-chat": [
        ("import json\nbody = {'model': 'deepseek-chat', 'messages': [{'role': 'user', 'content': '你好'}], 'stream': False}\nprint(json.dumps(body, ensure_ascii=False))", "{\"model\": \"deepseek-chat\", \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}], \"stream\": false}", "先看清请求体的 model、messages 和 stream；真实调用还需要 URL、Bearer 鉴权与超时。"),
        ("response = {'choices': [{'message': {'content': '你好！'}}]}\nprint(response['choices'][0]['message']['content'])", "你好！", "从模拟响应提取 content；这一步不用联网。"),
    ],
    "D25-errors": [
        ("from urllib.error import HTTPError\ntry:\n    raise HTTPError('https://example.test', 401, 'unauthorized', {}, None)\nexcept HTTPError as error:\n    print(error.code)", "401", "状态码来自 HTTPError.code，应保留在 ApiError 中供调用者判断。"),
        ("import json\ntry:\n    json.loads('not json')\nexcept json.JSONDecodeError:\n    print('响应不是 JSON')", "响应不是 JSON", "响应格式错误与 HTTP 状态错误是两类失败，分别处理。"),
    ],
    "D26-prompt": [
        ("titles = ['Python 函数', 'HTTP 请求']\ngoal = '调用接口'\nprint(f'知识范围标题：{\"、\".join(titles)}\\n目标：{goal}')", "知识范围标题：Python 函数、HTTP 请求\n目标：调用接口", "只传标题范围和学习目标，不把索引标题说成视频正文。"),
        ("completed = False\nprint(f'已完成：{completed}\\n要求：请指出下一步练习')", "已完成：False\n要求：请指出下一步练习", "提示词需要说明任务要求和完成状态，模型才知道给什么反馈。"),
    ],
    "D26-parse": [
        ("import json\ntext = '前缀 {\"summary\": \"可继续\"} 后缀'\nprint(json.loads(text[text.find('{'):text.rfind('}') + 1]))", "{'summary': '可继续'}", "先截取 JSON 片段，再调用 json.loads；提交时还要处理找不到花括号的情况。"),
        ("import json\ntry:\n    json.loads('{bad}')\nexcept json.JSONDecodeError:\n    print('解析失败')", "解析失败", "错误格式必须明确失败，不能用空 dict 假装成功。"),
    ],
    "D27-client": [
        ("messages = [{'role': 'user', 'content': '给我反馈'}]\nresponse = {'choices': [{'message': {'content': '{\"ok\": true}'}}]}\nprint(messages[0]['role'], response['choices'][0]['message']['content'])", "user {\"ok\": true}", "先封装消息，再从响应中取出待解析的文本。"),
        ("import json\ncontent = '{\"ok\": true}'\nprint(json.loads(content)['ok'])", "True", "send_message 最终返回结构化 dict，不能把原始文本直接交给业务层。"),
    ],
    "D27-flow": [
        ("result = {'summary': '已完成', 'strengths': [], 'issues': [], 'next_steps': ['继续练习']}\nrequired = {'summary', 'strengths', 'issues', 'next_steps'}\nprint(required <= result.keys())", "True", "评审流程返回前检查四个必需字段。"),
        ("result = {'summary': '缺字段'}\nrequired = {'summary', 'strengths', 'issues', 'next_steps'}\nprint(sorted(required - result.keys()))", "['issues', 'next_steps', 'strengths']", "缺字段时明确指出问题，而不是填空默认值。"),
    ],
    "D28-test": [
        ("from unittest.mock import Mock\nresponse = Mock()\nresponse.read.return_value = b'{\"choices\": []}'\nprint(response.read().decode('utf-8'))", "{\"choices\": []}", "用 mock 提供确定的响应，测试不连接真实 API。"),
        ("from urllib.error import HTTPError\nerror = HTTPError('https://example.test', 401, 'bad key', {}, None)\nprint(error.code)", "401", "失败测试需要检查错误类型与状态码。"),
    ],
    "D28-review": [
        ("完成了哪些功能：请求、解析、评审。\n验证证据：本地 mock 测试通过。", "一份有证据的复盘", "写清做了什么及如何验证。"),
        ("下一次改进：增加无效 JSON 与 HTTP 401 的测试。", "一条具体的下一步", "复盘指出可执行的改进点，不使用空泛的“继续优化”。"),
    ],
}


def example_for(section_id: str, title: str, syntax: str, index: int) -> dict[str, str]:
    if section_id in AI_EXAMPLES:
        code, output, explanation = AI_EXAMPLES[section_id][index % 2]
        is_review = section_id == "D28-review"
        return {"language": "text" if is_review else "python", "code": code, "output": output,
                "explanation": explanation + "请对照这一段的具体输入和输出再做自己的练习；遇到边界输入时，应先确认本节要求的结果。",
                "source_kind": "file_fragment" if is_review else "python",
                "runnable": not is_review, **({"target_path": "D28 复盘文本框"} if is_review else {})}
    if section_id in CORE_EXAMPLES:
        code, output, _ = CORE_EXAMPLES[section_id][index % 2]
        explanation = CORE_EXAMPLE_EXPLANATIONS[section_id][index % 2]
        return {"language": "python", "code": code, "output": output, "explanation": explanation, "source_kind": "python", "runnable": True}
    if section_id in SECTION_EXAMPLES:
        code, output = SECTION_EXAMPLES[section_id][index % 2]
        notes = DEV_EXAMPLE_EXPLANATIONS.get(section_id, SECTION_EXAMPLE_NOTES[section_id])
        language = "python" if syntax not in {"contract", "html", "review", "requirements", "pyproject"} else ("json" if syntax == "contract" else "text")
        return {"language": language, "code": code, "output": output, "explanation": notes[index % 2], **_example_contract(section_id, syntax)}
    if syntax == "requirements":
        code = "需求：添加任务；验收：POST /api/tasks 返回 201。"
        output = "文档把功能和可观察结果对应起来。"
    elif syntax in {"contract", "pyproject"}:
        code = '{"title": "买牛奶", "done": false}' if syntax == "contract" else "[project]\nname = \"taskproj\""
        output = "解析后字段和类型与契约一致。"
    elif syntax in {"html", "review"}:
        code = "<button id=\"add\">新增</button>" if syntax == "html" else "复盘：先契约，再实现，再测试。"
        output = "控件/文字能被用户看见并操作。"
    elif syntax in {"db", "api", "project-test", "api-test", "cli", "main", "config", "package"}:
        code = f"def lesson_example():\n    return {section_id!r}"
        output = repr(section_id)
    elif "async" in title or section_id.startswith("D17"):
        code = "import asyncio\n\nasync def main():\n    return 1\n\nprint(asyncio.run(main()))"
        output = "1"
    else:
        code = f"# {title}\nvalue = {index}\nprint(value)"
        output = str(index)
    notes = SECTION_EXAMPLE_NOTES.get(section_id)
    explanation = notes[index % 2] if notes else f"代码先给出一个可观察输入，再检查 {syntax} 的结果和失败边界。修改输入后，输出或错误应发生与该修改相称的变化，不能只凭程序退出判断正确。"
    return {"language": "python" if syntax not in {"contract", "html", "review", "requirements", "pyproject"} else ("json" if syntax == "contract" else "text"), "code": code, "output": output, "explanation": explanation, **_example_contract(section_id, syntax)}


def make_section(spec: dict[str, Any], catalog_refs: list[str], index: int) -> dict[str, Any]:
    section_id = spec["id"]
    title = spec["title"]
    objective = spec["objective"]
    syntax = spec["syntax"]
    # Example numbering is local to the section.  ``index`` is the catalog/task
    # position used for deterministic fallbacks; using it here would swap the
    # two hand-written examples for every other section and detach explanations
    # from their own code.
    examples = [example_for(section_id, title, syntax, 0), example_for(section_id, title, syntax, 1)]
    kind = "code" if section_id.startswith(("D02-", "D03-", "D04-", "D05-", "D06-", "D07-", "D08-", "D09-", "D10-", "D11-", "D12-", "D13-", "D14-", "D15-", "D16-", "D17-")) else {"contract": "json", "pyproject": "text", "html": "text", "review": "text", "requirements": "text", "runbook": "text", "package": "text", "config": "code", "main": "code", "db": "code", "api": "code", "project-test": "code", "api-test": "code", "cli": "code"}.get(syntax, "text")
    if section_id == "D24-rebuild":
        kind = "command"
    practice: dict[str, Any] = {
        "kind": kind,
        "scenario": f"在“{title}”中解决一个真实开发问题，而不是只背概念。",
        "instructions": f"围绕“{title}”完成输入式练习：先写最小版本，再运行示例并修正边界。",
        "expected_behavior": f"提交内容能运行或被确定性检查，且能说明“{title}”的关键行为。",
        "hints": f"先复现示例输出，再只修改一处；遇到错误先看类型、行号和输入。{syntax}",
        "starter_content": "" if kind != "code" else "# 先写一个能运行的最小版本\n",
        "input_examples": [
            {"label": "最小输入", "value": f"使用本节要求的最小可运行输入：{title}", "expected": "得到与本节目标对应的最小结果。"},
            {"label": "边界输入", "value": f"使用空值、缺字段或失败路径测试：{title}", "expected": "得到明确的边界结果、异常或错误提示，而不是静默成功。"},
        ],
    }
    teaching = CORE_TEACHING.get(section_id) or DEV_TEACHING.get(section_id) or NONCORE_TEACHING.get(section_id) or PROJECT_TEACHING.get(section_id)
    if teaching:
        practice.update(teaching["practice"])
        practice["input_examples"] = teaching["input_examples"]
    if section_id in CORE_INPUT_EXAMPLES:
        practice["input_examples"] = CORE_INPUT_EXAMPLES[section_id]
        practice["input_identifiers"] = CORE_INPUT_IDENTIFIERS[section_id]
    if section_id in CORE_PRACTICE_CONTRACTS:
        practice.update(CORE_PRACTICE_CONTRACTS[section_id])
    practice.setdefault("starter_policy", "complete")
    if kind == "code":
        practice["file_name"] = "main.py" if syntax not in {"api", "config"} else ("app.py" if syntax == "api" else "main.py")
        if syntax == "project-test":
            practice["file_name"] = "tests/test_project.py"
        elif syntax == "api-test":
            practice["file_name"] = "tests/test_api.py"
    if spec.get("project_file"):
        practice["project_file"] = spec["project_file"]
    if spec.get("project_file"):
        practice["workspace_deps"] = spec.get("workspace_deps", [])
        if section_id.endswith(("-acceptance", "-api-contract", "-create-list", "-update-delete", "-schema", "-crud-routes", "-static", "-api-errors", "-cli-mutate", "-html-fetch", "-integrate", "-artifacts")):
            practice["continues_file"] = True
    elif spec.get("workspace_deps"):
        practice["workspace_deps"] = spec["workspace_deps"]
    if spec.get("project_file") and kind == "code" and str(spec["project_file"]).endswith(".py"):
        practice["file_name"] = str(spec["project_file"])
    section = {
        "id": section_id,
        "title": title,
        "catalog_refs": catalog_refs,
        "objective": objective,
        "explanation": [
            f"本节先用初学者语言理解“{title}”：{objective}。不要把语法当成孤立规则，要先观察它解决的输入和输出问题。",
            f"Python 3 中，{syntax}。示例把一个小动作拆开，关键行的顺序、数据形状和错误边界都需要能被你复述。",
            f"最后把概念放回练习：先运行正常输入，再主动制造边界情况。只有看到输出、异常或文件变化，才算真正知道“{title}”如何工作。",
        ],
        "syntax": syntax,
        "js_bridge": f"如果你有 JavaScript 经验，可以把它与 {title} 做辅助对照；对照只帮助定位差异，练习必须完整使用 Python 3。",
        "examples": examples,
        "common_errors": [
            {
                "error": f"最小输入没有形成可观察的 {title} 结果",
                "symptom": "程序运行但没有目标输出、文件变化或断言证据。",
                "cause": f"只搭了结构，没有把 {title} 的输入传到结果边界。",
                "fix": "先写一个固定输入和预期输出，再逐步替换为真实输入。",
                "example": {"code": "# 只有占位结构，没有调用或断言", "symptom": "运行无输出", "fix": "补充一次具体调用并打印/断言结果"},
            },
            {
                "error": f"失败路径没有针对 {title} 的处理",
                "symptom": "空值、错误格式或资源失败时得到 traceback 或静默错误结果。",
                "cause": "练习只验证了成功样例，没有定义边界输入和错误契约。",
                "fix": "为一个真实边界输入写明确返回值、异常或 stderr 结果。",
                "example": {"code": "value = None  # 边界输入", "symptom": "边界路径未定义", "fix": "显式检查边界并给出预期结果"},
            },
        ],
        "guided_practice": {
            "goal": f"用一个最小可运行例子掌握 {title}，再验证一个会改变结果的边界。",
            "starter": f"# 先为 {title} 写出最小输入和观察点\n",
            "steps": [
                {"action": "复制第一个示例的输入，运行并记录实际结果。", "expected": "实际结果与示例预期一致，且能指出产生结果的关键行。"},
                {"action": "只修改一个与本节概念直接相关的参数或分支。", "expected": "输出或异常按修改点发生可解释变化。"},
                {"action": "加入一个空值、错误值或资源失败输入。", "expected": "边界得到明确结果，不被静默包装成正常成功。"},
            ],
            "check": "运行成功和边界两次，保存输出/异常作为本节验证证据。",
        },
        "practice": practice,
        "key_points": [objective, f"Python 3 规则：{syntax}", "运行结果和错误信息都是反馈证据"],
        "frontend_bridge": f"前端经验只作辅助：{title} 必须先按 Python 3 的执行、类型和错误规则完成。",
        "example": examples[0],
        "steps": ["读懂目标和输入输出", "运行第一个示例", "完成独立练习并验证边界"],
    }
    if teaching:
        section["explanation"] = teaching["explanation"]
        section["js_bridge"] = teaching["js_bridge"]
        section["common_errors"] = teaching["common_errors"]
        section["guided_practice"] = teaching["guided_practice"]
        section["steps"] = [step["action"] for step in teaching["guided_practice"]["steps"]]
    if not catalog_refs and not spec.get("project_file"):
        section["supplemental"] = True
        section["supplemental_note"] = "本节是课程重建中的能力补充，不占用原课程索引条目。"
    return section


def enrich_existing(section: dict[str, Any], index: int) -> dict[str, Any]:
    spec = {"id": section["id"], "title": section["title"], "objective": section["practice"].get("instructions", "理解本节的 Python 运行规则。"), "syntax": section["practice"].get("kind", "python")}
    teaching = make_section(spec, list(section.get("catalog_refs", [])), index)
    for key in ("practice",):
        teaching[key].update(section[key])
    if section["id"] == "D28-test":
        # 这是明确要求学员填写测试函数体的 starter；其余声明/配置类 starter
        # 仍保持 complete，不能因为历史数据里有占位异常而放宽规则。
        teaching["practice"]["starter_policy"] = "function_body"
    examples = [
        {
            **example,
            "expected": example.get("expected") or "运行后得到本小节声明的可观察结果。",
        }
        for example in teaching["practice"].get("input_examples", [])
    ]
    if not examples:
        action = section["practice"].get("action", "本节实践")
        examples.append({"label": "正常输入", "value": str(action), "expected": "动作完成并返回本地验证结果。"})
    if len(examples) < 2:
        examples.append({"label": "边界输入", "value": "重复执行或检查失败路径", "expected": "得到明确的幂等结果或后端错误，而不是静默忽略。"})
    teaching["practice"]["input_examples"] = examples
    teaching["explanation"] = [
        f"本节目标是：{spec['objective']} 先用已有例子观察输入和输出，再开始修改。",
        f"本节的核心结构是 {spec['syntax']}。Python 3 会按明确的缩进、类型和异常规则执行，不能只凭 JavaScript 经验猜测。",
        "完成练习时要同时检查正常路径和边界路径；本地验证通过只是证据，仍要能解释关键行为什么这样写。",
    ]
    return teaching


# D01 is an environment procedure, not a Python syntax lesson.  Keep its five
# records explicit so a learner sees real Windows commands and the evidence
# produced by the fixed backend actions instead of a code-editor exercise.
D01_TEACHING: dict[str, dict[str, Any]] = {
    "D01-onboarding": {
        "title": "先写下你的学习目标",
        "objective": "D01 只有一个目标：让这台电脑能够运行后面的 Python 练习。现在先写一句你想用 Python 做什么，随后按页面顺序准备环境。",
        "syntax": "本节不用写 Python 程序，也不用背解释器、pip、pytest 等术语。",
        "explanation": [
            "你现在只需要写一句具体目标，例如“我想查询业务数据，逐步开发 AI 助手”。这句话用于记录方向，不作为环境是否可用的证明。",
            "提交目标后依次点击检测环境、创建项目专用环境、安装学习工具、最终检查。页面会告诉你每步的结果，安装时可能需要联网。",
            "所有环境步骤通过后，在页面底部填写实际完成证据并标记 D01 完成，然后进入 D02。",
        ],
        "js_bridge": "有前端经验可以把 Python 看作新的运行环境；今天先让它能运行，不需要先记住每个工具的定义。",
        "examples": [
            {"language": "text", "code": "我想用 Python 查询业务数据。", "output": "一条具体的学习目标", "explanation": "这句话只记录你想用 Python 完成的具体事情，不要求出现任何工具名称。它保存的是学习方向；电脑是否准备好，要由后面的固定动作实际检查。", "source_kind": "file_fragment", "runnable": False, "target_path": "D01 学习目标输入框"},
            {"language": "text", "code": "我想用 Python 做一个能调用 AI 的小工具。", "output": "一条具体的学习目标", "explanation": "这句话说明你想做一个什么工具，足以开始今天的学习。以后可以修改目标；D01 能否完成仍取决于环境动作的真实结果。", "source_kind": "file_fragment", "runnable": False, "target_path": "D01 学习目标输入框"},
        ],
        "common_errors": [
            {"error": "还没开始就被术语卡住", "symptom": "不知道该输入命令还是写代码。", "cause": "把后面的环境操作和本节目标混在了一起。", "fix": "本节只写一句目标，下一节再点击固定检测按钮。", "example": {"code": "我想用 Python 做什么？", "symptom": "不需要专业词", "fix": "用自己的话写一句目标"}},
            {"error": "把目标当成环境验证", "symptom": "写完目标后以为 D01 已经全部完成。", "cause": "目标记录不检查本机 Python、.venv 和依赖。", "fix": "继续依次运行后面的四个固定动作，以实际报告作为完成证据。", "example": {"code": "我想用 Python 查询数据", "symptom": "只记录了目标", "fix": "继续进行环境检测"}},
        ],
        "guided_practice": {"goal": "写一句你想用 Python 做的事。", "starter": "我想用 Python ________。", "steps": [{"action": "在下面的文本框写一句学习目标。", "expected": "目标能说明你打算做什么。"}, {"action": "点击“运行并验证”。", "expected": "目标保存成功后，进入“检测当前环境”。"}], "check": "只检查是否写下目标；真正的环境准备由后面四个动作验证。"},
        "practice": {"kind": "text", "scenario": "在开始配置前记录自己的学习目标。", "instructions": "写一句你想用 Python 做什么，例如“我想查询业务数据，逐步开发 AI 助手”。", "expected_behavior": "保存一句具体目标，随后可以进入环境检测。", "hints": "不用解释术语，也不用输入 PowerShell 命令。", "starter_content": "", "input_examples": [{"label": "学习目标", "value": "我想用 Python 查询业务数据。", "expected": "记录目标并进入下一节。"}, {"label": "另一种目标", "value": "我想用 Python 做一个 AI 小工具。", "expected": "记录目标并进入下一节。"}]},
        "steps": ["写一句想用 Python 做的事", "点击运行并验证", "进入环境检测"],
    },
    "D01-detect": {
        "title": "检测我的环境",
        "objective": "用真实 PowerShell 命令查清当前 Python launcher、多版本 PATH、版本、可执行文件和项目根；点击“重新检测”后对照后端报告，不靠猜测继续。",
        "syntax": "where.exe python；python --version；python -c；Get-Location（固定检测命令）",
        "explanation": [
            "在 Windows 上，`python` 可能由 Python Launcher、PATH 中的某个安装目录或 Microsoft Store alias 解析；`where.exe python` 会列出 PATH 命中的候选文件，`python --version` 只报告当前命令实际选中的版本。多个结果并不自动表示错误，关键是确认选中的解释器满足课程版本。",
            "`python -c \"import sys; print(sys.executable)\"` 从解释器内部读取真实路径，比只看命令名称更可靠；`Get-Location` 则显示 PowerShell 当前工作目录。应用的“重新检测”会在服务端项目根运行固定探测，并返回 env、checks、stdout、stderr、exit_code，避免把浏览器文本当成证据。",
            "本节的通过标准是当前 Python >= 3.11 且项目根含课程文件；`.venv`、pip、pytest 尚未存在时，检测应诚实显示未创建，而不是把 D01 其他步骤提前标成完成。若版本不合格，记录完整路径后修复 PATH/安装，再重新点击检测。",
        ],
        "js_bridge": "`where.exe`/`Get-Location` 是 PowerShell 的系统探测，类似 Node 中查看 process.execPath 和 process.cwd()，但本节必须理解 Windows Python launcher 和 PATH 的实际选择。",
        "examples": [
            {"language": "powershell", "code": "where.exe python\npython --version\npython -c \"import sys; print(sys.executable)\"\nGet-Location", "output": "候选路径；Python 3.11+；实际 python.exe 路径；当前项目目录", "explanation": "四条命令分别回答“PATH 找到什么”“当前版本是什么”“解释器实际文件在哪里”“命令从哪里运行”。多版本机器上 where.exe 可能输出多行，真正要记录的是 sys.executable 与版本是否对应；Get-Location 不在项目根时应先修正目录。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
            {"language": "powershell", "code": "Get-Command python -All\npy -0p\npython --version", "output": "PowerShell 解析到的 python 命令；Launcher 管理的版本列表；当前选中版本", "explanation": "Get-Command 展示 PowerShell 的命令解析结果，py -0p 展示 Python Launcher 注册的安装，最后 python --version 验证实际默认版本。若两个列表与默认版本不一致，不要盲目删除版本，先用 sys.executable 和课程要求判断应固定哪个入口。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
        ],
        "common_errors": [
            {"error": "python 不是课程要求的版本", "symptom": "检测报告 Python 版本 < 3.11，或 python -c 的路径指向旧安装。", "cause": "PATH 顺序、多版本 launcher 或 Store alias 选中了错误解释器。", "fix": "保留 where.exe/py -0p 证据，安装/选择 Python 3.11+ 后重新打开 PowerShell，再复查 sys.executable。", "example": {"code": "python --version\npython -c \"import sys; print(sys.version_info[:2])\"", "symptom": "显示 Python 3.10 或更低。", "fix": "不在项目中改代码，先修 Python 安装或命令选择。"}},
            {"error": "在错误目录检测或创建环境", "symptom": "Get-Location 不是真实项目根，报告找不到 data/curriculum.json。", "cause": "终端工作目录与应用后端 project_root 不一致。", "fix": "切换到 D:\\CODEX\\MY-工作台 后再运行；网页动作始终以服务端固定项目根为准。", "example": {"code": "Get-Location\nTest-Path .\\data\\curriculum.json", "symptom": "Test-Path 返回 False。", "fix": "用 Set-Location 切换到项目根并重新检测。"}},
        ],
        "guided_practice": {"goal": "把 PATH、多版本和项目根三个问题分开观察。", "starter": "where.exe python\npython --version\npython -c \"import sys; print(sys.executable)\"\nGet-Location", "steps": [{"action": "点击“重新检测”，先看 Python 版本与可执行文件两项 checks。", "expected": "报告明确列出版本、路径和是否 >= 3.11。"}, {"action": "在 PowerShell 运行 where.exe python 与 Get-Location，并与报告的 project_root 对照。", "expected": "能解释 PATH 候选与后端固定根目录，不把候选列表当成最终解释器。"}, {"action": "若失败，保存 stderr/失败 check，修复后再次点击，不修改文本框伪造结果。", "expected": "第二次报告能显示真实变化，成功时 completed=true 并推进下一节。"}], "check": "版本、解释器路径、项目根三项证据可互相解释；失败时能指出是版本、PATH 还是 cwd。"},
        "practice": {"kind": "env_action", "action": "detect", "scenario": "确认 Windows 当前 Python 和项目根，建立后续动作的基线。", "instructions": "点击“重新检测”。随后阅读后端 checks、env、stdout、stderr、exit_code；不要在文本框输入命令。", "expected_behavior": "当前 Python >= 3.11，项目根课程文件存在；报告诚实显示 .venv/pip/pytest 尚未就绪也可以，后续动作会处理它们。", "hints": "where.exe 可能返回多个路径；以 python -c 输出的 sys.executable 和报告为准。", "starter_content": "", "input_examples": [{"label": "固定动作", "value": "点击重新检测（后端执行 where/版本/项目根探测）", "expected": "返回 checks、env、stdout、stderr、exit_code，不执行用户输入。"}, {"label": "失败修复", "value": "若版本不足或项目根错误，记录 stderr/路径后修复并再次检测", "expected": "第二次报告反映真实修复，不能靠文字标记通过。"}]},
        "steps": ["阅读 Windows launcher、PATH 与 cwd 的区别", "点击重新检测并查看后端证据", "根据版本/路径失败原因修复后复测"],
    },
    "D01-create-venv": {
        "title": "创建项目专用环境（.venv）",
        "objective": "用当前合格解释器创建项目根下的 .venv；理解激活只是改变当前终端 PATH，也能用 .venv\\Scripts\\python.exe 的显式路径工作。",
        "syntax": "python -m venv .venv；.\\.venv\\Scripts\\Activate.ps1；.\\.venv\\Scripts\\python.exe",
        "explanation": [
            "`python -m venv .venv` 是用当前选中的 Python 调用标准库 venv 模块，在项目根创建隔离目录；它不是下载一个神秘 Python，也不会安装项目依赖。网页按钮执行同一固定命令，后端随后用 `.venv\\Scripts\\python.exe --version` 检查文件确实可运行。",
            "PowerShell 激活脚本 `.\\.venv\\Scripts\\Activate.ps1` 只修改当前终端会话里的 PATH 和提示符；关闭终端后它不会改变项目配置。即使不激活，也可以始终用显式路径 `.\\.venv\\Scripts\\python.exe -m pip`，这在脚本和教学中更不容易串环境。",
            "Windows 常见失败是 ExecutionPolicy 阻止 Activate.ps1，这不等于 venv 创建失败；此时先用显式 Python 路径继续，或按组织策略在当前用户范围调整执行策略。已有 .venv 不应删除重建，按钮会保留它并验证版本，避免抹掉学习者已安装的包。",
        ],
        "js_bridge": "这相当于 Node 项目使用本地工具链目录，但 Python venv 由 `python -m venv` 创建并通过 Scripts\\python.exe 选择；不要把 PowerShell 激活误解为 JavaScript 的 import。",
        "examples": [
            {"language": "powershell", "code": "python -m venv .venv\nTest-Path .\\.venv\\Scripts\\python.exe\n.\\.venv\\Scripts\\python.exe --version", "output": "True；.venv Python 版本 >= 3.11", "explanation": "第一行创建环境，第二行检查 Windows 解释器文件存在，第三行直接运行隔离解释器确认它不是空目录。若 Test-Path 为 False，应查看创建命令 stderr；不要因为目录名出现就认为创建成功。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
            {"language": "powershell", "code": ".\\.venv\\Scripts\\Activate.ps1\npython -c \"import sys; print(sys.prefix)\"\ndeactivate", "output": "sys.prefix 指向项目 .venv；deactivate 后恢复原终端", "explanation": "激活后 python 命令通过 PATH 指向 .venv，sys.prefix 可以证明实际环境；deactivate 只退出当前会话。若 Activate.ps1 被策略拦截，跳过激活并用显式 `.\\.venv\\Scripts\\python.exe -c ...` 得到同样的证据。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
        ],
        "common_errors": [
            {"error": "ExecutionPolicy 阻止 Activate.ps1", "symptom": "PowerShell 报 running scripts is disabled，激活失败。", "cause": "当前用户或组织策略不允许执行脚本文件；这与 venv 目录能否创建是两件事。", "fix": "先使用 `.\\.venv\\Scripts\\python.exe` 显式路径；若遵循组织政策，再由用户按许可调整 CurrentUser 执行策略，完成后重新激活。", "example": {"code": ".\\.venv\\Scripts\\Activate.ps1", "symptom": "PSSecurityException / scripts disabled。", "fix": "不删除 .venv，改用显式解释器路径或按组织策略处理。"}},
            {"error": "已有 .venv 被误删或用错误 Python 重建", "symptom": "之前安装的包消失，或 .venv 版本仍低于 3.11。", "cause": "把创建动作当成清理动作，或在错误 PATH 下重新执行。", "fix": "先点击按钮让后端检查已有环境；只有明确需要重建时才由用户手动决定，并先保存环境证据。", "example": {"code": "Remove-Item -Recurse .venv\npython -m venv .venv", "symptom": "学习依赖和历史环境被删除。", "fix": "不要在课程动作中执行删除；使用幂等创建/验证。"}},
        ],
        "guided_practice": {"goal": "创建并验证 .venv，不要求在编辑器里写 Python。", "starter": "python -m venv .venv\nTest-Path .\\.venv\\Scripts\\python.exe\n.\\.venv\\Scripts\\python.exe --version", "steps": [{"action": "点击“创建 .venv”，阅读创建成功和 Python 可运行两项 checks。", "expected": "后端返回 passed=true，且 .venv Python 路径位于项目根。"}, {"action": "尝试理解激活与显式路径的差别；若策略阻止激活，直接执行 .venv\\Scripts\\python.exe --version。", "expected": "无论是否激活，都能用真实输出证明隔离解释器可运行。"}, {"action": "重复点击创建按钮，观察后端不会删除重建。", "expected": "报告说明已有环境被保留并重新验证，完成状态保持稳定。"}], "check": "存在可运行的 .venv\\Scripts\\python.exe；激活失败也有不依赖激活的继续方案。"},
        "practice": {"kind": "env_action", "action": "create_venv", "scenario": "在项目根创建不会污染全局 Python 的 .venv。", "instructions": "点击“创建 .venv”。后端固定执行当前解释器的 `-m venv .venv`，然后验证 .venv\\Scripts\\python.exe；不要在文本框输入命令。", "expected_behavior": ".venv 创建成功且其 Python 可运行；已有环境不会被删除重建。", "hints": "PowerShell 激活不是必需条件；ExecutionPolicy 报错时阅读说明并使用显式路径。", "starter_content": "", "input_examples": [{"label": "创建", "value": "点击创建 .venv", "expected": "检查 .venv 文件存在且 .venv Python 可运行。"}, {"label": "幂等", "value": "再次点击创建 .venv", "expected": "保留原环境并重新验证，不删除已安装内容。"}]},
        "steps": ["执行固定 venv 创建并检查 Scripts\\python.exe", "理解激活与显式路径两种调用方式", "识别 ExecutionPolicy/已有环境边界"],
    },
    "D01-install": {
        "title": "安装学习工具与测试依赖",
        "objective": "只用项目 .venv 的 Python 调用 pip，以 editable 方式安装当前项目和 dev 依赖；理解安装动作需要联网确认，成功证据是同一解释器能导入 pytest 与 learnctl。",
        "syntax": ".\\.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"",
        "explanation": [
            "` .\\.venv\\Scripts\\python.exe -m pip` 把 pip 绑定到刚创建的解释器；相比裸 `pip`，它不会因为 PATH 顺序改变而把包安装到另一套 Python。`-e .` 是 editable install，源码仍在当前工作区，修改后无需反复复制安装；`.[dev]` 还声明 pytest 等开发依赖。",
            "安装命令会访问包索引，因此网页按钮要求二次确认，后端只执行固定参数，不执行文本框命令。安装输出中的成功/失败、退出码、pytest 导入检查和 learnctl 路径会返回到页面；网络、权限或构建错误应原样作为修复线索。",
            "安装完成不等于测试通过：先用 `.venv\\Scripts\\python.exe -c \"import pytest, learnctl; print(...)\"` 检查导入，再进入最终验证。若 pip 显示已安装但导入失败，优先检查调用的 Python 路径和 editable 指向，不要改用系统 pytest。",
        ],
        "js_bridge": "npm install 与 Python `python -m pip install` 都是包安装动作，但本节强调 Python 解释器和 pip 必须成对；editable install 也不能类比成把源码打包复制。",
        "examples": [
            {"language": "powershell", "code": ".\\.venv\\Scripts\\python.exe -m pip --version\n.\\.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"", "output": "pip 路径位于 .venv；editable 安装完成并安装 dev 依赖", "explanation": "第一行确认 pip 来自 .venv，第二行用固定 Python 安装当前项目和 dev extra；命令中的 `-e .` 让修改直接作用于工作区。安装需要网络和确认，失败时应读取 stderr/exit_code，而不是把“命令已发送”当成功。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
            {"language": "powershell", "code": ".\\.venv\\Scripts\\python.exe -c \"import sys, pytest, learnctl; print(sys.executable); print(pytest.__version__); print(learnctl.__file__)\"", "output": "三行分别是 .venv Python、pytest 版本、当前工作区内 learnctl 路径", "explanation": "这个 probe 同时验证解释器、测试依赖和 editable 包来源，三行输出应能互相对应到项目 .venv 与当前工作区。若 pytest 可导入但 learnctl 路径在别处，editable 安装没有满足本课目标。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
        ],
        "common_errors": [
            {"error": "使用裸 pip 安装", "symptom": "pip 报权限错误，或安装成功后 .venv Python import pytest 失败。", "cause": "pip 命令由 PATH 解析到了系统 Python。", "fix": "改用 `.\\.venv\\Scripts\\python.exe -m pip`，再用同一显式路径 import 验证。", "example": {"code": "pip install -e \".[dev]\"", "symptom": "包进入错误 site-packages。", "fix": "让 Python 选择自己的 -m pip。"}},
            {"error": "网络/构建错误被误认为安装成功", "symptom": "页面显示命令结束，但 exit_code 非 0 或 stderr 有依赖/构建错误。", "cause": "只看 stdout 或按钮点击，没有阅读后端 checks 和退出码。", "fix": "保存失败报告，修复网络、权限或 pyproject 问题后再次确认安装；不切换 provider 或偷偷使用全局包。", "example": {"code": ".\\.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"", "symptom": "ERROR / non-zero exit code。", "fix": "以 stderr 的第一条真实原因定位，再复测。"}},
        ],
        "guided_practice": {"goal": "用同一个 .venv Python 完成安装和导入证据。", "starter": ".\\.venv\\Scripts\\python.exe -m pip --version\n.\\.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"", "steps": [{"action": "确认浏览器提示后点击安装；阅读 pip install check 的状态和 exit_code。", "expected": "成功时安装命令 exit_code=0，失败时页面保留 stderr。"}, {"action": "用固定 probe 检查 sys.executable、pytest.__version__、learnctl.__file__。", "expected": "三个来源都与项目 .venv/工作区对应。"}, {"action": "若失败，只根据 stderr 修复并再次点击；不要把裸 pip 或文本框命令作为替代。", "expected": "复测报告能显示具体修复结果，网络失败不会被静默包装。"}], "check": "`.venv\\Scripts\\python.exe -m pip` 成功，pytest 可导入，learnctl 指向当前项目，三项证据来自后端动作报告。"},
        "practice": {"kind": "env_action", "action": "install", "scenario": "把当前 learnctl 以 editable 方式和 pytest 等 dev 依赖装入 .venv。", "instructions": "确认联网提示后点击安装。后端固定执行 `.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"`；不要要求学员在文本框写代码或命令。", "expected_behavior": "安装退出码为 0，.venv 能导入 pytest，learnctl editable 路径指向当前项目。", "hints": "只看后端返回的 checks、stdout、stderr、exit_code；裸 pip 不是本节的证据。", "starter_content": "", "input_examples": [{"label": "固定安装", "value": "确认后点击安装学习工具与测试依赖", "expected": "固定 pip 命令成功，返回安装输出和退出码。"}, {"label": "导入核验", "value": ".venv\\Scripts\\python.exe -c import pytest, learnctl", "expected": "页面报告 pytest 可导入且 learnctl 指向当前工作区。"}]},
        "steps": ["确认 .venv pip 的来源", "确认联网后执行固定 editable 安装", "阅读导入和安装证据，失败则按 stderr 修复"],
    },
    "D01-verify": {
        "title": "检查环境是否准备完成",
        "objective": "运行最后的固定验证：.venv 版本、固定 Python smoke、pytest 导入、learnctl editable 路径全部通过，才把 D01 视为可复现环境。",
        "syntax": "固定 python -c smoke + pytest import + editable path + exit_code/checks",
        "explanation": [
            "最终验证不是再看一个版本号，而是把运行时、依赖、源码来源和测试入口放在同一份报告里：固定小程序从 `.venv` 执行，pytest 必须能导入，learnctl 必须解析到当前项目，版本必须 >= 3.11。任何一项失败都会让本节保持未完成。",
            "页面会展示每项 check 的名称、passed/detail，以及后端实际 stdout、stderr 和 exit_code；固定 smoke 的 JSON 输出可证明解释器真的执行了代码。读报告时先找第一项失败，再根据路径、缺包、版本或退出码修复，不要只看“动作未通过”。",
            "成功标准是全部 checks 为通过并返回 completed=true，之后 D02 才能解锁；重复验证应该幂等，不会改写项目代码。若测试失败，保留报告中的命令和错误，修复环境后重跑验证，环境证据由后端产生而不是由用户在文本框声称。",
        ],
        "js_bridge": "这类似 CI 的 smoke test，但本节验证的是 Python venv、pytest 和 editable import 的真实链路；Node 的 `npm test` 不能替代 `.venv` Python 的报告。",
        "examples": [
            {"language": "powershell", "code": ".\\.venv\\Scripts\\python.exe -c \"import sys, pytest, learnctl; print(sys.version); print(pytest.__version__); print(learnctl.__file__)\"\n.\\.venv\\Scripts\\python.exe -m pytest -q tool_tests", "output": "版本/依赖/源码路径三行证据；tool_tests 全部 passed", "explanation": "第一条 probe 证明 .venv 能执行 Python、导入 pytest 和当前 learnctl，第二条用同一解释器运行回归测试并返回报告。测试数量和耗时会变化，但 exit_code 必须为 0；任何 traceback 或导入路径异常都应阻止完成。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
            {"language": "powershell", "code": ".\\.venv\\Scripts\\python.exe -m pytest -q tool_tests\n$LASTEXITCODE\nGet-Location", "output": "测试报告；$LASTEXITCODE 为 0；项目根目录", "explanation": "pytest 的报告说明断言是否通过，`$LASTEXITCODE` 把进程退出码带回 PowerShell，Get-Location 再确认命令没有跑到错误目录。只看到“收集到测试”不算成功，必须是退出码 0 且没有失败测试。", "source_kind": "command", "runnable": False, "target_path": "Windows PowerShell"},
        ],
        "common_errors": [
            {"error": "验证使用了系统 pytest 而不是 .venv pytest", "symptom": "裸 pytest 通过，但固定 probe 或后端报告显示 .venv 无法导入 pytest。", "cause": "PowerShell PATH 在激活状态之外指向另一套测试运行器。", "fix": "使用 `.\\.venv\\Scripts\\python.exe -m pytest -q tool_tests`，并检查报告中的解释器与版本。", "example": {"code": "pytest -q tool_tests", "symptom": "通过结果不能证明项目 venv 可复现。", "fix": "改用 .venv Python -m pytest。"}},
            {"error": "只看测试通过，不看 editable 路径和退出码", "symptom": "旧安装版本被测试，或某个 check 失败但页面被误读为成功。", "cause": "没有读取 learnctl.__file__、checks 和 `$LASTEXITCODE`。", "fix": "按报告逐项确认：版本、smoke、pytest、editable 路径和 exit_code 全部通过。", "example": {"code": "$LASTEXITCODE\npython -c \"import learnctl; print(learnctl.__file__)\"", "symptom": "退出码非 0 或路径不在当前项目。", "fix": "回到 install/路径步骤修复后重新 verify。"}},
        ],
        "guided_practice": {"goal": "读懂完整环境报告，并用证据决定 D01 是否完成。", "starter": ".\\.venv\\Scripts\\python.exe -m pytest -q tool_tests\n$LASTEXITCODE", "steps": [{"action": "点击“运行环境验证”，按 check 顺序阅读版本、smoke、pytest、editable 四类结果。", "expected": "能指出每个 check 验证的对象，而不是只看总的 passed。"}, {"action": "展开 stdout/stderr，确认 smoke 输出和错误为空/可解释；记录 exit_code。", "expected": "成功时 exit_code=0、pytest 无失败，learnctl 路径属于当前项目。"}, {"action": "模拟阅读一条失败报告：先定位第一条失败，再回到对应 D01 步骤修复并重跑。", "expected": "不会通过文本框或状态按钮伪造完成，后端报告通过后才推进 D02。"}], "check": "全部 checks 通过、exit_code 为 0、报告路径和版本符合当前项目；重复点击不改变证据含义。"},
        "practice": {"kind": "env_action", "action": "verify", "scenario": "用固定 smoke、pytest 和 editable import 证明环境可复现。", "instructions": "点击“运行环境验证”，阅读后端返回的 checks、stdout、stderr、exit_code 和 completed；本节不提供文本命令编辑器。", "expected_behavior": "版本、固定小程序、pytest 导入、learnctl 当前项目路径全部通过，后端才标记本节完成。", "hints": "先修第一条失败；裸 pytest、旧终端状态和用户输入都不能替代后端证据。", "starter_content": "", "input_examples": [{"label": "固定验证", "value": "点击运行环境验证", "expected": "返回固定 smoke、pytest、editable、版本四类 checks。"}, {"label": "报告阅读", "value": "读取 stdout、stderr、exit_code 与 learnctl 路径", "expected": "exit_code=0 且所有 checks 通过，D02 才解锁。"}]},
        "steps": ["运行固定环境验证", "按 checks/stdout/stderr/exit_code 读取报告", "修复第一条失败并重跑直到全部通过"],
    },
}


def enrich_d01(section: dict[str, Any]) -> dict[str, Any]:
    record = D01_TEACHING[section["id"]]
    result = {
        "id": section["id"],
        "title": record["title"],
        "catalog_refs": list(section.get("catalog_refs", [])),
        "objective": record["objective"],
        "explanation": record["explanation"],
        "syntax": record["syntax"],
        "js_bridge": record["js_bridge"],
        "examples": record["examples"],
        "common_errors": record["common_errors"],
        "guided_practice": record["guided_practice"],
        "practice": record["practice"],
        "key_points": [record["objective"], record["syntax"], "真实动作报告包含 checks、stdout、stderr、exit_code"],
        "frontend_bridge": "本节不要求在文本框模拟命令；点击固定动作后阅读后端真实证据。",
        "example": record["examples"][0],
        "steps": record["steps"],
    }
    if section["id"] != "D01-onboarding":
        result["practice"]["action"] = record["practice"]["action"]
    return result


def build() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    old_tasks = {task["id"]: task for task in data["tasks"]}
    core = core_specs()
    common = common_specs()
    project = project_specs()
    new_titles = {
        "D02": "Python 基础语法一：执行、类型、数字与字符串", "D03": "Python 基础语法二：分支与循环", "D04": "Python 基础语法三：函数、参数与作用域", "D05": "Python 基础语法四：容器、引用与迭代", "D06": "Python 基础语法五：异常、资源与上下文", "D07": "Python 基础语法六：模块、包、类与数据对象",
        "D08": "常用开发一：路径、UTF-8 与 JSON", "D09": "常用开发二：命令行工具", "D10": "常用开发三：配置与环境变量", "D11": "常用开发四：日志", "D12": "常用开发五：HTTP 客户端", "D13": "常用开发六：FastAPI 基础", "D14": "常用开发七：FastAPI 参数与错误", "D15": "常用开发八：pytest 与 mock", "D16": "常用开发九：SQLite", "D17": "常用开发十：asyncio",
        "D18": "真实项目一：需求、验收与契约", "D19": "真实项目二：骨架、配置与入口", "D20": "真实项目三：SQLite 数据层", "D21": "真实项目四：FastAPI 业务层与静态入口", "D22": "真实项目五：测试与验收防线", "D23": "真实项目六：CLI 与原生网页", "D24": "真实项目七：重建、集成与交付",
    }
    old_catalog_refs = {task_id: list(old_tasks[task_id]["lesson"][0].get("catalog_refs", [])) for task_id in old_tasks}
    artifact_map = {
        "D18": ["docs/requirements.md", "contract.json"],
        "D19": ["pyproject.toml", "taskproj/__init__.py", "taskproj/config.py", "taskproj/main.py", "README.md"],
        "D20": ["taskproj/db.py"],
        "D21": ["taskproj/api.py"],
        "D22": ["tests/test_project.py", "tests/test_api.py"],
        "D23": ["taskproj/cli.py", "taskproj/static/index.html"],
        "D24": ["docs/runbook.md", "docs/review.md"],
    }
    for task in data["tasks"]:
        task_id = task["id"]
        if task_id in new_titles:
            task["title"] = new_titles[task_id]
        if task_id in artifact_map:
            task["artifacts"] = artifact_map[task_id]
        if task_id == "D01":
            task["learning_goal"] = "先写下学习目标，再按页面顺序准备并检查这台电脑的 Python 环境。"
            task["lesson"] = [enrich_d01(section) for section in task["lesson"]]
        elif task_id in core:
            task["lesson"] = [make_section(spec, old_catalog_refs[task_id], i) for i, spec in enumerate(core[task_id])]
        elif task_id in common:
            task["lesson"] = [make_section(spec, old_catalog_refs[task_id], i) for i, spec in enumerate(common[task_id])]
        elif task_id in project:
            task["lesson"] = [make_section(spec, old_catalog_refs[task_id], i) for i, spec in enumerate(project[task_id])]
        else:
            task["lesson"] = [enrich_existing(section, i) for i, section in enumerate(task["lesson"])]
    order = [f"D{i:02d}" for i in range(1, 29)]
    for index, task_id in enumerate(order):
        task = old_tasks[task_id]
        task["prerequisites"] = [] if index == 0 else [order[index - 1]]
    # 入门阶段的指引和选修安排与生成数据同源，重建课程时不会丢失。
    sections = {section["id"]: section for task in data["tasks"] for section in task["lesson"]}
    sections["D03-comprehension"]["explanation"].insert(
        0, "列表用 [] 按顺序存值，字典用 {键: 值} 查找值，集合用 {} 保存不重复元素；本节先借用这三种容器，D05 会系统学习。"
    )
    sections["D04-varargs"]["explanation"].insert(
        0, "*args 在函数里是 tuple，**kwargs 是 dict；现在只需按模板读取它们，容器的增删改会在 D05 学习。"
    )
    for section_id in ("D03-match", "D04-global-nonlocal", "D04-lambda",
                       "D05-iterators-generators", "D07-inheritance", "D10-dotenv"):
        sections[section_id]["optional"] = True

    align_beginner_contracts(data)
    add_beginner_drills(data)
    data["schema_version"] = 3
    data["curriculum_version"] = "3.0.0"
    data["meta"]["curriculum_rebuild"] = "v3: Python syntax first, common development second, real project third, AI last"
    data["stages"][0].update({"title": "Python 零基础入门", "goal": "从第一行输出开始，依次掌握变量、判断、循环、函数和容器；每个任务配有离线加练，可反复完成。"})
    data["stages"][1]["title"] = "常用开发能力"
    data["stages"][2]["title"] = "真实 task-manager 项目"
    data["stages"][3].update({"title": "AI 应用（D24 后）", "prerequisites": ["S3"]})
    from practice_first_content import apply_practice_first
    apply_practice_first(data)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()

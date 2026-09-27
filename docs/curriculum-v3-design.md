# Curriculum v3 教学重建设计

## 目标与顺序

v3 面向零 Python 基础学习者。主线只有一条：先完成 D01 环境，再按顺序完成 D02-D07 的 Python 核心语法，随后完成 D08-D17 的常用开发能力，再从零完成 D18-D24 的真实 `task-manager` 项目，最后才进入 D25-D28 的可选 AI 应用。诊断只提供学习建议，不改变主线完成状态；直接 URL 只能查看锁定说明，不能绕过前置小节进行 validate 或 done。

每个必修教学小节都使用同一套明确的数据契约：`objective` 本节目标、`explanation` 至少三段详细概念、`syntax` Python 语法规则、`js_bridge` 仅作辅助对照、`examples` 至少两个含代码/输出/关键行解释的示例、`common_errors` 错误与原因、`guided_practice` 分步引导、`practice` 独立输入式练习与真实本地验证。数据校验拒绝缺字段、空段落、模板化的单一示例和选择题。

## 阶段与任务

| 阶段 | 任务 | 教学目的 | 依赖 |
| --- | --- | --- | --- |
| S1 环境与 Python 语法 | D01 | 准备解释器、虚拟环境、pytest 与工作区 | 无 |
| S1 环境与 Python 语法 | D02-D07 | 完整、连续、可运行地学习 Python 3 核心语法 | 前一任务 |
| S2 常用开发能力 | D08-D17 | 文件/JSON、CLI、配置、日志、HTTP、FastAPI、pytest/mock、SQLite、asyncio | 前一任务 |
| S3 真实项目 | D18-D24 | 从需求到交付完整制作本地 task-manager | 前一任务 |
| S4 AI 应用 | D25-D28 | DeepSeek 调用、提示词、严格解析、mock 测试与复盘 | D24；不影响 D01-D24 |

## D02-D07 核心语法小节（40 节）

### D02 执行模型、名字、类型、数字与字符串

1. `D02-execution` 程序如何执行：顶层语句、缩进块、注释与 Python 3 解释器。
2. `D02-names` 变量命名、赋值、动态类型，以及 `type()` / `isinstance()`。
3. `D02-numbers` `int` / `float`、算术运算、比较结果与精度边界。
4. `D02-bool-none` `bool`、`None`、真值判断与 `is None`。
5. `D02-strings` 字符串字面量、转义、索引、切片与不可变性。
6. `D02-string-methods` 常用字符串方法、清洗顺序与 f-string。

### D03 分支与循环控制

1. `D03-if` `if` / `elif` / `else` 的条件结构与边界。
2. `D03-match` 基础 `match` / `case`，以及何时仍应使用 `if`。
3. `D03-for` `for` 遍历可迭代对象与 `range()`。
4. `D03-while` `while` 循环、循环条件与避免死循环。
5. `D03-break-continue` `break`、`continue` 与提前结束/跳过当前轮。
6. `D03-enumerate-zip` `enumerate()`、`zip()` 与并行遍历。
7. `D03-comprehension` 列表/集合/字典推导式的条件与可读性边界。

### D04 函数、参数、作用域与可调用对象

1. `D04-def-return` 函数定义、调用、参数、`return` 与无返回值。
2. `D04-default-keyword` 默认参数、关键字参数与参数顺序。
3. `D04-varargs` `*args`、`**kwargs` 的收集与解包。
4. `D04-scope` 局部/全局作用域、LEGB 查找与变量遮蔽。
5. `D04-global-nonlocal` `global`、`nonlocal` 与闭包状态。
6. `D04-lambda` 基础 lambda、`sorted(key=...)` 与何时应该写普通函数。
7. `D04-type-hints` 类型标注、返回类型、`Callable` 与运行时不强制。

### D05 容器、引用、复制与迭代

1. `D05-list-tuple` list/tuple 创建、索引、切片、增删改与不可变 tuple。
2. `D05-dict-set` dict/set 创建、访问、增删改与键的约束。
3. `D05-mutability` 可变对象、引用别名、浅复制与 `copy()`。
4. `D05-unpacking` 序列解包、`*` 解包、字典 `**` 合并与常见报错。
5. `D05-traversal` 容器遍历、嵌套数据与安全访问。
6. `D05-comprehensions` 多种推导式的输入、过滤与结果类型。
7. `D05-iterators-generators` 迭代器协议、`iter()` / `next()` 与生成器 `yield`。

### D06 异常、资源与上下文

1. `D06-exception-types` `ValueError`、`TypeError`、`KeyError`、`IndexError` 的区别。
2. `D06-try-except` `try` / `except` 精确捕获与错误信息。
3. `D06-else-finally` `else` / `finally` 的执行时机与清理保证。
4. `D06-raise` 主动 `raise`、异常链与输入校验。
5. `D06-custom` 自定义异常类、继承与业务错误语义。
6. `D06-with` `with`、上下文管理器与文件/锁等资源释放。

### D07 模块、包、标准库与面向对象

1. `D07-import` `import`、`from ... import`、别名与模块命名空间。
2. `D07-package` 包目录、`__init__.py`、绝对导入与相对导入边界。
3. `D07-main` `__name__ == "__main__"` 守卫与可导入入口。
4. `D07-stdlib` `pathlib`、`json`、`datetime` 等标准库的查文档与组合使用。
5. `D07-class-instance` class、实例、属性、方法与 `self`。
6. `D07-inheritance` 继承、`super()`、方法重写与组合优先。
7. `D07-dataclass` `dataclass`、字段默认值与类型标注的协作。

覆盖自审：程序执行/缩进/注释/命名/赋值/动态类型/type/isinstance（D02-1/2）；数字/比较/bool/None/真值（D02-3/4）；字符串全部核心操作与 f-string（D02-5/6）；四种容器、增删改、遍历、可变性、引用复制（D05-1 至 5）；条件、match、循环、range、break/continue、enumerate/zip（D03 全部）；函数参数、作用域、global/nonlocal、lambda、标注（D04 全部）；推导式/迭代器/生成器（D03-7、D05-6/7）；异常全流程、自定义异常、with（D06 全部）；模块/包/`__name__`/标准库/类/继承/dataclass（D07 全部）。矩阵无遗漏。

## D08-D17 常用开发能力

这些任务严格按上一任务末尾继续，下面每行都是一个独立教学小节。每节都必须实现完整教学契约，并把练习写成能运行或能检查具体行为的输入式任务。

### D08 路径、UTF-8 与 JSON

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D08-pathlib` 路径对象与目录遍历 | D07 `D07-stdlib`；无工作区依赖 | 写 `find_python_files(root)`，用 `Path` 找到并排序 `.py` 文件，验证相对路径结果 | `main.py` |
| `D08-utf8` UTF-8 文本读写与编码边界 | `D08-pathlib`；`main.py` | 写 `read_text_utf8(path)` / `write_text_utf8(path, text)`，在临时目录验证中文往返 | `main.py`（延续） |
| `D08-json-read` JSON 数组/对象读取与类型检查 | `D08-utf8`；`main.py` | 写 `load_records(path)`，拒绝非数组、缺少 `title` 的记录 | `main.py`（延续） |
| `D08-json-report` 统计并写出 JSON 报告 | `D08-json-read`；`main.py` | 写 `build_report(records)` / `save_report(path, report)`，断言计数和 UTF-8 JSON 输出 | `main.py`（延续） |

### D09 命令行工具

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D09-parser` argparse 基本参数 | D08 `D08-json-report`；无工作区依赖 | 创建 parser，解析 `--input`、`--output`、`--verbose`，用固定 argv 断言 Namespace | `main.py` |
| `D09-subcommands` 子命令与参数分派 | `D09-parser`；`main.py` | 增加 `report` / `check` 子命令，将解析结果分派到独立函数 | `main.py`（延续） |
| `D09-errors` 参数错误、`parser.error` 与退出码 | `D09-subcommands`；`main.py` | 缺输入、文件不存在、JSON 无效分别给出明确 stderr 与非零退出码 | `main.py`（延续） |
| `D09-entry` 可执行入口与命令行回归 | `D09-errors`；`main.py` | 用子进程运行成功和失败命令，验证 stdout/stderr/exit code | `main.py`（延续） |

### D10 配置与环境变量

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D10-env` 环境变量读取与默认值 | D09 `D09-entry`；无工作区依赖 | 写 `get_env(name, default)`，验证存在、缺失、空字符串策略 | `main.py` |
| `D10-convert` 配置类型转换与错误 | `D10-env`；`main.py` | 写 `get_int_env` / `get_bool_env`，对非法值返回明确错误或默认值 | `main.py`（延续） |
| `D10-dotenv` `.env` 文件解析 | `D10-convert`；`main.py` | 写不依赖第三方库的 `load_dotenv(path)`，处理空行、注释、首尾空白 | `main.py`（延续） |
| `D10-config` 组合成不可变配置对象 | `D10-dotenv`；`main.py` | 用 `dataclass` 生成 `Settings`，验证环境变量优先于 `.env` 和默认值 | `main.py`（延续） |

### D11 日志

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D11-logger` logger、级别与传播 | D10 `D10-config`；无工作区依赖 | 写 `get_logger(name)`，验证级别和重复调用不增加 handler | `main.py` |
| `D11-format` formatter 与结构化上下文 | `D11-logger`；`main.py` | 增加时间、级别、logger 名和消息格式，使用捕获 handler 断言输出 | `main.py`（延续） |
| `D11-stream` 控制台 handler 与错误级别 | `D11-format`；`main.py` | 配置 stdout/stderr 目标和 INFO/WARNING/ERROR 行为 | `main.py`（延续） |
| `D11-file` 文件日志与关闭资源 | `D11-stream`；`main.py` | 写 `configure_file_logging(path)`，在临时目录验证日志落盘和 handler 清理 | `main.py`（延续） |

### D12 HTTP 客户端

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D12-request` urllib 请求对象与 GET | D11 `D11-file`；无工作区依赖 | 写 `get_json(url, opener=...)`，使用 mock opener 断言 method/header/JSON | `main.py` |
| `D12-response` 状态码、响应体与 JSON 错误 | `D12-request`；`main.py` | 区分非 2xx、非法 JSON、缺字段，返回明确自定义异常 | `main.py`（延续） |
| `D12-post` POST JSON 与 Content-Type | `D12-response`；`main.py` | 写 `post_json(url, payload, opener=...)`，mock 断言 UTF-8 body 和 headers | `main.py`（延续） |
| `D12-timeout` timeout、网络错误与可测试边界 | `D12-post`；`main.py` | 将 timeout 作为参数并把 `URLError` 转成业务错误；严禁真实联网 | `main.py`（延续） |

### D13 FastAPI 基础

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D13-app` 创建 FastAPI app 与健康检查 | D12 `D12-timeout`；无工作区依赖 | 创建 app 和 `/health`，用 TestClient 断言 200/JSON | `app.py` |
| `D13-route` 路径参数与查询参数 | `D13-app`；`app.py` | 写 `/items/{item_id}` 与 `limit` 查询参数，验证类型转换和响应 | `app.py`（延续） |
| `D13-response` 响应模型与状态码 | `D13-route`；`app.py` | 增加 Pydantic 响应模型和创建接口的 201 响应 | `app.py`（延续） |
| `D13-lifecycle` 应用生命周期与依赖函数 | `D13-response`；`app.py` | 用 lifespan/依赖函数管理内存资源，在 TestClient 上验证启动与关闭 | `app.py`（延续） |

### D14 FastAPI 参数与错误处理

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D14-model` Pydantic 请求体校验 | D13 `D13-lifecycle`；无工作区依赖 | 定义输入模型，验证必填、长度与类型错误返回 422 | `app.py` |
| `D14-service` 路由与业务函数分离 | `D14-model`；`app.py` | 把业务判断移到纯函数/服务函数，路由只负责输入输出 | `app.py`（延续） |
| `D14-errors` HTTPException 与错误契约 | `D14-service`；`app.py` | 对不存在资源返回 404，对业务冲突返回 409，断言 detail | `app.py`（延续） |
| `D14-deps` 依赖注入与可替换数据源 | `D14-errors`；`app.py` | 用 `Depends` 注入存储，测试时 override dependency，不触碰真实网络 | `app.py`（延续） |

### D15 pytest 与 mock

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D15-assert` pytest 测试函数与断言 | D14 `D14-deps`；无工作区依赖 | 为前序纯函数写成功、边界、异常三类测试 | `test_main.py` |
| `D15-fixture` fixture、tmp_path 与隔离 | `D15-assert`；`main.py` | 用 fixture 创建临时配置/文件，证明测试不依赖当前目录 | `test_main.py`（延续） |
| `D15-mock` patch/mock 隔离 HTTP | `D15-fixture`；`main.py` | mock `urllib` opener，断言调用参数并覆盖异常分支 | `test_client.py` |
| `D15-api` TestClient API 回归 | `D15-mock`；`app.py`、`test_client.py` | 为 FastAPI 路由写请求体、成功、422、404 测试 | `test_api.py` |

### D16 SQLite 标准库

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D16-connect` sqlite3 连接与关闭 | D15 `D15-api`；无工作区依赖 | 写 `create_connection(path)`，验证临时 DB、row_factory 与关闭 | `main.py` |
| `D16-schema` 建表、主键与默认值 | `D16-connect`；`main.py` | 写幂等 `init_db(conn)`，断言表结构和默认 done 值 | `main.py`（延续） |
| `D16-crud` 参数化 SQL 增删改查 | `D16-schema`；`main.py` | 实现 add/list/complete/delete，验证输入作为参数而非 SQL 拼接 | `main.py`（延续） |
| `D16-transaction` 事务、回滚与资源边界 | `D16-crud`；`main.py` | 模拟失败操作，验证 rollback，成功后 commit，补 CRUD pytest | `main.py`、`test_db.py` |

### D17 asyncio 基础

| ID / 标题 | 依赖 | 练习 | 产物 |
| --- | --- | --- | --- |
| `D17-coroutine` async 函数、await 与 asyncio.run | D16 `D16-transaction`；无工作区依赖 | 写可等待的 `fetch_one` mock，并从同步入口运行 | `main.py` |
| `D17-gather` gather 并发聚合与顺序 | `D17-coroutine`；`main.py` | 同时运行多个可控延迟任务，断言结果顺序与总耗时关系 | `main.py`（延续） |
| `D17-timeout` wait_for 超时与取消 | `D17-gather`；`main.py` | 写 `with_timeout(coro, seconds)`，断言 TimeoutError 和取消清理 | `main.py`（延续） |
| `D17-boundary` 异步错误边界与测试 | `D17-timeout`；`main.py` | 用 pytest-asyncio 或 `asyncio.run` 测成功/失败/超时，不调用真实服务 | `main.py`、`test_async.py` |

## D18-D24 真实 task-manager 项目拆分

每个小节只推进一小块真实项目。`工作区依赖` 是必须从前序工作区读取的文件；`本节修改产物` 是本节允许新增或延续修改的文件；验证方式必须能指出具体失败原因。D18-D24 所有小节完成后，才允许 D24 任务 done。

### D18 需求、验收与契约

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D18-scope` 需求边界与用户故事 | D17 `D17-boundary`；无文件 | 写添加/列出/完成/删除四个用户故事和非目标 | `docs/requirements.md` | 文本结构校验四操作、SQLite、本地边界 |
| `D18-acceptance` 验收清单与运行场景 | `D18-scope`；读取 `docs/requirements.md` | 把用户故事拆成可观察的成功/失败场景 | `docs/requirements.md`（延续） | 检查场景覆盖 CRUD、CLI、API、网页 |
| `D18-data-contract` 数据模型与 JSON 契约 | `D18-acceptance`；读取需求文档 | 定义 Task 字段、done 表示、错误响应结构 | `contract.json` | JSON schema/字段和示例值确定性校验 |
| `D18-api-contract` API 路由契约与验收映射 | `D18-data-contract`；读取 `contract.json` | 写 GET/POST/PATCH/DELETE 路径、输入输出和状态码 | `contract.json`（延续） | 契约校验引用全部四类操作和错误码 |

### D19 项目骨架、配置与入口

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D19-pyproject` 打包配置与测试命令 | D18 `D18-api-contract`；读取需求/契约 | 只写项目名、Python 版本、运行依赖和 pytest dev 依赖 | `pyproject.toml` | TOML 解析、build-system、依赖和 pytest 命令检查 |
| `D19-package` 包目录与 `__init__.py` | `D19-pyproject`；读取 `pyproject.toml` | 创建包标记和公开版本常量，不写业务实现 | `taskproj/__init__.py` | 文件存在、可导入、版本字符串检查 |
| `D19-config` 配置模块与数据库路径 | `D19-package`；读取 `taskproj/__init__.py` | 从 `TASKPROJ_DB` 和默认值得到路径，保持纯函数可测 | `taskproj/config.py` | AST/运行测试覆盖环境变量和默认路径 |
| `D19-main` 项目入口 | `D19-config`；读取 config.py | 写最小入口并说明它与 API/CLI 的边界 | `taskproj/main.py` | import/入口运行检查 |
| `D19-readme` README 启动说明 | `D19-main`；读取 `taskproj/main.py` | 单独写从零安装、测试和启动说明 | `README.md` | README 命令、路径和产物引用检查 |

### D20 SQLite 数据层

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D20-connection` 连接生命周期与建表 | D19 全部小节；读取 `taskproj/config.py` | 写 create_connection/init_db，使用 row_factory 和显式关闭 | `taskproj/db.py` | 临时 SQLite 建表和资源边界测试 |
| `D20-create-list` 新增与列表查询 | `D20-connection`；读取 `taskproj/db.py` | 只实现 add_task/list_tasks，参数化 SQL，保持稳定排序 | `taskproj/db.py`（延续） | 真实 sqlite3 CRUD 测试 |
| `D20-update-delete` 完成与删除 | `D20-create-list`；读取同一 db.py | 实现 complete_task/delete_task，区分不存在记录 | `taskproj/db.py`（延续） | 成功、重复、未知 ID 行为测试 |
| `D20-db-tests` 数据层回归与事务 | `D20-update-delete`；读取真实 db.py | 在临时目录中设计测试用例，先验证事务边界；测试文件在 D22 落盘 | 本节无新文件，测试设计作为输入 | 运行/断言临时 SQLite 行为，D22 再写入 `tests/test_project.py` |

### D21 FastAPI 业务层与静态入口

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D21-app` FastAPI app 与 lifespan | D20 `D20-db-tests`；读取 db.py/config.py | 创建 app、连接依赖和 `/health`，不复制数据层实现 | `taskproj/api.py` | TestClient 健康检查和启动关闭测试 |
| `D21-schema` Task 输入/输出模型 | `D21-app`；读取 `contract.json` | 定义标题输入和 Task 响应模型，校验空标题 | `taskproj/api.py`（延续） | 422 响应和返回字段确定性检查 |
| `D21-crud-routes` CRUD 路由和错误 | `D21-schema`；读取 db.py/api.py | 分步接入列表/新增/完成/删除，每节只接一组路由 | `taskproj/api.py`（延续） | TestClient 成功、404、422 测试 |
| `D21-static` 静态首页挂载与错误边界 | `D21-crud-routes`；读取 contract/api.py | 在 API 中挂载 `taskproj/static`，统一处理业务错误，不吞异常；网页文件留到 D23 | `taskproj/api.py`（延续） | API 路径和静态目录挂载检查 |

### D22 项目测试与验收防线

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D22-db-fixtures` 数据层 fixture 与隔离 | D21 全部小节；读取 db.py | 把临时 DB fixture 接到已有 CRUD 测试，不改真实源码 | `tests/test_project.py`（延续） | pytest 临时目录隔离检查 |
| `D22-api-tests` API TestClient 基础回归 | `D22-db-fixtures`；读取 api.py/db.py | 覆盖健康、列表、新增、完成、删除 | `tests/test_api.py` | TestClient 全路由回归 |
| `D22-api-errors` API 错误与边界回归 | `D22-api-tests`；读取 contract.json | 覆盖空标题、未知 ID、重复完成和错误 detail | `tests/test_api.py`（延续） | 422/404/409 等状态码检查 |
| `D22-acceptance` 公开验收脚本与失败定位 | `D22-api-errors`；读取全部项目文件 | 将数据层/API/契约检查串成单一 pytest 命令 | `tests/test_project.py`、`tests/test_api.py`（延续） | 两个测试文件真实运行，输出可定位断言 |

### D23 CLI 与原生网页

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D23-cli-parser` CLI 子命令与共享配置 | D22 `D22-acceptance`；读取 config.py/db.py | 只接 argparse parser、add/list 子命令和共享连接 | `taskproj/cli.py` | 固定 argv 的解析和 add/list 子进程测试 |
| `D23-cli-mutate` CLI 完成/删除与退出码 | `D23-cli-parser`；读取真实 cli.py/db.py | 接入 done/rm、未知 ID 和错误退出码 | `taskproj/cli.py`（延续） | add/list/done/rm 四命令真实运行 |
| `D23-html-structure` 原生网页结构与可访问控件 | `D23-cli-mutate`；读取 contract.json、api.py | 写页面骨架、列表、输入框和按钮，不先堆完整脚本 | `taskproj/static/index.html` | HTML 结构和四类控件检查 |
| `D23-html-fetch` fetch 渲染与 CRUD 交互 | `D23-html-structure`；读取真实 api.py | 分步接入 GET/POST/PATCH/DELETE 和 DOM 更新 | `taskproj/static/index.html`（延续） | 静态 JS fetch 路径、方法和事件检查 |

### D24 重建、集成、runbook 与复盘

| ID / 标题 | 前置/工作区依赖 | 本节练习 | 本节修改产物 | 验证方式 |
| --- | --- | --- | --- | --- |
| `D24-rebuild` 从空目录重建与安装 | D23 全部小节；读取 pyproject/README/全部 taskproj 文件 | 按命令序列创建 venv、安装、建库、跑测试 | `docs/runbook.md` | 临时空 workspace 重建命令检查 |
| `D24-integrate` API/CLI/网页集成演示 | `D24-rebuild`；读取 api.py/cli.py/static/index.html | 记录启动 API、CLI 操作、浏览器操作和预期结果 | `docs/runbook.md`（延续） | 集成验收：pytest、CLI、FastAPI、静态首页 |
| `D24-artifacts` 15 个真实产物核对 | `D24-integrate`；读取全部工作区文件 | 对照 contract 和 runbook 清点 15 个文件，不复制隐藏脚手架 | `docs/runbook.md`（延续） | 文件集合、依赖链、项目验收函数检查 |
| `D24-review` 项目复盘与交付证据 | `D24-artifacts`；读取所有产物和验收输出 | 说明需求到实现、失败修正、复用边界和下一步 | `docs/review.md` | 复盘内容结构与 D24 acceptance 真实通过 |

关键项目依赖必须从前序工作区文件读取，validate 不提供隐藏完整实现。D23 的网页产物明确是 `taskproj/static/index.html`，并由 D21 的 FastAPI 静态挂载连接起来。

## 章节预算与阶段计数

| 阶段 | 任务 | 小节数预算 | 说明 |
| --- | --- | ---: | --- |
| S1 环境与 Python 语法 | D01 | 5 | 环境检测、创建、安装、验证和入门 |
| S1 环境与 Python 语法 | D02-D07 | 40 | 纯 Python 核心语法，逐节顺序门禁 |
| S2 常用开发能力 | D08-D17 | 40 | 每任务 4 节，文件/API/测试/并发能力逐步增加 |
| S3 真实项目 | D18-D24 | 29 | D19 五节，其余任务四节；从契约到交付，不跳写整文件 |
| S4 AI 应用 | D25-D28 | 8 | 保留现有 DeepSeek mock/variation 能力，依赖 D24 |
| **总计** | **D01-D28** | **122** | 其中 D02-D07 40 个核心语法小节，D08-D17 40 个常用开发小节，D18-D24 29 个项目小节 |

每个预算小节都必须有独立 ID、前置关系、输入式练习和确定性验证；不能用增加一大段文字代替拆分小节。

## 迁移策略

课程版本升级到 `3.0.0`。读取旧 schema 2 状态时保留未知字段、诊断报告、evidence、tests 等无害历史；D01 若环境证据仍存在则保留，D02-D24 的旧完成小节和任务 done 状态全部清空/降级为 `in_progress`，D25-D28 也不得在 D24 未完成时开放。迁移只在内存执行，下一次正常保存持久化；不把旧语义 ID 猜测映射到新语义。

# D05–D29 课程审核与本地验收

本轮逐节检查 D05–D28 的 112 节，覆盖题意、例子、补全、独立实验、签名与行为验收；追加 D29 的 3 节系统教学。当前共 29 任务、149 小节、120 张知识卡、217 道补全练习。

## 旧→新映射

- D01–D28 的任务 ID、146 个小节 ID 和既有学习记录保持不变。D18–D24 的 15 个最终产物路径保持不变。
- D05 的 len、比较、raise ValueError 和 tuple 就地教学；函数边界与签名对齐，不添加无关类型校验。
- D06–D28 在当前小节补短卡/不同题局部例，并修正对应行为验收；基础示例和补全不写完成记录。
- D29-tools → agentlab/tools.py；D29-loop → agentlab/runner.py；D29-delivery → tests/test_agentlab.py。三个新节从未完成开始，D29 依赖 D28，不把工具循环暗藏进旧练习。
- curriculum 版本保持 3.0.0，practice_first_revision=2，course_audit_revision=1；已有 v3 记录不触发版本重置。历史 v2→v3 的既有迁移规则没有改动。

## 逐节知识与教学证据

以下记录对应生成来源 scripts/course_readiness_data.json。表中证据用于核对知识出现位置；实际行为由 tool_tests 运行，不把关键词出现当作行为证明。

| 小节（原 ID 保留） | 作业所需知识 | 已教/本节补充证据 |
| --- | --- | --- |
| D05-list-tuple | len、长度比较、raise ValueError、tuple转换 | 本节四张可运行卡和四道渐进补全；D03 zip短卡也已补长度。 |
| D05-dict-set | dict、set、sorted、strip和循环 | 本节set/sorted卡；D02字符串，D03循环。 |
| D05-mutability | 引用、append、copy、浅复制 | 本节两个独立对象示例和输出。 |
| D05-unpacking | 字典合并、星号解包、长度边界、ValueError | 本节解包示例；D05首节已讲len/raise，题面明确两个函数签名。 |
| D05-traversal | 列表遍历、dict.get、缺省值 | D03循环与本节get短卡；标题缺失边界明确。 |
| D05-comprehensions | enumerate、lower、字典/集合推导 | D03 enumerate与推导；本节lower卡和补全。 |
| D05-iterators-generators | iter、next、yield与耗尽 | 本节两个可运行例；保持选修，不作为必修前置。 |
| D05-tags | split、strip、成员判断、set/sorted、join | D02字符串；本节成员判断卡和边界。 |
| D05-counts | dict.get、遍历累加、键值更新 | 本节get计数小例和补全；D03循环。 |
| D05-cart | 取字段、乘法、sum与generator expression | 本节sum小例和补全；D02数值与本节组合。 |
| D06-exception-types | 异常类型、精确捕获、索引/键访问、函数返回 | D02-names教type/isinstance；D05容器访问；本节运行int失败、KeyError捕获。 |
| D06-try-except | int转换、只捕获ValueError、保留TypeError | 本节示例int/except；D02-names已教类型。 |
| D06-else-finally | 成功else、总会finally、events.append | 本节两条例展示else/finally；D03/D05已用append。 |
| D06-raise | None/类型/空白边界、strip、主动raise及异常链 | D02已教None/isinstance；本节positive和from异常链。 |
| D06-custom | 异常子类、pass、strip、业务异常 | 本节SUPPORT解释父类/pass且运行；输入清洗已教。 |
| D06-with | open/read、UTF8、with生命周期 | 本节with文字清楚；运行例却是Path/StringIO。 |
| D06-parse | int、ValueError返回None | D06-try-except已教；本节明确输入字符串、负数/空白合法。 |
| D06-positive | 转换与业务范围分开、raise ValueError | D06-raise已教，本节明确非整数及非正数量拒绝。 |
| D06-average | 空列表、总和/个数、除法、不修改输入 | len由D05修复；sum在D04-varargs运行例出现；循环和除法已教。 |
| D07-import | import/from/as、math.ceil、Path.suffix | 本节math.ceil及Path.name短例。 |
| D07-package | 模块文件、from导入、调用平台函数 | import此前已教；生效验证器提供helpers.py。 |
| D07-main | __name__守卫、导入与直接执行分离 | 本节文字和运行例明确。 |
| D07-stdlib | UTF8读文件、JSON解析、dict/name类型检查 | 本节SUPPORT只演示loads字符串；Path前节已教。 |
| D07-class-instance | class/self/__init__、独立实例状态 | 本节完整教学和两个运行例。 |
| D07-inheritance | 继承、super初始化、方法重写 | 本節示例用super扩展方法，但没有子类构造调用父类。 |
| D07-dataclass | 类型标注、装饰器、字段、repr/default_factory | D04类型标注、本节DECORATOR短卡及field运行例。 |
| D07-slug | strip/lower/replace、导入无副作用 | strip/lower此前已教；D07-main守卫已教。 |
| D07-counter | 实例状态、+=、方法返回 | D07-class-instance已教且运行Counter雏形。 |
| D07-dataclass-total | dataclass字段、自定义方法、self、乘法 | D07-dataclass/class-instance已教；本节说明price/quantity。 |
| D08-pathlib | Path/glob/name排序、exists/is_file | Path/name/suffix已教；本节例运行/与glob。 |
| D08-utf8 | read_text/write_text、encoding、splitlines | 本节明确UTF8并运行往返。 |
| D08-json-read | loads、dict/字段类型、strip、JSONDecodeError | D07-stdlib补后已有读取/解析；本节JSON和错误例。 |
| D08-json-report | 计数、JSON文件序列化、UTF8 | 循环/len/sum此前已教，生成器表达式在D05例出现。 |
| D08-read-lines | 读取、splitlines、strip、循环过滤 | 补D08-utf8短卡后此前覆盖；本节说明空行规则。 |
| D08-json-total | JSON列表读取、amount求和、空输入、解析错误 | D07/D08读取及解析、D04-varargs的sum、循环已教。 |
| D08-json-report-drill | len、构造字典、UTF8写JSON、不转义 | 修复D08-json-report后覆盖；本节明确文件内容。 |
| D09-parser | ArgumentParser/add_argument/parse_args、int/default、开关 | 本节两个运行例有类型/默认/位置参数。 |
| D09-subcommands | 子parser、required、set_defaults与args.func | 本节运行例只教选择子命令和TITLE。 |
| D09-errors | SystemExit(2)、stderr、参数错误 | 本节文字解释精确退出码，例捕获SystemExit。 |
| D09-entry | main(argv=None)、guard、退出码、subprocess回归 | 本节短卡SystemExit；D07-main已教守卫。 |
| D09-greet-cli | required选项、help、参数输出 | D09-parser已教，当前解释required及help。 |
| D09-repeat-cli | int与范围校验、parser.error、循环输出 | 类型/比较/循环已教，本节文字点明parser.error。 |
| D09-square-cli | 整数位置参数、平方、可导入函数、守卫 | D09-parser/entry及D07-main覆盖。 |
| D10-env | os.environ、get默认、空值、None映射注入 | 本节运行os.environ.get；默认参数/None此前已教。 |
| D10-convert | strip/lower/in/集合、int与端口范围、raise | 前置基础已教，本节as_bool运行例。 |
| D10-dotenv | 逐行读取、strip、startswith、split maxsplit=1、缺失文件 | 读取/split/strip此前已教；本节有首次等号例。 |
| D10-config | dataclass配置、classmethod/cls、转换及默认 | dataclass和转换此前已教。 |
| D11-logger | getLogger、级别、handler、传播、重复初始化 | 本节文字有概念，例只数NullHandler。 |
| D11-format | Formatter字段、参数化消息、logger.exception | 本节LogRecord/Formatter运行例；异常此前已教。 |
| D11-stream | StringIO、StreamHandler、双层级别、清理 | 本節完整运行INFO被过滤/WARNING保留及getvalue。 |
| D11-file | UTF8 FileHandler、格式、flush/close/removeHandler、重复setup | 本节两例及说明覆盖基本API。 |
| D12-request | Request/GET；可调用参数；with；read bytes→decode | D06-with已有StringIO.read；D12两卡教函数参数和bytes；Request字段实验 |
| D12-response | status/2xx比较；decode；json.loads；RuntimeError与JSONDecodeError传播 | 本节200<=status<300实验；D08-json-read；D06-raise示范RuntimeError/异常传播 |
| D12-post | dumps→encode→POST Request；Content-Type；with/read/loads | D08-json-report dumps/ensure_ascii；本节POST构造实验与bytes/callable卡 |
| D12-timeout | GET；timeout关键字；异常传播；单次调用 | 本节fake_open记录timeout与抛TimeoutError；D04-default-keyword；D06-raise |
| D13-app | FastAPI；装饰器注册；dict响应；导入不启动；真实路由请求 | D13装饰器卡；D07-import/主入口；例只直接health() |
| D13-route | 路径模板同名参数；查询默认值；框架类型转换/422 | D13-app注册语法；D04-type-hints说明Python不自动校验；本节口述路径/query |
| D13-response | BaseModel字段模板；response_model；status_code；POST | D07-class-instance；本节模型卡/model_dump实验 |
| D13-lifecycle | yield资源分界；asynccontextmanager；lifespan；Depends；生命周期TestClient | D13明确D17后选修；当前同步contextmanager例 |
| D14-model | BaseModel必填/default；model_dump；ValidationError≠HTTP422 | D13响应模型卡；本节直接构造/缺title实际异常 |
| D14-service | strip/空文本判定/ValueError；传入repo.add；业务与路由分离 | D02-string-methods、D02-bool-none、D06-raise、D07-class-instance；本节空白拒绝实验 |
| D14-errors | repo.get结果None判断；HTTPException404/detail；保留原对象 | D02 is None；本节HTTPException对象字段与raise示例 |
| D14-deps | Depends传函数/框架调用；provider替换；override清理 | D12callable卡；本节说明Depends与dependency_overrides；starter给标记 |
| D15-assert | test_收集/实际assert；被测函数；正常边界；pytest命令 | 本节解释test_和AssertionError；D04函数；当前实验只有顶层assert |
| D15-fixture | @pytest.fixture；同名参数注入；tmp_path Path/function隔离 | D08-pathlib/UTF8；D13装饰器；starter有完整note_path |
| D15-mock | Mock/MagicMock；with响应；patch查找位置；call_args；参数断言 | D12函数注入；本节Mock/patch.object例与MagicMock starter |
| D15-api | TestClient真实GET/POST(json=)；app fixture；200/201/404及字段 | D13app；D15fixture；本节文字与starterTestClient |
| D16-connect | sqlite3.connect；:memory:/文件路径；连接所有权；close | 本节查询select1、关闭后ProgrammingError；已有with不close卡 |
| D16-schema | CREATE/IF NOT EXISTS；PRIMARYKEY/NOTNULL/DEFAULT；游标fetch | 本节建表/PRAGMA/default实验；D05索引 |
| D16-crud | INSERT/SELECT/UPDATE/DELETE/WHERE/参数tuple；lastrowid/fetchall/rowcount；bool字段 | 当前只INSERT/?/rowcount实验；D05tuple/dict、D02bool |
| D16-transaction | commit/rollback；异常重新raise；多个操作原子性；借入连接不关闭 | D06 try/裸raise；本节with conn成功/失败计数实验 |
| D17-coroutine | async def/coroutine执行时机；await；sleep(0)；run入口 | 本节完整async main/await卡及让出控制权实验 |
| D17-gather | 多个coroutine；*展开动态列表；gather结果按输入顺序 | D04-varargs必修文字明确调用*；本节gather两个固定参数实验 |
| D17-timeout | wait_for(awaitable,timeout)；超时取消；finally传播 | 本节成功/超时实验；D06with/finally概念；starter给slow |
| D17-boundary | await处异常；只捕获ValueError；Task/create_task/cancel/await；finally | D06异常分类；本节只是正常run与外层ValueError |
| D18-scope | 用户故事；边界；非目标 | 本节Given/When/Then；D14错误边界 |
| D18-acceptance | 场景；状态码；状态变化 | D13/D14状态；本节场景 |
| D18-data-contract | JSON；输入/输出；样例值/类型标记 | D08 JSON；validate_contract实际约定 |
| D18-api-contract | 路由；对象数组；状态码；保留前节 | D13/D14；validate_contract六条路由 |
| D19-pyproject | TOML；build-system；运行/dev依赖；包/测试发现 | D01安装；validate_project_file依赖要求 |
| D19-package | 传统包；初始化；导入副作用 | D07包/导入 |
| D19-config | env非空fallback；Path | D10-env；D08 Path |
| D19-main | main；守卫；退出码；导入无副作用 | D07/D09 |
| D19-readme | 安装/测试说明；当前/未来入口 | D01及D19 |
| D20-connection | 连接；Row；schema；commit/close | D16连接/建表/事务，Row术语 |
| D20-create-list | 参数SQL；lastrowid；Row转dict；bool；排序 | D16 CRUD；D05推导式 |
| D20-update-delete | UPDATE/DELETE；rowcount；commit；bool | D16 rowcount仅出现 |
| D20-db-tests | fixture；导入真实函数；隔离连接；行为断言 | D15；D16 |
| D21-app | asynccontextmanager；yield资源；lifespan；Depends；TestClient上下文 | D17 async；D14依赖，前期生命周期为选修 |
| D21-schema | BaseModel；field_validator；classmethod；strip；ValidationError | D14模型；当前卡缺cls说明 |
| D21-crud-routes | Depends；真实DB函数；HTTP映射 | D13/D14/D20与模型 |
| D21-static | __file__；Path.parent；FileResponse | D08路径；本节响应 |
| D22-db-fixtures | pytest注入；tmp_path；yield/finally；隔离连接 | D15 fixture；D21资源 |
| D22-api-tests | TestClient上下文；override函数映射；monkeypatch；临时DB | D15 API；D14依赖；D21生命周期 |
| D22-api-errors | 422/404；detail；不写库；重复删除 | D14错误；前节客户端 |
| D22-acceptance | 读contract；当前API/DB；分步边界 | D08；D20/D21 |
| D23-cli-parser | argparse子命令；dispatch；共享配置；连接所有权 | D09；D19；D20 |
| D23-cli-mutate | done/rm；整数参数；stderr；退出码 | D09错误；D20 |
| D23-html-structure | 完整HTML；label/id；button type；空/错误区域 | 用户开发经验；本节控件 |
| D23-html-fetch | fetch协议；JSON body；response.ok；textContent；错误状态 | 已有JS经验；D12/D21协议 |
| D24-rebuild | 源码副本；临时目录；venv解释器；dev安装；pytest | D01环境；D18-D23产物 |
| D24-integrate | 同一DB；三入口；启动停止；证据 | D19-D23 |
| D24-artifacts | 15文件映射；存在性；排除项；阶段/最终边界 | _PROJECT_REQUIRED_FILES；D08 exists |
| D24-review | 证据；failure/fix；取舍；下一步；最终验收 | 前课实际产物 |
| D25-chat | 请求体/POST/鉴权/超时/嵌套响应提取 | D12-post 示例完整讲 Request(data=JSON bytes, method, headers)；D12-request 讲响应 with/read；D12-timeout 讲超时真实调用点；D04-default-keyword 仅教普通关键字；单独 * 未明确讲；当前例子仅请求体序列化与模拟响应嵌套提取；BYTES 卡已给 encode/decode |
| D25-errors | ApiError(status_code)、HTTP 非200/网络/坏JSON分别转换 | D06-custom 异常类型；D07-inheritance 讲 super/属性；D12-response 讲 JSONDecodeError；D12-timeout 只描述 HTTPError/URLError；本节演示 HTTPError.code 与 JSONDecodeError 两条 |
| D26-prompt | 逐标题范围、索引边界、目标/要求/完成状态 | D02-string-methods 已教 join、f-string；D03 循环与 D05 容器已教；本节两个例子展示标题/目标与完成状态/要求 |
| D26-parse | 定位一段JSON对象、解析，缺失/错误抛ValueError | D08-json-read 与 D12-response 已教 JSON/JSONDecodeError；D02字符串课讲 strip/split/join，未讲 find/rfind；当前示例直接 text.find、rfind 和切片组合 |
| D27-client | 消息封装，call_chat→parse_ai_json | D07-import、D25/D26 接口；当前两例展示消息和文本→dict；平台确实写入 deepseek_client.py 与 prompt.py |
| D27-flow | build_prompt/send_message组合，四字段齐全后返回，否则ValueError | D26-prompt；D27-client；D05 dict/set 已讲基本创建与修改；没有任何前课例子教 keys() 或 set <=、set -；本节直接使用 |
| D28-test | 离线mock：正常、401、非JSON均真实行为断言 | D15-mock 有 Mock(return_value)/assert_called_once_with 与 patch.object恢复；D15前课没有 __enter__.return_value、side_effect、pytest.raises 示例；本节仅 Mock.read.return_value 与 HTTPError构造两个例子 |
| D28-review | 3-5句能力、mock、索引边界、重建交付证据 | D24-artifacts/runbook/review 已要求实际命令/错误/修正文件；当前例子仅两句话复盘方向，无Python新语法 |

## 验收与限制

- 确定性失败优先；AI 按当前作业完整要求生成题目专属自然语言解析，逐项核对完成/未完成/待确认，引用本次代码行与运行证据，提供三级思考问题。结构、证据与常见答案泄露形态校验拦截不可信输出；缺少上下文明示限制，不向模型发送私有参考实现。自然语言判断可能误判，不能用结构校验声称语义完全可靠。
- 固定代码执行、JSON/TOML/文本/命令、环境动作、补全、示例、诊断与白名单 pytest 入口均绑定服务端本次真实结果。AI 变式没有固定行为 oracle，界面明确只提供辅助评审，不记课程通过。
- AI 变式传本节公开知识卡、示例、规则和已完成前序必修教学；拒绝未教导入/调用名称。这是范围检查，不能证明任意生成题在语义上完全正确。
- 教学卡/补全/例子的 Python 实际执行并比对输出，未修改补全起始代码不得通过。测试课程用错误实现检验学生测试是否发现故障，采集/语法错误不算检出。
- HTTP/AI 练习使用本地假 HTTP 或离线 mock；API 客户端、异步、日志、SQLite、项目分步与最终验收执行真实行为。实验有临时目录、限时与输出限制，仍不是安全沙箱。
- 浏览器回归只使用临时工作区和临时服务：逐节教学→示例→补全→作业顺序、当前语法说明、移动端宽度、AI 不给答案、结果冲突和竞态。没有操作活动学习页面。
- 本轮最终回归阻断真实 DeepSeek transport。真实模型反馈质量和费用未验证；不能用 mock 结果宣称真实模型效果。
- 本任务未重启活动服务或刷新学习页面。加载本地后端修改前，请先保存编辑器与内存中的实验/变式内容，再安全启动或重启服务。
- 本地测试、构建与浏览器结果见实际执行日志；没有创建分支/PR、提交、推送、部署或触发 CI。

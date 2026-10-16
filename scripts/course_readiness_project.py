"""BUILD-time D18-D24 teaching overlay. Call apply(data) after practice-first.
Stable IDs/paths; no learner-state or runtime writes. Parent owns validators."""
from __future__ import annotations
import copy
from typing import Any


def card(title, rule, code, output):
    return dict(title=title, rule=rule, code=code, output=output, source_kind="python", runnable=True)


def gap(identifier, title, item, old, new, instruction):
    assert old in item["code"]
    return dict(id=identifier, title=title, instructions=instruction, starter=item["code"].replace(old,new,1),
                reference=item["code"], output=item["output"], source_kind="python", runnable=True)


TOML = card("TOML：表、字符串和数组",
    "作用：保存项目配置。常用：名称、版本和依赖。写法：[表名]切换表，文本用引号，多个值用数组；dev是开发依赖组，安装.[dev]时选择。",
    "import tomllib\ntext = '''\n[project]\nname = \"demo-notes\"\nversion = \"0.1.0\"\n[project.optional-dependencies]\ndev = [\"pytest>=8\"]\n'''\ndata = tomllib.loads(text)\nprint(data['project']['name'])\nprint(data['project']['optional-dependencies']['dev'])\n", "demo-notes\n['pytest>=8']")
ROW = card("sqlite3.Row：按列名读查询结果",
    "作用：row_factory改变查询结果表示。常用：按列名取值、序列化结果。写法：连接设置sqlite3.Row，dict(row)转字典；SQLite的0/1用bool(value)转真假。",
    "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.row_factory = sqlite3.Row\ntry:\n    row = conn.execute('SELECT 7 AS code, 1 AS active').fetchone()\n    print(dict(row))\n    print(bool(row['active']))\nfinally:\n    conn.close()\n", "{'code': 7, 'active': 1}\nTrue")
INSERT = card("lastrowid：读取刚插入的编号",
    "作用：cursor.lastrowid提供插入行编号。常用：新增后继续查询。写法：保存execute返回的cursor，成功commit后读取编号；execute返回对象不是业务记录。",
    "import sqlite3\nconn = sqlite3.connect(':memory:')\ntry:\n    conn.execute('CREATE TABLE labels (id INTEGER PRIMARY KEY, text TEXT)')\n    cursor = conn.execute('INSERT INTO labels(text) VALUES (?)', ('绿色',))\n    conn.commit()\n    print(cursor.lastrowid)\n    print(conn.execute('SELECT text FROM labels').fetchone()[0])\nfinally:\n    conn.close()\n", "1\n绿色")
ROWCOUNT = card("rowcount：区分命中与不存在",
    "作用：cursor.rowcount记录UPDATE/DELETE影响行数。常用：识别目标不存在。写法：保存execute返回的cursor，以rowcount大于0形成bool，成功提交；零行不能宣称成功。",
    "import sqlite3\nconn = sqlite3.connect(':memory:')\ntry:\n    conn.execute('CREATE TABLE labels (id INTEGER PRIMARY KEY, text TEXT)')\n    conn.execute('INSERT INTO labels(text) VALUES (?)', ('绿色',))\n    cursor = conn.execute('DELETE FROM labels WHERE id = ?', (999,))\n    conn.commit()\n    print(cursor.rowcount)\n    print(cursor.rowcount > 0)\nfinally:\n    conn.close()\n", "0\nFalse")
ASYNC = card("asynccontextmanager：进入、使用、清理",
    "作用：把async生成器变成异步资源边界。常用：应用启动/关闭。写法：装饰器配yield，yield前准备，finally清理，async with进入/退出。FastAPI接收lifespan函数，import不调用它。",
    "import asyncio\nfrom contextlib import asynccontextmanager\nevents = []\n@asynccontextmanager\nasync def session():\n    events.append('准备')\n    try:\n        yield '演示资源'\n    finally:\n        events.append('清理')\nasync def run():\n    async with session() as resource:\n        events.append(resource)\nasyncio.run(run())\nprint(events)\n", "['准备', '演示资源', '清理']")
REQUEST = card("yield依赖：请求借用后释放",
    "作用：yield提供资源，请求结束后清理。常用：请求连接。写法：Depends接收依赖函数，依赖try/yield/finally；不能先关闭后提供。请求级与应用级资源分别安排清理。",
    "from fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\nevents = []\ndef get_label():\n    events.append('准备')\n    try:\n        yield '颜色'\n    finally:\n        events.append('释放')\ndemo = FastAPI()\n@demo.get('/label')\ndef label(value=Depends(get_label)):\n    return {'value': value}\nwith TestClient(demo) as client:\n    print(client.get('/label').json())\nprint(events)\n", "{'value': '颜色'}\n['准备', '释放']")
VALIDATOR = card("field_validator与classmethod",
    "作用：清洗或拒绝字段输入。常用：拒绝纯空白。写法：field_validator指定字段，classmethod让cls接收类，value接收字段值；返回清洗值，raise ValueError拒绝并包装成ValidationError。",
    "from pydantic import BaseModel, ValidationError, field_validator\nclass Nickname(BaseModel):\n    name: str\n    @field_validator('name')\n    @classmethod\n    def clean(cls, value):\n        value = value.strip()\n        if not value:\n            raise ValueError('昵称不能为空')\n        return value\nprint(Nickname(name=' 小林 ').name)\ntry:\n    Nickname(name='   ')\nexcept ValidationError:\n    print('昵称无效')\n", "小林\n昵称无效")
FIXTURE = card("资源外壳：finally保证归还",
    "作用：清理与成功/失败路径分离。常用：pytest fixture在yield后关闭资源。写法：准备后try/yield/finally；下面contextmanager展示相同借用顺序，正式测试用pytest.fixture和参数注入。",
    "from contextlib import contextmanager\nevents = []\n@contextmanager\ndef resource():\n    events.append('准备')\n    try:\n        yield '测试资源'\n    finally:\n        events.append('归还')\ntry:\n    with resource() as value:\n        events.append(value)\n        raise ValueError('模拟失败')\nexcept ValueError:\n    events.append('已定位')\nprint(events)\n", "['准备', '测试资源', '归还', '已定位']")
OVERRIDE = card("dependency_overrides：替换函数并恢复",
    "作用：测试替换请求依赖。常用：临时配置/假资源。写法：键为原依赖函数，值为替代函数；通过with TestClient请求，finally清除覆盖，不污染下一例，无需lambda。",
    "from fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\ndef read_flag():\n    return False\ndef fake_flag():\n    return True\ndemo = FastAPI()\n@demo.get('/flag')\ndef flag(value=Depends(read_flag)):\n    return {'value': value}\ndemo.dependency_overrides[read_flag] = fake_flag\ntry:\n    with TestClient(demo) as client:\n        print(client.get('/flag').json())\nfinally:\n    demo.dependency_overrides.clear()\nprint(len(demo.dependency_overrides))\n", "{'value': True}\n0")
ENV = card("monkeypatch.setenv：测试后恢复环境",
    "作用：临时改变被测环境。常用：隔离路径/开关，测试结束恢复。写法：pytest测试参数monkeypatch，调用setenv(name,value)；下方context只演示恢复顺序，不读取现有环境全集。",
    "import os\nfrom pytest import MonkeyPatch\nwith MonkeyPatch.context() as change:\n    change.setenv('LEARNCTL_CARD_DEMO', '临时值')\n    print(os.environ['LEARNCTL_CARD_DEMO'])\n    change.delenv('LEARNCTL_CARD_DEMO')\n    print(os.environ.get('LEARNCTL_CARD_DEMO', '无临时值'))\n", "临时值\n无临时值")
STDERR = card("print的file参数：错误写stderr",
    "作用：file参数选择输出通道。常用：CLI错误stderr，成功stdout。写法：print(message,file=sys.stderr)；main返回非零整数，入口SystemExit交给终端。下方错误文字在stderr栏。",
    "import sys\nprint('名称缺失', file=sys.stderr)\nprint('错误提示已写入 stderr')\n", "错误提示已写入 stderr")
ANCHOR = card("__file__：从当前模块定位邻接文件",
    "作用：表示当前模块位置。常用：从包目录找资源，不依赖启动cwd。写法：Path(__file__).parent取所在目录，再/组合；此例只看固定文件名，不读取文件。",
    "from pathlib import Path\nmodule_path = Path(__file__)\nresource = module_path.parent / 'assets' / 'logo.svg'\nprint(resource.name)\nprint(resource.suffix)\n", "logo.svg\n.svg")
EMPTY = card("HTTP 204：跳过响应体解析",
    "作用：判断响应是否有正文。常用：兼容204无JSON响应。写法：先检查成功，再判断204；当前任务项目删除固定200 JSON，兼容分支不改变项目契约。",
    "status = 204\nprint('无响应体' if status == 204 else '解析 JSON')\n", "无响应体")


def ex(path, code, output, why="", kind="file_fragment", language="python"):
    prefix = "# " + path + "\n" if kind == "file_fragment" else ""
    return dict(language=language, code=prefix+code, output=output,
        explanation=why or "不同业务的局部写法，不是当前正式题完整答案。",
        source_kind=kind, runnable=False, target_path=path)


def tx(path, code, output, why=""):
    return ex(path,code,output,why,language="text")


def jx(code, output, why):
    return ex("contract.json",code,output,why,"json_fragment","json")


def jsx(code, output, why):
    return ex("taskproj/static/index.html",code,output,why,"javascript","javascript")


def cmd(code, output, why):
    return ex("docs/runbook.md",code,output,why,"command","text")


UPDATES = {}
COVERAGE = []
def lesson(sid, requires, evidence, gaps, instructions, explanations, syntax, steps,
           expected, examples, starter=None, cards=None, drills=None, deps=None, provided=None, inputs=None):
    COVERAGE.append(dict(section=sid,requires=requires,evidence=evidence,gaps=gaps))
    patch = dict(instructions=instructions,explanation=explanations,syntax=syntax,steps=steps,expected=expected,examples=examples)
    for key,value in dict(starter=starter,cards=cards,drills=drills,deps=deps,provided=provided,inputs=inputs).items():
        if value is not None: patch[key] = value
    UPDATES[sid] = patch


lesson("D18-scope", ["用户故事","边界","非目标"], "本节Given/When/Then；D14错误边界", ["文本验收仅长度/关键词"],
    "编辑docs/requirements.md，写添加/列表/完成/删除四个用户故事的输入和可观察结果；补空白标题、未知ID及非目标。写行为，不写SQL/函数实现。",
    ["用户故事写谁、做什么、成功后看到什么。边界说明拒绝什么，非目标说明这一轮不实现什么。",
     "本节只创建需求文件；后续API、CLI、网页共同遵守它，不提前生成实现。"],
    "用户故事=角色+动作+结果；边界与非目标单列。",
    ["写四个动作的输入和结果。","补空白/未知ID拒绝规则与非目标。","核对规则能被验收，移除实现细节。"],
    "四个动作可验收；成功/失败与非目标明确。",
    [tx("docs/requirements.md","## 用户故事格式\n- Given 有一张便签，When 按编号归档，Then 不再出现在未归档列表。","不同业务的状态变化。"),
     tx("docs/requirements.md","## 本轮边界\n- 非目标：便签共享/账户权限。\n- 非法输入：内容只有空白时拒绝。","不同业务的非目标与边界。")])

lesson("D18-acceptance", ["场景","状态码","状态变化"], "D13/D14状态；本节场景", ["旧PATCH路径缺/done"],
    "继续docs/requirements.md，补主流程、错误流程的请求/预期/定位。固定POST创建、GET列表、PATCH /api/tasks/{task_id}/done完成、DELETE删除；空标题422、未知ID404、删除200 JSON。",
    ["每一步至少有字段、状态码或stdout可比較，不只写正常。",
     "现在写验收计划，不要求API/CLI已经存在。完成路径固定/done，删除固定200 JSON。"],
    "场景=输入/操作/预期/失败定位。",
    ["列主流程各步状态变化。","补空白、未知ID、重复删除。","把模糊结果写成字段/状态码。"],
    "场景可指导真实测试，方法/路径/状态一致。",
    [tx("docs/requirements.md","## 场景格式（便签）\n1. 新建获得编号。\n2. 列表含编号。\n3. 归档后不在未归档列表。","不同业务的逐步验收。"),
     tx("docs/requirements.md","| 输入 | 预期 | 定位 |\n| 未知便签编号 | 404 | 检查资源 |\n| 空白内容 | 422 | 检查输入验证 |","错误同时有结果与定位。")],
    starter="# docs/requirements.md\n## 主流程\n# 补请求与预期\n## 错误流程\n# 补边界与定位\n")

lesson("D18-data-contract", ["JSON","输入/输出","样例值/类型标记"], "D08 JSON；validate_contract实际约定", ["输出类型字符串冲突","错误键名冲突","starter完整通过"],
    '只写数据契约：task.input.title为"string"类型标记；task.output含整数id、字符串title、布尔done的样例值；errors固定empty_title=422、unknown_id=404。不检查endpoints。',
    ["JSON双引号，布尔true/false，空值null；解析后才是Python True/False/None。",
     "本项目简单约定：input.title写string标记，output写真实类型样例，不写id='integer'、done='boolean'。",
     "errors固定empty_title/unknown_id；路由表下一节补。"],
    "input用约定类型标记；output用真实JSON类型样例。",
    ["填input标记。","填三种类型output。","核两种错误，验证真实JSON类型。"],
    "task/errors结构及真实类型正确。",
    [jx('{"note":{"input":{"body":"string"},"output":{"note_id":7,"body":"示例","archived":false}}}',"不同资源类型标记与样例值分开。","任务字段按正式要求填写，不照搬便签键。"),
     jx('{"errors":{"bad_body":422,"missing_note":404}}',"不同资源的输入/不存在错误。","任务错误名称由题目固定。")],
    starter='{\n  "task": {"input": {"title": ""}, "output": {"id": null, "title": "", "done": null}},\n  "errors": {"empty_title": null, "unknown_id": null}\n}\n',
    inputs=[("output整数/字符串/布尔","三字段保持真实类型"),("done字符串","类型验证失败")])

lesson("D18-api-contract", ["路由","对象数组","状态码","保留前节"], "D13/D14；validate_contract六条路由", ["routes/endpoints冲突","错误键冲突","旧GET单任务例不存在"],
    "保留task/errors，添加endpoints对象数组：GET /、GET /health、GET /api/tasks、POST /api/tasks、PATCH /api/tasks/{task_id}/done、DELETE /api/tasks/{task_id}。每项method/path；创建201、删除200 JSON，非法422、未知404。",
    ["endpoints是JSON对象数组，每项method/path与后续实现一致。",
     "本项目不要求GET单个任务；PATCH /done不需要done请求体。",
     "保留task和empty_title/unknown_id，不改名为routes/missing/invalid。"],
    "method/path共同识别接口；endpoints对象数组。",
    ["打开前节contract保留原字段。","逐项补六条接口。","核POST201/DELETE200 JSON/404/422。"],
    "数据契约保留，六条方法/路径一致。",
    [jx('{"endpoints":[{"method":"POST","path":"/api/notes","status":201},{"method":"DELETE","path":"/api/notes/{note_id}","status":200}]}',"不同资源接口数组。","只示范结构，任务路由自行填写。"),
     jx('{"errors":{"bad_body":422,"missing_note":404}}',"不同资源错误对象。","任务仍保留正式错误键名。")],
    starter='{\n  "task": {"input": {"title": ""}, "output": {"id": null, "title": "", "done": null}},\n  "errors": {"empty_title": null, "unknown_id": null},\n  "endpoints": []\n}\n',
    inputs=[("POST /api/tasks正常title","201 JSON task"),("PATCH /api/tasks/999/done","404 detail")])

lesson("D19-pyproject", ["TOML","build-system","运行/dev依赖","包/测试发现"], "D01安装；validate_project_file依赖要求", ["必需依赖没教","未创建包就要求安装成功"],
    '编辑pyproject.toml：项目名/版本、Python>=3.11、setuptools构建后端、taskproj包发现和tests路径；运行fastapi/uvicorn/pydantic，dev pytest/httpx。当前只验证TOML；完整副本后安装-e ".[dev]"。',
    ["[project]保存name/version/requires-python/dependencies；[project.optional-dependencies]的dev保存pytest/httpx。",
     "[build-system]用requires=['setuptools>=68']和build-backend='setuptools.build_meta'指定构建；[tool.setuptools.packages.find]的include限制taskproj*。",
     "[tool.pytest.ini_options]的testpaths=['tests']控制发现。包/测试后续才创建，此刻不要求实际安装/collect-only成功。"],
    "TOML表/引号/数组；运行与dev依赖分开。",
    ["解析元数据/构建表。","补依赖/包发现/pytest目录。","配置验证，完整安装留D24。"],
    "配置可解析，构建/运行/dev依赖齐，路径一致。",
    [tx("pyproject.toml",'[project]\nname = "demo-notes"\nversion = "0.1.0"\nrequires-python = ">=3.11"',"不同项目元数据。"),
     tx("pyproject.toml",'[tool.setuptools.packages.find]\ninclude = ["notekit*"]\n[tool.pytest.ini_options]\ntestpaths = ["checks"]',"不同包/测试目录发现示例。")],
    starter='[build-system]\n# TODO: requires/build-backend\n\n[project]\nname = "task-manager"\n# TODO: version/requires-python/dependencies\n\n[project.optional-dependencies]\n# TODO: dev\n\n[tool.setuptools.packages.find]\n# TODO: include\n\n[tool.pytest.ini_options]\n# TODO: testpaths\n',
    cards=[TOML],drills=[gap("toml-field","补全：按表取名称",TOML,"data['project']['name']","data['project'][None]","合法TOML已提供，补键读取名称，不按行切字符串。")])

lesson("D19-package", ["传统包","初始化","导入副作用"], "D07包/导入", ["__all__无关","text类型可能误写说明"],
    "创建taskproj/__init__.py，提交Python内容，只定义__version__字符串或包说明；导入不得打印/开库/启动。",
    ["__init__.py标记包，可以只放版本或模块文档字符串。","目标是Python文件，当前文本编辑器不代表提交Markdown；不要求__all__。"],
    "包初始化只声明版本/说明。",
    ["填Python版本/说明。","删除资源副作用。","从项目根导入检查无输出。"],
    "包可导入且无副作用。",
    [ex("taskproj/__init__.py",'PACKAGE_LABEL = "便签工具"',"不同包的局部字符串声明。"),
     ex("taskproj/__init__.py",'"""便签工具包说明。"""',"模块文档字符串合法。")],
    starter="# taskproj/__init__.py\n# TODO：仅定义版本或包说明\n")

lesson("D19-config", ["env非空fallback","Path"], "D10-env；D08 Path", ["正式完整答案","空字符串未验"],
    "定义get_db_path() -> Path，非空TASKPROJ_DB优先，缺失/空回退taskproj.db；仅读环境，不打印秘密，不在import建库。API/CLI复用同一函数。",
    ["环境值为字符串，缺失与空都应回退默认。","Path表示路径；配置不创建数据库。函数固定get_db_path，不引入database_path/get_int_env。"],
    "非空环境优先；缺失/空默认Path。",
    ["测试缺失/空/自定义。","检查Path类型。","检查import不建库/输出环境。"],
    "三类环境返回规定Path，无副作用。",
    [ex("taskproj/config.py","theme = os.environ.get('NOTE_THEME') or 'light'","不同配置的fallback，os已导入。"),
     ex("taskproj/config.py","cache_path = Path('cache') / 'notes.json'","不同资源组合Path。")],
    starter="import os\nfrom pathlib import Path\n\ndef get_db_path():\n    pass  # TODO：返回规定Path\n",
    inputs=[("TASKPROJ_DB缺失/空","Path('taskproj.db')"),("TASKPROJ_DB=sample.db","Path('sample.db')")])

lesson("D19-main", ["main","守卫","退出码","导入无副作用"], "D07/D09", ["导入未来.api","提前初始化","未验import"],
    "定义main(argv=None)：打印一行'任务管理项目已启动'，返回0；守卫调用入口，import无输出。此节不导入未来API/初始化数据库。",
    ["main是直接执行动作，import只建立定义。","守卫把main返回整数交给SystemExit；0成功。数据库D20、API D21才建立。"],
    "main整数退出码；守卫区分运行/import。",
    ["填提示和返回码。","直接执行观察一行/0。","import无输出/建库。"],
    "直接运行一行提示/0；import无副作用。",
    [ex("taskproj/main.py","def preview_message():\n    return '便签预览'","不同辅助函数可安全导入。"),
     ex("taskproj/main.py","if __name__ == '__main__':\n    raise SystemExit(0)","最小守卫，不含当前main完整实现。")],
    starter="def main(argv=None):\n    pass  # TODO：提示/返回码\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n")

lesson("D19-readme", ["安装/测试说明","当前/未来入口"], "D01及D19", ["未来入口未标记","dev安装缺失"],
    'README写Python要求、安装-e ".[dev]"、当前main、测试和TASKPROJ_DB默认值；API/CLI/网页先标为后续规划，D24补实测。',
    ["README说明cwd/解释器和配置。dev安装同时获得pytest/httpx。","当前main已存在，API/CLI后续生成；不把未来文件缺失作为当前错误。"],
    "说明区分已有入口/后续计划/实际证据。",
    ["写版本/安装/配置。","核当前main。","后续入口标规划，D24补证据。"],
    "安装/配置正确，现有与未来入口区分。",
    [tx("README.md",'## 开发安装\n从项目根使用项目venv：\npython -m pip install -e ".[dev]"',"dev安装有测试依赖。"),
     tx("README.md","## 当前与后续\n- 当前main。\n- API/CLI完成后再补实测。","未生成内容明确标记。")])

lesson("D20-connection", ["连接","Row","schema","commit/close"], "D16连接/建表/事务，Row术语", ["旧配置接口","init_db参数错","Row没用法"],
    "taskproj/db.py提供create_connection(path)、init_db(conn)，设置sqlite3.Row，幂等创建id/title/done表并提交；import不开库，调用者finally关闭。",
    ["create_connection接路径返回连接，init_db接已有conn，不接路径。",
     "Row让结果可按列名读/转dict；schema可重复。get_db_path由入口读取后传路径，数据层不读配置。",
     "当前验证只检查连接/建表，不要求未来测试文件。"],
    "create_connection(path)返回conn；init_db(conn)用现有连接。",
    ["内存路径连接并设置Row。","init_db两次，核真实字段/default。","调用者finally关闭。"],
    "Row/表字段/default有效，初始化重复安全。",
    [ex("taskproj/db.py","connection.row_factory = sqlite3.Row\n# connection已创建。","只设置结果表示。"),
     ex("taskproj/db.py","LABEL_SCHEMA = 'CREATE TABLE IF NOT EXISTS labels (id INTEGER PRIMARY KEY, text TEXT NOT NULL)'","不同表约束，不是任务建表答案。")],
    starter="import sqlite3\n\ndef create_connection(path):\n    pass  # TODO：连接/Row\n\ndef init_db(conn):\n    pass  # TODO：幂等建表/提交\n",
    cards=[ROW],drills=[gap("row-bool","补全：整数状态转bool",ROW,"bool(row['active'])","None","平台提供Row，转换active，不把整个row当bool。")])

lesson("D20-create-list", ["参数SQL","lastrowid","Row转dict","bool","排序"], "D16 CRUD；D05推导式", ["cursor用法不足","done int/bool","未来测试命令","裸tuple fixture"],
    "保留前节，新增add_task(conn,title)/list_tasks(conn)。空白抛ValueError；绑定INSERT/commit，返回整数id；列表id升序，字典含id:int/title:str/done:bool。",
    ["execute第二参数绑定值，单元组(value,)；保存cursor.lastrowid。",
     "Row按列名/转dict；done 0/1转bool，ORDER BY id ASC。",
     "此时没有tests/test_project.py，用验证按钮检查当前函数。"],
    "INSERT绑定/commit/lastrowid；列表字段/排序/bool。",
    ["新增两标题核编号/排序。","引号值绑定。","空白拒绝不写库；done是真bool。"],
    "id/字段/顺序/真假正确；空白拒绝。",
    [ex("taskproj/db.py","cursor = connection.execute('INSERT INTO labels(text) VALUES (?)', ('绿色',))\nconnection.commit()\nnew_label_id = cursor.lastrowid","不同资源保存cursor，非完整函数。"),
     ex("taskproj/db.py","rows = connection.execute('SELECT id, text FROM labels ORDER BY id ASC').fetchall()\nlabels = [dict(row) for row in rows]","不同资源列表，连接已设置Row。")],
    cards=[INSERT],drills=[gap("new-row-id","补全：读取插入编号",INSERT,"print(cursor.lastrowid)","print(None)","从实际cursor读取编号，表和插入已提供。")])

lesson("D20-update-delete", ["UPDATE/DELETE","rowcount","commit","bool"], "D16 rowcount仅出现", ["未知/bool验收不足","未来测试命令"],
    "保留前节，实现complete_task(conn,task_id)/delete_task(conn,task_id)，参数SQL并commit；存在成功True，未知False，删除后列表消失。",
    ["UPDATE/DELETE绑定编号，cursor.rowcount为命中数，0表示不存在。",
     "转换bool，不无条件True；用当前验证按钮查状态，不依赖未来pytest文件。连接由调用者关闭。"],
    "rowcount形成bool；提交后观察真实状态。",
    ["完成后列表done=True。","删除后列表消失。","未知/重复删除返回False。"],
    "存在改变状态返回True；未知False。",
    [ex("taskproj/db.py","cursor = connection.execute('UPDATE labels SET text = ? WHERE id = ?', ('蓝色', 8))\nconnection.commit()\nchanged = cursor.rowcount > 0","不同表修改文字判断命中。"),
     ex("taskproj/db.py","cursor = connection.execute('DELETE FROM labels WHERE id = ?', (999,))\nconnection.commit()\nremoved = cursor.rowcount > 0","不同表删除未知编号。")],
    cards=[ROWCOUNT],drills=[gap("affected-rows","补全：命中数转bool",ROWCOUNT,"cursor.rowcount > 0","None","未知编号影响零行，补真实命中判断。")])

lesson("D20-db-tests", ["fixture","导入真实函数","隔离连接","行为断言"], "D15；D16", ["无project_file","db对象/conn冲突","assert True可过"],
    "写独立测试草稿：导入真实db函数，fixture隔离连接/init_db，测试两条新增及排序、完成/删除、未知ID并清理。平台临时运行test_project.py；本节保存草稿，不生成正式文件，D22建立tests/test_project.py。",
    ["db fixture是sqlite连接，用add_task(db,title)/list_tasks(db)，不是db业务方法。",
     "默认function scope独立，:memory:/tmp_path隔离，finally关闭。",
     "本节是临时独立测试草稿；正式测试产物D22生成，不能要求其已存在。"],
    "fixture提供conn，真实函数(conn,...)；临时草稿与正式产物不同。",
    ["写独立fixture/真实导入。","至少两条新增核字段/顺序。","写完成/删除/未知ID与清理断言。"],
    "真实临时pytest有行为证据，能发现数据层错误。",
    [ex("tests/test_project.py","def test_label_text(conn):\n    row = conn.execute('SELECT 4 AS code, \"绿色\" AS text').fetchone()\n    assert row['text'] == '绿色'","不同资源读取实际结果；conn由fixture提供。"),
     ex("tests/test_project.py","def test_unknown_label(conn):\n    cursor = conn.execute('DELETE FROM labels WHERE id = ?', (999,))\n    assert cursor.rowcount == 0","不同资源边界断言。")],
    starter="import pytest\nfrom taskproj.db import create_connection, init_db, add_task, list_tasks, complete_task, delete_task\n\n@pytest.fixture\ndef db():\n    pass  # TODO：隔离连接/清理\n\ndef test_task_creation(db):\n    pass  # TODO：真实行为\n",
    provided="独立测试草稿在临时项目运行test_project.py，不落盘正式tests/test_project.py；D22创建正式产物。")


API_DEPS = ["taskproj/__init__.py","taskproj/db.py","taskproj/config.py"]
lesson("D21-app", ["asynccontextmanager","yield资源","lifespan","Depends","TestClient上下文"], "D17 async；D14依赖，前期生命周期为选修", ["async资源缺口","health旧路径","init_db/close_db错误","未来测试","弱AST"],
    "taskproj/api.py定义lifespan并传FastAPI(lifespan=lifespan)，启动用get_db_path/create_connection/init_db(conn)准备表并finally关闭启动连接；get_db以yield提供请求连接并finally关闭。GET /health返回{'status':'ok'}，import不开库/启动。本节不做模型/CRUD/首页。",
    ["应用级lifespan在TestClient/服务进入时准备，退出时清理，import只声明函数/app。",
     "请求get_db创建连接，yield借给路由，finally关闭；启动连接和请求连接分别拥有并关闭，不共享已关闭连接。",
     "路径统一get_db_path。SQLite线程归属参数见连接卡：check_same_thread=False不提供并发写锁。当前平台行为验证不依赖未来tests/test_api.py。"],
    "lifespan接函数；请求try/yield/finally；health不依赖任务行。",
    ["先观察两张不同资源卡的生命周期。","接真实config/db，分清启动/请求连接所有权。","验证import无副作用与with TestClient生命周期/health。"],
    "真实启动初始化、请求借用后关闭、退出清理，health200/ok。",
    [ex("taskproj/api.py","@asynccontextmanager\nasync def label_lifetime(app):\n    events.append('label-start')\n    try:\n        yield\n    finally:\n        events.append('label-stop')","不同资源的局部生命周期，导入/events由教学卡提供。"),
     ex("taskproj/api.py","def get_label():\n    try:\n        yield '颜色'\n    finally:\n        events.append('label-release')","不同请求资源提供后清理，非数据库完整答案。")],
    starter="from contextlib import asynccontextmanager\nfrom fastapi import FastAPI, Depends\nfrom taskproj.config import get_db_path\nfrom taskproj.db import create_connection, init_db\n\n@asynccontextmanager\nasync def lifespan(app):\n    pass  # TODO：初始化/清理/yield\n\ndef get_db():\n    pass  # TODO：请求连接/yield/finally\n\napp = FastAPI(lifespan=lifespan)\n\n@app.get('/health')\ndef health():\n    pass  # TODO：健康响应\n",
    cards=[ASYNC,REQUEST],drills=[gap("resource-yield","补全：借用后清理",ASYNC,"yield '演示资源'","yield None","异步外壳已提供，补借给调用者的值，观察finally。")],
    deps=API_DEPS,inputs=[("导入api","不开库/启动"),("with TestClient","生命周期触发，health200/ok")])

lesson("D21-schema", ["BaseModel","field_validator","classmethod","strip","ValidationError"], "D14模型；当前卡缺cls说明", ["TaskOut/Task冲突","卡是整题答案","提前POST","弱AST"],
    "保留app/lifespan/get_db/health；定义TaskIn(title:str)，清洗并拒绝纯空白；Task(id:int,title:str,done:bool)。直接构造模型，坏输入ValidationError；此节不要求POST。",
    ["输入TaskIn，输出Task，名称固定，不用TaskOut。",
     "field_validator注册字段，classmethod先接类cls，value接字段；返回清洗值，raise ValueError由Pydantic包装ValidationError。",
     "直接构造没有HTTP状态；下一节接框架才转422，现在不要求POST201。"],
    "字段验证器返回/拒绝；直接构造ValidationError。",
    ["运行Nickname不同字段例。","补两模型，保留API。","核正常/空白/缺失，不请求未来POST。"],
    "字段/类型正确，清洗title，空白/缺失拒绝。",
    [ex("taskproj/api.py","class LabelOut(BaseModel):\n    code: int\n    text: str\n    active: bool","不同资源输出字段，非Task完整实现。"),
     ex("taskproj/api.py","@field_validator('name')\n@classmethod\ndef clean_name(cls, value):\n    return value.strip()\n# 放在不同Nickname模型内。","局部cls/清洗写法，非完整正式模型。")],
    starter="from pydantic import BaseModel, field_validator\n\n# 继续已生成API内容，追加模型。\nclass TaskIn(BaseModel):\n    pass  # TODO：输入字段/验证\n\nclass Task(BaseModel):\n    pass  # TODO：输出字段\n",
    cards=[VALIDATOR],drills=[gap("field-clean","补全：清洗昵称",VALIDATOR,"value = value.strip()","value = None","外壳提供不同业务模型，补清洗并观察空白拒绝。")],
    deps=["taskproj/api.py","contract.json",*API_DEPS],inputs=[("TaskIn正常","清洗后title"),("TaskIn缺字段/空白","ValidationError")])

lesson("D21-crud-routes", ["Depends","真实DB函数","HTTP映射"], "D13/D14/D20与模型", ["service假对象","DELETE204旧契约","Router新要求","弱AST"],
    "保留已有API/模型，接GET/POST /api/tasks、PATCH /api/tasks/{task_id}/done、DELETE /api/tasks/{task_id}，Depends(get_db)调用真实db函数。创建201、删除200 JSON、未知404、非法title422。本节不检查首页/HTML。",
    ["只编排模型、真实taskproj.db函数、HTTP，不造service对象/复制SQL。",
     "POST接TaskIn；PATCH /done无额外done体；删除成功200 JSON而非204。",
     "HTTPException映射404；输入拒绝先于写库，当前只测CRUD，不读取未来页面。"],
    "真实函数+Depends连接；201/200/404/422按契约。",
    ["接列表/新增核字段状态。","接完成/删除核后续列表。","覆盖未知/缺失/空白/重复删除。"],
    "CRUD真实改临时库，状态/字段/路径正确。",
    [ex("taskproj/api.py","@app.get('/api/labels')\ndef read_labels():\n    return [{'code': 7, 'text': '绿色'}]","不同资源局部GET返回形状。"),
     ex("taskproj/api.py","if missing_label:\n    raise HTTPException(status_code=404, detail='标签不存在')","不同查询结果映射404，非完整CRUD。")],
    starter="# 保留真实API和模型；使用已教app路由追加当前CRUD。\n# TODO：Depends(get_db)、真实db函数、GET/POST/PATCH /done/DELETE与状态码。\n",
    deps=["taskproj/api.py",*API_DEPS],inputs=[("POST正常title","201 task"),("DELETE存在","200 JSON/列表消失"),("PATCH未知","404 detail")])

lesson("D21-static", ["__file__","Path.parent","FileResponse"], "D08路径；本节响应", ["StaticFiles旧方案","未生成HTML提前200"],
    "保留API，GET /用FileResponse返回Path(__file__).parent/'static'/'index.html'。HTML D23生成；当前只验路由/响应目标，不要求文件存在/首页200。",
    ["__file__表示模块路径，Path(__file__).parent定位包目录，不依赖cwd。",
     "FileResponse指向文件；当前只声明未来目标，不能请求尚未生成页面。",
     "保留/api路由，不用挂到/的StaticFiles旧方案；D23/D24再检查真实首页。"],
    "__file__锚定资源；FileResponse当前声明未来目标。",
    ["运行邻接路径卡。","补首页FileResponse目标。","当前只验路径，D23后请求。"],
    "页面目标正确，API保留，不读未来HTML。",
    [ex("taskproj/api.py","asset = Path(__file__).parent / 'assets' / 'logo.svg'","不同邻接资源，不读文件。"),
     ex("taskproj/api.py","response = FileResponse(asset)\n# 构造响应与资源是否已生成是不同检查。","局部响应写法。")],
    starter="from pathlib import Path\nfrom fastapi.responses import FileResponse\n\n# 保留API，在此补GET /目标响应，当前不读取未来HTML。\n",
    cards=[ANCHOR],deps=["taskproj/api.py",*API_DEPS],inputs=[("当前首页声明","包内static/index.html，不需已存在"),("已有API","仍保留")])

lesson("D22-db-fixtures", ["pytest注入","tmp_path","yield/finally","隔离连接"], "D15 fixture；D21资源", ["连接当业务对象","缺导入","测试质量不足"],
    "创建正式tests/test_project.py：真实db函数，db(tmp_path)创建临时库/init_db，yield连接，finally关闭；默认function scope。至少两例证明每例tasks从空开始，覆盖CRUD/未知ID和资源清理，不读cwd数据库。",
    ["pytest按测试参数名注入同名fixture；db是conn，用add_task(db,title)，不是db.add_task。",
     "tmp_path每例不同目录；yield前准备，finally关闭。至少两例都从空表开始，证明不共享。",
     "D20是独立草稿，此节首次生成正式tests/test_project.py。"],
    "fixture参数注入；每例临时库；yield/finally关闭。",
    ["真实导入与隔离fixture。","至少两例从空开始，断言真实CRUD。","重复运行，确认关闭/无共享/无真实DB。"],
    "正式隔离测试有行为证据且资源关闭。",
    [ex("tests/test_project.py","@pytest.fixture\ndef label_connection(tmp_path):\n    connection = sqlite3.connect(tmp_path / 'labels.db')\n    try:\n        yield connection\n    finally:\n        connection.close()","不同资源临时路径/关闭，导入sqlite3/pytest后使用，不含正式CRUD。"),
     ex("tests/test_project.py","def test_empty_labels(label_connection):\n    label_connection.execute('CREATE TABLE labels (text TEXT)')\n    assert label_connection.execute('SELECT text FROM labels').fetchall() == []","不同资源参数获得连接。")],
    starter="import pytest\nfrom taskproj.db import create_connection, init_db, add_task, list_tasks, complete_task, delete_task\n\n@pytest.fixture\ndef db(tmp_path):\n    pass  # TODO：创建/初始化/yield/finally\n\ndef test_task_flow(db):\n    pass  # TODO：真实行为\n",
    cards=[FIXTURE],deps=["taskproj/__init__.py","taskproj/db.py"])

lesson("D22-api-tests", ["TestClient上下文","override函数映射","monkeypatch","临时DB"], "D15 API；D14依赖；D21生命周期", ["override用法不足","PATCH旧路径","app fixture凭空"],
    "创建tests/test_api.py，自行导入真实app/get_db并写db/client fixture。进入with TestClient前设置临时TASKPROJ_DB；按需override临时连接，finally清覆盖。断言health及真实CRUD状态/字段。",
    ["平台提供真实模块，不提供app/client fixture；自己导入和编写，同D15参数注入。",
     "monkeypatch.setenv('TASKPROJ_DB',str(tmp_path/'api.db'))在TestClient前设置；测试结束恢复。启动与请求指向同一临时路径。",
     "override键原函数、值替代函数，finally清除；PATCH固定/done，不额外done body。连接创建者关闭。"],
    "环境先设置；with触发生命周期；override结束恢复。",
    ["先观察override和环境卡。","写隔离fixture再进入TestClient。","主流程逐条断言状态/字段/后续列表。"],
    "真实API隔离主流程正确且环境/覆盖恢复。",
    [ex("tests/test_api.py","def test_label_lookup(client):\n    response = client.get('/api/labels')\n    assert response.status_code == 200","不同资源状态断言，client由业务fixture提供。"),
     ex("tests/test_api.py","def test_label_missing(client):\n    response = client.delete('/api/labels/999')\n    assert response.status_code == 404","不同资源请求边界。")],
    starter="import pytest\nfrom fastapi.testclient import TestClient\nfrom taskproj.api import app, get_db\nfrom taskproj.db import create_connection, init_db\n\n# TODO：自编db/client fixture；平台不提供app/client fixture。\ndef test_health(client):\n    pass  # TODO：请求/JSON断言\n",
    cards=[ENV,OVERRIDE],drills=[gap("override-function","补全：替代依赖函数",OVERRIDE,"demo.dependency_overrides[read_flag] = fake_flag","demo.dependency_overrides[read_flag] = None","/flag不同接口补函数对象，而非调用值/None。")],
    deps=API_DEPS+["taskproj/api.py"],inputs=[("POST正常","201完整task"),("PATCH已存在/done","200/后续列表done=True")])

lesson("D22-api-errors", ["422/404","detail","不写库","重复删除"], "D14错误；前节客户端", ["无关测试可过"],
    "继续真实tests/test_api.py，补缺title、纯空白、未知ID、重复删除；核422/404、安全detail无traceback、拒绝不写库；保留成功/隔离测试。",
    ["失败也验证副作用：空白拒绝后库为空，未知/重复删除不伪成功。",
     "422 detail可为Pydantic错误列表，404为应用消息；按约定字段/状态检查，不锁完整框架内部错误文字。",
     "沿用临时client/db，不造真实数据库，不读取未来CLI/HTML。"],
    "错误状态/detail与未发生写入一起验证。",
    ["缺字段/空白422且库空。","未知404/安全detail。","成功删除后重复404。"],
    "错误真实覆盖、不污染库，已有成功测试仍通过。",
    [ex("tests/test_api.py","def test_missing_label(client):\n    response = client.delete('/api/labels/999')\n    assert response.status_code == 404\n    assert 'traceback' not in response.text","不同资源安全错误。"),
     ex("tests/test_api.py","def test_bad_label_content(client):\n    response = client.post('/api/labels', json={})\n    assert response.status_code == 422","不同资源缺字段请求。")],
    starter="# 保留fixture/成功测试，追加缺字段/空白/未知/重复删除/未写库断言。\n")

lesson("D22-acceptance", ["读contract","当前API/DB","分步边界"], "D08；D20/D21", ["contract依赖遗漏","无关测试可过"],
    "继续tests/test_api.py，读已有contract.json，把字段/方法/路径/错误约定对应真实API/DB断言。仅当前已生成内容，不查CLI/HTML/runbook/review，15文件最终验收D24。",
    ["contract是已有文件，读后把契约对应真实响应。",
     "空临时库走主流程，不靠旧数据/assert True。",
     "当前只读contract/db/api/tests；未来文件不存在正常。"],
    "已有契约对应真实行为，不提前依赖未来产物。",
    ["读contract选择真实断言。","空库走成功/失败。","整份现有测试回归，不查未来文件。"],
    "当前契约/API/DB一致，有成功/错误行为证据。",
    [ex("tests/test_api.py","contract = json.loads((Path(__file__).parents[1] / 'contract.json').read_text(encoding='utf-8'))","D08读已有JSON，Path/json在starter导入。"),
     ex("tests/test_api.py","def test_label_contract(client):\n    response = client.get('/api/labels')\n    assert response.status_code == 200\n    assert isinstance(response.json(), list)","不同资源协议断言。")],
    starter="from pathlib import Path\nimport json\n\n# 保留当前测试/fixture，补contract与当前API/DB断言，不查未来产物。\n",
    deps=API_DEPS+["taskproj/api.py","tests/test_api.py","tests/test_project.py","contract.json"])


lesson("D23-cli-parser", ["argparse子命令","dispatch","共享配置","连接所有权"], "D09；D19；D20", ["database_path旧名","关闭不足"],
    "taskproj/cli.py定义build_parser/main(argv=None)，支持add TITLE/list，分派真实db函数；统一get_db_path，连接try/finally关闭；守卫直接执行，import无输出。",
    ["沿用args.command或set_defaults(func=handler)，不需要lambda/eval。",
     "配置函数固定get_db_path，入口创建连接/init_db后调用真实数据层，不复制SQL。",
     "main返回整数，成功stdout稳定，finally关闭。"],
    "解析器只解析；main分派并关闭资源。",
    ["离线解析add/list/缺参数。","新增后list可见。","核import无输出与连接关闭。"],
    "add/list有效，跨进程同库，入口/资源边界正确。",
    [ex("taskproj/cli.py","sub = parser.add_subparsers(dest='command', required=True)\nsub.add_parser('show')","不同命令局部子解析器。"),
     ex("taskproj/cli.py","if args.command == 'show':\n    result = show_handler(args)","不同动作使用已教函数分派。")],
    starter="import argparse\nfrom taskproj.config import get_db_path\nfrom taskproj.db import create_connection, init_db, add_task, list_tasks\n\ndef build_parser():\n    pass  # TODO：add/list\n\ndef main(argv=None):\n    pass  # TODO：解析/配置/真实DB/关闭/退出码\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n")

lesson("D23-cli-mutate", ["done/rm","整数参数","stderr","退出码"], "D09错误；D20", ["service假对象","结果字典旧协议","stderr未示范","未知ID未验"],
    "保留add/list，新增done/rm TASK_ID，argparse转换int；真实complete_task/delete_task。成功0，未知ID写stderr/非零，不伪成功；finally关闭。",
    ["DB False表示未命中，main转非零与错误文字。",
     "print(...,file=sys.stderr)写错误，成功stdout；不是返回stdout/stderr字典。",
     "实际调用真实db函数，不使用未生成service对象。"],
    "bool映射退出码；file=sys.stderr选择错误通道。",
    ["运行两个通道短卡。","接done/rm与关闭逻辑。","核存在/未知/重复删除退出码与通道。"],
    "成功0；未知非零stderr，真实状态改变。",
    [ex("taskproj/cli.py","def require_label(code):\n    if code < 1:\n        return 2\n    return 0","不同参数边界返回整数。"),
     ex("taskproj/cli.py","error_stream = sys.stderr\n# file参数选择此错误通道，不返回输出字典。","实际可运行写法在卡中。")],
    starter="# 保留parser/main与add/list，追加done/rm、错误stderr/非零状态、关闭。\n",
    cards=[STDERR],drills=[gap("error-channel","补全：错误输出通道",STDERR,"file=sys.stderr","file=None","选择错误通道，使错误进stderr而确认留stdout。")])

lesson("D23-html-structure", ["完整HTML","label/id","button type","空/错误区域"], "用户开发经验；本节控件", ["starter缺外壳","静态属性弱验"],
    "创建taskproj/static/index.html完整HTML：h1、关联label/input的form、明确type按钮、ul#tasks、空状态/错误区域；此节只结构，下节fetch。",
    ["先html/head/body，再label.for对应input.id。",
     "提交type=submit，列表操作type=button，避免意外提交。",
     "空/错误各有独立id和清楚文字，下一节继续同文件，不提前要求CRUD。"],
    "完整文档；label关联；按钮type明确。",
    ["补表单/控件。","补列表/空/错误区域。","静态核结构与名称。"],
    "完整HTML和可访问控件，留交互更新入口。",
    [tx("taskproj/static/index.html",'<label for="note-body">便签内容</label>\n<input id="note-body" name="body">\n<button type="submit">保存便签</button>',"不同资源label关联。"),
     tx("taskproj/static/index.html",'<ul id="notes"></ul>\n<p id="notes-empty">尚无便签</p>\n<p id="notes-error" role="alert"></p>',"不同资源空/错误区域。")],
    starter='<!doctype html>\n<html lang="zh-CN">\n<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>任务管理</title></head>\n<body>\n<!-- TODO：标题、可访问表单、列表、空状态、错误区域 -->\n</body>\n</html>\n')

lesson("D23-html-fetch", ["fetch协议","JSON body","response.ok","textContent","错误状态"], "已有JS经验；D12/D21协议", ["只教GET/DELETE","starter仅函数","浏览器验收不足"],
    "继续完整HTML，GET加载、POST新增、PATCH /api/tasks/{id}/done完成、DELETE删除；POST JSON/Content-Type，先response.ok再解析，删除200 JSON，兼容204跳过json。textContent显示标题；失败展示错误、不渲染成功。",
    ["POST使用JSON.stringify/application/json，PATCH /done无额外done body。",
     "先检查ok再await json；204无正文，但本项目删除固定200 JSON。",
     "createElement/textContent显示用户文字，不拼innerHTML；成功重载列表，失败更新错误区。"],
    "按契约方法/路径/body，先状态再解析，安全DOM。",
    ["GET/textContent渲染。","逐次POST/PATCH/DELETE并更新列表。","API失败展示错误；HTML样式标题应纯文本显示。"],
    "真实四步CRUD，空/错误正确，标题安全。",
    [jsx("async function saveNote(body) {\n  const response = await fetch('/api/notes', {\n    method: 'POST',\n    headers: {'Content-Type': 'application/json'},\n    body: JSON.stringify({body})\n  });\n  if (!response.ok) throw new Error(await response.text());\n  return response.json();\n}","不同资源的POST JSON局部写法。","不是完整任务页面；字段按正式契约。"),
     jsx("const item = document.createElement('li');\nitem.textContent = note.body;\nnotesList.append(item);","不同资源安全DOM。","note/notesList由不同业务上层提供，用户文字不拼HTML。")],
    starter="<!-- 继续上一节完整HTML，保留文档/控件；在script中逐步补GET/POST/PATCH /done/DELETE与错误。 -->\n",
    cards=[EMPTY])

lesson("D24-rebuild", ["源码副本","临时目录","venv解释器","dev安装","pytest"], "D01环境；D18-D23产物", ["空目录无源码","仍用全局Python","dev缺失","强制uvicorn"],
    'runbook先复制当前已生成源码/配置/测试到新临时目录，不复制原.venv/.learn/DB/缓存；副本创建venv，明确venv解释器安装-e ".[dev]"再pytest。记录cwd/预期/定位；API启动下节，勿删除原学习目录。',
    ["空目录不能直接pip -e .，先复制当前源文件/配置/测试。",
     "Windows用.venv\\Scripts\\python.exe，其他平台.venv/bin/python，创建环境后不能仍用全局python。",
     "dev安装后测试，仅此次副本DB；本节只重建/安装/测试，uvicorn留下一节。"],
    "源文件先存在；统一venv解释器；不删原目录。",
    ["创建新临时副本，排除环境/记录/DB。","venv解释器安装dev。","同解释器pytest，记录实际证据。"],
    "重建可复现，解释器/dev正确，不清理原目录。",
    [cmd('python -m venv .venv\n.venv\\Scripts\\python.exe -m pip install -e ".[dev]"\n.venv\\Scripts\\python.exe -m pytest -q',"Windows副本根，明确venv。","前提已复制当前源文件/配置/测试。"),
     cmd("$ Test-Path pyproject.toml\nTrue\n$ Test-Path taskproj\nTrue","源代码已存在才安装。","只读检查，不删原环境/记录。")],
    starter="# docs/runbook.md\n## 重建前提\n# 源文件副本/cwd/排除项\n## 创建环境\n# venv\n## 开发安装\n# venv解释器/.[dev]\n## 测试\n# 同解释器pytest/预期/定位\n",
    inputs=[("副本根，源码已复制","venv/安装dev/pytest按序"),("源码未复制","先检查配置/包缺失，不继续安装")])

lesson("D24-integrate", ["同一DB","三入口","启动停止","证据"], "D19-D23", ["共享路径/停止范围不足"],
    "继续runbook，三入口同一临时TASKPROJ_DB；先pytest，再uvicorn taskproj.api:app，再CLI/浏览器GET /走四步。记端口/stdout/HTTP/DOM，Ctrl+C停止，只清此次副本。",
    ["API/CLI进程同一TASKPROJ_DB，浏览器经API读同库。",
     "三入口用已通过pytest的副本，不用原学习数据库。",
     "启动终端Ctrl+C停止；清理仅此次副本，不删原.venv/.learn/learner_workspace。"],
    "共享配置连接三入口；测试后启动；真实证据。",
    ["设同一临时DB先测试。","API/CLI/网页走主流程。","记证据/Ctrl+C/副本清理范围。"],
    "三入口同一真实状态，启动/停止/证据可复现。",
    [cmd("# 同一临时TASKPROJ_DB\npython -m uvicorn taskproj.api:app\n# 另一终端相同路径\npython -m taskproj.cli list","同库API/CLI，再浏览器GET /。","使用项目venv和此次副本路径。"),
     cmd("# 证据格式\nPOST -> GET -> PATCH /done -> DELETE\n# 每步记状态/字段/DOM。","沿同一契约记录主流程。","不是只写已完成。")],
    starter="# docs/runbook.md\n# 保留重建/安装/测试，补同库三入口/证据/Ctrl+C/清理范围。\n")

lesson("D24-artifacts", ["15文件映射","存在性","排除项","阶段/最终边界"], "_PROJECT_REQUIRED_FILES；D08 exists", ["review尚未生成"],
    "runbook列15文件的路径/创建修改节/使用者/验证；docs/review.md标下一节创建。列DB/缓存/密钥排除项，实际完整存在验收在review生成后。",
    ["清单是实际产物责任，不是模板。",
     "review下一节写，此时未存在正常，应标待创建。",
     "数据库/缓存非交付源码；最终按钮对完整副本核15文件与真实行为。"],
    "清单区分当前/后续产物，最终验收后移。",
    ["对应15路径责任。","查当前存在，review标待创建。","注明排除/最终时机。"],
    "15路径可追溯，review待创建清楚。",
    [tx("docs/runbook.md","| 文件 | 章节 | 验证 |\n| taskproj/db.py | D20 | 数据层回归 |\n| taskproj/static/index.html | D23 | 浏览器交互 |","局部表，完整清单自行整理。"),
     cmd("$ Test-Path docs/runbook.md\nTrue\n# docs/review.md下一节创建后参加最终验收。","当前/后续状态不同。","不提前要求未来文件。")],
    starter="# docs/runbook.md\n# 保留前文，补15责任表/当前状态/排除项/最终时机。\n")

lesson("D24-review", ["证据","failure/fix","取舍","下一步","最终验收"], "前课实际产物", ["lifespan harness冲突","POST200兼容","HTML标记不足"],
    "创建review四段evidence/failure-fix/tradeoffs/next steps，引用真实文件/命令/错误类型；此时才执行15文件、pytest、SQLite、API/CLI/浏览器CRUD完整验收，区分未测，不粘标准代码。",
    ["实际命令/退出码/状态/界面变化才是证据。",
     "一次真实失败定位文件，写修复/复测，再给取舍/具体下一步。",
     "review后15文件齐全；最终with TestClient触发lifespan，网页已生成才实际请求/交互。"],
    "真实证据+失败定位/复测+取舍+下一步。",
    ["四段引用实际记录。","最终完整验收与隔离浏览器四步。","区分通过/未测/剩余问题。"],
    "复盘有证据，所有现有产物和三入口回归。",
    [tx("docs/review.md","## Evidence\n- 实际pytest命令/退出码。\n- 一条HTTP状态和CLI输出。","记录本人真实结果。"),
     tx("docs/review.md","## Failure and fix\n- 现象。\n- 文件/原因。\n- 修复/复测命令及结果。","非标准复盘答案。")],
    starter="# docs/review.md\n## Evidence\n\n## Failure and fix\n\n## Tradeoffs\n\n## Next steps\n")

THREAD = card("SQLite线程归属参数：项目接口的必需边界",
    "作用：check_same_thread=False允许连接跨线程借用。常用：FastAPI同步依赖/路由可能由不同工作线程调用。写法：sqlite3.connect(path,check_same_thread=False)；连接创建者仍负责close，此参数不是锁，不保证并发写安全。这里不要求手写线程。",
    "import sqlite3\nconn = sqlite3.connect(':memory:', check_same_thread=False)\ntry:\n    print(conn.execute('SELECT 3').fetchone()[0])\nfinally:\n    conn.close()\n", "3")
UPDATES["D20-connection"]["cards"].append(THREAD)
UPDATES["D20-connection"]["instructions"] += " 本项目后续同步API可能跨线程借连接，create_connection的sqlite3.connect显式使用check_same_thread=False；该参数不是锁。"
UPDATES["D20-connection"]["explanation"].append("跨线程归属参数现在就地提供作用与写法，后续API不会暗中要求回改；暂不要求线程编程。")

VALIDATOR_FIXES = [
    {"where":"learnctl/practice.py:_D20_CRUD_SETUP","fix":"使用当前M.create_connection(DB)并保持Row，避免正确dict(row)实现收到tuple。只用已生成方法。"},
    {"where":"D19-config/main/package","fix":"配置缺失/空/覆盖和Path；入口直接运行0/提示、import无副作用；包应验合法Python，文本关键词会误拒绝合法版本。"},
    {"where":"D20-update-delete","fix":"实际已有/未知/重复删除返回bool并改变状态。"},
    {"where":"D20-db-tests/D22 tests","fix":"临时副本行为mutation证明测试发现当前错误，不能凭assert关键字/无关True。behavior_d18_d24负责。"},
    {"where":"D21 app/schema/CRUD/static","fix":"真实分步行为：app only health/lifespan/get_db；schema直接模型；CRUD不查首页；static只目标路径不读未来HTML。behavior_d18_d24负责。"},
    {"where":"D22-acceptance deps","fix":"本overlay补contract.json和已生成包/配置/DB依赖，不补未来产物。"},
    {"where":"D23 CLI/HTML","fix":"CLI未知ID非零stderr；HTML结构解析属性，浏览器真实四步/错误/textContent；仅关键词不足。"},
    {"where":"D24 validate_command","fix":"当前仅重建/安装/pytest；uvicorn留D24-integrate，不能额外提前验。"},
    {"where":"learnctl/practice.py:_ACCEPT_API_HARNESS","fix":"with TestClient触发生命周期，POST严格201，DELETE200 JSON；behavior_d18_d24负责。"}
]


def apply(data: dict[str, Any]) -> None:
    """Apply BUILD-time edits only; safe to call twice without duplicate drills."""
    sections = {s["id"]:s for t in data["tasks"] for s in t["lesson"]}
    for sid,u in UPDATES.items():
        s = sections[sid]
        p = s["practice"]
        pf = s["practice_first"]
        p.update(instructions=u["instructions"],expected_behavior=u["expected"],
                 hints="先运行短卡/不同题局部例，再按本节契约自己实现。失败比较实际输入、结果、路径和生命周期。")
        s.update(explanation=list(u["explanation"]),syntax=u["syntax"],objective=u["expected"],
                 key_points=[u["expected"],u["syntax"],"实际结果与错误类型是证据。"],
                 examples=copy.deepcopy(u["examples"]))
        s["example"] = s["examples"][0]
        s["common_errors"] = copy.deepcopy(COMMON_ERRORS[sid])
        if "starter" in u: p.update(starter_content=u["starter"],starter_policy="complete")
        pairs = u.get("inputs") or [(u["steps"][0],u["expected"]),(u["steps"][-1],u["expected"])]
        p["input_examples"] = [{"label":f"用例 {i+1}","value":a,"expected":b} for i,(a,b) in enumerate(pairs)]
        if "input_identifiers" in p:
            p["input_identifiers"] = [name for name in p["input_identifiers"] if any(name in a for a,_ in pairs)]
        if "deps" in u: p["workspace_deps"] = list(dict.fromkeys(u["deps"]))
        s["guided_practice"].update(goal=u["instructions"],starter=p["starter_content"],
            steps=[{"action":a,"expected":u["expected"]} for a in u["steps"]],check=u["expected"])
        s["steps"] = list(u["steps"])
        s["frontend_bridge"] = "已有前端经验辅助理解边界；按当前真实文件与契约验证，不要求未来产物。"
        s["js_bridge"] = s["frontend_bridge"]
        pf.update(goal=u["instructions"],rules=[u["syntax"],"简短教学/不同题小例在前，当前实践在后；不提前要求未来产物。"])
        from practice_first_content import _fill_drill
        pf["drills"] = [drill for drill in pf["drills"] if not drill["id"].startswith("fill-")]
        for index, example in enumerate(s["examples"]):
            drill = _fill_drill(example, index)
            if drill:
                pf["drills"].append(drill)
        if "cards" in u: pf["cards"] = copy.deepcopy(u["cards"])
        if "drills" in u:
            new = {x["id"]:x for x in u["drills"]}
            pf["drills"] = [x for x in pf["drills"] if x["id"] not in new] + copy.deepcopy(list(new.values()))
        deps = p.get("workspace_deps",[])
        pf["provided"] = u.get("provided") or (("已生成真实依赖："+"、".join(deps)) if deps else "仅提交当前编辑器；独立实验在临时目录，不改学习记录。")
    sections["D19-package"]["practice"]["kind"] = "code"
    sections["D19-package"]["practice"]["file_name"] = "__init__.py"
    # Stable section IDs, 15 final paths, no progress migration.


# Detailed reference remains folded; each paragraph explains a distinct concrete
# concept. These are authored explanations, not padding to satisfy length tests.
DETAILED = {
"D18-scope": [
"用户故事写角色、动作与结果，例如归档便签后它不再出现在未归档列表。只写支持功能，不能说明用户怎样判断成功。",
"输入边界写可以接受和必须拒绝的情况；非目标写本轮不做的需求。这两类说明可以防止后续API、CLI和网页各自猜规则。",
"本节只创建需求文件，不需要数据库或服务已经存在。检查四个动作和空白/未知编号的描述是否能转成后续可执行验收。"],
"D18-acceptance": [
"验收场景把用户故事变成操作序列，每一步记录输入与可比较的结果。字段变化、HTTP状态和终端输出都可以形成证据。",
"本项目完成路径固定PATCH /api/tasks/{task_id}/done，删除成功为200 JSON。方法、路径和结果应一起写清，不能只写请求成功。",
"当前记录的是执行计划，不要求后续API/CLI文件已经生成。实现后再按相同顺序执行成功与失败场景，定位第一处状态差异。"],
"D18-data-contract": [
"JSON使用双引号、true/false和null；解析后才得到Python字符串、布尔与None。合法JSON仍可能有错误字段类型，需要单独核对。",
"本项目采用简单契约约定：input.title写string类型标记，output填真实类型样例值。把id填成integer字符串并不满足整数输出样例。",
"errors键固定empty_title与unknown_id，分别记录422和404。本节只核数据结构，路由数组到下一节再加入，不提前检查endpoints。"],
"D18-api-contract": [
"endpoints是由对象组成的JSON数组，每项method和path共同识别接口。只写路径会漏掉同一路径上不同方法的输入/结果区别。",
"保留前节task和errors，不能用routes替换endpoints或改错误键名。本项目没有单任务GET接口，完成操作固定PATCH /done。",
"创建返回201，删除返回200 JSON，输入错误422和未知ID404需要一致。写完契约逐项对照，后续API、测试和网页都按这张表工作。"],
"D19-pyproject": [
"[project]保存name、version、requires-python和dependencies；[project.optional-dependencies]的dev保存pytest/httpx等开发测试依赖。",
"[build-system]用requires=['setuptools>=68']和build-backend='setuptools.build_meta'选择构建后端；包发现include应限制taskproj*，测试路径指向tests。",
"当前先核TOML结构和依赖声明。包目录下一节创建，测试后续创建；不能把此刻安装或测试收集找不到文件当作学习者失败。"],
"D19-package": [
"传统包使用__init__.py标记目录，文件可以只保存版本字符串或模块文档字符串。导入时会执行顶层代码，所以不能在这里开库或启动服务。",
"当前编辑器提交并执行Python，目标文件须是Python内容，不能提交Markdown正文或终端命令。此题不要求额外学习__all__导出列表。",
"从项目根导入taskproj，应只得到包定义而没有输出或资源副作用。包名与pyproject发现目录相同，后续模块才能通过稳定路径导入。"],
"D19-config": [
"环境变量输入是字符串，缺失与空字符串都按本题回退默认路径。非空自定义值优先，不应顺便读取或打印其他秘密环境。",
"Path把路径文本变成可组合的对象，配置函数只选择来源和默认值。数据库连接/建表由后续调用者负责，不能在配置导入时创建。",
"函数名固定get_db_path并返回Path，API与CLI复用同一配置边界。分别验证缺失、空字符串和自定义三组输入，避免开发机环境偶然通过。"],
"D19-main": [
"main集中直接执行时的动作，__name__守卫让导入只建立定义。入口返回整数，由SystemExit把它交给终端；零表示成功。",
"此节只实现启动提示，数据库在D20、API在D21建立。不导入未来.api，也不在此时提前初始化或启动uvicorn，避免未生成依赖失败。",
"用直接执行检查一行提示和退出码零，再用独立导入检查没有输出。两条路径都正确，后续测试才能安全复用入口模块。"],
"D19-readme": [
"README说明源文件放在哪里、使用哪个解释器、怎样安装与测试。开发安装选择.[dev]，才能同时得到pytest和TestClient依赖httpx。",
"当前main已生成，但API、CLI和网页入口是后续计划，必须标明生成章节。不能让读者现在运行还不存在的文件并把失败归给当前作业。",
"D24从完整临时副本按说明实测，再补三入口和数据库路径证据。现在先检查命令与已有文件对应、TASKPROJ_DB默认值说明一致。"],
"D20-connection": [
"create_connection接收路径并返回连接，init_db接收已有连接而不是路径。连接与表是不同资源层次，创建连接不等于表已经存在。",
"sqlite3.Row让查询结果支持列名读取，init_db幂等创建id/title/done并提交。调用者负责finally关闭连接，数据层不在导入时读取配置或开库。",
"后续同步API可能跨线程借用连接，sqlite3.connect使用check_same_thread=False；它解除线程归属检查，不是锁。当前只验证连接/建表，不读取未来测试文件。"],
"D20-create-list": [
"execute的第二个参数绑定值，单个参数元组必须有逗号。INSERT返回cursor，commit后读取lastrowid作为新增记录的整数编号。",
"查询结果按id升序；Row可转dict，SQLite done整数零/一必须显式转bool。字段、顺序和真假类型都属于后续API/CLI共用的输出契约。",
"此刻tests/test_project.py尚未正式生成，使用当前验证按钮测试两条任务、引号标题和空白拒绝。检查拒绝后没有多出行，不能只看函数返回。"],
"D20-update-delete": [
"UPDATE和DELETE也用问号绑定编号，避免把输入拼到SQL。成功操作提交后，应从列表看到完成状态或记录消失，而不是只输出文字。",
"cursor.rowcount记录影响行数，零表示目标不存在。两个函数返回真正bool，未知或重复删除不能无条件True，否则入口会伪造成功。",
"此节继续已有数据层代码，用当前验证按钮核存在/未知/重复情况。连接仍由创建者finally关闭，不依赖后续才创建的测试文件。"],
"D20-db-tests": [
"db fixture产出的是SQLite连接，业务调用写add_task(db,title)等真实函数。不能照搬db.add_task方法，因为连接对象没有任务业务接口。",
"默认function scope使每例从隔离数据库开始，连接准备后init_db，清理放finally。至少两条新增验证字段与排序，再测试完成/删除/未知ID。",
"本节是保存学习草稿并临时运行的独立测试，不落盘正式测试文件。D22首次创建tests/test_project.py，当前不要求该未来路径已经存在。"],
"D21-app": [
"应用级lifespan在服务或TestClient上下文进入时初始化，退出时清理。import只建立函数/app，不应创建数据库或启动实际端口。",
"请求级get_db创建连接，yield借给路由，finally关闭；启动连接与请求连接各自有所有权。不能先关闭再返回，也不能共享已关闭连接。",
"路径统一get_db_path，启动调用真实create_connection和init_db(conn)。本节只验生命周期/get_db/health，不需要未来模型、CRUD、首页或测试文件。"],
"D21-schema": [
"TaskIn接收输入title，Task表达输出id/title/done，类名按当前契约固定。模型可以直接构造，此时错误是ValidationError而不是HTTP响应。",
"field_validator注册字段处理，classmethod使首参数cls接收类，value是字段值。返回清洗结果；raise ValueError拒绝，再由Pydantic包装错误。",
"用正常、纯空白和缺字段分别构造模型，并保留已有API定义。POST路由下一节才建立，当前不能要求接口201或提前新增业务实现。"],
"D21-crud-routes": [
"路由编排输入模型、Depends连接、真实taskproj.db函数和状态码。SQL留数据层，不使用未生成service对象或额外Router注册要求。",
"POST接TaskIn且201，PATCH /done不额外接done请求体，删除成功200 JSON。未知ID404，模型错误在写库前422，不把失败返回200。",
"在空临时库按创建、列表、完成、删除观察状态变化，再检查未知、空白和重复删除。本节不要求首页，避免读取D23才生成的HTML。"],
"D21-static": [
"__file__表示当前模块文件位置，Path(__file__).parent定位包目录。资源路径以模块为锚点，换启动cwd仍应指向相同包内文件。",
"FileResponse以指定路径表达文件响应，但声明与文件已生成是不同阶段。此节仅目标static/index.html，不读取或要求未来页面已经存在。",
"保留已有/api路由，使用当前明确FileResponse方案，不混用根路径StaticFiles旧教学。D23生成HTML后，D24才实际请求首页检查200。"],
"D22-db-fixtures": [
"pytest按测试参数名注入同名fixture产出的连接；业务函数接conn作为参数。目标文件是正式tests/test_project.py，不是D20临时测试草稿。",
"tmp_path每例提供独立目录，默认function scope不共享行。至少两例都从空tasks开始，yield前准备，finally关闭，证明隔离与清理。",
"真实导入create_connection/init_db和CRUD函数，连续执行检查没有固定cwd数据库残留。错误先比较实际状态，不通过放宽断言隐藏数据层问题。"],
"D22-api-tests": [
"平台提供真实workspace模块，不提供app/client fixture；自行导入app/get_db并建立fixture，沿用D15的参数注入和默认测试隔离。",
"进入with TestClient前用monkeypatch设置临时TASKPROJ_DB，生命周期与请求指向同一路径。请求依赖override键是原函数，值是替代函数对象。",
"finally清除覆盖，连接由创建者关闭，环境由monkeypatch恢复。逐步检查health/CRUD状态与字段；PATCH路径固定/done，不额外要求done请求体。"],
"D22-api-errors": [
"失败测试同时观察协议和副作用，缺字段/纯空白输入拒绝后列表仍为空。未知ID与重复删除不能伪造成功，分别得到稳定错误。",
"422 detail可为Pydantic错误列表，404 detail为应用消息，不锁住框架内部完整格式。安全边界检查约定字段和没有traceback/秘密内容。",
"沿用前节临时DB/client，不创建真实目录数据库，也不读取未来CLI/HTML。保留成功测试，再补失败测试，防止修复错误边界破坏主流程。"],
"D22-acceptance": [
"contract.json是已生成的真实文件，读取后把字段、方法/路径及错误约定对应到实际API请求。仅解析JSON并不证明实现符合契约。",
"从空临时库连数据层和API走主流程，再比较错误状态与未发生写入。不能借旧数据库或无关assert True宣称行为通过。",
"当前依赖仅contract、db、api和现有tests；CLI/HTML/runbook/review后续生成，未存在正常。15文件完整检查明确放到D24最后交付。"],
"D23-cli-parser": [
"argparse只声明和解析子命令，main把Namespace分派到真实函数。用args.command或set_defaults，不需要选修lambda或eval命令文本。",
"路径固定get_db_path，main创建连接/init_db后调用数据层，不重复写SQL。add/list共享同一TASKPROJ_DB，跨进程才能看到前次新增。",
"main返回整数并通过守卫交给终端，连接finally关闭。测试解析、真实stdout和import无输出，区分语法、配置和业务状态的问题。"],
"D23-cli-mutate": [
"数据层False表示未命中，CLI main转换成清楚提示和非零退出码。不能只打印错误后返回零，否则shell和验收会误认为成功。",
"print的file参数选择sys.stderr，成功信息留stdout；主入口返回整数，不返回包含stdout/stderr的字典。不同通道在结果栏分别观察。",
"done/rm参数用argparse转换整数，再调用真实complete_task/delete_task。保留add/list与finally关闭，检查未知及重复删除真实退出码。"],
"D23-html-structure": [
"先提供完整html/head/body外壳，再建立h1、form和可访问label/input。label.for与input.id对应，用户才知道输入框的名称和用途。",
"提交按钮type=submit，任务操作按钮type=button，避免列表操作意外触发表单。列表、空状态与错误区各有稳定id，后续脚本可以定点更新。",
"此节只结构与可访问名称，不要求fetch已经完成。下一节继续同一完整HTML，不能把JavaScript片段当整个文件覆盖已有控件。"],
"D23-html-fetch": [
"POST用JSON.stringify和application/json发送对象，PATCH /done不额外接done体。请求方法、路径和字段都来自真实API契约，不另造客户端业务规则。",
"先检查response.ok，再await response.json，204没有正文。当前任务删除固定200 JSON，兼容204分支不会修改后端约定或隐藏失败。",
"createElement/textContent把用户标题当文本，不拼innerHTML；成功后重载列表，失败显示错误区。实际新增/完成/删除和含HTML标题都要用浏览器观察。"],
"D24-rebuild": [
"空目录没有项目源文件，不能直接pip -e .；先复制当前源码、配置和测试到新的临时项目根，不复制原环境、学习记录、数据库或缓存。",
"创建venv后明确使用它的Python：Windows .venv\\Scripts\\python.exe，其他平台.venv/bin/python。安装-e .[dev]获得开发测试依赖，再同解释器pytest。",
"记录cwd、命令、预期和定位，只清此次临时副本，不删原学习目录。本节仅重建/安装/测试，服务启动及三入口操作留下一节。"],
"D24-integrate": [
"API和CLI各是独立进程，必须设置同一临时TASKPROJ_DB才能观察同一任务状态。浏览器请求API，不在网页中生成另一套任务数据。",
"先在项目副本通过pytest再启动uvicorn，用CLI/浏览器走同一主流程。分别记录stdout、HTTP状态/字段和DOM，不只写所有入口正常。",
"停止服务使用启动终端Ctrl+C，说明临时副本清理范围。不删除原.venv/.learn/learner_workspace，也不把未保存内容当可丢弃文件。"],
"D24-artifacts": [
"15文件清单描述真实路径、创建/修改章节、使用者及验证方式。只列文件名不能解释上游契约怎样约束数据层、接口、测试和页面。",
"docs/review.md在下一节才生成，本节明确标待创建。当前检查已有文件，不能把这一步尚未存在review误报成学习失败。",
"数据库、缓存和秘密不属于交付源码，不删除原记录。review生成后，最终按钮才核完整15文件和所有真实行为，分清计划与最终证据。"],
"D24-review": [
"证据来自实际命令、退出码、状态或界面变化，不能用已完成三字替代。四段分别记录成果、真实失败/修复、取舍和可执行下一步。",
"失败记录具体文件与原因，修正后用同一命令复测，不粘标准代码作为自己的结果。通过、未测与剩余问题必须分开写，方便下一轮判断。",
"review创建后15产物齐全，最终API通过with TestClient触发生命周期，页面已经生成才请求首页/运行浏览器四步。完整验证全部在临时副本进行。"]
}

EX_NOTES = {
"D18-scope": [
"便签归档后离开未归档列表是用户可观察结果，而不是内部函数名。换成分享等新动作时也要写明确结果；这段不提供当前四故事的完整成稿。",
"非目标收住权限/共享等本轮范围，空白内容界定失败输入。没有边界会让各入口自行接受坏数据；本项目任务规则按正式题自行整理。"],
"D18-acceptance": [
"三步便签场景每一步都有新的状态可比较，所以能形成验收顺序。只记录调用而没有结果不能验证成功；当前任务四步和路径由正式题填写。",
"表格同时记录状态与先查的边界，资源缺失与输入不合格有不同原因。此时只写计划，不要求尚未生成的服务能发请求；实现后再收实际证据。"],
"D18-data-contract": [
"note_id填整数、archived填布尔，而input.body使用string标记，两种用途分开。JSON语法通过仍可能类型不符；正式任务字段不能照搬便签键名。",
"不同业务错误键对应输入拒绝和资源不存在的两类状态。任务项目的正式键固定empty_title/unknown_id；这里示范错误对象形状，不替你写完整契约。"],
"D18-api-contract": [
"endpoints数组每项是一个包含method/path的对象，同一路径不同方法也能分开记录。便签路径不能原样作为任务答案；正式题六条接口需要自行补齐。",
"错误对象继续保留输入/不存在的语义，不能在扩充路由时把前节约定丢掉。任务仍使用正式错误键；只加数组不等于数据契约已经正确。"],
"D19-pyproject": [
"name/version/requires-python使用TOML字符串，版本不能当数值计算。项目名称与可导入包名是不同概念；示例不同项目，正式名称和依赖自行填写。",
"include限制包发现范围，testpaths选择测试目录，两个路径不必同名。示例notekit/checks不是本项目目录；当前只核配置，不要求未来包/测试已经存在。"],
"D19-package": [
"赋值语句声明不同包的标签字符串，导入时只建立这个值，不启动资源。不要照搬它代替正式版本；包初始化含副作用会破坏后续导入测试。",
"模块文档字符串也是合法Python包说明，执行它不会开库或打印。目标文件虽由文本编辑器录入仍须是Python；这里不要求额外__all__或业务实现。"],
"D19-config": [
"or让缺失或空主题回退light，os须已导入，展示同样的非空优先规则。变量并非数据库路径，不是正式函数答案；自定义非空主题应优先保留。",
"Path与斜杠组合出不同缓存文件的位置，但不创建它也不读取数据。配置函数应返回路径对象，资源打开留给调用者；不能用字符串拼接依赖平台分隔符。"],
"D19-main": [
"函数定义只保存不同辅助行为，导入不会自动执行返回值或输出。正式入口仍需自己打印提示/返回状态；不应为示范而导入尚未生成API。",
"守卫只在直接执行时交给SystemExit零状态，导入时跳过该动作。此例仅展示进程边界，不含当前main实现；完整入口还需验证实际提示和无导入输出。"],
"D19-readme": [
"开发安装选择.[dev]得到测试依赖，命令在项目根使用已选venv解释器。源码或包未生成时不能要求安装成功；正式重建D24用完整副本核实。",
"当前与后续分开写，读者能判断眼下哪些命令可实际执行。API/CLI未生成不属于D19作业失败；D24应把这些计划更新为本人实测证据。"],
"D20-connection": [
"设置row_factory改变以后查询行的表示，本身不连接或建表，connection须先存在。没有Row时dict(row)不能按列名转换；当前完整连接函数由学习者编写。",
"LABEL_SCHEMA只是不同表SQL字符串，声明变量不会执行建表。IF NOT EXISTS帮助重复初始化，NOT NULL约束必填；当前tasks字段和提交行为按正式契约实现。"],
"D20-create-list": [
"execute返回cursor，绑定参数与commit使不同标签写入稳定，lastrowid获得本次编号。不能把cursor直接当记录返回；此片段不是当前add_task完整函数。",
"查询结果用Row转换字典并稳定排序，连接必须已配置row_factory。此处不同标签没有done字段；正式任务还要把SQLite整数状态转成真正bool。"],
"D20-update-delete": [
"不同表的UPDATE绑定文字和编号，命中数形成changed真假，commit保存修改。零行不表示成功；此片段不是当前完成任务函数的完整实现。",
"删除不存在编号时rowcount为零，因此removed为False，不能无条件成功。正式删除函数仍要由学习者编写；后续列表也应核记录真实消失。"],
"D20-db-tests": [
"conn是fixture提供的连接，SQL取得不同资源实际字段，再用assert比较值。连接不是db业务对象；正式任务测试导入真实函数，不复制数据层实现。",
"未知标签删除影响零行，用实际cursor验证失败副作用，而不是无关assert True。labels表由不同业务fixture准备；正式题当前临时草稿不生成后续测试文件。"],
"D21-app": [
"异步上下文装饰器把yield前后分成进入/退出，finally保证不同资源结束事件。events和导入见短卡；不能把未定义init_db()/close_db()照抄进当前数据库应用。",
"get_label借用字符串后才追加释放事件，展示请求依赖的所有权顺序。实际数据库依赖还要自己创建/yield/close连接；不是提前关闭后return，也不是完整API答案。"],
"D21-schema": [
"不同输出模型用标注固定code/text/active，构造时框架按字段验证。它不要求请求路由已经存在；正式Task字段按当前契约填写，不使用旧TaskOut类名。",
"field_validator注册name，classmethod让cls收到类，返回strip后的文本。该片段在不同模型中使用，不包含当前TaskIn完整验证；正式题还要拒绝清洗后空白。"],
"D21-crud-routes": [
"不同标签GET只展示装饰器把函数返回列表编码成响应，未提供整套业务实现。正式路由要接真实依赖和数据库状态，不能只靠同名空函数通过。",
"不同查询结果missing_label控制HTTPException404，状态与detail共同表达资源不存在。条件来自真实查询，不能无条件抛错误；正式CRUD不得凭空调用service对象。"],
"D21-static": [
"模块位置与assets组合出不同资源路径，换cwd仍以当前模块为锚点。这里不读取logo文件，避免把声明路径与已生成资源混淆；正式首页路径自行填写。",
"FileResponse构造响应目标，文件真正发送才需要存在；当前阶段只核声明。未来index.html尚未生成不是作业错误，完整页面请求应在D23/D24验证。"],
"D22-db-fixtures": [
"tmp_path由pytest提供，不同标签fixture在yield前创建连接、finally后关闭。实际使用需导入sqlite3/pytest；正式任务还要初始化真实schema且至少两例从空开始。",
"测试参数名选择fixture连接，建不同labels表再检查实际空查询结果。不能写db.list_tasks伪对象；正式任务测试真实函数，当前片段只说明参数注入与断言。"],
"D22-api-tests": [
"client从学习者自己的fixture取得，进程内请求不同标签路由并比较状态。状态通过不代表字段正确，正式主流程还要核JSON字段和后续库状态。",
"不同资源的未知编号得到404，测试通过客户端观察真实协议边界。fixture应恢复环境和override，不把当前工作目录数据库当输入；正式PATCH路径固定/done。"],
"D22-api-errors": [
"响应状态和无traceback一起检查不同资源安全错误，不把内部堆栈交给用户。正式错误测试还需保留正常行为和临时库隔离，不用拼接假响应替代真实请求。",
"缺字段JSON触发422，表示输入边界失败而非成功创建。正式任务还应查列表确认没写库；不能捕获错误后把失败响应当200成功。"],
"D22-acceptance": [
"Path从测试文件定位既有contract，UTF-8读取后json.loads解析对象，不依赖cwd。路径存在只是前提；测试还需把约定与实际API/DB行为逐项对应。",
"不同标签接口比较状态及JSON形状，是可观察行为断言。正式验收不是只运行无关True测试；此阶段不检查后续CLI、HTML或交付文档存在。"],
"D23-cli-parser": [
"required子命令避免空输入默默选择动作，局部show示例只展示解析结构。正式add/list和参数需自行编写，解析阶段不执行数据库副作用。",
"args.command选择不同处理函数，Namespace直接作为参数传入，不使用eval字符串。示例show_handler须由不同业务提供，正式main接真实函数并finally关闭连接。"],
"D23-cli-mutate": [
"不同编号规则返回整数状态，零表示成功而非输出字典。正式done/rm还要依据真实数据层bool判断，不能通过写静态提示伪造任务变化。",
"sys.stderr是错误通道对象，file参数选择它；可运行卡分别显示stdout/stderr。此局部不包含当前CLI完整答案，正式main要非零返回并保留成功输出通道。"],
"D23-html-structure": [
"label.for对应input.id形成可访问名字，submit按钮提交不同便签表单。任务控件和完整文档仍需自行建立，不能只贴孤立标签通过整页结构验收。",
"不同便签列表、空状态和role=alert错误区分别保留更新目标。结构先确定，脚本后接入；没有fetch属于此节正常状态，不提前要求完整CRUD。"],
"D23-html-fetch": [
"不同便签POST明确方法、JSON字符串和Content-Type，先检查ok再解析。当前任务字段/路径不能照抄便签接口；这是协议局部例，不是整个HTML页面答案。",
"createElement构造li，textContent把便签内容当文字，append加入已准备列表。note/notesList来自上层逻辑；含HTML样式输入应原样显示，不进入innerHTML解释。"],
"D24-rebuild": [
"Windows使用刚创建venv的Python执行安装和测试，避免全局包偶然满足依赖。前提已复制当前源文件到新副本项目根，空目录没有pyproject不能直接安装。",
"Test-Path只读核配置与包存在，不会删除或生成源码。True来自新副本已复制内容；原环境、学习记录和数据库不应复制或被清理。"],
"D24-integrate": [
"API和另一终端CLI使用同一临时数据库，才能观察相同任务状态。两者使用项目venv，浏览器通过API读同库；不能把不同进程默认cwd差异隐藏。",
"记录POST/GET/PATCH /done/DELETE的实际字段与状态，以及页面变化。启动终端Ctrl+C停止，只清理本次副本；此顺序不是空泛的三入口正常报告。"],
"D24-artifacts": [
"局部表把文件对应创建章节与验证方法，便于缺失时回到正确上游。完整十五条由学习者核实实际文件，不复制表格便宣称完整交付。",
"runbook此时已有，review下一节才创建，状态应明确标待完成。不能提前要求未来文件存在；最终完整检查在review生成后进行，数据库不属于源码产物。"],
"D24-review": [
"Evidence填写实际pytest退出码、HTTP状态和CLI输出，每条能被复现核对。不是把示例文字直接当自己的结果；未执行的范围必须明确标未测。",
"失败段记录本人现象、定位文件、原因和同命令复测，让修正有因果证据。不是标准答案复盘；下一步还需具体行动和未解决问题，不能只写继续学习。"]
}
for _sid,_detail in DETAILED.items():
    UPDATES[_sid]["explanation"] = _detail
for _sid,_notes in EX_NOTES.items():
    for _example,_note in zip(UPDATES[_sid]["examples"],_notes):
        _example["explanation"] = _note


# 逐节错因使用真实接口、资源与阶段边界；例子只展示错误片段。
COMMON_ERRORS = {
    section: [
        {
            "error": error,
            "symptom": symptom,
            "cause": cause,
            "fix": fix,
            "example": {"code": code, "symptom": symptom, "fix": fix},
        }
        for error, symptom, cause, fix, code in rows
    ]
    for section, rows in {
        "D18-scope": [
            (
                "用内部调用代替用户故事",
                "需求写了 SQL 和函数名，却无法判断用户完成了什么动作。",
                "把内部实现当成需求，遗漏新增、列表、完成、删除的可观察结果。",
                "先按角色、动作、结果写用户故事，再检查四个动作是否都有可观察的结果。",
                "用户故事：执行 INSERT INTO tasks，再调用 db.commit()。",
            ),
            (
                "遗漏非目标与输入边界",
                "各入口自行扩展功能，空白标题和未知编号的处理没有共同依据。",
                "需求只列正常动作，没有界定拒绝哪些输入及本轮不做哪些功能。",
                "补充空白标题、未知编号的结果，并明确本轮非目标；先限定范围再讨论实现。",
                "需求：支持任务管理。\n# 没有输入边界，也没有非目标。",
            ),
        ],
        "D18-acceptance": [
            (
                "主流程只写操作没有预期状态",
                "清单包含四个步骤，却无法判定每一步是否真的改变了任务。",
                "验收未记录新增后的编号、列表字段、完成状态和删除后的集合变化。",
                "给每个步骤补充可观察字段或状态，串联同一编号的完整路径。",
                "1. 创建\n2. 查询\n3. 完成\n4. 删除\n# 各步均未注明结果。",
            ),
            (
                "错误场景被当作普通成功请求",
                "空白标题和重复删除只要收到响应就被算作通过。",
                "验收只覆盖顺利路径，没有写失败输入对应的状态码和状态不变条件。",
                "逐个记录坏输入、预期状态和应保留的数据库状态，核对 422 与 404 的区别。",
                "错误场景：只要服务器返回 HTTP 响应就算成功。",
            ),
        ],
        "D18-data-contract": [
            (
                "把类型名称当输出样例值",
                "JSON 能解析，但任务的 id 和 done 变成了字符串。",
                "把说明字段中的 integer、boolean 标记直接复制到了输出样例中。",
                "区分类型描述与实际输出，检查样例值的 JSON 类型及任务字段。",
                '{"task":{"output":{"id":"integer","title":"观察输入","done":"boolean"}}}',
            ),
            (
                "JSON 使用 Python 布尔字面量",
                "契约在检查字段之前就解析失败。",
                "把 Python 的 False 或 None 写进 JSON，混淆了两种数据语法。",
                "先检查 JSON 的引号、布尔值和空值写法，再检查字段约定。",
                '{"task":{"output":{"id":1,"title":"观察输入","done":False}}}',
            ),
        ],
        "D18-api-contract": [
            (
                "路由列表沿用旧 routes 字段",
                "当前契约读取方找不到 endpoints，无法核对 API 表。",
                "采用了旧文档的顶层键，未与当前 task、errors、endpoints 结构对齐。",
                "核对当前契约顶层结构，再逐条检查方法、路径、成功结果和错误结果。",
                '{"routes":[{"method":"GET","path":"/api/tasks"}]}',
            ),
            (
                "完成路径遗漏 done 段",
                "客户端完成任务时得到 404 或 405。",
                "把专门的完成接口误写成一般 PATCH 任务路径。",
                "逐字符核对完成接口的路径模板、task_id 和末尾 done 段。",
                '{"method":"PATCH","path":"/api/tasks/{task_id}"}',
            ),
        ],
        "D19-pyproject": [
            (
                "只声明运行依赖未声明开发依赖",
                "干净环境可以启动服务，却无法执行 pytest 或 TestClient。",
                "本机已有 pytest、httpx 掩盖了构建声明遗漏。",
                "区分运行依赖与 dev 依赖，检查 D24 使用开发依赖安装的命令。",
                '[project]\ndependencies = ["fastapi", "uvicorn", "pydantic"]\n# 没有 dev 依赖声明。',
            ),
            (
                "包发现范围包含无关目录",
                "构建扫描到学习记录或其它顶层目录，安装失败或交付混入无关内容。",
                "setuptools 的包发现范围没有限定到本项目的 taskproj 包。",
                "核对包目录与包发现设置；当前先完成声明，干净安装在最终验收复核。",
                '[tool.setuptools.packages.find]\ninclude = ["*"]',
            ),
        ],
        "D19-package": [
            (
                "导入包时就打开数据库",
                "仅 import taskproj 就产生数据库文件或留下未关闭连接。",
                "在 __init__.py 顶层获取运行资源，导入副作用超过版本声明。",
                "检查顶层可执行语句；把资源创建留给显式入口，保持包导入可观察地安静。",
                "import sqlite3\nconnection = sqlite3.connect('taskproj.db')",
            ),
            (
                "包初始化文件写成文档文本",
                "Python 导入包时报语法错误或名称错误。",
                "把 Markdown 式说明当成 __init__.py 的 Python 内容保存。",
                "先确认目标文件是 Python 源码，再以合法文档字符串或版本声明表达说明。",
                "任务管理包说明\n- 包含版本",
            ),
        ],
        "D19-config": [
            (
                "空环境变量没有回退",
                "TASKPROJ_DB 存在但为空时，配置得到空路径或当前目录。",
                "os.environ.get 的默认值只处理键不存在，不能处理已存在的空字符串。",
                "分别观察未设置、空字符串、自定义路径三种输入，定位回退条件。",
                "value = os.environ.get('TASKPROJ_DB', 'taskproj.db')\n# 空字符串仍会保留下来。",
            ),
            (
                "配置返回值仍是普通字符串",
                "调用方无法按 Path 的接口处理数据库位置。",
                "只读取环境文本，没有转换成当前契约要求的路径对象。",
                "同时检查返回类型和路径内容；配置读取本身不应创建数据库。",
                "return os.environ.get('TASKPROJ_DB') or 'taskproj.db'",
            ),
        ],
        "D19-main": [
            (
                "模块导入直接运行 main",
                "导入入口模块时就打印启动提示，测试收集受到额外输出干扰。",
                "模块顶层调用 main，没有区分导入与作为程序执行。",
                "分别测试导入和直接执行；定位入口保护条件及 main 的退出码。",
                "def main(argv=None):\n    print('任务管理项目已启动')\nmain()",
            ),
            (
                "入口提前依赖未来 API 文件",
                "D19 的启动入口报 ModuleNotFoundError，尚未进入本节逻辑。",
                "从 D21 才生成的 api.py 导入对象，越过当前文件边界。",
                "核对当前已生成的模块列表，本节入口先完成提示及退出行为。",
                "from .api import app\n# api.py 在后续课程创建。",
            ),
        ],
        "D19-readme": [
            (
                "未来命令写成当前已经可运行",
                "照 README 运行 CLI 或 API 命令时，模块还不存在。",
                "没有把后续计划与当前可执行能力区分开。",
                "为计划命令注明对应创建章节，最终在 D24 用实际运行结果补证据。",
                "当前可运行：python -m taskproj.cli list\n# D19 尚未生成 cli.py。",
            ),
            (
                "安装和测试解释器不一致",
                "README 的安装成功了，但执行测试仍提示缺依赖。",
                "裸 pip 与 python 可能来自不同环境，文档没有限定工作目录和解释器。",
                "给命令注明项目目录与虚拟环境，安装和测试都使用同一 Python。",
                "pip install -e .\npython -m pytest\n# 没有说明两者所属环境。",
            ),
        ],
        "D20-connection": [
            (
                "把数据库路径传给 init_db",
                "初始化报字符串没有 execute 方法。",
                "混淆创建连接与初始化表两层接口，init_db 的输入应是连接。",
                "核对两个函数的参数类型和调用顺序，并明确连接由谁关闭。",
                "init_db(':memory:')",
            ),
            (
                "连接遗漏 Row 行表示",
                "查询结果用 row['id'] 或 dict(row) 时失败。",
                "默认 sqlite3 行是元组，但后续代码按字段名称访问。",
                "在实际连接上观察查询行类型，核对 row_factory，避免靠猜下标补救。",
                "conn = sqlite3.connect(':memory:')\nrow = conn.execute('SELECT 1 AS id').fetchone()\nvalue = row['id']",
            ),
        ],
        "D20-create-list": [
            (
                "新增写入没有提交",
                "同一连接可看到任务，重新连接后任务消失。",
                "INSERT 仍处于未提交事务，只在当前连接里看起来成功。",
                "用第二个连接观察持久结果，定位写入后的事务提交及返回编号。",
                "conn.execute('INSERT INTO tasks(title) VALUES (?)', ('观察输入',))\n# 没有提交事务。",
            ),
            (
                "列表保留 SQLite 的整数 done",
                "输出出现 0 或 1，按布尔类型核对时失败。",
                "直接将数据库行转换为字典，没有转换对外字段类型。",
                "观察列表中每个字段的实际类型，特别核对 done 是否是布尔值。",
                "return [dict(row) for row in rows]\n# done 仍可能是数据库中的整数。",
            ),
        ],
        "D20-update-delete": [
            (
                "不存在编号也返回删除成功",
                "重复删除或删除未知编号仍得到 True。",
                "没有用受影响行数判断记录是否存在，忽略了 DELETE 的实际结果。",
                "对比首次删除、重复删除、未知编号，定位受影响行数与返回值的关系。",
                "conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))\nconn.commit()\nreturn True",
            ),
            (
                "完成操作被实现为状态翻转",
                "第二次完成同一任务时，任务又变回未完成。",
                "把完成当成 toggle，破坏重复完成应保持 done 的约定。",
                "重复执行完成并查询状态，核对更新目标是否始终表示已完成。",
                "UPDATE tasks SET done = 1 - done WHERE id = ?",
            ),
        ],
        "D20-db-tests": [
            (
                "把连接 fixture 当业务对象",
                "测试报 sqlite3.Connection 没有 add_task 方法。",
                "fixture 提供连接，而业务函数是接收连接的独立模块函数。",
                "核对 fixture 返回值、导入名和函数签名，再检查调用的参数顺序。",
                "def test_create(db):\n    db.add_task('观察输入')",
            ),
            (
                "测试只断言无关常量",
                "实现的排序、完成或删除被破坏，测试仍全部通过。",
                "断言没有观察当前 CRUD 调用产生的字段和状态。",
                "用实际输入检查新增字段、两条排序、完成、删除及未知编号，确认坏实现会失败。",
                "def test_everything():\n    assert True",
            ),
        ],
        "D21-app": [
            (
                "数据库初始化发生在导入时",
                "测试未进入客户端生命周期，数据库就已创建。",
                "启动连接放在模块顶层，没有受 lifespan 的进入与退出管理。",
                "分别观察导入、启动、退出；核对启动连接和请求连接各自的所有者。",
                "startup_conn = create_connection(get_db_path())\ninit_db(startup_conn)\n# 这些语句放在模块顶层。",
            ),
            (
                "依赖提供已关闭连接",
                "健康检查正常，但数据库请求报 Cannot operate on a closed database。",
                "get_db 在 yield 前关闭连接，或复用了已关闭的启动连接。",
                "检查 yield 前后顺序；连接应由使用它的请求结束后释放。",
                "conn = create_connection(get_db_path())\nconn.close()\nyield conn",
            ),
        ],
        "D21-schema": [
            (
                "输出模型仍沿用 TaskOut 名称",
                "当前练习导入 Task 时失败，或路由无法引用约定模型。",
                "照搬了旧模型名称，没有对齐当前 TaskIn 与 Task 公开接口。",
                "核对公开类名和输入、输出字段，同时保留前节应用与健康检查。",
                "class TaskOut(BaseModel):\n    id: int\n# 当前契约要求的输出名称是另一名称。",
            ),
            (
                "只声明 str 就认为会拒绝空白",
                "纯空白标题可以通过输入模型。",
                "字符串类型校验不会自动表示去空白及非空的业务限制。",
                "分别构造正常、空白、缺失标题，观察清洗与拒绝发生在哪一步。",
                "class TaskIn(BaseModel):\n    title: str\n# 没有表达空白标题的限制。",
            ),
        ],
        "D21-crud-routes": [
            (
                "删除仍采用 204 空正文",
                "客户端要求 200 和 JSON 时，状态码或解析结果不符合契约。",
                "沿用了旧删除协议，没有对齐当前删除响应与未知编号行为。",
                "核对本轮 DELETE 的状态、正文及 404 分支，再观察删除后的列表。",
                "@app.delete('/api/tasks/{task_id}', status_code=204)",
            ),
            (
                "路由调用未定义的 service",
                "模块能加载，请求执行到业务调用时却发生 NameError。",
                "使用了项目中未生成的服务对象，而非当前 db 模块的实际函数接口。",
                "查看 workspace_deps 中的真实导入与签名，定位连接及业务返回值的传递。",
                "return service.create_task(payload)",
            ),
        ],
        "D21-static": [
            (
                "静态路径依赖启动工作目录",
                "从另一目录启动时，首页找不到 index.html。",
                "相对路径从 cwd 解析，没有以 api.py 所在包目录定位资源。",
                "比较不同启动目录的目标路径，核对文件位置与模块文件位置的关系。",
                "return FileResponse('taskproj/static/index.html')",
            ),
            (
                "导入时检查尚未生成的静态目录",
                "D21 应用加载即报目录不存在，D23 尚未有机会创建页面。",
                "StaticFiles 在挂载时校验未来目录，提前要求后续产物。",
                "当前只核对首页响应的目标路径，HTML 文件内容等到 D23 创建后验证。",
                "app.mount('/', StaticFiles(directory='taskproj/static', html=True))",
            ),
        ],
        "D22-db-fixtures": [
            (
                "多个测试共享固定项目数据库",
                "后运行的测试读到前例任务，测试顺序改变就失败。",
                "连接指向固定数据库文件，fixture 未实现每例临时路径和隔离。",
                "至少两例分别检查空表和 tmp_path 所属路径，再观察退出后的连接状态。",
                "shared = create_connection('taskproj.db')\n# 所有测试复用同一个连接和文件。",
            ),
            (
                "清理步骤抛错阻止连接关闭",
                "teardown 失败后连接仍能使用，文件可能继续被占用。",
                "关闭前的清理动作异常，没有 finally 保证释放本例拥有的资源。",
                "检查清理异常路径，确认即使前置清理失败也会尝试关闭连接。",
                "yield conn\nraise ValueError('模拟 teardown 失败')\nconn.close()",
            ),
        ],
        "D22-api-tests": [
            (
                "进入 TestClient 后才设置数据库环境",
                "lifespan 已在默认路径初始化，测试读取错误数据库。",
                "把环境准备放在启动之后，忽略客户端上下文进入会触发生命周期。",
                "核对准备环境、进入客户端、请求、退出的顺序，并观察临时数据库位置。",
                "with TestClient(app) as client:\n    monkeypatch.setenv('TASKPROJ_DB', str(tmp_path / 'api.db'))",
            ),
            (
                "依赖覆盖在测试结束后残留",
                "后续测试继续获得旧临时连接，或请求遇到已关闭连接。",
                "app 是共享对象，dependency_overrides 中的替换没有恢复。",
                "检查覆盖使用的函数对象与清理时机，连续运行两例验证后例不借用前例资源。",
                "app.dependency_overrides[get_db] = fake_db\n# 测试结束没有恢复覆盖。",
            ),
        ],
        "D22-api-errors": [
            (
                "只断言响应对象存在",
                "未知编号返回 200 或坏输入被接受，错误测试仍通过。",
                "httpx 响应对象存在不等于符合错误协议。",
                "逐例比较状态、detail 及实际状态变化，定位 404 和 422 的分支。",
                "response = client.delete('/api/tasks/999')\nassert response",
            ),
            (
                "拒绝请求后未检查数据库状态",
                "接口回了 422，却已写入不合法任务，测试没有发现。",
                "只观察响应状态，没有验证失败请求不应产生业务写入。",
                "坏输入之后再查询列表，核对响应与数据状态共同符合拒绝语义。",
                "response = client.post('/api/tasks', json={'title': '   '})\nassert response.status_code == 422\n# 没有查询列表。",
            ),
        ],
        "D22-acceptance": [
            (
                "验收读取旧 routes 键",
                "contract.json 能解析，验收却因 KeyError 停止。",
                "验收读取方没有跟随 D18 当前 endpoints 契约字段。",
                "核对读取的顶层键与条目字段，从真实契约映射到请求再比较结果。",
                "for route in contract['routes']:\n    assert route['method']",
            ),
            (
                "中间验收要求未来 CLI 文件",
                "D22 无法完成，因为 cli.py 或页面尚未创建。",
                "把 D24 全项目文件清单提前用于当前阶段。",
                "列出本节已生成文件，只验证这些文件；最终跨入口验收留给 D24。",
                "assert Path('taskproj/cli.py').exists()\n# cli.py 在 D23 创建。",
            ),
        ],
        "D23-cli-parser": [
            (
                "建立解析器时就调用 handler",
                "构建解析器产生业务动作，或 args.func 得到返回值而不是函数。",
                "set_defaults 需要保存可调用对象，却传入函数调用的结果。",
                "观察构建、解析、分发三个时机，确认业务只在完成解析之后执行。",
                "add.set_defaults(func=run_add())",
            ),
            (
                "main 忽略传入 argv",
                "main(['list']) 读取了测试进程参数，结果不可控。",
                "parse_args 未接收 main 的 argv，使显式输入被 sys.argv 替代。",
                "分别检查显式列表输入和命令行默认输入，定位参数传递断点。",
                "def main(argv=None):\n    args = build_parser().parse_args()",
            ),
        ],
        "D23-cli-mutate": [
            (
                "业务失败写入 stdout 且退出零",
                "未知编号在终端看似成功，脚本无法从退出码和错误流判断失败。",
                "把数据库未找到记录的返回值映射成了成功分支。",
                "同时观察退出码、stdout、stderr 和数据库状态，核对未知编号路径。",
                "if not found:\n    print('任务不存在')\n    return 0",
            ),
            (
                "任务编号保持任意文本",
                "非法编号进入数据库业务，而不是在解析阶段被拒绝。",
                "TASK_ID 参数没有声明整数转换，Namespace 中仍是字符串。",
                "比较合法整数和非数字参数的解析结果，先定位解析层再检查业务调用。",
                "rm.add_argument('task_id')\n# 未指定整数类型。",
            ),
        ],
        "D23-html-structure": [
            (
                "label 未关联实际输入 ID",
                "点击标签不聚焦标题输入，辅助工具也无法识别对应关系。",
                "label 的 for 和 input 的 id 不一致。",
                "逐个核对语义属性与目标元素，不能仅凭标签文字在视觉上相邻。",
                '<label for="task-name">标题</label>\n<input id="title">',
            ),
            (
                "完成删除按钮意外提交表单",
                "点击删除时触发新增提交，或页面发生刷新。",
                "表单内部 button 未标明用途，浏览器采用默认提交行为。",
                "检查按钮类型与表单事件，再观察一次点击实际触发了哪些请求。",
                '<form><button data-action="delete">删除</button></form>',
            ),
        ],
        "D23-html-fetch": [
            (
                "未检查状态就解析 JSON",
                "空正文或非 JSON 错误页触发解析异常，掩盖真实 HTTP 失败。",
                "把所有响应都视为有 JSON 正文，忽略 ok、状态和正文边界。",
                "先观察状态与正文存在性再解析；本轮正常删除仍按 200 JSON 契约核对。",
                "const body = await response.json();\n// 没有检查响应状态与正文。",
            ),
            (
                "任务标题直接拼入 innerHTML",
                "用户输入的标签样式被解释成 HTML，标题没有按原文显示。",
                "把外部数据当成页面标记写入，而非作为文本节点。",
                "使用含尖括号的标题观察渲染边界，检查元素创建和文本赋值方式。",
                "item.innerHTML = task.title;",
            ),
        ],
        "D24-rebuild": [
            (
                "空目录没有源码就尝试安装",
                "editable 安装报找不到 pyproject.toml 或 taskproj 包。",
                "只创建了临时目录，没有先准备完整源码副本。",
                "核对副本中的源码清单后再建环境，学习记录和运行数据库无需复制。",
                "cd 新临时空目录\npython -m pip install -e .",
            ),
            (
                "创建虚拟环境后仍使用旧解释器",
                "安装落在旧环境，干净环境运行时仍缺依赖。",
                "创建 venv 不会自动改变当前解释器选择。",
                "核对安装和测试命令中的 Python 都来自同一新 venv，同时确认当前目录。",
                "python -m venv .venv\npython -m pip install -e '.[dev]'\n# 没有激活或显式选择新解释器。",
            ),
        ],
        "D24-integrate": [
            (
                "API 与 CLI 使用不同数据库",
                "CLI 新增成功，网页或 API 列表却看不到该任务。",
                "两个进程的 TASKPROJ_DB 或默认工作目录不一致。",
                "为本次集成显式设置同一临时数据库路径，追踪同一编号经过各入口的状态。",
                "# API 终端：TASKPROJ_DB=api.db\n# CLI 终端：TASKPROJ_DB=cli.db",
            ),
            (
                "服务启动日志被当作集成证据",
                "健康接口正常，但新增、完成、删除和 CLI 还没有实际验证。",
                "仅观察服务启动，没有走过跨入口的同一任务状态链。",
                "先运行测试，再逐项记录 HTTP、CLI、页面的真实结果，结束后停止本次临时服务。",
                "python -m uvicorn taskproj.api:app\n# 看到启动日志就记录集成完成。",
            ),
        ],
        "D24-artifacts": [
            (
                "当前清单提前要求下一节 review",
                "整理交付时因 review.md 尚不存在而被阻塞。",
                "把下一节才生成的复盘文件误当作当前必须已完成的产物。",
                "给清单注明当前已有与下一节待生成，最终检查在 review 创建后再核对全量。",
                "assert Path('docs/review.md').exists()\n# 还没有执行下一节。",
            ),
            (
                "把数据库与虚拟环境当作交付源码",
                "交付包含本机任务和环境文件，却遗漏模块、测试或文档职责。",
                "没有区分可重建源码与运行时产物。",
                "按源码清单核对文件职责，在副本中整理交付；保留原项目学习记录和运行文件。",
                "交付：taskproj.db、.venv、__pycache__。\n# 没有核对源码和测试责任。",
            ),
        ],
        "D24-review": [
            (
                "未执行的检查被记为通过",
                "复盘列出全部通过，却没有可以复核的命令和结果。",
                "把计划、示例或完成标记替代了真实验证证据。",
                "记录实际命令、退出码和观察值；未执行的范围明确写成未测。",
                "Evidence：pytest/API/CLI/网页全部通过。\n# 无执行命令或结果记录。",
            ),
            (
                "修正后没有同输入复测",
                "改了文件，但不能判断原始故障是否真正消除。",
                "复盘只有修改动作，没有把原输入与修正后的结果连接起来。",
                "用原输入和同命令复测，记录变化，再核对受影响范围的回归结果。",
                "Failure：创建状态不对。\nFix：已改 api.py。\nRetest：未记录。",
            ),
        ],
    }.items()
}

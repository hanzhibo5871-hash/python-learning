# Python / API / AI 学习路径（可视化工具版）

## 1. 使用方式

这是一条面向有前端基础学习者的**产物驱动**路径。原始 131 个来源条目只作为 `source_catalog` 知识范围标题索引；主线按阶段、任务和小节推进，不要求打开来源内容，也不下载或抓取来源。

每个小节都是**输入型实践**（没有选择题）：编码（code）、配置/契约（json）、复盘（text）、命令（command）或环境固定动作（env_action）。任务页默认显示课程与实践输入区，提供**保存草稿 / 运行并验证 / 重置为起始内容**三个按钮。本地验证只在本机执行，验证通过才完成小节；失败保留草稿，不自动把任务标记为完成。

启动工作台：

```powershell
python -m learnctl serve --open
```

D01 首次进入会讲清“将学什么、今天做什么、每步为什么需要”，并通过实时检测与四个固定动作把环境配置真实落地。

## 2. 阶段总览

| 阶段 | 目标 | 任务 | 主要产物 |
| --- | --- | --- | --- |
| S1 真实环境与基础语法 | 配置可验证的本地环境，掌握基础语法并完成第一个业务程序 | D01-D07 | `.venv` 环境、商品表单清洗程序 |
| S2 常用开发能力 | 掌握路径/JSON、CLI、配置/日志、HTTP/FastAPI、测试、SQLite、asyncio | D08-D17 | 一套可独立验证的开发能力 |
| S3 真实普通项目 | 从需求、契约、目录、配置、数据层、接口、测试、演示到重建交付 | D18-D24 | 可运行、可测试、可重建的本地任务管理项目 |
| S4 AI 应用 | 掌握 DeepSeek 官方 API 调用与提示词工程，完成一个可运行 AI 应用 | D25-D28 | 带 mock 测试的 AI 学习助手 |

S2 依赖 S1；S3 依赖 S2；S4 依赖 S2（不依赖 S3）。LangChain 云模型是显式选修，默认关闭，不进入主线。

## 3. 任务清单

### S1 真实环境与基础语法（D01-D07）

| 任务 | 主题 | 核心产物 |
| --- | --- | --- |
| D01 | 配置并验证你的 Python 开发环境 | 实时检测 + `.venv` + 可编辑安装验证 |
| D02 | 第一个业务程序：商品表单清洗与含税金额 | `clean_name` / `parse_price` / `process_form` |
| D03 | 条件与循环 | 评分等级、求和/倒计时/查找 |
| D04 | 函数、参数与作用域 | 默认参数、`*args/**kwargs`、闭包 |
| D05 | 数据容器 | 切片、计数、去重、合并 |
| D06 | 异常处理 | 安全除法、自定义异常 |
| D07 | 模块与包 | 导入自定义模块、`__main__` 守卫 |

### S2 常用开发能力（D08-D17）

| 任务 | 主题 | 核心产物 |
| --- | --- | --- |
| D08 | 路径、UTF-8 与 JSON | 读取/统计/写回 JSON 报告 |
| D09 | 命令行工具 | argparse 参数与错误退出码 |
| D10 | 配置与环境变量 | `os.environ` 与 `.env` 解析 |
| D11 | 日志 | 控制台与文件日志 |
| D12 | HTTP 客户端 | GET/POST + 错误处理（本地 mock 校验） |
| D13 | FastAPI 基础 | `/health`、路径/查询参数（补充） |
| D14 | FastAPI 参数与错误处理 | pydantic 模型与 HTTPException（补充） |
| D15 | 单元测试与 API 测试 | pytest 单测与 mock 测试（补充） |
| D16 | SQLite 标准库 | 建表与参数化 CRUD（补充） |
| D17 | asyncio 基础 | gather 与 wait_for 超时（补充） |

### S3 真实普通项目：本地任务管理（D18-D24）

| 任务 | 主题 | 核心产物 |
| --- | --- | --- |
| D18 | 需求与契约设计 | 需求说明与 JSON 契约（补充） |
| D19 | 项目骨架与配置 | `taskproj/config.py` 与入口 |
| D20 | SQLite 数据层 | `taskproj/db.py` 参数化 CRUD |
| D21 | API 与业务层 | `taskproj/api.py` FastAPI 路由 |
| D22 | 测试与验收 | 数据层单测与接口 mock 测试 |
| D23 | CLI 与网页演示 | `taskproj/cli.py` 子命令 |
| D24 | 重建交付与复盘 | 重建命令序列与复盘 |

### S4 AI 应用（D25-D28）

| 任务 | 主题 | 核心产物 |
| --- | --- | --- |
| D25 | DeepSeek API 调用 | `call_chat` + `ApiError`（本地 mock 校验） |
| D26 | 提示词与索引驱动 | `build_prompt` + `parse_ai_json` |
| D27 | AI 应用项目 | `send_message` + `review_submission` 流程 |
| D28 | 测试与交付复盘 | AI 客户端 mock 测试与复盘 |

## 4. 完成定义

- 小节完成：本地 validator 全部检查通过（`code` / `json` / `text` / `command` / `env_action` 各自确定性校验）。
- 任务完成：手动填写证据并 `progress mark <TASK> --status done`（不自动完成）。
- 练习（可选）：`python -m learnctl test <exercise_id>` 运行课程声明的 `learner_tests/*.py`。
- 阶段完成：阶段内任务全部完成；最终验收以重建演示为准。

## 5. 安全与边界

- 本地验证只绑定 `127.0.0.1`；代码在本机执行，UI 明确这不是假装安全的沙箱。
- 除 AI 助教按钮外，工具不联网；AI 调用只发送当前可见练习内容与相关索引标题。
- FastAPI、SQLite、asyncio、测试、配置/日志/CLI、JSON 工程实践与 DeepSeek API 均为 `supplemental` 真实开发补充，索引标题只作知识范围，不代表视频正文。

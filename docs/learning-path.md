# Python / API / AI 学习路径（实践优先）

D01–D28 是任务编号，不是固定天数。每节先看短规则和缺失知识卡，再改代码、比较结果、完成独立作业；补全练习不替代作业验收。

| 任务 | 目标与实践节奏 | 已声明的复习入口 |
| --- | --- | --- |
| D01 | 依次点击环境按钮；以实际检测通过为准，不必背术语。 | 无需前置 |
| D02 | 先改变量或表达式，运行看变化。函数外壳由起始代码提供，D04 再从头编写。 | D01-verify |
| D03 | 先运行条件表，再补分支或循环。and 是同时成立，or 是至少一个成立，not 是取反。 | D02-names、D02-numbers、D02-bool-none |
| D04 | 先写返回值，再打印观察；参数、默认值、作用域分开练，不把输入校验混进第一题。 | D03-if、D02-string-methods |
| D05 | 打印容器修改前后，再写函数处理新数据。空容器用 []、{}、set() 区分。 | D03-for、D04-def-return |
| D06 | 先制造一次错误，再处理它。预期要求抛异常时，正确抛出也会显示为通过。 | D03-if、D04-def-return |
| D07 | 先调用一个模块，再创建一个小对象。平台提供的辅助文件会明确列出。 | D04-def-return、D06-try-except |
| D08 | 每次写文件后立即读回，观察真实内容；实验在临时目录进行，不改你的项目文件。 | D07-import、D06-with、D05-traversal |
| D09 | 先传一组 argv，再传错误参数；分别观察正常输出、错误输出和退出码。 | D04-default-keyword、D07-main、D06-try-except |
| D10 | 使用一份小字典模拟环境，逐项读取和转换；不要打印真实密钥。 | D07-import、D05-dict-set、D06-raise、D07-dataclass |
| D11 | 只发一条日志，比较级别、输出位置和重复次数，再增加处理器。 | D07-import、D06-with |
| D12 | 先构造请求，再用本页提供的假响应观察结果；不需要联网或自己编写 mock 框架。 | D08-json-read、D06-with、D06-raise |
| D13 | 先让一个 GET 接口返回 JSON，再改路径和参数；复杂异步生命周期放到 D17 后复练。 | D04-def-return、D04-type-hints、D12-response |
| D14 | 依次练模型、业务函数、错误映射和依赖；不要求提前安装数据库。 | D13-app、D07-class-instance、D06-raise |
| D15 | 先运行一个成功测试，再故意改错一次，阅读差异；不是只有 assert 就算通过。 | D04-def-return、D08-pathlib、D13-app |
| D16 | 用内存数据库练连接、建表、增删改查；每一步查询表内容，不只看“执行成功”。 | D04-def-return、D06-try-except、D15-assert |
| D17 | 先 await 一个结果，再并发两个任务，最后观察超时和取消；先不接真实网络。 | D04-def-return、D06-try-except |
| D18 | 先完成数据字段，再增加接口；这一节不要求实现后续路由或项目文件。 | D08-json-read、D13-route、D14-errors |
| D19 | 一次只生成一个真实文件。说明中的函数名、路径和验证器保持一致。 | D07-package、D07-main、D10-env、D15-assert |
| D20 | 先连接和建表，再新增查询，最后完成删除；不提前检查下一节功能。 | D16-schema、D16-crud、D19-config |
| D21 | 先健康接口和模型，再 CRUD，最后首页路径；完整 HTML 在 D23 才生成。 | D14-model、D14-deps、D17-coroutine、D20-update-delete |
| D22 | 只测试当前已经生成的文件。15 个交付文件的完整核对放在 D24。 | D15-fixture、D15-api、D21-crud-routes |
| D23 | 先 add/list，再 done/rm；网页先结构，再逐次接入 GET/POST/PATCH/DELETE。 | D09-subcommands、D20-update-delete、D21-crud-routes |
| D24 | 用现有真实文件演示一次重建、测试和三种入口，不用另写一篇长报告。 | D19-readme、D22-api-errors、D23-html-fetch |
| D25 | 先模拟请求体和响应，再写客户端；真实调用需自行配置 Key，本地验证不用 Key。 | D12-post、D12-timeout、D06-custom、D24-review |
| D26 | 提示词只组织已授权内容；解析后检查形状，不把坏 JSON 当成功。 | D08-json-read、D02-string-methods、D25-chat |
| D27 | 把请求、解析和字段检查接起来；平台提供的模块只是本地测试夹具，不冒充你的交付物。 | D25-errors、D26-parse、D26-prompt |
| D28 | 写正常、401 和非 JSON 三个真实测试；最后用简短文字记录证据。 | D15-mock、D27-flow |

## 验收与进度

S1（D01–D07）完成环境和基础语法，S2（D08–D17）完成常用开发，S3（D18–D24）完成真实任务管理器，S4（D25–D28）组合 AI API 应用。S4 依赖 S3，不跳过普通项目。

示例/补全题运行只显示结果，正式作业验证通过才完成小节；任务全部必修通过后仍需在页面底部填写证据并标记完成。原有选修保留，D13 生命周期额外标为 D17 后选修；必修所需的最小 yield/装饰器用法由前置卡提供。

D01 不用编程：写一句目标 → 检测 → 创建 .venv → 安装依赖 → 最终检查。安装可能联网。Windows 启动脚本优先使用项目 .venv 的解释器，避免装好了依赖却用另一个 Python 启动。

工具测试 `python -m pytest -q tool_tests` 与学员练习测试 `python -m learnctl test <exercise_id>` 不混用。更多说明见 [实践优先版维护说明](practice-first.md)。

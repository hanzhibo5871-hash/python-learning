# DeepSeek 调用审计与 Windows 真实 API 验收

审计日期：2026-10-12。基线：main `d097342c536102b925076940f4a4c62b0d6e9413`。

**真实接口验收状态：尚未完成。** 单元测试、回环 HTTP 测试和浏览器里的模拟服务，都不证明用户电脑、真实 Key、账户余额或 DeepSeek 线上服务可用。本次没有使用真实 Key，也没有向官方 API 发出带 Key 的请求。

## 调用链与修复

浏览器显式操作 → 本机 `POST /api/ai/test|chat|generate|review` → `learnctl/ai.py` → 官方 `POST https://api.deepseek.com/chat/completions` → 响应校验 → 本机 JSON → 页面显示。

| 核对项 | 发现与处理 |
| --- | --- |
| 模型兼容性 | 旧 `deepseek-chat` 已被官方公告退役。更新为当前文档中的 `deepseek-flash`，显式 `thinking.type=disabled`，保持简短的非思考答疑，不做自动切模型。实际账号可用性仍待真实验收。 |
| 请求格式 | UTF-8 JSON、POST、Bearer、`stream:false`；文本最多 1024 输出 token，结构化输出最多 4096；生成/评审保留 `response_format:{type:"json_object"}` 和提示词中的 JSON 约束。 |
| 响应解析 | 非流式响应前导空白可解析；拒绝非 JSON、错误类型、非 assistant、空文本，以及缺失/异常 `finish_reason`。只有 `stop` 才接收；`length`、过滤、工具调用、资源中断或 aborted 不显示为成功，不发起结构修复。 |
| 网络与超时 | 原先 TimeoutError、断流等可绕过 AI 错误路径；现在连接、成功响应读取、HTTP 错误响应读取均统一为 AiError。TLS 校验保持开启，错误响应也关闭。 |
| HTTP 错误 | 400/401/402/404/422/429/500/503 提供本地中文处理建议；不展示上游响应体或原始代理异常，避免回显凭据、学习内容。失败不自动重试。 |
| 前端失败显示 | 本机 AI 端点以 HTTP 200 返回 `ok:false`；原 fetch 包装器未拒绝这种结果，测试连接会误报成功。现在全部 AI 操作统一拒绝失败信封，非 JSON 本机响应也报错。 |
| 上下文 | 沿用服务端当前小节、3 轮成功对话、完整轮次裁剪与总字符上限、限长的当前编辑器及验证摘要；历史 role 为数组/对象原会触发 TypeError，现安全拒绝。前端失败不写入历史、输入保留，迟到响应隔离保持有效。 |
| 密钥保护 | 内存 Key 优先于环境变量；拒绝内部空白、非 ASCII、控制字符，错误不含原始 Key；阻止 HTTP 重定向转发 Authorization。状态端点不返回 Key，不写文件或日志。清除内存 Key 后仍可能读到环境变量，须分别清理。 |

结构化输出只在完整模型文本违反 JSON/schema 时允许一次同模型修复。HTTP/网络/超时/中断/空响应不触发这次修复；普通答疑从不自动重试。

### 自动化覆盖及边界

- `tool_tests/test_ai_transport.py` 测试实际 Request 的 URL、UTF-8、头、超时参数、模型与模式；注入连接/读取超时、TLS、断流和 HTTPError，检查资源关闭及不泄密。
- 同文件用本机临时 HTTP 服务执行真实 urllib 回环请求，测试 301/302/303/307/308 均不访问重定向目标。仅使用虚拟密钥。
- `tool_tests/test_ai.py` 保留当前课时、上下文限长、JSON/schema、一次结构修复与不重试覆盖；成功夹具补齐正式响应的 role/finish_reason。
- `tool_tests/test_web.py` 验证 HTTP 错误信封、密钥验证、超时后恢复和原有文件不被改写；临时测试进度不提交。
- `tool_tests/test_ai_frontend.py` 执行真实 JS 请求包装器，覆盖 HTTP 200 + `ok:false`、HTTP 错误、坏 JSON及恢复；无需浏览器。
- `scripts/browser_tutor_smoke.py` 在临时工作区验证三个按钮不误报成功，以及对话失败重试、完整历史、切课时和清空后的隔离。provider 为模拟实现。

60 秒是 urllib 底层阻塞操作的超时，**不是严格的整次请求墙钟时限**。DNS、代理和服务器持续发送保活数据会影响总时长；当前仍为非流式，不提供取消远端生成。卡住时可用 Ctrl+C 停止本机服务再启动；这不会撤销已送达提供方的请求，也不能保证不计费。真实代理/TLS、持续保活、线上限流和模型质量仍需实机观察。

D25 等教学示例仍含旧模型名称，它们属于学习者实现与模拟验证，不是本次修复的工作台助教调用链；实际独立调用前需按当前官方文档更换模型并关闭思考模式。本次未改课程或学习进度。

## Windows 最小真实验收（约 5 分钟）

需要：Windows 11、Python 3.11+、已更新到本修复的源码、用户自己的有效 DeepSeek API Key 与可用 API 余额。会产生少量真实 API 费用。账号网页登录会员不等于 API 余额。

### 1. 启动与配置

在工作台根目录打开 PowerShell。先用 `git status --short` 检查自己的改动；不要强制覆盖、重置或清理。修复尚未合并时，可在工作区干净的情况下获取 PR 的分支：

```powershell
git fetch origin
git switch --track origin/fix/deepseek-api-compatibility
```

若本地已存在同名分支，使用 `git switch fix/deepseek-api-compatibility`；合并后正常更新 main 即可。保留 `.learn`、`.venv` 和本地练习目录，不要提交它们。

双击 `start_learning.bat`；或使用已有项目环境：

```powershell
.\.venv\Scripts\python.exe -m learnctl serve --open
```

如果尚未创建项目环境，用 `python -m learnctl serve --open`，按 D01 已有流程准备环境；不必为了 AI 验收重建现有环境。

在当前课时打开“AI 助教”，把真实 Key 粘贴到密码框，点击保存到本次服务内存。输入框应清空，页面只显示已配置。不要把 Key 写进代码、命令行字面量、`.env`、草稿、笔记、截图或聊天。

可在浏览器打开 `http://127.0.0.1:8765/api/ai/status`（使用实际启动端口），应看到 `provider=deepseek`、`model=deepseek-flash`、`configured=true`、`key_source=session`，没有 Key 文本。**这里只证明配置存在，不证明连接成功。**

### 2. 连接测试

点击一次“测试连接”。通过条件：显示“连接成功”且有非空文本；不能仅凭“已配置”判定。失败时记录 HTTP 状态/中文错误即可，不复制请求头或 Key。连续点击没有必要。

### 3. 正常提问与上下文

保持当前正在学习的小节，提问：

> 请用两句话解释当前小节的核心概念，并给一个最短例子。

通过条件：有正常中文回答，主题符合当前小节；随后问“刚才例子中的第二行有什么作用？”，应能结合上一轮回答。正常答复未出现“被截断”等错误。

不要点击课程“标记完成”或正式验证来证明 API 成功。AI 回答不改变小节完成状态。切到另一课时应有独立对话，刷新会清空浏览器对话。

### 4. 失败与恢复

1. 把服务内存中的 Key 临时改为虚拟值 `dummy-invalid-key-for-acceptance`（不是你的真实 Key），保存后点击“测试连接”。预期显示鉴权失败（通常 HTTP 401），**不得显示连接成功**；若是网络/余额错误，说明当前测试被其他原因阻挡，不能算通过鉴权验收。
2. 用同一个虚拟 Key 发一个当前课时问题。预期报错、问题仍留在输入框，成功历史不增加。
3. 从你自己的安全记录重新粘贴真实 Key 并保存；再点“测试连接”应成功，然后重发输入框里的问题，应只追加一轮成功对话，不包含失败轮次。
4. Ctrl+C 停止服务后重新启动。若没有设置环境变量，状态应恢复为未配置。重新输入真实 Key 即可；原学习进度和草稿应保留。

常见失败处理：401 重新检查 Key；402 检查 API 余额；429/500/503 等待后手动再点一次；404 检查是否实际运行了修复后的版本；TLS/网络/超时检查电脑时间、网络和代理，保留证书校验。超时后远端请求是否已计费未知，避免连续重复点击。

### 5. 只记录脱敏验收结论

以下记录保存在自己的本地记录中即可，无需提交 GitHub：

```text
验收时间（北京时间）：
源码提交：
Windows / Python 版本：
状态：model=deepseek-flash，configured=true，无密钥回显 [通过/失败]
真实连接测试：有非空回复 [通过/失败]
当前课时问答与追问：[通过/失败]
错误密钥：报错且不误报连接成功 [通过/失败]
失败问题保留、历史不增加：[通过/失败]
恢复真实密钥后同问题重发：[通过/失败]
未设置环境变量时，服务重启后密钥消失：[通过/失败/不适用]
最终：真实 API 验收 [完成/尚未完成]
```

未完成任一关键项，就保留“尚未完成”并写明阻挡错误；不要用 CI 通过替代实机验收。

## 官方协议依据（2026-10-12 核对）

- [旧模型退役公告](https://api-docs.deepseek.com/news/news260424/)
- [当前模型名称](https://api-docs.deepseek.com/quick_start/pricing/)
- [对话接口：模式、JSON、token 上限、finish_reason](https://api-docs.deepseek.com/api/create-chat-completion/)
- [错误状态码](https://api-docs.deepseek.com/quick_start/error_codes/)

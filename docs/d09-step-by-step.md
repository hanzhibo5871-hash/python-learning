# D09：从“看懂输入”到“选择功能”

这一版沿用库存场景，把原先挤在四节里的命令行知识拆成 **11 个小步**。每节都是“用途与场景 → 完整示例和实际输出 → 两道补全/改写 → 一道独立作业”。原来的三节加练继续选修。

不需要一口气学完，也不必先背下整个 argparse。先说清楚当前这一行在做什么，再动手。

## 学习顺序

| 顺序 | 小节 ID | 本次只弄懂什么 | 独立作业 |
|---|---|---|---|
| 01 | D09-argv | argv 是自选名字；列表里面先都是文字 | 原样返回三个输入字符串 |
| 02 | D09-position | 创建解析器、声明位置参数、解析输入各做什么 | product_options(argv) |
| 03 | D09-options | --delta、type=int、default=0 | adjustment_options(argv) |
| 04 | D09-stock | Namespace 用点号；库存字典用方括号 | adjust_stock(argv) |
| 05 | D09-parser | 带值选项与 store_true 开关 | --limit 与 --verbose |
| 06 | D09-command-name | 总解析器、子解析器、dest 各是什么 | 只识别 show / adjust |
| 07 | D09-if-dispatch | 分派就是根据命令选择代码 | 用 if 查看或调整库存 |
| 08 | D09-function-value | 保存函数与立即调用函数的区别 | call_action(action, value) |
| 09 | D09-subcommands | 先绑定处理函数，再统一调用 | list / add 的函数分派 |
| 10 | D09-errors | 输入错误、stderr、SystemExit 与 --help | parse_or_error(argv) |
| 11 | D09-entry | argv=None、空列表、真实终端与入口守卫 | 真正可从终端调整库存 |

建议先完成 01–05，把普通参数吃透；再做 06–09，解决子命令和函数分派；最后做 10–11，连接错误处理和终端。第 09 节将 show/adjust 换成 list/add，练同一种结构的迁移，不增加数据库、网络或文件存储要求。

## 不要混淆的几组概念

**输入与结果。** `argv` 是传进去的字符串列表；`args` 是保存解析结果的变量。它们都是自选名字。`Namespace` 是结果对象的类型，不需要自己手写这个类。

**制定规则与真正解析。** `add_argument(...)` 只登记规则；`parse_args(argv)` 才用这些规则处理一次输入。声明 `product` 后，从结果里读取 `args.product`；用户填的是“原料”，不是单词 product。

**库配置与自己取的名字。** `type`、`default`、`action`、`dest` 是库方法接受的配置名；`product`、`command`、`func` 是本例自己选的字段名。换字段名时，要一起修改后续读取位置。

**识别命令与执行命令。** `dest="command"` 让结果保存用户选的命令名称；`set_defaults(func=handle_list)` 保存处理函数；`args.func(args)` 才调用函数。先用 `if` 做同一件事，再理解这种简化写法。

**函数本身与函数返回值。** `action = handle_list` 只是保存函数；`action = handle_list(...)` 会马上执行并保存返回值。这是第 08 节要单独练的内容。

**模拟列表与真实命令。** `parse_args(["原料", "--delta", "-3"])` 只解析这份列表；`parse_args(None)` 读取本次真实命令行；`parse_args([])` 是明确没有参数。不能用 `argv or []` 将后两种情况合并。

## 库存练习的边界

正数入库、负数出库、零不变。只检查输入形式，**不要求调整量为正，也不拒绝负库存**。题目保证商品已经存在；不新增商品、不写数据库、不添加余额校验。第 04/07 节要求返回新库存，不是只打印；第 11 节才按命令行要求打印并返回退出码 0。

同一段程序里连续调用会在当前库存上继续调整；每个网页实验使用独立临时进程，重启终端程序也会重新创建初始库存。当前练习不做持久化。

三道原有选修加练保留：问候命令、重复输出命令、可导入的平方命令。只有“重复输出”选修题明确规定次数必须为正，不要把这条业务规则移到库存调整或 --limit 练习中。

## 旧进度与新练习

保留 `D09-parser`、`D09-subcommands`、`D09-errors`、`D09-entry` 以及三道加练的 ID。新增七节使用新 ID；不删除 `.learn`、已有草稿、完成证据或学习者项目文件，不把旧完成记录冒充成新增练习的验证结果。

已经完成旧 D09 的学习者，可以从第 01 节顺序复习。旧四节的说明和部分验收要求已补充明确，重新提交旧草稿时会使用新要求；第 09 节明确处理函数返回的文字，第 11 节明确真实库存命令入口，不保证所有旧草稿无需调整就能重新通过。

## 更新与打开

在本地仓库目录获取已合并的最新 main 后，关闭旧工作台进程，再运行：

```powershell
git pull --ff-only
python -m learnctl serve --open
```

也可以双击 `start_learning.bat`。不要删除学习进度或重置草稿。已有本地修改导致 pull 拒绝时，先保存自己的修改，不要使用强制覆盖命令。

## 维护与验收

课程内容在 `scripts/d09_course.py`，由 `scripts/build_curriculum_v3.py` 在通用实践版构建后应用。生成的 `data/curriculum.json` 和短讲解目录 `teaching-catalog.js` 必须一起提交；重复构建应没有漂移。

独立作业在 `learnctl/d09_checks.py` 使用已有临时子进程框架检查真实行为，包含默认值、负数、未知输入、SystemExit、错误前不更新库存、连续调用、函数返回值及真实终端。不是只检查是否出现某个方法名。工作台不把隐藏补全参考答案发给浏览器。

Python 官方参考：[argparse](https://docs.python.org/3/library/argparse.html)。本课只使用 Python 3.11 已支持的 API。

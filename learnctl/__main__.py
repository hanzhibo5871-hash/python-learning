from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .curriculum import MODULE_STATUSES, load_curriculum
from .diagnostic import collect_answers, load_answers, persist_diagnostic, run_diagnostics
from .errors import LearnctlError, UsageError
from .progress import TASK_STATUSES, load_progress, task_status
from .test_runner import run_exercise
from .workflow import (
    missing_prerequisites,
    missing_stage_prerequisites,
    missing_required_sections,
    module_status,
    required_sections,
    task_payload,
    today_payload,
    update_module,
    update_option,
    update_task,
)


STATUS_LABELS = {
    "learn": "需要学习",
    "practice": "需要练习",
    "mastered": "已掌握",
}


def _configure_utf8_streams() -> None:
    """集中把 stdout/stderr 配置为 UTF-8，保证管道、重定向与控制台跨平台一致。

    Windows 默认控制台代码页（cp936/GBK）会让 CLI 的 JSON 与错误消息在管道里
    变成 GBK 字节；这里在 CLI 入口统一 reconfigure 成 UTF-8 并采用严格 errors，
    不修改用户全局环境、不散落到各处 print、不回退到 GBK。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="strict")
        except (OSError, ValueError):
            # 流已关闭或该实现不支持 reconfigure 时保持原状，不影响其他流。
            continue


class ChineseArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"参数错误：{message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(prog="python -m learnctl", description="本地 Python 学习进度工具")
    commands = parser.add_subparsers(dest="command", required=True)

    diagnose = commands.add_parser("diagnose", help="运行 D0-D5 学习诊断")
    diagnose.add_argument("--json", action="store_true", help="仅输出 JSON")
    diagnose.add_argument("--answers", type=Path, metavar="PATH", help="从 JSON 文件读取 D1-D5 答案")

    today = commands.add_parser("today", help="查看当前主线任务")
    today.add_argument("--json", action="store_true", help="仅输出 JSON")

    lesson = commands.add_parser("lesson", help="查看任务知识卡")
    lesson.add_argument("task_id", nargs="?", metavar="TASK", help="任务 ID，省略时使用今日任务")
    lesson.add_argument("--json", action="store_true", help="仅输出 JSON")

    progress = commands.add_parser("progress", help="查看或更新进度")
    progress_commands = progress.add_subparsers(dest="progress_command")

    mark = progress_commands.add_parser("mark", help="更新任务状态")
    mark.add_argument("task_id", metavar="TASK")
    mark.add_argument("--status", choices=sorted(TASK_STATUSES), required=True)
    mark.add_argument("--evidence")

    module = progress_commands.add_parser("module", help="更新知识模块掌握程度")
    module.add_argument("module_id", metavar="ID")
    module.add_argument("--status", choices=sorted(MODULE_STATUSES), required=True)

    option = progress_commands.add_parser("option", help="启用或关闭选修方向")
    option.add_argument("option_id", metavar="ID")
    switch = option.add_mutually_exclusive_group(required=True)
    switch.add_argument("--enabled", action="store_true")
    switch.add_argument("--disabled", action="store_true")

    test = commands.add_parser("test", help="运行课程中指定的 pytest 练习")
    test.add_argument("exercise_id", metavar="EXERCISE")
    test.add_argument("--verbose", action="store_true", help="直接显示 pytest 输出")

    serve = commands.add_parser("serve", help="启动本地可视化学习工作台")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--open", action="store_true", help="启动后打开浏览器")
    return parser


def _paths() -> tuple[Path, Path, Path]:
    root = Path.cwd()
    return root / "data" / "curriculum.json", root / ".learn" / "progress.json", root / ".learn" / "diagnostic-report.json"


def _diagnose_command(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    progress_path: Path,
    report_path: Path,
    json_output: bool,
    answers_path: Path | None,
) -> int:
    supplied = load_answers(answers_path) if answers_path is not None else None
    prompt_stream = sys.stderr if json_output else sys.stdout
    answers = collect_answers(
        curriculum,
        supplied,
        prompt_stream=prompt_stream,
        input_stream=sys.stdin,
    )
    report = run_diagnostics(curriculum, answers, progress["options"])
    persist_diagnostic(report, curriculum, progress, report_path, progress_path)
    if json_output:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print("Python 学习诊断结果")
        print("诊断  得分  关键用例  结论")
        for item in report["diagnostics"]:
            decision = {"pass": "通过", "partial": "部分通过", "fail": "未通过"}[item["level"]]
            critical = "通过" if item["critical_passed"] else "未通过"
            print(f"{item['id']:<5} {item['score']:>3}%  {critical:<6} {decision}")
        print("知识模块建议：")
        for status in sorted(MODULE_STATUSES):
            values = "、".join(report["recommendations"][status]) or "无"
            print(f"  {STATUS_LABELS[status]}（{status}）：{values}")
        print(f"报告已写入：{report_path}")
    return 0 if report["passed"] else 1


_missing_prerequisites = missing_prerequisites
_missing_stage_prerequisites = missing_stage_prerequisites
_module_status = module_status
_task_payload = task_payload
_today_payload = today_payload


def _print_today(payload: dict[str, Any]) -> None:
    if payload["all_done"]:
        print("主线任务已全部完成。")
        return
    task = payload["task"]
    print(f"今日任务：{task['id']} {task['title']}")
    if payload["blocked"]:
        print(f"当前任务被前置条件阻塞：{'、'.join(payload['missing_prerequisites'])}")
        return
    print(f"学习目标：{task['learning_goal']}")
    print("知识模块：")
    if not task["modules"]:
        print("  无")
    for module in task["modules"]:
        print(f"  {module['id']} [{module['status']}] {module['title']}")
    print(f"编码动作：{task['coding_task']}")
    print(f"产物：{'；'.join(task['artifacts'])}")
    print("验收测试：")
    for exercise in task["exercises"]:
        print(f"  {exercise['id']}：{exercise['command']}")
    print(f"验收：{'；'.join(task['acceptance'])}")


def _print_lesson(payload: dict[str, Any]) -> None:
    if payload["all_done"]:
        print("主线任务已全部完成。")
        return
    task = payload["task"]
    print(f"知识卡：{task['id']} {task['title']}")
    if payload["blocked"]:
        print(f"前置条件：{'、'.join(payload['missing_prerequisites'])} 尚未完成")
    print(f"学习目标：{task['learning_goal']}")
    print("概念卡：")
    for concept in task["concepts"]:
        print(f"  - {concept}")
    print(f"前端类比：{task['frontend_bridge']}")
    print(f"关键语法示例（{task['snippet']['language']}）：")
    print(task["snippet"]["code"])
    print(f"编码任务：{task['coding_task']}")
    print(f"产物：{'；'.join(task['artifacts'])}")
    print("验收测试：")
    for exercise in task["exercises"]:
        print(f"  {exercise['id']}：{exercise['command']}")
    print(f"验收：{'；'.join(task['acceptance'])}")
    if task["references"]:
        print("可选官方文档：")
        for reference in task["references"]:
            print(f"  {reference['title']}：{reference['url']}")


def _mark_task(curriculum: dict[str, Any], progress: dict[str, Any], progress_path: Path, args: argparse.Namespace) -> int:
    update_task(curriculum, progress, progress_path, args.task_id, args.status, args.evidence or "")
    print(f"任务 {args.task_id} 已更新为 {args.status}。")
    return 0


def _mark_module(curriculum: dict[str, Any], progress: dict[str, Any], progress_path: Path, args: argparse.Namespace) -> int:
    update_module(curriculum, progress, progress_path, args.module_id, args.status)
    print(f"知识模块 {args.module_id} 已更新为 {args.status}。")
    return 0


def _set_option(curriculum: dict[str, Any], progress: dict[str, Any], progress_path: Path, args: argparse.Namespace) -> int:
    enabled = bool(args.enabled)
    update_option(curriculum, progress, progress_path, args.option_id, enabled)
    print(f"选修项 {args.option_id} 已{'启用' if enabled else '关闭'}。")
    return 0


def _print_progress(curriculum: dict[str, Any], progress: dict[str, Any]) -> None:
    print("学习进度")
    for stage in curriculum["stages"]:
        done = sum(task_status(progress, task_id) == "done" for task_id in stage["task_ids"])
        print(f"  {stage['id']} {stage['title']}：{done}/{len(stage['task_ids'])}")
    print("知识模块掌握程度：")
    for module in curriculum["modules"]:
        enabled = not module.get("optional_track_id") or progress["options"].get(module["optional_track_id"], False)
        if enabled:
            print(f"  {module['id']}：{_module_status(module, progress)}")
    payload = _today_payload(curriculum, progress)
    if payload["all_done"]:
        print("下一任务：全部完成")
    else:
        task = payload["task"]
        print(f"下一任务：{task['id']} {task['title']}")
        if payload["blocked"]:
            print(f"阻塞项：{'、'.join(payload['missing_prerequisites'])}")
    print("选修项：")
    for track in curriculum["optional_tracks"]:
        enabled = progress["options"].get(track["id"], track["default_enabled"])
        print(f"  {track['id']}：{'已启用' if enabled else '已关闭'}")


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_streams()
    args_list = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(args_list)
    curriculum_path, progress_path, report_path = _paths()
    json_output = bool(getattr(args, "json", False))
    try:
        if args.command == "serve":
            from .web.server import serve as serve_web

            return serve_web(Path.cwd(), args.host, args.port, args.open)
        curriculum = load_curriculum(curriculum_path)
        progress = load_progress(progress_path, curriculum)
        if args.command == "diagnose":
            return _diagnose_command(curriculum, progress, progress_path, report_path, json_output, args.answers)
        if args.command == "today":
            payload = _today_payload(curriculum, progress)
            if json_output:
                print(json.dumps(payload, ensure_ascii=False))
            else:
                _print_today(payload)
            return 1 if payload["blocked"] else 0
        if args.command == "lesson":
            explicit_task = args.task_id is not None
            if not explicit_task:
                payload = _today_payload(curriculum, progress)
            else:
                task = curriculum["_index"]["tasks"].get(args.task_id)
                if task is None:
                    raise UsageError(f"任务 ID 不存在：{args.task_id}")
                payload = _task_payload(curriculum, progress, task)
            if json_output:
                print(json.dumps(payload, ensure_ascii=False))
            else:
                _print_lesson(payload)
            return 0 if explicit_task else (1 if payload["blocked"] else 0)
        if args.command == "progress":
            if args.progress_command == "mark":
                return _mark_task(curriculum, progress, progress_path, args)
            if args.progress_command == "module":
                return _mark_module(curriculum, progress, progress_path, args)
            if args.progress_command == "option":
                return _set_option(curriculum, progress, progress_path, args)
            _print_progress(curriculum, progress)
            return 0
        if args.command == "test":
            exercise = curriculum["_index"]["exercises"].get(args.exercise_id)
            if exercise is None:
                raise UsageError(f"练习 ID 不存在：{args.exercise_id}")
            return run_exercise(exercise, Path.cwd(), progress, progress_path, verbose=args.verbose)
        raise UsageError(f"未知命令：{args.command}")
    except LearnctlError as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc), "exit_code": exc.exit_code}, ensure_ascii=False))
        else:
            print(f"错误：{exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

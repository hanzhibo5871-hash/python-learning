"""Run separate, local Python experiments without changing learning progress.

This is NOT a security sandbox. It has a fixed temporary working directory,
output and time limits, and never executes shell/command snippets. The learner
explicitly clicks Run; like the existing validator, Python has local user rights.
"""
from __future__ import annotations

import difflib
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .errors import UsageError

MAX_CODE_BYTES = 32_768
MAX_OUTPUT_BYTES = 40_000
EXPERIMENT_TIMEOUT = 5.0


def _bounded_run(source: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix='learnctl-experiment-') as directory:
        root = Path(directory)
        (root / 'experiment.py').write_text(source, encoding='utf-8')
        environment = dict(os.environ)
        environment.update(PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        # Examples do not require secrets; keep API credentials out of child env.
        for name in list(environment):
            if name.endswith(('_API_KEY', '_TOKEN', '_SECRET')):
                environment.pop(name, None)
        start = time.monotonic()
        proc = subprocess.Popen([sys.executable, '-u', 'experiment.py'], cwd=root,
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False)
        buffers: dict[str, bytearray] = {'stdout': bytearray(), 'stderr': bytearray()}
        overflow = threading.Event()

        def read_stream(name: str, stream: Any) -> None:
            try:
                while True:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    capacity = MAX_OUTPUT_BYTES - len(buffers[name])
                    buffers[name].extend(chunk[:max(0, capacity)])
                    if len(chunk) > capacity:
                        overflow.set()
                        try:
                            proc.kill()
                        except OSError:
                            pass
                        break
            finally:
                stream.close()

        readers = [threading.Thread(target=read_stream, args=(name, stream), daemon=True)
                   for name, stream in [('stdout', proc.stdout), ('stderr', proc.stderr)]]
        for thread in readers:
            thread.start()
        timeout = False
        try:
            proc.wait(timeout=EXPERIMENT_TIMEOUT)
        except subprocess.TimeoutExpired:
            timeout = True
            proc.kill()
            proc.wait()
        for thread in readers:
            thread.join(timeout=1)
        return {'stdout': bytes(buffers['stdout']).decode('utf-8', errors='replace'),
                'stderr': bytes(buffers['stderr']).decode('utf-8', errors='replace'),
                'exit_code': proc.returncode, 'timeout': timeout,
                'output_limited': overflow.is_set(),
                'duration_ms': round((time.monotonic() - start) * 1000)}


def run_experiment(section: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    mode = body.get('mode', 'example')
    if not isinstance(mode, str) or mode not in {'example', 'card', 'drill'}:
        raise UsageError('实验类型必须是 example、card 或 drill')
    index = body.get('index')
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise UsageError('实验编号必须是非负整数')
    sources = section.get('examples', []) if mode == 'example' else section.get('practice_first', {}).get(mode + 's', [])
    if index >= len(sources):
        raise UsageError('实验编号不存在')
    item = sources[index]
    if not item.get('runnable') or item.get('source_kind') != 'python':
        raise UsageError('此处只运行 Python 示例；命令、HTML 和文件片段请按指定位置操作')
    source = body.get('content', item.get('code', item.get('starter', '')))
    if not isinstance(source, str) or not source.strip():
        raise UsageError('实验代码不能为空')
    if len(source.encode('utf-8')) > MAX_CODE_BYTES:
        raise UsageError('实验代码超过 32 KiB 限制')
    result = _bounded_run(source)
    expected = str(item.get('output', ''))
    actual = result['stdout'].replace('\r\n', '\n').rstrip('\n')
    normalized_expected = expected.replace('\r\n', '\n').rstrip('\n')
    same = actual == normalized_expected
    result.update(expected=expected, actual=actual,
        passed=same and result['exit_code'] == 0 and not result['timeout'] and not result['output_limited'],
        completed=False, mode=mode, index=index,
        diff='\n'.join(difflib.unified_diff(normalized_expected.splitlines(), actual.splitlines(),
                       fromfile='预期输出', tofile='实际输出', lineterm='')))
    result['message'] = ('已达到本练习的预期输出；这不代表主作业已完成。' if result['passed'] else
                         '实验已运行；修改输入后出现不同结果可以是正常现象，请对照预期和实际。')
    if result['timeout']:
        result['message'] = '超过 5 秒已终止，请检查循环或等待条件。'
    if result['output_limited']:
        result['message'] = '输出超过限制已终止，请检查是否不断打印。'
    return result

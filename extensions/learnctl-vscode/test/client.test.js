'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const {EventEmitter} = require('node:events');
const path = require('node:path');
const {PassThrough} = require('node:stream');
const test = require('node:test');
const vm = require('node:vm');
const {resolvePython, resolveLocalPath, runCli} = require('../src/client');

function processFixture(stdout, stderr = '', exitCode = 0, inspect = () => {}) {
  return (pythonPath, args, options) => {
    inspect(pythonPath, args, options);
    const child = new EventEmitter();
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.stdin = new PassThrough();
    process.nextTick(() => {
      const output = Buffer.from(stdout, 'utf8');
      // 拆开中文的 UTF-8 字节，确认客户端按流解码而非逐块强转字符串。
      const split = Math.max(1, output.indexOf(Buffer.from('中')) + 1);
      child.stdout.write(output.subarray(0, split));
      child.stdout.end(output.subarray(split));
      child.stderr.end(Buffer.from(stderr, 'utf8'));
      child.emit('close', exitCode);
    });
    return child;
  };
}

test('default interpreter is the declared project virtual environment', () => {
  assert.equal(resolvePython('C:\\学习 项目', '', 'win32'), 'C:\\学习 项目\\.venv\\Scripts\\python.exe');
  assert.equal(resolvePython('/projects/学习 项目', '', 'linux'), '/projects/学习 项目/.venv/bin/python');
});

test('configured absolute interpreter is retained and relative interpreter uses root', () => {
  const absolute = 'C:\\Python 自定义\\..\\python.exe';
  assert.equal(resolvePython('C:\\项目', absolute, 'win32'), absolute);
  assert.equal(resolvePython('C:\\项目', '工具/python.exe', 'win32'), 'C:\\项目\\工具\\python.exe');
  assert.equal(resolvePython('/projects/example', '/custom/../python', 'linux'), '/custom/../python');
  assert.equal(resolvePython('/projects/example', 'env/bin/python', 'linux'), '/projects/example/env/bin/python');
});

test('CLI preserves argument arrays, cwd, Unicode output, UTF-8 environment and no shell', async () => {
  const args = ['lesson', '中文 空格;$(不会执行)'];
  const output = '{"title":"中文课程"}\n';
  const root = path.resolve('中文 学习项目');
  const pythonPath = path.join(root, '.venv', 'Scripts', 'python.exe');
  const result = await runCli({root, pythonPath, args, spawn: processFixture(output, '中文提示\n', 0,
    (executable, commandArgs, options) => {
      assert.equal(executable, pythonPath);
      assert.deepEqual(commandArgs, ['-m', 'learnctl', ...args, '--json']);
      assert.equal(options.cwd, root);
      assert.equal(options.shell, false);
      assert.equal(options.windowsHide, true);
      assert.equal(options.env.PYTHONUTF8, '1');
    })});
  assert.deepEqual(result, {exitCode: 0, stdout: output, stderr: '中文提示\n', data: {title: '中文课程'}});
  assert.deepEqual(args, ['lesson', '中文 空格;$(不会执行)']);
});

test('backend error JSON throws its error text unchanged', async () => {
  const message = '课程小节被锁定：D06\n请先完成前置学习。';
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['practice', 'prepare', 'D07', 'D07-import'],
    spawn: processFixture(JSON.stringify({ok: false, error: message}), '不得替代后端原文', 1)}),
  error => error.message === message);
});

test('practice check exit 1 with passed false is a displayable validation result', async () => {
  const data = {passed: false, checks: [{name: '返回值', passed: false, detail: '期望3，实际0'}]};
  const result = await runCli({root: '.', pythonPath: 'python', args: ['practice', 'check', 'D07', 'D07-import'],
    spawn: processFixture(JSON.stringify(data), '', 1)});
  assert.equal(result.exitCode, 1);
  assert.deepEqual(result.data, data);
});

test('other nonzero JSON commands throw combined backend streams unchanged', async () => {
  const stdout = '{"passed":false}\n';
  const stderr = '中文后端错误\n';
  for (const args of [['lesson', 'D07'], ['practice', 'prepare', 'D07', 'D07-import']]) {
    await assert.rejects(runCli({root: '.', pythonPath: 'python', args,
      spawn: processFixture(stdout, stderr, 1)}), error => error.message === stdout + stderr);
  }
});

test('nonzero plain-text backend errors preserve stdout and stderr in JSON mode', async () => {
  const stderr = 'usage: python -m learnctl\n参数错误：必须指定 SECTION\n';
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['practice', 'check', 'D07'],
    spawn: processFixture('', stderr, 2)}), error => error.message === stderr);
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['lesson', 'D07'],
    spawn: processFixture('启动失败\n', 'Python 模块导入错误\n', 1)}),
  error => error.message === '启动失败\nPython 模块导入错误\n');
});

test('real subprocess startup errors on stderr are preserved', async () => {
  const backendError = '模拟 Python 启动错误：无法导入 learnctl\n';
  let calls = 0;
  await assert.rejects(runCli({root: process.cwd(), pythonPath: process.execPath, args: ['lesson', 'D07'],
    spawn: (_executable, _args, options) => {
      calls += 1;
      return childProcess.spawn(process.execPath,
        ['-e', `process.stderr.write(${JSON.stringify(backendError)}); process.exitCode = 2;`], options);
    }}), error => error.message === backendError);
  assert.equal(calls, 1);
});

test('synchronous spawn errors are retained', async () => {
  const launchError = new Error('无法启动解释器');
  launchError.code = 'EACCES';
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['lesson', 'D07'],
    spawn: () => { throw launchError; }}), error => error === launchError);
});

test('unexpected practice check exit code does not simulate validation failure', async () => {
  const stdout = '{"passed":false}';
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['practice', 'check', 'D07', 'D07-import'],
    spawn: processFixture(stdout, '程序崩溃', 3)}), error => error.message === stdout + '程序崩溃');
});

test('JSON output must contain exactly one valid JSON document', async () => {
  for (const stdout of ['前置日志\n{"ok":true}', '{"ok":true}\n{"ok":true}', '{broken', '']) {
    await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['lesson', 'D07'],
      spawn: processFixture(stdout)}), SyntaxError);
  }
});

test('non-JSON progress mark returns text and does not add the JSON argument', async () => {
  const args = ['progress', 'mark', 'D07', '--status', 'done', '--evidence', '编辑器 验收通过'];
  const result = await runCli({root: '.', pythonPath: 'python', args, json: false,
    spawn: processFixture('任务 D07 已更新为 done。\n', '', 0,
      (_executable, commandArgs) => assert.deepEqual(commandArgs, ['-m', 'learnctl', ...args]))});
  assert.equal(result.text, '任务 D07 已更新为 done。\n');
  assert.equal(result.stdout, result.text);
  assert.equal(Object.hasOwn(result, 'data'), false);
});

test('non-JSON failures preserve backend output', async () => {
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['progress', 'mark', 'D07'], json: false,
    spawn: processFixture('任务无法完成\n', '错误：必修小节未通过\n', 1)}),
  error => error.message === '任务无法完成\n错误：必修小节未通过\n');
});

test('missing interpreter rejects without another spawn or PATH lookup', async () => {
  const root = process.cwd();
  const missing = path.join(root, '.missing-learnctl-interpreter', 'python.exe');
  let calls = 0;
  await assert.rejects(runCli({root, pythonPath: missing, args: ['lesson', 'D07'],
    spawn: (executable, args, options) => {
      calls += 1;
      assert.equal(executable, missing);
      return childProcess.spawn(executable, args, options);
    }}), error => error.code === 'ENOENT');
  assert.equal(calls, 1);
});

test('local file resolver accepts only relative paths within root', () => {
  const root = path.resolve('学习 项目');
  assert.equal(resolveLocalPath(root, 'learner_workspace/中文 文件.py'), path.join(root, 'learner_workspace', '中文 文件.py'));
  for (const relative of ['', '../outside.py', '../../outside.py', '/outside.py', 'C:\\outside.py', 'C:outside.py', '\\\\server\\share\\file.py']) {
    assert.throws(() => resolveLocalPath(root, relative));
  }
});

test('AI request is UTF-8 JSON stdin; Key is absent from arguments and environment', async () => {
  const key = 'offline-stdin-secret-中文-49183';
  const input = {api_key: key, question: '解释这段中文代码', history: [{role: 'user', content: '上个问题'}]};
  let stdin = '';
  const output = JSON.stringify({answer: '中文回答'});
  const fixture = processFixture(output, '', 0, (_executable, args, options) => {
    assert.deepEqual(args, ['-m', 'learnctl', 'ai', 'ask', 'D07', 'D07-main', '--json']);
    assert.equal(args.some(value => value.includes(key)), false);
    assert.equal(Object.values(options.env).includes(key), false);
    assert.equal(options.env.PYTHONUTF8, '1');
  });
  const result = await runCli({root: '.', pythonPath: 'python', args: ['ai', 'ask', 'D07', 'D07-main'], input,
    spawn: (...args) => {
      const child = fixture(...args);
      child.stdin.setEncoding('utf8');
      child.stdin.on('data', chunk => { stdin += chunk; });
      return child;
    }});
  assert.equal(stdin, JSON.stringify(input));
  assert.deepEqual(JSON.parse(stdin), input);
  assert.equal(result.data.answer, '中文回答');
});

test('stdin transport uses no filesystem or temporary-file API', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/client.js'), 'utf8');
  const loaded = {exports: {}};
  const imports = [];
  vm.runInNewContext(source, {module: loaded, process, require: name => {
    imports.push(name);
    if (name === 'node:path') return path;
    if (name === 'node:child_process') return childProcess;
    throw new Error(`unexpected I/O module: ${name}`);
  }});
  await loaded.exports.runCli({root: '.', pythonPath: 'python', args: ['ai', 'test'], input: {api_key: 'offline-key'},
    spawn: processFixture('{"content":"ok"}')});
  assert.deepEqual(imports, ['node:child_process', 'node:path']);
});

test('AbortSignal cancels the actual child process and rejects as AbortError', {timeout: 5000}, async t => {
  const controller = new AbortController();
  let child;
  let started;
  let closed;
  const spawned = new Promise(resolve => { started = resolve; });
  const stopped = new Promise(resolve => { closed = resolve; });
  const pending = runCli({root: process.cwd(), pythonPath: process.execPath, args: ['ai', 'ask', 'D07', 'D07-main'],
    input: {question: '离线取消测试'}, signal: controller.signal,
    spawn: (_executable, _args, options) => {
      assert.equal(options.signal, controller.signal);
      child = childProcess.spawn(process.execPath, ['-e', 'process.stdin.resume(); setInterval(() => {}, 1000);'], options);
      child.once('spawn', started);
      child.once('close', closed);
      return child;
    }});
  t.after(() => { if (child && child.exitCode === null && child.signalCode === null) child.kill(); });
  const rejected = assert.rejects(pending, error => error.name === 'AbortError');
  await spawned;
  controller.abort();
  await rejected;
  await stopped;
  assert.equal(controller.signal.aborted, true);
  assert.ok(child.exitCode !== null || child.signalCode !== null);
});

test('stdin transport failures retain their original error', async () => {
  const error = new Error('JSON stdin 写入失败');
  error.code = 'EPIPE';
  await assert.rejects(runCli({root: '.', pythonPath: 'python', args: ['ai', 'test'], input: {api_key: 'offline-key'},
    spawn: () => {
      const child = new EventEmitter();
      child.stdout = new PassThrough(); child.stderr = new PassThrough();
      child.stdin = new EventEmitter();
      child.stdin.end = () => process.nextTick(() => child.stdin.emit('error', error));
      return child;
    }}), value => value === error);
});

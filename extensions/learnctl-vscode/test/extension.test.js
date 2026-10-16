'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const extensionSource = fs.readFileSync(path.join(__dirname, '../src/extension.js'), 'utf8');
const workspaceChanged = '课程工作区已改变，请在新工作区重新执行操作。';
const tick = () => new Promise(resolve => setImmediate(resolve));

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

function section(id, localFile) {
  return { id, title: id, optional: false, completed: false, locked: false, local_file: localFile };
}

async function harness(sections = [section('D07-main', 'learner_workspace/lessons/D07/D07-main/main.py')], taskId = 'D07', stored = new Map()) {
  const commands = new Map();
  const rootA = path.resolve('review-course-A');
  const rootB = path.resolve('review-course-B');
  const calls = [];
  const errors = [];
  const outputLines = [];
  const picks = [];
  const hooks = {};
  const secrets = new Map();
  const files = new Map();
  const panels = [];
  const renders = [];
  const providers = new Map();
  const launched = [];
  const tasks = new Map([[taskId, sections]]);
  let foldersChanged;
  let editorChanged, documentChanged, fileChanged, fileDeleted;
  const payload = (id = taskId) => ({ task: { id, title: id, references: [], lesson: {
    sections: tasks.get(id), required_completed: 0, required_sections: tasks.get(id).length
  } } });
  const checked = id => ({ passed: true, path: [...tasks.values()].flat().find(value => value.id === id).local_file,
    content: 'print("学习")\n',
    checks: [{ passed: true, name: '后端行为验收', detail: '通过' }] });
  for (const course of [rootA, rootB]) for (const value of sections) files.set(path.join(course, value.local_file), 'print("学习")\n');
  const disposable = () => ({ dispose() {} });
  const uri = fsPath => ({ scheme: 'file', fsPath, toString: () => fsPath });
  const vscode = {
    EventEmitter: class { constructor() { this.event = disposable; } fire() {} dispose() {} },
    TreeItem: class {}, ThemeIcon: class {},
    Uri: { file: uri, joinPath: (base, ...parts) => uri(path.join(base.fsPath, ...parts)), parse: uri },
    ProgressLocation: { Window: 1 }, ViewColumn: { Beside: 2, One: 1 },
    TreeItemCollapsibleState: { Expanded: 2 },
    TaskRevealKind: { Always: 1 }, TaskPanelKind: { Shared: 1 },
    ProcessExecution: class { constructor(command, args, options) { Object.assign(this, { command, args, options }); } },
    Task: class { constructor(definition, scope, name, source, execution) { Object.assign(this, { definition, scope, name, source, execution }); } },
    tasks: { executeTask: async task => { launched.push(task); return { task }; } },
    env: { openExternal: async () => {}, clipboard: { writeText: async () => {} } },
    workspace: {
      isTrusted: true,
      workspaceFolders: [{ name: 'A', uri: { scheme: 'file', fsPath: rootA } }],
      textDocuments: [],
      getConfiguration: () => ({ get: () => '' }),
      onDidChangeWorkspaceFolders: callback => { foldersChanged = callback; return disposable(); },
      onDidChangeTextDocument: callback => { documentChanged = callback; return disposable(); },
      createFileSystemWatcher: () => ({ dispose() {},
        onDidChange: callback => { fileChanged = callback; return disposable(); },
        onDidDelete: callback => { fileDeleted = callback; return disposable(); }
      }),
      openTextDocument: async uri => hooks.openTextDocument ? hooks.openTextDocument(uri) : ({ uri, isDirty: false })
    },
    window: {
      createOutputChannel: () => ({
        append: value => outputLines.push(value), appendLine: value => outputLines.push(value),
        show() {}, clear: () => { outputLines.length = 0; }, dispose() {}
      }),
      registerTreeDataProvider: (name, provider) => { providers.set(name, provider); return disposable(); },
      onDidChangeActiveTextEditor: callback => { editorChanged = callback; return disposable(); },
      withProgress: (_options, callback) => callback(),
      showInputBox: options => hooks.inputBox ? hooks.inputBox(options) : Promise.resolve('实际运行证据'),
      showQuickPick: (choices, options) => {
        picks.push({ choices, options });
        return hooks.quickPick ? hooks.quickPick(choices) : Promise.resolve(undefined);
      },
      showInformationMessage: async () => {},
      showErrorMessage: async message => { errors.push(message); },
      showTextDocument: async () => {},
      createWebviewPanel: () => {
        let onDispose, onMessage;
        const panel = {
          webview: { html: '', cspSource: 'vscode-webview://review', asWebviewUri: value => value,
            onDidReceiveMessage: callback => { onMessage = callback; return disposable(); }
          }, viewColumn: 4, reveals: [], reveal(column, preserveFocus) { this.reveals.push({column, preserveFocus}); },
          sendMessage: message => onMessage(message),
          onDidDispose: callback => { onDispose = callback; return disposable(); },
          dispose: () => { onDispose(); }
        };
        panels.push(panel);
        return panel;
      }
    },
    commands: {
      registerCommand: (name, callback) => { commands.set(name, callback); return disposable(); },
      executeCommand: async (name, ...args) => name === 'setContext' ? undefined : commands.get(name)(...args)
    }
  };
  const client = {
    resolvePython: root => path.join(root, 'python.exe'),
    resolveLocalPath: (root, local) => path.join(root, local),
    runCli: async request => {
      calls.push(request);
      if (hooks.runCli) {
        const response = await hooks.runCli(request);
        if (response !== undefined) return response;
      }
      if (request.args[0] === 'progress') return { stdout: `${taskId} 完成`, stderr: '' };
      if (request.args[0] === 'practice') return { data: checked(request.args[3]), stderr: '' };
      if (request.args[0] === 'example') {
        const relative = `learner_workspace/examples/${request.args[2]}/${request.args[3]}/${request.args[5]}-${Number(request.args[7]) + 1}.py`;
        return { data: { path: relative, created: true, content: 'print("公开教学代码")\n' }, stderr: '' };
      }
      if (request.args[0] === 'catalog') return { data: { stages: [{ id: 'S1', title: '基础', task_ids: [...tasks.keys()], done_count: 0, total_count: tasks.size }],
        tasks: [...tasks].map(([id, values]) => ({ id, title: id, stage_id: 'S1', status: 'todo', blocked: false,
          required_completed: 0, required_sections: values.length })) }, stderr: '' };
      if (request.args[0] === 'ai') {
        if (request.args[1] === 'status') return { data: { configured: Boolean(request.input.api_key), model: 'deepseek-chat' }, stderr: '' };
        if (request.args[1] === 'test') return { data: { content: '连接测试成功' }, stderr: '' };
        return { data: { answer: `回答：${request.input.question}`, context: { summary: request.args[3] } }, stderr: '' };
      }
      return { data: payload(request.args[0] === 'lesson' ? request.args[1] : taskId), stderr: '' };
    }
  };
  const loaded = { exports: {} };
  vm.runInNewContext(extensionSource, {
    module: loaded,
    require: name => {
      if (name === 'vscode') return vscode;
      if (name === 'node:fs') return { existsSync: () => true, readFileSync: file => {
        if (files.has(file)) return files.get(file);
        const error = new Error('文件不存在'); error.code = 'ENOENT'; throw error;
      } };
      if (name === './client') return client;
      if (name === './lesson') return {
        renderLesson: (data, value, result, ui) => {
          renders.push({ payload: data, section: value, result, ui });
          return JSON.stringify({ sectionId: value.id, result, ui });
        },
        renderDashboard: (data, ui) => { renders.push({ catalog: data, ui }); return JSON.stringify({ catalog: data, ui }); }
      };
      return require(name);
    }, process, AbortController
  });
  const context = { subscriptions: [], extensionUri: uri(path.resolve(__dirname, '..')),
    secrets: {
      get: async key => hooks.secretGet ? hooks.secretGet(key) : secrets.get(key),
      store: async (key, value) => { secrets.set(key, value); },
      delete: async key => { secrets.delete(key); }
    },
    workspaceState: {
      get: (key, value) => stored.has(key) ? structuredClone(stored.get(key)) : value,
      update: async (key, value) => { stored.set(key, structuredClone(value)); }
    }
  };
  const api = loaded.exports.activate(context);
  await api.ready;
  assert.equal(api.getPayload().task.id, taskId);
  return {
    api, calls, errors, outputLines, picks, hooks, vscode, rootA, rootB, checked,
    secrets, stored, files, panels, renders, providers, tasks, launched,
    edit: file => documentChanged({ document: { uri: uri(file) } }),
    changeFile: file => fileChanged(uri(file)), deleteFile: file => fileDeleted(uri(file)),
    changeEditor: editor => { vscode.window.activeTextEditor = editor; editorChanged(editor); },
    command: (name, item) => commands.get(`learnctl.${name}`)(item),
    switchWorkspace: (course = rootB) => {
      vscode.workspace.workspaceFolders = [{ name: path.basename(course), uri: { scheme: 'file', fsPath: course } }];
      foldersChanged();
    }
  };
}

test('完成证据输入期间切换工作区，不向新课程写入旧任务进度', async () => {
  const h = await harness();
  const evidence = deferred();
  const entered = deferred();
  h.hooks.inputBox = () => { entered.resolve(); return evidence.promise; };
  const pending = h.command('completeTask');
  await entered.promise;
  h.switchWorkspace();
  evidence.resolve('A 课程中实际运行的证据');
  await pending;
  assert.equal(h.calls.filter(call => call.args[0] === 'progress').length, 0);
  assert.deepEqual(h.errors, [workspaceChanged]);
  assert.equal(h.api.getPayload(), undefined);
  // 中止旧操作后仍能正常载入新工作区，不能一直停留在旧 revision。
  await h.command('refresh');
  assert.equal(h.calls.at(-1).root, h.rootB);
  assert.equal(h.api.getPayload().task.id, 'D07');
});

test('保存作业期间切换工作区，不把旧小节交给新课程检查', async () => {
  const h = await harness();
  const saving = deferred();
  const entered = deferred();
  h.vscode.workspace.textDocuments = [{
    uri: h.vscode.Uri.file(path.join(h.rootA, h.api.getSection().local_file)), isDirty: true,
    save: () => { entered.resolve(); return saving.promise; }
  }];
  const pending = h.command('check', { sectionId: 'D07-main' });
  await entered.promise;
  h.switchWorkspace();
  saving.resolve(true);
  await pending;
  assert.equal(h.calls.filter(call => call.args[0] === 'practice').length, 0);
  assert.deepEqual(h.errors, [workspaceChanged]);
  assert.equal(h.api.getPayload(), undefined);
});

test('旧工作区检查返回时已经切换，不发布旧结果或重载旧任务', async () => {
  const h = await harness();
  const response = deferred();
  const entered = deferred();
  h.hooks.runCli = request => { entered.resolve(); return response.promise; };
  const pending = h.command('check', { sectionId: 'D07-main' });
  await entered.promise;
  h.switchWorkspace();
  response.resolve({ data: h.checked('D07-main'), stderr: '' });
  await pending;
  const practiceCalls = h.calls.filter(call => call.args[0] === 'practice');
  assert.equal(practiceCalls.length, 1);
  assert.equal(practiceCalls[0].root, h.rootA);
  assert.equal(h.calls.some(call => call.root === h.rootB), false);
  assert.deepEqual(h.errors, [workspaceChanged]);
  assert.equal(h.api.getPayload(), undefined);
});

test('后端拒绝检查时保持原始错误文本', async () => {
  const h = await harness();
  const message = '错误：D07-main 尚未解锁；请先完成 D07-package。';
  h.hooks.runCli = async () => { throw new Error(message); };
  await h.command('check', { sectionId: 'D07-main' });
  assert.deepEqual(h.errors, [message]);
  assert.equal(h.outputLines.at(-1), message);
});

test('共享项目文件的快捷键检查使用当前已选小节', async () => {
  const localFile = 'learner_workspace/task-manager/taskproj/db.py';
  const h = await harness([section('D20-connection', localFile), section('D20-crud', localFile)], 'D20');
  await h.command('showSection', { sectionId: 'D20-crud' });
  h.vscode.window.activeTextEditor = { document: { uri: h.vscode.Uri.file(path.join(h.rootA, localFile)) } };
  await h.command('check');
  const call = h.calls.find(value => value.args[0] === 'practice');
  assert.deepEqual(Array.from(call.args), ['practice', 'check', 'D20', 'D20-crud']);
  assert.equal(h.picks.length, 0);
});

test('共享文件与当前小节不一致时先选节，再检查用户明确选择的小节', async () => {
  const shared = 'learner_workspace/task-manager/taskproj/db.py';
  const h = await harness([
    section('D20-config', 'learner_workspace/task-manager/taskproj/config.py'),
    section('D20-connection', shared), section('D20-crud', shared)
  ], 'D20');
  h.vscode.window.activeTextEditor = { document: { uri: h.vscode.Uri.file(path.join(h.rootA, shared)) } };
  h.hooks.quickPick = async choices => choices.find(choice => choice.section.id === 'D20-crud');
  await h.command('check');
  assert.equal(h.picks.length, 1);
  const call = h.calls.find(value => value.args[0] === 'practice');
  assert.deepEqual(Array.from(call.args), ['practice', 'check', 'D20', 'D20-crud']);
});

test('检查前保存所有已打开的作业文件，课程工具源码不被顺带保存', async () => {
  const h = await harness();
  const saved = [];
  const dirty = relative => ({
    uri: h.vscode.Uri.file(path.join(h.rootA, relative)), isDirty: true,
    save: async () => { saved.push(relative); return true; }
  });
  const main = 'learner_workspace/lessons/D07/D07-main/main.py';
  const helper = 'learner_workspace/lessons/D07/D07-main/helpers.py';
  h.vscode.workspace.textDocuments = [dirty(main), dirty(helper), dirty('learnctl/practice.py'),
    dirty('learner_workspace/examples/D07/D07-main/card-1.py')];
  h.hooks.runCli = async request => {
    assert.deepEqual(saved, [main, helper]);
    if (request.args[0] === 'practice') return { data: h.checked('D07-main'), stderr: '' };
  };
  await h.command('check', { sectionId: 'D07-main' });
  assert.deepEqual(saved, [main, helper]);
  assert.deepEqual(h.errors, []);
});

const aiCalls = (h, action = 'ask') => h.calls.filter(call => call.args[0] === 'ai' && call.args[1] === action);
function pendingAi(h) {
  const entered = deferred();
  const response = deferred();
  h.hooks.runCli = request => {
    if (request.args[0] === 'ai' && request.args[1] === 'ask') {
      entered.resolve(request);
      return response.promise;
    }
  };
  return { entered, response };
}

test('AI Key 配置和移除仅使用 SecretStorage 与 JSON stdin', async () => {
  const h = await harness();
  const key = 'offline-test-secret-中文-7319';
  h.hooks.inputBox = options => { assert.equal(options.password, true); return Promise.resolve(key); };
  await h.command('configureAi');
  assert.equal(h.secrets.get('learnctl.deepseek.apiKey'), key);
  const configured = aiCalls(h, 'status').at(-1);
  assert.equal(configured.input.api_key, key);
  assert.equal(configured.args.some(value => value.includes(key)), false);
  await h.command('showSection');
  assert.equal(h.panels.at(-1).webview.html.includes(key), false);
  assert.equal(JSON.stringify([...h.stored]).includes(key), false);
  await h.command('removeAi');
  assert.equal(h.secrets.has('learnctl.deepseek.apiKey'), false);
  assert.deepEqual(Object.keys(aiCalls(h, 'status').at(-1).input), []);
  assert.equal(h.renders.at(-1).ui.ai.configured, false);
});

test('AI 成功保存本节问答，不执行检查或写入学习进度', async () => {
  const h = await harness();
  h.secrets.set('learnctl.deepseek.apiKey', 'stdin-only-offline-key');
  const result = await h.command('askAi', { question: 'return 和 print 有什么区别？', includeCode: false });
  assert.equal(result.answer, '回答：return 和 print 有什么区别？');
  const call = aiCalls(h)[0];
  assert.equal(call.root, h.rootA);
  assert.deepEqual(Array.from(call.args), ['ai', 'ask', 'D07', 'D07-main']);
  assert.equal(call.input.api_key, 'stdin-only-offline-key');
  assert.equal(call.input.include_code, false);
  assert.equal(h.api.getAiState().messages.length, 2);
  assert.equal(h.api.getAiState().input, '');
  assert.equal(h.calls.some(value => ['practice', 'progress'].includes(value.args[0])), false);
  assert.equal(JSON.stringify([...h.stored]).includes('stdin-only-offline-key'), false);
});

test('AI 等待回答时可以导航，结果只写回提问的小节', async () => {
  const h = await harness([section('D07-main', 'learner_workspace/main.py'), section('D07-next', 'learner_workspace/next.py')]);
  const waiting = pendingAi(h);
  const pending = h.command('askAi', { question: '解释入口' });
  await waiting.entered.promise;
  await h.command('next');
  assert.equal(h.api.getSection().id, 'D07-next');
  assert.equal(h.api.getAiState().messages.length, 0);
  assert.equal(h.renders.at(-1).ui.ai.pendingElsewhere, true);
  waiting.response.resolve({ data: { answer: '入口解释', context: '来自 main' } });
  await pending;
  assert.equal(h.api.getAiState().messages.length, 0);
  await h.command('previous');
  assert.equal(h.api.getSection().id, 'D07-main');
  assert.equal(h.api.getAiState().messages[1].content, '入口解释');
});

test('AI 对话按课程根目录、任务和小节隔离并能恢复对应历史', async () => {
  const h = await harness([section('D07-main', 'learner_workspace/main.py'), section('D07-next', 'learner_workspace/next.py')]);
  h.tasks.set('D08', [section('D08-json', 'learner_workspace/json.py')]);
  await h.command('askAi', { question: 'A 的 D07-main' });
  await h.command('next');
  assert.equal(h.api.getAiState().messages.length, 0);
  await h.command('askAi', { question: 'A 的 D07-next' });
  await h.command('chooseTask', { taskId: 'D08' });
  assert.equal(h.api.getAiState().messages.length, 0);
  await h.command('askAi', { question: 'A 的 D08-json' });
  await h.command('chooseTask', { taskId: 'D07' });
  assert.equal(h.api.getAiState().messages[0].content, 'A 的 D07-main');
  h.switchWorkspace();
  await h.command('refresh');
  assert.equal(h.api.getAiState().messages.length, 0);
  await h.command('askAi', { question: 'B 的 D07-main' });
  h.switchWorkspace(h.rootA);
  await h.command('refresh');
  assert.equal(h.api.getAiState().messages[0].content, 'A 的 D07-main');
  assert.equal(h.stored.size, 4);
});

test('AI 失败保留后端错误原文，失败不会伪造成功问答', async () => {
  const h = await harness();
  const message = 'DeepSeek 请求失败：HTTP 401\n请检查 API Key。';
  h.hooks.runCli = async request => { if (request.args[0] === 'ai' && request.args[1] === 'ask') throw new Error(message); };
  await h.command('askAi', { question: '为什么失败？' });
  assert.equal(h.api.getAiState().error, message);
  assert.equal(h.api.getAiState().messages.length, 0);
  assert.equal(h.api.getAiState().input, '为什么失败？');
});

test('取消 AI 请求向子进程传递 AbortSignal，迟到回答不恢复历史', async () => {
  const h = await harness();
  const waiting = pendingAi(h);
  const pending = h.command('askAi', { question: '取消这次问题' });
  const request = await waiting.entered.promise;
  h.command('cancelAi');
  assert.equal(request.signal.aborted, true);
  waiting.response.resolve({ data: { answer: '取消后的迟到回答' } });
  await pending;
  assert.equal(h.api.getAiState().messages.length, 0);
  assert.equal(h.api.getAiState().error, '');
});

test('清空对话会取消当前请求，迟到回答不能重新填入清空的对话', async () => {
  const h = await harness();
  await h.command('askAi', { question: '原有问题' });
  const waiting = pendingAi(h);
  const pending = h.command('askAi', { question: '等待中的问题' });
  const request = await waiting.entered.promise;
  await h.command('clearChat');
  assert.equal(request.signal.aborted, true);
  waiting.response.resolve({ data: { answer: '迟到回答' } });
  await pending;
  assert.equal(h.api.getAiState().messages.length, 0);
  assert.equal(h.api.getAiState().input, '');
  assert.equal([...h.stored.values()][0].messages.length, 0);
});

test('AI 读取凭据前占位，并发提问只启动一个请求', async () => {
  const h = await harness();
  const secret = deferred();
  const entered = deferred();
  h.hooks.secretGet = () => { entered.resolve(); return secret.promise; };
  const first = h.command('askAi', { question: '第一个问题' });
  await entered.promise;
  const second = h.command('askAi', { question: '第二个问题' });
  await tick();
  secret.resolve('offline-key');
  await Promise.all([first, second]);
  assert.equal(aiCalls(h).length, 1);
  assert.equal(h.api.getAiState().messages[0].content, '第一个问题');
});

test('输入问题期间可以取消，输入框随后返回也不会启动网络请求', async () => {
  const h = await harness();
  const input = deferred();
  const entered = deferred();
  h.hooks.inputBox = () => { entered.resolve(); return input.promise; };
  const pending = h.command('askAi');
  await entered.promise;
  h.command('cancelAi');
  input.resolve('已经取消的问题');
  await pending;
  assert.equal(aiCalls(h).length, 0);
  assert.equal(h.api.getAiState().messages.length, 0);
});

test('凭据读取期间取消，凭据随后返回也不会启动网络请求', async () => {
  const h = await harness();
  const secret = deferred();
  const entered = deferred();
  h.hooks.secretGet = () => { entered.resolve(); return secret.promise; };
  const pending = h.command('askAi', { question: '等待凭据' });
  await entered.promise;
  h.command('cancelAi');
  secret.resolve('offline-key');
  await pending;
  assert.equal(aiCalls(h).length, 0);
});

test('连接测试使用单独的 ai test，不把探针写入对话或学习进度', async () => {
  const h = await harness();
  await h.command('askAi', { question: '真实课程问题' });
  const before = JSON.stringify(h.api.getAiState().messages);
  const draftRevision = h.api.getAiState().draftRevision;
  await h.command('saveChatDraft', { taskId: 'D07', sectionId: 'D07-main', input: '准备继续询问的问题',
    includeCode: false, includeSelection: false, draftRevision });
  h.secrets.set('learnctl.deepseek.apiKey', 'test-connection-secret');
  await h.command('testAi');
  const call = aiCalls(h, 'test')[0];
  assert.deepEqual(Array.from(call.args), ['ai', 'test']);
  assert.deepEqual(Object.keys(call.input), ['api_key']);
  assert.equal(call.input.api_key, 'test-connection-secret');
  assert.equal(JSON.stringify(h.api.getAiState().messages), before);
  assert.equal(h.api.getAiState().input, '准备继续询问的问题');
  assert.equal(h.api.getAiState().draftRevision, draftRevision);
  assert.match(h.api.getAiState().info, /连接测试成功/);
  assert.equal(h.calls.some(value => value.args[0] === 'progress'), false);
  h.hooks.runCli = request => { if (request.args[0] === 'ai' && request.args[1] === 'test') throw new Error('后端测试连接失败'); };
  await h.command('testAi');
  assert.equal(h.api.getAiState().error, '后端测试连接失败');
  assert.equal(h.api.getAiState().input, '准备继续询问的问题');
  assert.equal(h.api.getAiState().draftRevision, draftRevision);
});

test('过期草稿消息不能恢复成功发送或清空后已删除的问题', async () => {
  const h = await harness();
  const revision = h.api.getAiState().draftRevision;
  const item = { taskId: 'D07', sectionId: 'D07-main', input: '过期问题', includeCode: false,
    includeSelection: false, draftRevision: revision };
  await h.command('saveChatDraft', item);
  assert.equal(h.api.getAiState().input, '过期问题');
  await h.command('askAi', { question: '实际发送的问题' });
  await h.command('saveChatDraft', item);
  assert.equal(h.api.getAiState().input, '');
  const current = h.api.getAiState().draftRevision;
  await h.command('clearChat');
  await h.command('saveChatDraft', { ...item, draftRevision: current });
  assert.equal(h.api.getAiState().input, '');
  assert.equal([...h.stored.values()][0].input, '');
});

test('小节导航与刷新保留检查结果，编辑后标记过期且不发送旧验收摘要', async () => {
  const h = await harness([section('D07-main', 'learner_workspace/main.py'), section('D07-next', 'learner_workspace/next.py')]);
  const result = await h.command('check', { sectionId: 'D07-main' });
  assert.equal(h.renders.at(-1).result, result);
  assert.equal(h.renders.at(-1).ui.staleResult, false);
  await h.command('askAi', { question: '解释刚通过的结果' });
  assert.equal(JSON.parse(aiCalls(h)[0].input.validation_summary).passed, true);
  await h.command('next');
  assert.equal(h.renders.at(-1).result, undefined);
  await h.command('previous');
  await h.command('refresh');
  assert.equal(h.renders.at(-1).result, result);
  h.edit(path.join(h.rootA, result.path));
  assert.equal(h.renders.at(-1).ui.staleResult, true);
  await h.command('askAi', { question: '解释新代码' });
  assert.equal(aiCalls(h).at(-1).input.validation_summary, '');
  assert.equal(h.renders.at(-1).result, result);
});

test('文件监听将外部修改或删除后的检查结果标记过期', async () => {
  const h = await harness();
  const result = await h.command('check', { sectionId: 'D07-main' });
  h.changeFile(path.join(h.rootA, result.path));
  assert.equal(h.renders.at(-1).ui.staleResult, true);
  await h.command('check', { sectionId: 'D07-main' });
  assert.equal(h.renders.at(-1).ui.staleResult, false);
  h.deleteFile(path.join(h.rootA, result.path));
  assert.equal(h.renders.at(-1).ui.staleResult, true);
});

test('上一节和下一节按课程顺序导航，首尾边界不切到其他任务', async () => {
  const h = await harness([section('D07-main', 'learner_workspace/main.py'), section('D07-next', 'learner_workspace/next.py')]);
  assert.equal(await h.command('previous'), undefined);
  await h.command('next');
  assert.equal(h.api.getSection().id, 'D07-next');
  assert.equal(await h.command('next'), undefined);
  await h.command('previous');
  assert.equal(h.api.getSection().id, 'D07-main');
  assert.equal(h.providers.has('learnctl.catalog'), true);
});

test('迟到的其他小节 webview 消息不能检查当前小节', async () => {
  const h = await harness();
  await h.command('showSection');
  h.panels.at(-1).sendMessage({ action: 'check', taskId: 'D07', sectionId: 'D07-old' });
  await tick();
  assert.equal(h.calls.some(value => value.args[0] === 'practice'), false);
});

test('本课目录使用当前页面身份导航，旧页面消息不能再次改变小节', async () => {
  const h = await harness([section('D07-main', 'learner_workspace/main.py'), section('D07-next', 'learner_workspace/next.py')]);
  await h.command('showSection');
  h.panels.at(-1).sendMessage({ action: 'showSection', taskId: 'D07', sectionId: 'D07-main', targetSectionId: 'D07-next' });
  await tick();
  assert.equal(h.api.getSection().id, 'D07-next');
  h.panels.at(-1).sendMessage({ action: 'showSection', taskId: 'D07', sectionId: 'D07-main', targetSectionId: 'D07-main' });
  await tick();
  assert.equal(h.api.getSection().id, 'D07-next');
});

test('Windows CRLF 与后端统一换行一致，刚检查的代码仍可附验收摘要', async () => {
  const h = await harness();
  const file = path.join(h.rootA, h.api.getSection().local_file);
  h.files.set(file, 'print("学习")\r\n');
  await h.command('check', { sectionId: 'D07-main' });
  assert.equal(h.renders.at(-1).ui.staleResult, false);
  await h.command('askAi', { question: '解释本次验收' });
  assert.equal(JSON.parse(aiCalls(h)[0].input.validation_summary).passed, true);
});

test('课程提问读取凭据期间，连接测试也不能启动第二个 AI 请求', async () => {
  const h = await harness();
  const secret = deferred();
  const entered = deferred();
  h.hooks.secretGet = () => { entered.resolve(); return secret.promise; };
  const first = h.command('askAi', { question: '唯一的课程请求' });
  await entered.promise;
  const second = h.command('testAi');
  await tick();
  secret.resolve('offline-key');
  await Promise.all([first, second]);
  assert.equal(aiCalls(h).length, 1);
  assert.equal(aiCalls(h, 'test').length, 0);
});

test('等待 AI 期间切换工作区会取消旧请求，迟到响应不会写入新课程历史', async () => {
  const h = await harness();
  const waiting = pendingAi(h);
  const pending = h.command('askAi', { question: '旧课程的问题' });
  const request = await waiting.entered.promise;
  h.switchWorkspace();
  assert.equal(request.signal.aborted, true);
  waiting.response.resolve({ data: { answer: '旧课程的迟到回答' } });
  await pending;
  await h.command('refresh');
  assert.equal(h.api.getAiState().messages.length, 0);
  assert.equal([...h.stored.values()].some(value => value.messages.length > 0), false);
  assert.equal(aiCalls(h).length, 1);
  assert.equal(aiCalls(h)[0].root, h.rootA);
});

test('重新激活扩展能从 workspaceState 恢复本节问题、回答和草稿选项', async () => {
  const h = await harness();
  await h.command('askAi', { question: '重新打开也保留的问题', includeCode: false });
  const revision = h.api.getAiState().draftRevision;
  await h.command('saveChatDraft', { taskId: 'D07', sectionId: 'D07-main', input: '尚未发送的问题',
    includeCode: false, includeSelection: false, draftRevision: revision });
  const restored = await harness(undefined, 'D07', h.stored);
  assert.equal(restored.api.getAiState().messages[0].content, '重新打开也保留的问题');
  assert.equal(restored.api.getAiState().messages[1].content, '回答：重新打开也保留的问题');
  assert.equal(restored.api.getAiState().input, '尚未发送的问题');
  assert.equal(restored.api.getAiState().includeCode, false);
});

test('升级把旧版默认作业页调整到知识页，聊天和草稿继续保留', async () => {
  const root = path.resolve('review-course-A');
  const stored = new Map([[`learnctl.chat.${root}|D07|D07-main`, {
    messages: [{ role: 'user', content: '旧问题' }, { role: 'assistant', content: '旧回答' }],
    input: '未发送的问题', includeCode: true, includeSelection: false, activeTab: 'practice', draftRevision: 8
  }]]);
  const h = await harness(undefined, 'D07', stored);
  assert.equal(h.api.getAiState().activeTab, 'knowledge');
  assert.equal(h.api.getAiState().input, '未发送的问题');
  assert.equal(h.api.getAiState().messages[1].content, '旧回答');
  await h.command('changeTab', { tab: 'practice' });
  const restored = await harness(undefined, 'D07', h.stored);
  assert.equal(restored.api.getAiState().activeTab, 'practice');
});

test('准备教学示例只打开后端真实文件，不自动运行或完成正式作业', async () => {
  const h = await harness();
  const result = await h.command('prepareExample', { source: 'card', exampleIndex: 0, code: '不可信页面代码' });
  assert.equal(result.path, 'learner_workspace/examples/D07/D07-main/card-1.py');
  assert.deepEqual(Array.from(h.calls.at(-1).args), ['example', 'prepare', 'D07', 'D07-main', '--source', 'card', '--index', '0']);
  assert.equal(h.calls.at(-1).args.includes('不可信页面代码'), false);
  assert.equal(h.launched.length, 0);
  assert.equal(h.api.getAiState().activeTab, 'knowledge');
  assert.equal(h.calls.some(call => ['practice', 'progress'].includes(call.args[0])), false);
});

test('运行教学示例仅保存对应编辑文件，直接传 Python 参数且使用独立 cwd', async () => {
  const h = await harness();
  let saved = false;
  h.hooks.openTextDocument = uri => ({ uri, isDirty: true, save: async () => { saved = true; return true; } });
  const execution = await h.command('runExample', { source: 'example', exampleIndex: 1 });
  assert.equal(saved, true);
  assert.equal(h.launched.length, 1);
  const task = execution.task;
  const relative = 'learner_workspace/examples/D07/D07-main/example-2.py';
  assert.equal(task.scope.uri.fsPath, h.rootA);
  assert.equal(task.execution.command, path.join(h.rootA, 'python.exe'));
  assert.deepEqual(Array.from(task.execution.args), ['-u', path.join(h.rootA, relative)]);
  assert.equal(task.execution.options.cwd, path.join(h.rootA, 'learner_workspace/examples/D07/D07-main'));
  assert.equal(task.execution.options.env.PYTHONUTF8, '1');
  assert.equal(h.calls.some(call => ['practice', 'progress'].includes(call.args[0])), false);
});

test('教学文件保存取消或期间切换课程工作区，都不启动 Python 任务', async () => {
  const h = await harness();
  h.hooks.openTextDocument = uri => ({ uri, isDirty: true, save: async () => false });
  assert.equal(await h.command('runExample', { source: 'card', exampleIndex: 0 }), undefined);
  assert.equal(h.launched.length, 0);
  h.hooks.openTextDocument = uri => ({ uri, isDirty: true, save: async () => { h.switchWorkspace(); return true; } });
  await h.command('runExample', { source: 'card', exampleIndex: 0 });
  assert.equal(h.launched.length, 0);
  assert.equal(h.errors.at(-1), workspaceChanged);
});

test('AI 可解释本节教学示例选区，其他小节的教学文件不能混入', async () => {
  const h = await harness();
  const editor = relative => ({ document: { uri: { scheme: 'file', fsPath: path.join(h.rootA, relative) },
    isDirty: true, getText: () => 'print("自己修改")' },
    selection: { isEmpty: false, start: { line: 0 }, end: { line: 0 } } });
  h.changeEditor(editor('learner_workspace/examples/D07/D07-main/card-1.py'));
  await h.command('askAi', { question: '解释这段示例', includeSelection: true, includeCode: false });
  assert.match(aiCalls(h)[0].input.selection, /自己修改/);
  h.changeEditor(editor('learner_workspace/examples/D07/D07-other/card-1.py'));
  await h.command('askAi', { question: '不应混入', includeSelection: true });
  assert.equal(aiCalls(h).length, 1);
  assert.match(h.api.getAiState().error, /本节教学示例/);
});

test('重复验收和课程总览沿用面板原栏位，不再使用当前栏旁边创建分栏', async () => {
  const h = await harness();
  await h.command('showSection');
  const panel = h.panels[0];
  for (let index = 0; index < 3; index++) await h.command('check', { sectionId: 'D07-main' });
  await h.command('dashboard');
  await h.command('showSection');
  assert.equal(h.panels.length, 1);
  assert.ok(panel.reveals.length >= 5);
  assert.ok(panel.reveals.every(value => value.column === 4 && value.preserveFocus === true));
  panel.viewColumn = 3;
  await h.command('showSection');
  assert.equal(panel.reveals.at(-1).column, 3);
});

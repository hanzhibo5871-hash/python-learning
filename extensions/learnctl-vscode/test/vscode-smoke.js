'use strict';

// 仅供隔离测试宿主或开发宿主中的测试驱动调用，与学习者文件和进度隔离。
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const vscode = require('vscode');

async function replace(document, content) {
  const edit = new vscode.WorkspaceEdit();
  edit.replace(document.uri, new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length)), content);
  assert.equal(await vscode.workspace.applyEdit(edit), true);
}

async function runTeachingExample(runCommand, item, file) {
  // 在 executeTask 前订阅，短脚本也不能错过真实进程的结束事件。
  let finish;
  const ended = new Promise(resolve => { finish = resolve; });
  const subscription = vscode.tasks.onDidEndTaskProcess(event => {
    if (event.execution.task.definition.type === 'learnctl-example'
        && event.execution.task.definition.path === item.path) finish(event);
  });
  let timeout;
  try {
    const execution = await runCommand('runExample', item);
    assert.ok(execution);
    assert.equal(execution.task.source, 'Python 教学示例');
    assert.equal(execution.task.scope.uri.fsPath, vscode.workspace.workspaceFolders[0].uri.fsPath);
    assert.ok(execution.task.execution instanceof vscode.ProcessExecution);
    assert.equal(execution.task.execution.process,
      vscode.workspace.getConfiguration('learnctl').get('pythonPath'));
    assert.deepEqual(execution.task.execution.args, ['-u', file]);
    assert.equal(execution.task.execution.options.cwd, path.dirname(file));
    const event = await Promise.race([ended, new Promise((_, reject) => {
      timeout = setTimeout(() => reject(new Error('真实 Python 教学任务未在 20 秒内结束')), 20000);
    })]);
    assert.equal(event.exitCode, 0);
    return execution;
  } finally {
    clearTimeout(timeout);
    subscription.dispose();
  }
}

function learningTabGroup() {
  const groups = vscode.window.tabGroups.all.filter(group =>
    group.tabs.some(tab => tab.input instanceof vscode.TabInputWebview));
  assert.equal(groups.length, 1, '隔离窗口只应有一个学习 webview');
  return groups[0];
}

async function assertLearningLayout(column, groupCount) {
  // 使用主窗口命令作为布局更新后的焦点操作，检查也覆盖从学习面板发起的情况。
  await vscode.commands.executeCommand(column === vscode.ViewColumn.One
    ? 'workbench.action.focusFirstEditorGroup' : 'workbench.action.focusSecondEditorGroup');
  assert.equal(vscode.window.tabGroups.all.length, groupCount, '刷新学习面板不得新增分栏');
  assert.equal(learningTabGroup().viewColumn, column, '学习面板应保留所在栏位');
  assert.equal(vscode.window.tabGroups.activeTabGroup.viewColumn, column);
  assert.ok(vscode.window.tabGroups.activeTabGroup.activeTab.input instanceof vscode.TabInputWebview);
}

async function run() {
  const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
  // 仅允许外层启动器创建的隔离副本；重定向 AI 地址不得碰到正式课程。
  assert.equal(JSON.parse(await fs.readFile(path.join(root, 'vscode-offline-smoke.json'), 'utf8')).offline_only, true);
  const dummyKey = 'dummy-vscode-offline-key-2026';
  const requests = [];
  let resolveCancel;
  const cancelStarted = new Promise(resolve => { resolveCancel = resolve; });
  const server = http.createServer((request, response) => {
    assert.equal(request.url, '/chat/completions');
    const chunks = [];
    request.on('data', chunk => chunks.push(chunk));
    request.on('end', () => {
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      assert.equal(body.model, 'deepseek-flash');
      assert.deepEqual(body.thinking, {type: 'disabled'});
      assert.equal(request.headers.authorization, `Bearer ${dummyKey}`);
      // 不记录 Authorization 或 Key，仅保留请求形状和课程内容用于断言。
      requests.push({model: body.model, thinking: body.thinking, messages: body.messages});
      const question = body.messages.at(-1).content;
      if (question.includes('SMOKE_CANCEL')) { resolveCancel(); return; }
      if (question.includes('SMOKE_FAIL')) {
        response.writeHead(401, {'Content-Type': 'application/json'});
        response.end('{"error":{"message":"offline rejection"}}');
        return;
      }
      response.writeHead(200, {'Content-Type': 'application/json'});
      response.end(JSON.stringify({choices: [{message: {content: `离线回答：${question.split('\n\n')[0]}`}}]}));
    });
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  await fs.appendFile(path.join(root, 'learnctl/ai.py'),
    `\n# OFFLINE VSCODE SMOKE ONLY: all AI HTTP stays on loopback.\nBASE_URL = "http://127.0.0.1:${server.address().port}"\n`);
  try {
  const extension = vscode.extensions.getExtension('learnctl-local.learnctl-python-learning');
  assert.ok(extension);
  const api = await extension.activate();
  await api.ready;
  assert.equal(api.getPayload().task.id, 'D07');
  const runCommand = (name, item) => vscode.commands.executeCommand(`learnctl.${name}`,
    typeof item === 'string' ? {sectionId: item} : item);
  const phaseFile = path.join(root, 'vscode-smoke-phase-one.json');
  let firstPhase;
  try { firstPhase = JSON.parse(await fs.readFile(phaseFile, 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (firstPhase) {
    assert.equal(api.getSection().id, 'D07-main');
    assert.equal(api.getAiState().activeTab, 'knowledge');
    assert.equal(api.getAiState().knowledgeFirst, true);
    assert.equal(api.getAiState().messages[0].content, 'SMOKE_PERSIST');
    assert.match(api.getAiState().messages[1].content, /离线回答/);
    assert.equal(api.getAiState().input, '重启后保留的草稿');
    assert.equal(api.getAiState().includeCode, false);
    const restoredExample = await runCommand('prepareExample', {
      sectionId: 'D07-import', source: 'card', exampleIndex: 0
    });
    assert.equal(restoredExample.created, false);
    assert.equal(await fs.readFile(path.join(root, restoredExample.path), 'utf8'), firstPhase.exampleContent);
    assert.equal(JSON.parse(await fs.readFile(path.join(root, firstPhase.exampleResult), 'utf8')).marker, 'v03-edited');
    await runCommand('showSection', 'D07-main');
    await runCommand('testAi');
    assert.match(api.getAiState().error, /未配置 DeepSeek API Key/);
    assert.equal(requests.length, 0);
    await fs.writeFile(path.join(root, 'vscode-smoke-result.json'), JSON.stringify({
      passed: true, model: 'deepseek-flash', offline_only: true,
      checks: [...firstPhase.checks, '真实重启恢复本节历史和草稿', '移除后的 Key 在重启后仍不存在',
        'v0.2 阅读位置迁移到知识且保留聊天', '重启后教学示例修改和运行产物保留']
    }, null, 2));
    return;
  }
  assert.equal(api.getAiState().activeTab, 'knowledge');
  const exampleChecks = ['初次学习先进入知识'];
  const progressBeforeExample = await fs.readFile(path.join(root, '.learn/progress.json'), 'utf8');
  const exampleItem = {sectionId: 'D07-import', source: 'card', exampleIndex: 0};
  const starts = [];
  const startSubscription = vscode.tasks.onDidStartTask(event => starts.push(event.execution.task));
  let example;
  try { example = await runCommand('prepareExample', exampleItem); }
  finally { startSubscription.dispose(); }
  assert.equal(example.path, 'learner_workspace/examples/D07/D07-import/card-1.py');
  assert.equal(example.created, true);
  assert.equal(starts.length, 0);
  assert.equal(api.getAiState().activeTab, 'knowledge');
  const exampleFile = path.join(root, example.path);
  const exampleDocument = await vscode.workspace.openTextDocument(exampleFile);
  assert.equal(vscode.window.visibleTextEditors.some(editor => editor.document === exampleDocument), true);
  exampleChecks.push('准备教学示例只打开不运行');
  await runTeachingExample(runCommand, {...exampleItem, path: example.path}, exampleFile);
  exampleChecks.push('公开教学代码由真实 Python 任务运行');
  const editedExample = example.content + '\n# 学习者在独立示例中改写\n';
  await replace(exampleDocument, editedExample);
  await exampleDocument.save();
  const kept = await runCommand('prepareExample', exampleItem);
  assert.equal(kept.created, false);
  assert.equal(kept.content, editedExample);
  exampleChecks.push('重复准备保留教学示例修改');
  const exampleContent = editedExample + "import json, sys\nPath('result.json').write_text(json.dumps({'marker': 'v03-edited', 'python': sys.executable, 'cwd': str(Path.cwd())}), encoding='utf-8')\nprint('v03-edited')\n";
  await replace(exampleDocument, exampleContent);
  assert.equal(exampleDocument.isDirty, true);
  await runTeachingExample(runCommand, {...exampleItem, path: example.path}, exampleFile);
  assert.equal(exampleDocument.isDirty, false);
  assert.equal(await fs.readFile(exampleFile, 'utf8'), exampleContent);
  const exampleResult = path.relative(root, path.join(path.dirname(exampleFile), 'result.json'));
  const actualRun = JSON.parse(await fs.readFile(path.join(root, exampleResult), 'utf8'));
  assert.equal(actualRun.marker, 'v03-edited');
  assert.equal(path.resolve(actualRun.python).toLowerCase(), path.resolve(vscode.workspace.getConfiguration('learnctl').get('pythonPath')).toLowerCase());
  assert.equal(path.resolve(actualRun.cwd).toLowerCase(), path.resolve(path.dirname(exampleFile)).toLowerCase());
  exampleChecks.push('运行保存未保存示例并执行改写后的真实文件');
  assert.equal(await fs.readFile(path.join(root, '.learn/progress.json'), 'utf8'), progressBeforeExample);
  await assert.rejects(fs.stat(path.join(root, 'learner_workspace/lessons/D07/D07-import/main.py')), {code: 'ENOENT'});
  assert.equal(api.getPayload().task.lesson.required_completed, 0);
  exampleChecks.push('教学运行不创建正式作业且不登记进度');
  const labelsItem = {sectionId: 'D07-package', source: 'card', exampleIndex: 0};
  const labelsCard = await runCommand('prepareExample', labelsItem);
  const labelsCardFile = path.join(root, labelsCard.path);
  const labelsModule = path.join(path.dirname(labelsCardFile), 'labels.py');
  // 模拟以前留下的无效辅助模块；原始公开示例必须自行生成可导入的真实文件。
  await fs.writeFile(labelsModule, 'old invalid module content\n', 'utf8');
  await runTeachingExample(runCommand, {...labelsItem, path: labelsCard.path}, labelsCardFile);
  assert.match(await fs.readFile(labelsModule, 'utf8'), /^def emphasize\(text\):\r?\n/m);
  exampleChecks.push('labels 知识卡真实运行并重建旧辅助模块');
  await fs.writeFile(labelsModule, 'old invalid module content\n', 'utf8');
  let finishLabels;
  const labelsFinished = new Promise(resolve => { finishLabels = resolve; });
  const ordinarySource = 'VS Code 普通运行回归';
  const labelsSubscription = vscode.tasks.onDidEndTaskProcess(event => {
    if (event.execution.task.source === ordinarySource
        && event.execution.task.definition.path === labelsCard.path) finishLabels(event);
  });
  let labelsTimeout;
  try {
    // 模拟普通运行按钮：脚本在课节子目录，cwd 却在课程根目录。
    const task = new vscode.Task({type: 'learnctl-example', path: labelsCard.path},
      vscode.workspace.workspaceFolders[0], 'labels.py 与 cwd 不同目录', ordinarySource,
      new vscode.ProcessExecution(vscode.workspace.getConfiguration('learnctl').get('pythonPath'),
        ['-u', labelsCardFile], {cwd: root, env: {PYTHONUTF8: '1'}}));
    await vscode.tasks.executeTask(task);
    const finished = await Promise.race([labelsFinished, new Promise((_, reject) => {
      labelsTimeout = setTimeout(() => reject(new Error('labels 跨目录真实运行未在 20 秒内结束')), 20000);
    })]);
    assert.equal(finished.exitCode, 0);
    assert.match(await fs.readFile(labelsModule, 'utf8'), /^def emphasize\(text\):\r?\n/m);
    await assert.rejects(fs.stat(path.join(root, 'labels.py')), {code: 'ENOENT'});
  } finally {
    clearTimeout(labelsTimeout);
    labelsSubscription.dispose();
  }
  exampleChecks.push('labels 脚本与工作目录不同仍在脚本旁生成模块');
  const labelsExampleItem = {sectionId: 'D07-package', source: 'example', exampleIndex: 1};
  const labelsExample = await runCommand('prepareExample', labelsExampleItem);
  await runTeachingExample(runCommand, {...labelsExampleItem, path: labelsExample.path}, path.join(root, labelsExample.path));
  assert.equal(await fs.readFile(path.join(root, '.learn/progress.json'), 'utf8'), progressBeforeExample);
  await assert.rejects(fs.stat(path.join(root, 'learner_workspace/lessons/D07/D07-package')), {code: 'ENOENT'});
  exampleChecks.push('labels 教学示例真实运行且不影响正式作业和进度');
  await runCommand('showSection', 'D07-import');
  await runCommand('refresh');
  const prepared = await runCommand('prepare', 'D07-import');
  assert.equal(prepared.path, 'learner_workspace/lessons/D07/D07-import/main.py');
  const file = path.join(root, prepared.path);
  const document = await vscode.workspace.openTextDocument(file);
  await replace(document, 'def show_path(path):\n    return None\n');
  const failed = await runCommand('check', 'D07-import');
  assert.equal(failed.passed, false);
  assert.equal(document.isDirty, false);
  assert.equal(api.getPayload().task.lesson.required_completed, 0);
  const solution = 'from pathlib import Path\nimport math\n\ndef show_path(path):\n    return (Path(path).suffix, math.ceil(2.1))\n';
  await replace(exampleDocument, exampleContent + '# 作业检查不得顺带保存这次示例编辑\n');
  await replace(document, solution);
  assert.equal(document.isDirty, true);
  const passed = await runCommand('check', 'D07-import');
  assert.equal(passed.passed, true);
  assert.equal(document.isDirty, false);
  assert.equal(await fs.readFile(file, 'utf8'), solution);
  assert.equal(exampleDocument.isDirty, true);
  assert.equal(await fs.readFile(exampleFile, 'utf8'), exampleContent);
  await replace(exampleDocument, exampleContent);
  await exampleDocument.save();
  exampleChecks.push('正式作业检查不保存教学示例');
  assert.equal(api.getPayload().task.status, 'todo');
  assert.equal(api.getPayload().task.lesson.required_completed, 1);
  assert.equal(api.getPayload().task.lesson.sections.find(section => section.id === 'D07-package').locked, false);
  await runCommand('prepare', 'D07-import');
  assert.equal(await fs.readFile(file, 'utf8'), solution);
  assert.equal(await runCommand('prepare', 'D07-main'), undefined);
  await assert.rejects(fs.stat(path.join(root, 'learner_workspace/lessons/D07/D07-main/main.py')), { code: 'ENOENT' });
  const packageFile = await runCommand('prepare', 'D07-package');
  assert.equal(packageFile.fixtures[0].path, 'learner_workspace/lessons/D07/D07-package/helpers.py');
  const main = await vscode.workspace.openTextDocument(path.join(root, packageFile.path));
  const helper = await vscode.workspace.openTextDocument(path.join(root, packageFile.fixtures[0].path));
  await replace(main, "from helpers import greet\nprint(greet('世界'))\n");
  await replace(helper, helper.getText() + '\n# 编辑器中保存的教学文件\n');
  const packageResult = await runCommand('check', 'D07-package');
  assert.equal(packageResult.passed, true);
  assert.equal(helper.isDirty, false);
  const progress = JSON.parse(await fs.readFile(path.join(root, '.learn/progress.json'), 'utf8'));
  assert.deepEqual(progress.lesson_progress.D07.completed_sections, ['D07-import', 'D07-package']);
  assert.equal(progress.tasks.D07?.status || 'todo', 'todo');
  const checks = ['真实扩展激活', '课程读取与完整目录', '准备并打开文件', '失败不完成', '保存后验收',
    '已有文件不覆盖', '后端前置门禁', '多文件保存', '小节进度同步', '整课不自动完成'];
  checks.push(...exampleChecks);
  assert.equal(api.getCatalog().tasks.length, 29);
  await runCommand('showSection', 'D07-import');
  const learningColumn = learningTabGroup().viewColumn;
  assert.equal(learningColumn, vscode.ViewColumn.Two);
  // 留一个真实文本标签在第二栏，反复 Beside 会创建第三栏，不能因空栏关闭而漏掉问题。
  await vscode.window.showTextDocument(document, {viewColumn: learningColumn, preview: false});
  await runCommand('showSection', 'D07-import');
  const groupCount = vscode.window.tabGroups.all.length;
  await assertLearningLayout(learningColumn, groupCount);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    assert.equal((await runCommand('check', 'D07-import')).passed, true);
    await assertLearningLayout(learningColumn, groupCount);
    for (const command of ['dashboard', 'showSection', 'refresh', 'showSection']) {
      await runCommand(command, {sectionId: 'D07-import'});
      await assertLearningLayout(learningColumn, groupCount);
    }
  }
  checks.push('连续验收与课程刷新保留分栏宽度');
  // 模拟用户把学习面板移到第一栏，后续显示必须尊重该位置。
  await vscode.commands.executeCommand('workbench.action.moveEditorToFirstGroup');
  await assertLearningLayout(vscode.ViewColumn.One, groupCount);
  for (const command of ['check', 'dashboard', 'showSection', 'refresh', 'showSection']) {
    await runCommand(command, {sectionId: 'D07-import'});
    await assertLearningLayout(vscode.ViewColumn.One, groupCount);
  }
  checks.push('用户移动学习面板后验收与导航保留位置');
  const editor = await vscode.window.showTextDocument(document);
  await editor.edit(edit => edit.setEndOfLine(vscode.EndOfLine.CRLF));
  await runCommand('check', 'D07-import');
  assert.match(await fs.readFile(file, 'utf8'), /\r\n/);
  await runCommand('next');
  assert.equal(api.getSection().id, 'D07-package');
  await runCommand('previous');
  assert.equal(api.getSection().id, 'D07-import');
  assert.equal(api.getAiState().result.passed, true);
  checks.push('上一节下一节与检查结果保留');
  const progressBeforeAi = await fs.readFile(path.join(root, '.learn/progress.json'), 'utf8');

  // 仅替换测试宿主中的输入框取值；配置命令与 SecretStorage 仍使用真实 VS Code API。
  const showInputBox = vscode.window.showInputBox;
  vscode.window.showInputBox = async options => { assert.equal(options.password, true); return dummyKey; };
  let status;
  try { status = await runCommand('configureAi'); }
  finally { vscode.window.showInputBox = showInputBox; }
  assert.equal(status.configured, true);
  assert.equal(status.model, 'deepseek-flash');
  await runCommand('saveChatDraft', {taskId: 'D07', sectionId: 'D07-import', input: '连接测试前的待发送问题',
    includeCode: true, includeSelection: false, draftRevision: api.getAiState().draftRevision});
  const probeRevision = api.getAiState().draftRevision;
  await runCommand('testAi');
  assert.match(api.getAiState().info, /离线回答/);
  assert.equal(api.getAiState().messages.length, 0);
  assert.equal(api.getAiState().input, '连接测试前的待发送问题');
  assert.equal(api.getAiState().draftRevision, probeRevision);
  checks.push('真实 SecretStorage 配置 Key', 'Flash 非思考模式离线 HTTP 连接测试');
  checks.push('连接探针保留待发送草稿与 revision');

  const first = await runCommand('askAi', {question: 'SMOKE_Q_MAIN_1', includeCode: true});
  assert.equal(first.context.code_included, true);
  assert.equal(first.context.validation_included, true);
  assert.equal(api.getAiState().messages.length, 2);
  const second = await runCommand('askAi', {question: 'SMOKE_Q_MAIN_2', includeCode: false});
  assert.equal(second.context.code_included, false);
  assert.equal(api.getAiState().messages.length, 4);
  assert.ok(requests.at(-1).messages.some(message => message.role === 'user' && message.content === 'SMOKE_Q_MAIN_1'));
  assert.equal(api.getAiState().input, '');
  checks.push('中文 stdin 问答与追问历史', 'CRLF 作业保持有效验收上下文');

  await runCommand('next');
  assert.equal(api.getAiState().messages.length, 0);
  await runCommand('askAi', {question: 'SMOKE_PACKAGE'});
  await runCommand('previous');
  assert.equal(api.getAiState().messages.length, 4);
  await runCommand('chooseTask', {taskId: 'D08'});
  assert.equal(api.getAiState().messages.length, 0);
  await runCommand('chooseTask', {taskId: 'D07'});
  await runCommand('showSection', 'D07-import');
  assert.equal(api.getAiState().messages.length, 4);
  checks.push('任务与小节历史隔离');

  await replace(document, solution + '# 未保存的编辑\n');
  const edited = await runCommand('askAi', {question: 'SMOKE_CHANGED', includeCode: false});
  assert.equal(edited.context.validation_included, false);
  await document.save();
  await runCommand('askAi', {question: 'SMOKE_FAIL'});
  assert.equal(api.getAiState().error, 'DeepSeek API 错误：HTTP 401');
  checks.push('编辑后旧验收摘要不再发送', '后端 AI 错误原文');

  const exampleEditor = await vscode.window.showTextDocument(exampleDocument, vscode.ViewColumn.One);
  exampleEditor.selection = new vscode.Selection(0, 0, 0, exampleDocument.lineAt(0).text.length);
  const selectedExample = await runCommand('askAi', {
    question: 'SMOKE_EXAMPLE_SELECTION', includeCode: false, includeSelection: true
  });
  assert.equal(selectedExample.context.selection_included, true);
  const selectedContext = JSON.parse(requests.at(-1).messages.at(-1).content.split('\n').at(-1)).content;
  assert.match(selectedContext, /learner_workspace[\\/]examples[\\/]D07[\\/]D07-import[\\/]card-1.py/);
  assert.match(selectedContext, /from pathlib import Path/);
  checks.push('本节教学示例选区可发送给 AI');

  const beforeCancel = api.getAiState().messages.length;
  const pending = runCommand('askAi', {question: 'SMOKE_CANCEL', includeSelection: false});
  await cancelStarted;
  await runCommand('cancelAi');
  await pending;
  assert.equal(api.getAiState().messages.length, beforeCancel);
  assert.equal(api.getAiState().error, '');
  await runCommand('clearChat');
  assert.equal(api.getAiState().messages.length, 0);
  assert.equal(api.getAiState().input, '');
  checks.push('真实取消 Python 子进程', '清空本节对话');

  await runCommand('showSection', 'D07-main');
  const oldRevision = api.getAiState().draftRevision;
  await runCommand('askAi', {question: 'SMOKE_PERSIST', includeCode: false});
  await runCommand('saveChatDraft', {taskId: 'D07', sectionId: 'D07-main', input: '过期问题不能恢复',
    includeCode: true, includeSelection: false, draftRevision: oldRevision});
  assert.equal(api.getAiState().input, '');
  await runCommand('saveChatDraft', {taskId: 'D07', sectionId: 'D07-main', input: '重启后保留的草稿',
    includeCode: false, includeSelection: false, draftRevision: api.getAiState().draftRevision});
  assert.equal(api.getAiState().input, '重启后保留的草稿');
  checks.push('旧草稿拒绝与新草稿保存');

  const removed = await runCommand('removeAi');
  assert.equal(removed.configured, false);
  const requestCount = requests.length;
  const draftBeforeFailedProbe = api.getAiState().input;
  const failedProbeRevision = api.getAiState().draftRevision;
  await runCommand('testAi');
  assert.match(api.getAiState().error, /未配置 DeepSeek API Key/);
  assert.equal(api.getAiState().input, draftBeforeFailedProbe);
  assert.equal(api.getAiState().draftRevision, failedProbeRevision);
  assert.equal(requests.length, requestCount);
  assert.equal(await fs.readFile(path.join(root, '.learn/progress.json'), 'utf8'), progressBeforeAi);
  checks.push('移除 Key 后拒绝请求', 'AI 操作不修改学习进度');
  // 重启验证固定使用明确保存的草稿，不依赖当前页签或输入框焦点。
  await runCommand('saveChatDraft', {taskId: 'D07', sectionId: 'D07-main', input: '重启后保留的草稿',
    includeCode: false, includeSelection: false, draftRevision: api.getAiState().draftRevision});
  await fs.writeFile(phaseFile, JSON.stringify({passed: true, checks, exampleContent, exampleResult}, null, 2));
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
}

module.exports = { run };

'use strict';

const vscode = require('vscode');
const fs = require('node:fs');
const path = require('node:path');
const { resolvePython, resolveLocalPath, runCli } = require('./client');
const { renderLesson, renderDashboard } = require('./lesson');

const SECRET_KEY = 'learnctl.deepseek.apiKey';
const samePath = (a, b) => Boolean(a && b) && (process.platform === 'win32'
  ? path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase() : path.resolve(a) === path.resolve(b));
function within(root, file) {
  const relative = path.relative(root, file);
  return relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

function activate(context) {
  const output = vscode.window.createOutputChannel('Python 学习检查');
  const changed = new vscode.EventEmitter();
  const catalogChanged = new vscode.EventEmitter();
  const records = new Map();
  let root, payload, catalog, selectedId, panel;
  let panelMode = 'lesson';
  let busy = false;
  let workspaceRevision = 0;
  let operationRevision = 0;
  let aiStatus = { configured: false, model: 'deepseek-flash', key_source: null };
  let aiRequest;
  let codeEditor = vscode.window.activeTextEditor;

  // 用户在输入证据、保存或等待 AI 时仍可切换工作区；旧请求不能写入新课程。
  function assertWorkspace(revision = operationRevision) {
    if (revision !== workspaceRevision) throw new Error('课程工作区已改变，请在新工作区重新执行操作。');
  }
  async function courseRoot() {
    if (!vscode.workspace.isTrusted) throw new Error('请先在 VS Code 中信任课程工作区，再运行 Python 学习检查。');
    const candidates = (vscode.workspace.workspaceFolders || []).filter(folder => folder.uri.scheme === 'file'
      && fs.existsSync(path.join(folder.uri.fsPath, 'data', 'curriculum.json'))
      && fs.existsSync(path.join(folder.uri.fsPath, 'learnctl', '__main__.py')));
    if (root && candidates.some(folder => samePath(folder.uri.fsPath, root))) return root;
    if (!candidates.length) throw new Error('请通过“文件 → 打开文件夹”打开课程根目录（包含 data/curriculum.json 和 learnctl）。');
    const folder = candidates.length === 1 ? candidates[0] : (await vscode.window.showQuickPick(
      candidates.map(item => ({ label: item.name, description: item.uri.fsPath, folder: item })),
      { placeHolder: '选择要学习的课程工作区' }))?.folder;
    if (!folder) return undefined;
    assertWorkspace();
    root = folder.uri.fsPath;
    return root;
  }
  async function executeAt(course, args, options = {}) {
    const configured = vscode.workspace.getConfiguration('learnctl', vscode.Uri.file(course)).get('pythonPath', '');
    return runCli({ root: course, pythonPath: resolvePython(course, configured), args, ...options });
  }
  async function cli(args, json = true, input) {
    assertWorkspace();
    const course = await courseRoot();
    if (!course) return undefined;
    assertWorkspace();
    const response = await executeAt(course, args, { json, input });
    assertWorkspace();
    if (response.stderr) output.append(response.stderr);
    return response;
  }
  async function credentials(body) {
    const key = await context.secrets.get(SECRET_KEY);
    return key ? { ...body, api_key: key } : body;
  }
  const currentSection = () => payload?.task?.lesson.sections.find(section => section.id === selectedId);
  const stateKey = (taskId = payload?.task?.id, sectionId = selectedId, course = root) => `${course}|${taskId}|${sectionId}`;
  function record(key = stateKey()) {
    if (!records.has(key)) {
      const saved = context.workspaceState.get(`learnctl.chat.${key}`, {
        messages: [], input: '', includeCode: true, includeSelection: false, activeTab: 'knowledge', draftRevision: 0, knowledgeFirst: true
      });
      // 旧版默认先作业；升级时只重置阅读页签，保留聊天与草稿。
      records.set(key, { ...saved, activeTab: saved.knowledgeFirst ? saved.activeTab : 'knowledge',
        knowledgeFirst: true, error: '', info: '', stale: false });
    }
    return records.get(key);
  }
  async function persist(key, value) {
    // 仅保存问题、回答与阅读位置；凭据始终属于 VS Code SecretStorage。
    await context.workspaceState.update(`learnctl.chat.${key}`, {
      messages: value.messages, input: value.input, includeCode: value.includeCode,
      includeSelection: value.includeSelection, activeTab: value.activeTab, draftRevision: value.draftRevision,
      knowledgeFirst: value.knowledgeFirst
    });
  }
  function isStale(value) {
    if (!value.result) return false;
    if (value.stale) return true;
    const file = resolveLocalPath(value.course, value.result.path);
    // Python 的 read_text 会统一换行；Windows 作业的 CRLF 也按同一文本比较。
    try { return fs.readFileSync(file, 'utf8').replace(/\r\n?/g, '\n') !== value.result.content; }
    catch (error) { if (error.code === 'ENOENT') return true; throw error; }
  }
  function uiOptions() {
    const value = payload?.task && currentSection() ? record() : undefined;
    const currentTaskId = catalog?.tasks.find(task => task.status !== 'done' && !task.blocked)?.id;
    return {
      styleUri: panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', 'workbench.css')).toString(),
      scriptUri: panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', 'workbench.js')).toString(),
      cspSource: panel.webview.cspSource, stateKey: stateKey(), currentTaskId, busy,
      fileExists: Boolean(currentSection()?.local_file && fs.existsSync(resolveLocalPath(root, currentSection().local_file))),
      activeTab: value?.activeTab, staleResult: value ? isStale(value) : false,
      ai: { ...aiStatus, ...(value || {}), pending: Boolean(aiRequest),
        pendingQuestion: aiRequest?.key === stateKey() ? aiRequest.question : '',
        pendingElsewhere: Boolean(aiRequest && aiRequest.key !== stateKey()),
        context: value?.context }
    };
  }
  function updatePanel() {
    if (!panel) return;
    if (panelMode === 'dashboard' || payload?.all_done) {
      panel.title = 'Python 学习 · 课程总览';
      if (catalog) panel.webview.html = renderDashboard(catalog, uiOptions());
      return;
    }
    const section = currentSection();
    if (section) {
      panel.title = `${payload.task.id} · ${section.title}`;
      panel.webview.html = renderLesson(payload, section, record().result, uiOptions());
    } else panel.dispose();
  }
  async function load(taskId) {
    const response = await cli(taskId ? ['lesson', taskId] : ['today']);
    if (!response) return undefined;
    const courseCatalog = await cli(['catalog']);
    const status = await cli(['ai', 'status'], true, await credentials({}));
    payload = response.data;
    catalog = courseCatalog.data;
    aiStatus = status.data;
    const sections = payload.task?.lesson.sections || [];
    if (!sections.some(section => section.id === selectedId)) {
      selectedId = (sections.find(section => !section.optional && !section.completed && !section.locked) || sections[0])?.id;
    }
    changed.fire(); catalogChanged.fire();
    await vscode.commands.executeCommand('setContext', 'learnctl.hasCourse', true);
    updatePanel();
    return payload;
  }
  async function chooseSection(item) {
    if (!payload || item?.taskId && item.taskId !== payload.task?.id) await load(item?.taskId);
    if (!payload?.task) return undefined;
    if (item?.sectionId) selectedId = item.sectionId;
    return currentSection();
  }
  function ensurePanel() {
    if (panel) return;
    panel = vscode.window.createWebviewPanel('learnctl.lesson', 'Python 学习', vscode.ViewColumn.Beside, {
      enableScripts: true, retainContextWhenHidden: true,
      localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')]
    });
    panel.onDidDispose(() => { panel = undefined; }, null, context.subscriptions);
    panel.webview.onDidReceiveMessage(message => {
      if (panelMode === 'lesson' && (message.taskId !== payload?.task?.id || message.sectionId !== selectedId)) return;
      const actions = {
        prepare: 'prepare', check: 'check', previous: 'previous', next: 'next', dashboard: 'dashboard',
        chooseTask: 'chooseTask', today: 'today', complete: 'completeTask', openFile: 'openFile',
        configureAi: 'configureAi', testAi: 'testAi', removeAi: 'removeAi', clearChat: 'clearChat',
        askAi: 'askAi', cancelAi: 'cancelAi', copyCode: 'copyCode', openReference: 'openReference',
        saveChatDraft: 'saveChatDraft', changeTab: 'changeTab', showSection: 'showSection',
        prepareExample: 'prepareExample', runExample: 'runExample'
      };
      if (actions[message.action]) {
        const item = message.action === 'showSection' ? { ...message, sectionId: message.targetSectionId } : message;
        void vscode.commands.executeCommand(`learnctl.${actions[message.action]}`, item);
      }
    }, null, context.subscriptions);
    context.subscriptions.push(panel);
  }
  async function showSection(item) {
    const section = await chooseSection(item);
    assertWorkspace();
    if (!section) { if (payload?.all_done) return dashboard(); return undefined; }
    panelMode = 'lesson';
    // Beside 仅用于首次建栏；重复显示时保留现有栏位，避免每次检查新增分栏。
    ensurePanel(); updatePanel(); panel.reveal(panel.viewColumn, true);
    return section;
  }
  async function dashboard() {
    if (!payload) await load();
    if (!catalog) return undefined;
    panelMode = 'dashboard'; ensurePanel(); updatePanel(); panel.reveal(panel.viewColumn, true);
    return catalog;
  }
  async function chooseTask(item) {
    if (!catalog) await load();
    const taskId = item?.taskId || (await vscode.window.showQuickPick(catalog.tasks.map(task => ({
      label: `${task.id} ${task.title}`, description: `${task.required_completed}/${task.required_sections} 必修`, taskId: task.id
    })), { placeHolder: '选择课程，可预习锁定课程的内容' }))?.taskId;
    assertWorkspace();
    if (!taskId) return undefined;
    selectedId = undefined; await load(taskId);
    return showSection();
  }
  async function navigate(direction) {
    if (!payload?.task) await load();
    const sections = payload.task.lesson.sections;
    const target = sections[sections.findIndex(section => section.id === selectedId) + direction];
    if (target) return showSection({ sectionId: target.id });
    return undefined;
  }
  async function openFile(item) {
    const section = await chooseSection(item);
    if (!section?.local_file) return undefined;
    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(resolveLocalPath(root, section.local_file)));
    assertWorkspace();
    codeEditor = await vscode.window.showTextDocument(document, vscode.ViewColumn.One);
    return section.local_file;
  }
  async function prepare(item) {
    const section = await chooseSection(item);
    assertWorkspace();
    if (!section) return undefined;
    const response = await cli(['practice', 'prepare', payload.task.id, section.id]);
    if (!response) return undefined;
    record().activeTab = 'practice'; await persist(stateKey(), record());
    await openFile({ sectionId: section.id });
    await showSection({ sectionId: section.id });
    return response.data;
  }
  async function teachingExample(item = {}, run = false) {
    const section = await chooseSection(item);
    assertWorkspace();
    if (!section) return undefined;
    let selected = item;
    if (item.source === undefined) {
      const choices = [];
      for (const [source, examples] of [['card', section.practice_first?.cards || []], ['example', section.examples || []]]) {
        examples.forEach((example, exampleIndex) => {
          if (example.source_kind === 'python' && example.runnable === true) choices.push({
            label: example.title || `${source === 'card' ? '知识卡片' : '教学示例'} ${exampleIndex + 1}`,
            description: `${source} ${exampleIndex + 1}`, source, exampleIndex
          });
        });
      }
      selected = await vscode.window.showQuickPick(choices, { placeHolder: '选择要在编辑器中尝试的 Python 教学示例' });
      assertWorkspace();
      if (!selected) return undefined;
    }
    const response = await cli(['example', 'prepare', payload.task.id, section.id,
      '--source', selected.source, '--index', String(selected.exampleIndex)]);
    if (!response) return undefined;
    const file = resolveLocalPath(root, response.data.path);
    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(file));
    assertWorkspace();
    codeEditor = await vscode.window.showTextDocument(document, vscode.ViewColumn.One);
    record().activeTab = 'knowledge'; await persist(stateKey(), record());
    await showSection({ sectionId: section.id });
    if (!run) return response.data;
    if (document.isDirty && !await document.save()) return undefined;
    assertWorkspace();
    const folder = vscode.workspace.workspaceFolders.find(value => samePath(value.uri.fsPath, root));
    const configured = vscode.workspace.getConfiguration('learnctl', folder.uri).get('pythonPath', '');
    // ProcessExecution 直接传解释器与文件参数，终端支持输入，避免拼接 shell 命令。
    const task = new vscode.Task({ type: 'learnctl-example', path: response.data.path }, folder,
      `${payload.task.id} ${section.id} · ${selected.source} ${selected.exampleIndex + 1}`, 'Python 教学示例',
      new vscode.ProcessExecution(resolvePython(root, configured), ['-u', file], {
        cwd: path.dirname(file), env: { PYTHONUTF8: '1' }
      }));
    task.presentationOptions = { reveal: vscode.TaskRevealKind.Always, focus: true, panel: vscode.TaskPanelKind.Shared };
    return vscode.tasks.executeTask(task);
  }
  async function check(item) {
    if (!payload) await load();
    if (!payload?.task) return undefined;
    let section;
    if (item?.sectionId) section = await chooseSection(item);
    else {
      const active = vscode.window.activeTextEditor?.document.uri.fsPath;
      const matches = payload.task.lesson.sections.filter(value => value.local_file && samePath(resolveLocalPath(root, value.local_file), active));
      if (matches.length === 1) section = matches[0];
      else if (matches.some(value => value.id === selectedId)) section = currentSection();
      else section = (await vscode.window.showQuickPick(payload.task.lesson.sections.filter(value => value.local_file).map(value => ({
        label: value.title, description: value.id, section: value
      })), { placeHolder: '选择要检查的小节（连续项目可能共用同一文件）' }))?.section;
    }
    assertWorkspace();
    if (!section) return undefined;
    selectedId = section.id;
    const taskId = payload.task.id;
    const key = stateKey();
    const course = root;
    // 只保存学习者作业和辅助模块，不顺带保存课程工具源码。
    for (const document of vscode.workspace.textDocuments) {
      if (!document.isDirty || document.uri.scheme !== 'file'
          || !within(path.join(course, 'learner_workspace'), document.uri.fsPath)
          || within(path.join(course, 'learner_workspace', 'examples'), document.uri.fsPath)) continue;
      assertWorkspace();
      if (!await document.save()) return undefined;
    }
    const response = await cli(['practice', 'check', taskId, section.id]);
    if (!response) return undefined;
    const checked = response.data;
    Object.assign(record(key), { result: checked, course, stale: false, activeTab: 'result' });
    output.clear(); output.appendLine(`${taskId} ${section.id} · ${checked.path}`);
    for (const entry of checked.checks) output.appendLine(`${entry.passed ? '通过' : '未通过'}：${entry.name} ${entry.detail || ''}`);
    if (checked.learning_feedback) output.appendLine(checked.learning_feedback);
    if (checked.stdout) output.append(checked.stdout);
    if (checked.stderr) output.append(checked.stderr);
    if (!checked.passed) output.show(true);
    await load(taskId); await showSection({ sectionId: section.id });
    return checked;
  }
  async function completeTask() {
    if (!payload) await load();
    if (!payload?.task) return undefined;
    const taskId = payload.task.id;
    const evidence = await vscode.window.showInputBox({ title: `${taskId} 登记完成`,
      prompt: '填写实际运行的命令、结果或产物。课程程序会核验必修进度。', placeHolder: '例如：检查的命令与观察到的结果' });
    if (evidence === undefined) return undefined;
    const response = await cli(['progress', 'mark', taskId, '--status', 'done', '--evidence', evidence], false);
    if (!response) return undefined;
    output.append(response.stdout); void vscode.window.showInformationMessage(response.stdout.trim());
    selectedId = undefined; await load(); updatePanel();
    return response.stdout;
  }
  function selectedCode(section) {
    const editor = vscode.window.activeTextEditor || codeEditor;
    if (!editor || editor.selection.isEmpty || editor.document.uri.scheme !== 'file') {
      throw new Error('请先在当前作业或本节教学示例中选中需要询问的代码。');
    }
    const file = editor.document.uri.fsPath;
    const primary = section.local_file && resolveLocalPath(root, section.local_file);
    const allowed = within(path.join(root, 'learner_workspace', 'examples', payload.task.id, section.id), file)
      || primary && (samePath(primary, file) || within(path.dirname(primary), file)
        || section.local_file.startsWith('learner_workspace/task-manager/') && within(path.join(root, 'learner_workspace/task-manager'), file));
    if (!allowed) throw new Error('选中代码来自其他课程文件，请在当前作业、辅助模块或本节教学示例中重新选择。');
    return `${path.relative(root, file)} 第 ${editor.selection.start.line + 1}–${editor.selection.end.line + 1} 行（${editor.document.isDirty ? '含未保存修改' : '已保存'}）：\n${editor.document.getText(editor.selection)}`;
  }
  function validationSummary(value) {
    if (!value.result || isStale(value)) return '';
    return JSON.stringify({ passed: value.result.passed,
      checks: value.result.checks.map(check => ({ name: check.name, passed: check.passed, detail: check.detail }))
    }).slice(0, 1000);
  }
  async function askAi(item = {}, test = false) {
    await ready;
    if (aiRequest || busy || !payload?.task || !currentSection()) return undefined;
    const revision = workspaceRevision;
    const course = root, taskId = payload.task.id, section = currentSection(), key = stateKey();
    const value = record(key);
    // 在输入问题或读取密钥的首次异步等待前占位，避免两次点击并发发送。
    const controller = new AbortController();
    const request = { key, controller, question: test ? '测试 AI 连接' : '' };
    aiRequest = request;
    try {
      const question = test ? '' : item.question ?? await vscode.window.showInputBox({ prompt: '围绕当前小节提问', placeHolder: '例如：这次检查为什么未通过？' });
      if (!test && question === undefined || controller.signal.aborted) return undefined;
      assertWorkspace(revision);
      if (!test) {
        value.includeCode = item.includeCode ?? value.includeCode;
        value.includeSelection = item.includeSelection ?? value.includeSelection;
        value.input = question; value.draftRevision += 1;
      }
      value.activeTab = 'ai'; value.error = ''; value.info = '';
      const selection = !test && value.includeSelection ? selectedCode(section) : '';
      const body = await credentials(test ? {} : { question, history: value.messages.slice(-6),
        include_code: value.includeCode, selection, validation_summary: validationSummary(value) });
      assertWorkspace(revision);
      if (controller.signal.aborted) return undefined;
      request.question = test ? '测试 AI 连接' : question;
      await persist(key, value); updatePanel();
      try {
        const response = await executeAt(course, test ? ['ai', 'test'] : ['ai', 'ask', taskId, section.id], { input: body, signal: controller.signal });
        assertWorkspace(revision);
        if (controller.signal.aborted) return undefined;
        if (test) value.info = `连接成功：${response.data.content}`;
        else {
          value.messages = [...value.messages, { role: 'user', content: question }, { role: 'assistant', content: response.data.answer }].slice(-20);
          value.context = response.data.context; value.input = ''; value.draftRevision += 1;
        }
        await persist(key, value);
        return response.data;
      } finally {
        if (aiRequest === request) aiRequest = undefined;
      }
    } catch (error) {
      if (error.name !== 'AbortError' && revision === workspaceRevision) value.error = error.message;
      return undefined;
    } finally {
      if (request && aiRequest === request) aiRequest = undefined;
      if (revision === workspaceRevision) updatePanel();
    }
  }
  function cancelAi() {
    if (aiRequest) aiRequest.controller.abort();
  }
  async function configureAi() {
    cancelAi();
    const key = await vscode.window.showInputBox({ title: '配置 DeepSeek AI 助教', password: true,
      prompt: 'API Key 保存在 VS Code 密钥存储中。留空取消修改。', placeHolder: '输入 DeepSeek API Key', ignoreFocusOut: true });
    if (!key) return undefined;
    const status = await cli(['ai', 'status'], true, { api_key: key });
    await context.secrets.store(SECRET_KEY, key);
    aiStatus = status.data; updatePanel();
    return aiStatus;
  }
  async function removeAi() {
    cancelAi(); await context.secrets.delete(SECRET_KEY);
    const status = await cli(['ai', 'status'], true, {});
    aiStatus = status.data; updatePanel(); return aiStatus;
  }
  async function clearChat() {
    const key = stateKey();
    if (aiRequest?.key === key) cancelAi();
    const value = record(key);
    Object.assign(value, { messages: [], input: '', error: '', info: '', context: undefined, activeTab: 'ai', draftRevision: value.draftRevision + 1 });
    await persist(key, value); updatePanel();
  }
  async function saveDraft(item) {
    if (!currentSection() || item.taskId !== payload.task.id || item.sectionId !== selectedId) return;
    const value = record();
    if (item.draftRevision !== value.draftRevision) return;
    Object.assign(value, { input: item.input, includeCode: item.includeCode, includeSelection: item.includeSelection });
    await persist(stateKey(), value);
  }
  function markChanged(file) {
    let affected = false;
    for (const [key, value] of records.entries()) {
      if (!value.result) continue;
      const primary = resolveLocalPath(value.course, value.result.path);
      if (!value.stale && (samePath(primary, file) || within(path.dirname(primary), file)
          || value.result.path.startsWith('learner_workspace/task-manager/') && within(path.join(value.course, 'learner_workspace/task-manager'), file))) {
        value.stale = true;
        if (key === stateKey()) affected = true;
      }
    }
    if (affected) updatePanel();
  }
  async function guarded(title, operation) {
    if (busy) return undefined;
    busy = true; operationRevision = workspaceRevision; updatePanel();
    try { return await vscode.window.withProgress({ location: vscode.ProgressLocation.Window, title }, operation); }
    catch (error) { output.appendLine(error.message); output.show(true); void vscode.window.showErrorMessage(error.message); return undefined; }
    finally { busy = false; updatePanel(); }
  }
  const provider = {
    onDidChangeTreeData: changed.event, getTreeItem: item => item,
    getChildren() {
      if (!payload?.task) return payload?.all_done ? [new vscode.TreeItem('主线课程已全部完成')] : [];
      const task = payload.task;
      const heading = new vscode.TreeItem(`${task.id} ${task.title}`);
      heading.description = `必修 ${task.lesson.required_completed}/${task.lesson.required_sections}`;
      heading.tooltip = task.learning_goal;
      const sections = task.lesson.sections.map(section => {
        const item = new vscode.TreeItem(section.title); item.taskId = task.id; item.sectionId = section.id;
        item.contextValue = section.local_file ? 'localSection' : 'webSection'; item.description = section.optional ? '选修' : '必修';
        item.iconPath = new vscode.ThemeIcon(section.completed ? 'pass' : payload.blocked || section.locked ? 'lock' : 'circle-outline');
        item.tooltip = section.lock_reason || section.objective;
        item.command = { command: 'learnctl.showSection', title: '阅读小节', arguments: [item] };
        return item;
      });
      const complete = new vscode.TreeItem('填写运行证据，登记本课完成');
      complete.iconPath = new vscode.ThemeIcon('check-all'); complete.command = { command: 'learnctl.completeTask', title: '登记本课完成' };
      return [heading, ...sections, complete];
    }
  };
  const courseProvider = {
    onDidChangeTreeData: catalogChanged.event, getTreeItem: item => item,
    getChildren(parent) {
      if (!catalog) return [];
      if (!parent) return catalog.stages.map(stage => {
        const item = new vscode.TreeItem(stage.title, stage.id === payload?.task?.stage_id
          ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.Collapsed);
        item.stageId = stage.id; item.description = `${stage.done_count}/${stage.total_count}`; return item;
      });
      return catalog.tasks.filter(task => task.stage_id === parent.stageId).map(task => {
        const item = new vscode.TreeItem(`${task.id} ${task.title}`); item.taskId = task.id;
        item.description = `${task.required_completed}/${task.required_sections}`;
        item.iconPath = new vscode.ThemeIcon(task.status === 'done' ? 'pass' : task.blocked ? 'lock' : 'book');
        item.command = { command: 'learnctl.chooseTask', title: '查看课程', arguments: [item] }; return item;
      });
    }
  };
  const commands = {
    today: async () => { selectedId = undefined; await load(); return showSection(); },
    refresh: () => load(payload?.task?.id), dashboard, chooseTask, showSection, prepare, openFile, check, completeTask,
    previous: () => navigate(-1), next: () => navigate(1), configureAi, removeAi,
    prepareExample: item => teachingExample(item), runExample: item => teachingExample(item, true),
    openReference: item => { if (payload?.task.references.some(reference => reference.url === item.url)) return vscode.env.openExternal(vscode.Uri.parse(item.url)); }
  };
  const titles = new Map(require('../package.json').contributes.commands.map(command => [command.command, command.title]));
  for (const [name, operation] of Object.entries(commands)) context.subscriptions.push(vscode.commands.registerCommand(`learnctl.${name}`,
    item => guarded(titles.get(`learnctl.${name}`), () => operation(item))));
  const direct = {
    askAi, testAi: item => askAi(item, true), cancelAi, clearChat, saveChatDraft: saveDraft,
    changeTab: async item => { if (currentSection()) { record().activeTab = item.tab; await persist(stateKey(), record()); } },
    askSelection: async () => { if (currentSection()) { await showSection(); return askAi({ question: '请逐行解释选中的代码，并说明它和本节知识的关系。', includeSelection: true }); } },
    copyCode: item => vscode.env.clipboard.writeText(item.code)
  };
  for (const [name, operation] of Object.entries(direct)) context.subscriptions.push(vscode.commands.registerCommand(`learnctl.${name}`, operation));
  context.subscriptions.push(output, changed, catalogChanged,
    vscode.window.registerTreeDataProvider('learnctl.lessons', provider),
    vscode.window.registerTreeDataProvider('learnctl.catalog', courseProvider),
    vscode.window.onDidChangeActiveTextEditor(editor => { if (editor?.document.uri.scheme === 'file') codeEditor = editor; }),
    vscode.workspace.onDidChangeTextDocument(event => { if (event.document.uri.scheme === 'file') markChanged(event.document.uri.fsPath); }));
  const watcher = vscode.workspace.createFileSystemWatcher('**/learner_workspace/**');
  context.subscriptions.push(watcher, watcher.onDidChange(uri => markChanged(uri.fsPath)), watcher.onDidDelete(uri => markChanged(uri.fsPath)));
  context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders(() => {
    workspaceRevision += 1; cancelAi(); root = undefined; payload = undefined; catalog = undefined; selectedId = undefined; codeEditor = undefined;
    changed.fire(); catalogChanged.fire(); if (panel) panel.dispose();
    void vscode.commands.executeCommand('setContext', 'learnctl.hasCourse', false);
  }));
  const ready = guarded('读取 Python 学习进度', () => load());
  return { ready, getPayload: () => payload, getCatalog: () => catalog, getSection: currentSection, getAiState: () => record() };
}

module.exports = { activate };

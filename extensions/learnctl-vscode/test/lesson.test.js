'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { renderLesson, renderDashboard, renderResult } = require('../src/lesson');

function sample() {
  const section = {
    id: 'D07-import', title: '<script>attack()</script>', objective: '导入模块',
    explanation: ['说明'], examples: [{ code: 'print("<img>")', output: '<img>', explanation: '原样输出' }],
    practice: { instructions: '编写函数', expected_behavior: '返回元组', input_examples: [] },
    local_file: 'learner_workspace/main.py', completed: false, locked: false,
    practice_first: { rules: ['规则'], provided: '现有文件', cards: [] }
  };
  return { section, payload: { blocked: false, missing_prerequisites: [], task: {
    id: 'D07', title: '模块与对象', lesson: { required_completed: 0, required_sections: 6, sections: [section] }
  } } };
}

test('课程、代码和后端结果作为文本显示，脚本由 nonce 限制', () => {
  const { payload, section } = sample();
  const html = renderLesson(payload, section, { passed: false, checks: [
    { passed: false, name: '<b>检查</b>', detail: '<img onerror="attack()">' }
  ], stderr: 'NameError: <x>' });
  assert.ok(!html.includes('<script>attack()'));
  assert.ok(html.includes('&lt;script&gt;attack()&lt;/script&gt;'));
  assert.ok(html.includes('&lt;img onerror=&quot;attack()&quot;&gt;'));
  assert.ok(html.includes("default-src 'none'"));
  assert.match(html, /script-src 'nonce-[A-Za-z0-9+/]+'/);
  assert.ok(html.includes('NameError: &lt;x&gt;'));
});

test('后端锁定课程时禁用动作；D01–D06 不提供本地验收按钮', () => {
  const { payload, section } = sample();
  payload.blocked = true;
  payload.missing_prerequisites = ['D06'];
  assert.match(renderLesson(payload, section), /data-action="check" disabled/);
  delete section.local_file;
  assert.ok(!renderLesson(payload, section).includes('data-action="check"'));
});

test('四个学习Tab、作业文件、完成门禁和导航可读', () => {
  const { payload, section } = sample();
  const html = renderLesson(payload, section);
  for (const tab of ['practice', 'knowledge', 'result', 'ai']) {
    assert.ok(html.includes(`id="tab-${tab}"`));
    assert.ok(html.includes(`id="panel-${tab}"`));
  }
  assert.ok(html.includes('作业要求'));
  assert.ok(html.includes('验收要求'));
  assert.ok(html.includes('learner_workspace/main.py'));
  assert.match(html, /data-action="complete" disabled/);
  assert.match(html, /data-action="previous" disabled/);
  assert.match(html, /data-action="next" disabled/);
  payload.task.lesson.required_completed = 6;
  assert.ok(!renderLesson(payload, section).includes('data-action="complete" disabled'));
});

test('AI消息、草稿和后端错误原文均转义，不渲染AI HTML', () => {
  const { payload, section } = sample();
  const html = renderLesson(payload, section, undefined, {ai: {
    configured: true, model: 'deepseek-chat', draftRevision: 3,
    input: '</textarea><script>attack()</script>',
    messages: [{role: 'user', content: '<img src=x onerror=attack()>'},
      {role: 'assistant', content: '解释\n```python\nprint("<img>")\n```'}],
    error: '后端原文：<failure>\n连接拒绝'
  }});
  assert.ok(html.includes('&lt;/textarea&gt;&lt;script&gt;attack()&lt;/script&gt;'));
  assert.ok(html.includes('&lt;img src=x onerror=attack()&gt;'));
  assert.ok(html.includes('后端原文：&lt;failure&gt;\n连接拒绝'));
  assert.ok(html.includes('<pre><code>print(&quot;&lt;img&gt;&quot;)'));
  assert.ok(!html.includes('<script>attack()'));
  assert.ok(html.includes('data-draft-revision="3"'));
  assert.ok(html.includes('maxlength="2000"'));
});

test('AI处理中显示当前问题和取消；跨节请求使用独立说明', () => {
  const { payload, section } = sample();
  const pending = renderLesson(payload, section, undefined, {ai: {pending: true, pendingQuestion: '为什么失败？'}});
  assert.ok(pending.includes('正在思考…'));
  assert.ok(pending.includes('为什么失败？'));
  assert.ok(pending.includes('data-action="cancelAi"'));
  assert.match(pending, /id="ai-question"[^>]+ disabled/);
  const elsewhere = renderLesson(payload, section, undefined, {ai: {pendingElsewhere: true}});
  assert.ok(elsewhere.includes('正在回答另一小节'));
  assert.ok(!elsewhere.includes('正在思考…'));
  assert.ok(elsewhere.includes('data-action="cancelAi"'));
});

test('结果统计正确，过期结果必须重新检查', () => {
  const html = renderResult({passed: false, checks: [{passed: true, name: '导入'}, {passed: false, name: '调用', detail: '原始检查信息'}], stdout: '3', stderr: 'NameError'}, {staleResult: true});
  assert.ok(html.includes('1 项通过 · 1 项未通过'));
  assert.ok(html.includes('作业已修改，请重新检查'));
  assert.ok(html.includes('原始检查信息'));
  assert.ok(html.includes('stdout'));
  assert.ok(html.includes('stderr'));
  assert.ok(html.includes('class="check-item failed" open'));
});

test('课程总览按真实阶段展示任务和继续学习入口', () => {
  const tasks = Array.from({length: 29}, (_, index) => ({id: `D${String(index + 1).padStart(2, '0')}`, title: `课程 ${index + 1}`, status: index < 6 ? 'done' : 'todo', required_completed: index < 6 ? 5 : 0, required_sections: 5, stage_id: `S${Math.floor(index / 8) + 1}`}));
  const catalog = {tasks, stages: [1, 2, 3, 4].map(index => ({id: `S${index}`, title: `阶段 ${index}`, task_ids: tasks.filter(task => task.stage_id === `S${index}`).map(task => task.id), done_count: index === 1 ? 6 : 0, total_count: tasks.filter(task => task.stage_id === `S${index}`).length})), done_tasks: 6, total_tasks: 29};
  const html = renderDashboard(catalog, {currentTaskId: 'D07'});
  assert.equal((html.match(/<button type="button" class="task-card/g) || []).length, 29);
  assert.equal((html.match(/class="stage-heading"/g) || []).length, 4);
  assert.ok(html.includes('继续学习 D07'));
  assert.ok(html.includes('data-task-id="D07"'));
  assert.ok(html.includes('30 / 145'));
  assert.ok(html.includes('6<span>/ 29</span>'));
});

test('外部媒体采用本地来源与nonce，内联预览使用同一媒体', () => {
  const { payload, section } = sample();
  const external = renderLesson(payload, section, undefined, {styleUri: 'vscode-webview://media/workbench.css', scriptUri: 'vscode-webview://media/workbench.js', cspSource: 'vscode-webview://media'});
  assert.ok(external.includes('href="vscode-webview://media/workbench.css"'));
  assert.match(external, /<script nonce="[A-Za-z0-9+/]+" src="vscode-webview:\/\/media\/workbench.js"><\/script>/);
  assert.ok(external.includes("default-src 'none'"));
  assert.ok(!external.includes('<style nonce='));
  const inline = renderLesson(payload, section);
  assert.ok(inline.includes('const vscode = acquireVsCodeApi()'));
  assert.ok(inline.includes('--vscode-editor-background'));
});

function scriptHarness(saved = {}, draftRevision = 0) {
  const messages = [];
  const elements = new Map();
  function element(id, dataset = {}) {
    const value = {id, dataset, value: '', checked: false, disabled: false, hidden: false, listeners: {}, attributes: {}, classList: {toggle() {}}, addEventListener(event, fn) {this.listeners[event] = fn;}, setAttribute(key, item) {this.attributes[key] = item;}, focus() {this.focused = true;}};
    elements.set(id, value);
    return value;
  }
  const tabs = ['knowledge', 'practice', 'result', 'ai'].map(id => element(`tab-${id}`, {tab: id}));
  for (const tab of tabs) element(`panel-${tab.dataset.tab}`);
  const knowledgeActions = element('knowledge-actions');
  const assignmentActions = element('assignment-actions');
  const startPractice = element('start-practice', {switchTab: 'practice'});
  const question = element('ai-question');
  question.value = '后端草稿';
  const includeCode = element('include-code');
  includeCode.checked = true;
  const includeSelection = element('include-selection');
  element('question-count');
  element('send-ai');
  const form = element('ai-form');
  form.requestSubmit = () => form.listeners.submit({preventDefault() {}});
  const check = element('check', {action: 'check'});
  const chooseTask = element('choose', {action: 'chooseTask', taskId: 'D12'});
  const showSection = element('show', {action: 'showSection', targetSectionId: 'D07-package'});
  const prepareExample = element('prepare-example', {action: 'prepareExample', exampleSource: 'card', exampleIndex: '2', code: 'never execute message code'});
  const runExample = element('run-example', {action: 'runExample', exampleSource: 'example', exampleIndex: '0', code: 'never execute message code'});
  const chip = element('chip', {question: '解释知识点'});
  const state = {value: saved};
  const sandbox = {
    acquireVsCodeApi: () => ({getState: () => state.value, setState: value => {state.value = structuredClone(value);}, postMessage: value => {messages.push(value);}}),
    document: {body: {dataset: {taskId: 'D07', sectionId: 'D07-import', stateKey: 'root|D07|D07-import', draftRevision: String(draftRevision), activeTab: ''}}, getElementById: id => elements.get(id), querySelector: selector => tabs.find(tab => selector === `[data-tab="${tab.dataset.tab}"]`), querySelectorAll: selector => selector === '[data-tab]' ? tabs : selector === '[data-action]' ? [check, chooseTask, showSection, prepareExample, runExample] : selector === '[data-question]' ? [chip] : selector === '[data-switch-tab]' ? [startPractice] : []},
    window: {scrollY: 0, addEventListener() {}, scrollTo() {}}, requestAnimationFrame: fn => fn(), setTimeout: () => 1, clearTimeout() {}
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'media', 'workbench.js'), 'utf8'), sandbox);
  return {messages, state, question, includeCode, includeSelection, form, check, chooseTask, showSection, prepareExample, runExample, chip, tabs, knowledgeActions, assignmentActions, startPractice};
}

test('Webview恢复同节同revision草稿，发送动作包含小节和选项', () => {
  const ui = scriptHarness({stateKey: 'root|D07|D07-import', draftRevision: 0, input: '未发的问题', includeSelection: true, activeTab: 'ai'});
  assert.equal(ui.question.value, '未发的问题');
  assert.equal(ui.state.value.activeTab, 'ai');
  ui.form.requestSubmit();
  const draft = ui.messages.find(message => message.action === 'saveChatDraft');
  assert.equal(draft.draftRevision, 0);
  const ask = ui.messages.find(message => message.action === 'askAi');
  assert.equal(ask.taskId, 'D07');
  assert.equal(ask.sectionId, 'D07-import');
  assert.equal(ask.question, '未发的问题');
  assert.equal(ask.includeCode, true);
  assert.equal(ask.includeSelection, true);
});

test('新工作区和新版草稿不恢复旧内容，常用问题只填入输入框', () => {
  const changedRoot = scriptHarness({stateKey: 'another|D07|D07-import', draftRevision: 0, input: '旧项目草稿'});
  assert.equal(changedRoot.question.value, '后端草稿');
  const newDraft = scriptHarness({stateKey: 'root|D07|D07-import', draftRevision: 1, input: '旧revision'}, 2);
  assert.equal(newDraft.question.value, '后端草稿');
  newDraft.chip.listeners.click();
  assert.equal(newDraft.question.value, '解释知识点');
  assert.ok(!newDraft.messages.some(message => message.action === 'askAi'));
  assert.equal(newDraft.messages[0].draftRevision, 2);
});

test('检查选择结果Tab，导航卡片携带指定课程', () => {
  const ui = scriptHarness();
  ui.check.listeners.click();
  assert.equal(ui.state.value.activeTab, 'result');
  assert.equal(ui.messages.at(-1).action, 'check');
  assert.equal(ui.messages.at(-1).sectionId, 'D07-import');
  ui.chooseTask.listeners.click();
  assert.equal(ui.messages.at(-1).action, 'chooseTask');
  assert.equal(ui.messages.at(-1).taskId, 'D12');
});

test('Tab恢复不通知后端，用户切换才持久保存当前Tab', () => {
  const ui = scriptHarness();
  assert.equal(ui.messages.length, 0);
  ui.tabs[0].listeners.click();
  assert.equal(ui.messages[0].action, 'changeTab');
  assert.equal(ui.messages[0].tab, 'knowledge');
  assert.equal(ui.messages[0].sectionId, 'D07-import');
  ui.tabs[0].listeners.keydown({key: 'ArrowRight', preventDefault() {}});
  assert.equal(ui.messages.at(-1).tab, 'practice');
});

test('AI反馈显示连接原文、密钥来源和真实代码上下文', () => {
  const { payload, section } = sample();
  const html = renderLesson(payload, section, undefined, {fileExists: true, ai: {
    configured: true, key_source: 'request', info: '连接成功：deepseek-chat',
    context: {path: 'lessons/main.py', code_included: true, code_chars: 8000,
      code_truncated: true, selection_included: true, validation_included: true}
  }});
  assert.ok(html.includes('连接成功：deepseek-chat'));
  assert.ok(html.includes('VS Code 密钥库'));
  assert.ok(html.includes('已保存作业：lessons/main.py'));
  assert.ok(html.includes('代码上下文共 8000 字符，已截取'));
  assert.ok(html.includes('含选中代码 · 含检查结果'));
  assert.ok(html.includes('选中代码最多 2000 字符'));
  assert.ok(!html.includes('data-action="openFile" disabled'));
  const missing = renderLesson(payload, section, undefined, {fileExists: false, ai: {key_source: 'env'}});
  assert.ok(missing.includes('环境变量'));
  assert.match(missing, /data-action="openFile" disabled/);
  assert.ok(missing.includes('本节作业文件尚未准备'));
});

test('本课目录可直接跳节，目标ID不覆盖当前消息身份', () => {
  const {payload, section} = sample();
  const html = renderLesson(payload, section);
  assert.ok(html.includes('data-action="showSection" data-target-section-id="D07-import"'));
  assert.ok(html.includes('aria-current="step"'));
  const ui = scriptHarness();
  ui.showSection.listeners.click();
  const message = ui.messages.at(-1);
  assert.equal(message.action, 'showSection');
  assert.equal(message.taskId, 'D07');
  assert.equal(message.sectionId, 'D07-import');
  assert.equal(message.targetSectionId, 'D07-package');
});

test('初次默认知识讲解，知识在作业前且预期输出默认折叠', () => {
  const {payload, section} = sample();
  const html = renderLesson(payload, section);
  assert.ok(html.indexOf('id="tab-knowledge"') < html.indexOf('id="tab-practice"'));
  assert.ok(html.indexOf('id="panel-knowledge"') < html.indexOf('id="panel-practice"'));
  assert.ok(html.includes('id="tab-knowledge" class="tab active"'));
  assert.ok(html.includes('先读讲解 → 打开教学示例，在编辑器中改写运行 → 独立完成本节作业'));
  assert.ok(html.includes('<details class="predicted-output"><summary>先预测输出，再展开对照</summary>'));
  assert.ok(html.includes('id="assignment-actions" hidden'));
  const ui = scriptHarness();
  assert.equal(ui.state.value.activeTab, 'knowledge');
  assert.equal(ui.knowledgeActions.hidden, false);
  assert.equal(ui.assignmentActions.hidden, true);
});

test('开始本节作业只切作业Tab，不准备文件或执行验收', () => {
  const ui = scriptHarness();
  ui.startPractice.listeners.click();
  assert.equal(ui.state.value.activeTab, 'practice');
  assert.equal(ui.knowledgeActions.hidden, true);
  assert.equal(ui.assignmentActions.hidden, false);
  assert.equal(ui.messages.length, 1);
  assert.equal(ui.messages[0].action, 'changeTab');
  assert.equal(ui.messages[0].tab, 'practice');
});

test('仅明确可独立运行的Python教学卡和示例提供试跑按钮', () => {
  const {payload, section} = sample();
  section.practice_first.cards = [{title: '教学卡', code: 'print(1)', output: '1', source_kind: 'python', runnable: true}];
  section.examples = [
    {code: 'print(2)', output: '2', source_kind: 'python', runnable: true},
    {code: 'x = 1', source_kind: 'python', runnable: false},
    {code: 'print(3)', language: 'python'},
    {code: 'from my_project import helper', language: 'python', source_kind: 'file_fragment', runnable: false},
    {code: 'console.log(1)', source_kind: 'javascript', runnable: true},
    {code: 'GET /api/tasks', source_kind: 'http', runnable: false},
    {code: 'python --version', source_kind: 'command', runnable: false},
    {code: '{id: 1}', source_kind: 'contract', runnable: false}
  ];
  const html = renderLesson(payload, section);
  assert.equal((html.match(/data-action="prepareExample"/g) || []).length, 2);
  assert.equal((html.match(/data-action="runExample"/g) || []).length, 2);
  assert.ok(html.includes('data-example-source="card" data-example-index="0"'));
  assert.ok(html.includes('data-example-source="example" data-example-index="0"'));
  assert.ok(html.includes('此示例需要项目文件或模块上下文'));
  assert.ok(html.includes('JavaScript 对照示例'));
  assert.ok(html.includes('HTTP 请求示例'));
  assert.ok(html.includes('终端命令示例'));
  assert.ok(html.includes('接口或输出契约示例'));
});

test('锁定课程可预习教学示例，作业门禁仍保留且忙碌时禁用示例按钮', () => {
  const {payload, section} = sample();
  section.practice_first.cards = [{title: '预习', code: 'print(1)', source_kind: 'python', runnable: true}];
  payload.blocked = true;
  const html = renderLesson(payload, section);
  assert.ok(!html.includes('data-action="prepareExample" disabled'));
  assert.ok(!html.includes('data-action="runExample" disabled'));
  assert.match(html, /data-action="check" disabled/);
  const busy = renderLesson(payload, section, undefined, {busy: true});
  assert.match(busy, /data-action="prepareExample" disabled/);
  assert.match(busy, /data-action="runExample" disabled/);
});

test('示例准备和运行消息只含已知示例索引，不传入执行代码', () => {
  const ui = scriptHarness();
  ui.prepareExample.listeners.click();
  const prepared = ui.messages.at(-1);
  assert.equal(prepared.action, 'prepareExample');
  assert.equal(prepared.source, 'card');
  assert.equal(prepared.exampleIndex, 2);
  assert.equal(prepared.taskId, 'D07');
  assert.equal(prepared.sectionId, 'D07-import');
  assert.equal(prepared.code, undefined);
  ui.runExample.listeners.click();
  const run = ui.messages.at(-1);
  assert.equal(run.action, 'runExample');
  assert.equal(run.source, 'example');
  assert.equal(run.exampleIndex, 0);
  assert.equal(run.code, undefined);
  assert.equal(ui.state.value.activeTab, 'knowledge');
});

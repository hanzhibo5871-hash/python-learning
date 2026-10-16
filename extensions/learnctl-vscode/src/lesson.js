'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
}

function code(value, label = '', copy = false) {
  return `<div class="code-block">${label || copy ? `<div class="code-heading"><span>${escapeHtml(label)}</span>${copy ? `<button type="button" class="text-button" data-action="copyCode" data-code="${escapeHtml(value)}" aria-label="复制示例代码">复制</button>` : ''}</div>` : ''}<pre><code>${escapeHtml(value)}</code></pre></div>`;
}

function paragraphs(values) {
  return (values || []).filter(value => value !== undefined && value !== '').map(value => `<p>${escapeHtml(value)}</p>`).join('');
}

function badge(label, kind = '') {
  return `<span class="badge ${kind}">${escapeHtml(label)}</span>`;
}

function button(action, label, options = {}) {
  return `<button type="button" data-action="${action}" ${options.disabled ? 'disabled' : ''}${options.className ? ` class="${options.className}"` : ''}${options.title ? ` title="${escapeHtml(options.title)}"` : ''}${options.attributes ? ` ${options.attributes}` : ''}>${label}</button>`;
}

function progressBar(completed, total, label) {
  const percent = total ? Math.round(completed / total * 100) : 0;
  return `<div class="progress-label"><span>${escapeHtml(label)}</span><strong>${completed} / ${total}</strong></div><progress max="${Math.max(total, 1)}" value="${completed}" aria-label="${escapeHtml(label)} ${percent}%"></progress>`;
}

function documentPage(title, content, ids, ui) {
  const nonce = crypto.randomBytes(18).toString('base64');
  const source = ui.cspSource ? ` ${escapeHtml(ui.cspSource)}` : '';
  // 真实 Webview 使用已授权的本地资源；离线预览读取相同媒体，保持同一界面。
  const css = ui.styleUri ? `<link rel="stylesheet" href="${escapeHtml(ui.styleUri)}">` : `<style nonce="${nonce}">${fs.readFileSync(path.join(__dirname, '..', 'media', 'workbench.css'), 'utf8')}</style>`;
  const script = ui.scriptUri ? `<script nonce="${nonce}" src="${escapeHtml(ui.scriptUri)}"></script>` : `<script nonce="${nonce}">${fs.readFileSync(path.join(__dirname, '..', 'media', 'workbench.js'), 'utf8')}</script>`;
  return `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${nonce}'${source}; script-src 'nonce-${nonce}';"><title>${escapeHtml(title)}</title>${css}</head><body data-task-id="${escapeHtml(ids.taskId)}" data-section-id="${escapeHtml(ids.sectionId)}" data-state-key="${escapeHtml(ui.stateKey || `${ids.taskId}|${ids.sectionId}`)}" data-draft-revision="${ui.ai?.draftRevision || 0}" data-active-tab="${escapeHtml(ui.activeTab || '')}">${content}${script}</body></html>`;
}

function renderResult(result, ui = {}) {
  if (!result) return `<div class="empty-state"><span class="empty-symbol" aria-hidden="true">✓</span><h2>写好代码后，检查一次</h2><p>保存并检查会读取本地作业、运行本节验收，再展示每项结果。</p><p class="muted">通过小节会登记小节进度。全部必修通过后，再填写运行证据完成整课。</p></div>`;
  const checks = result.checks || [];
  const passed = checks.filter(check => check.passed).length;
  return `<section class="result-block" aria-live="polite">${ui.staleResult ? '<div class="notice warning"><strong>作业已修改，请重新检查</strong><p>以下是上次检查结果，不能代表当前文件。</p></div>' : ''}<div class="result-summary ${result.passed ? 'success' : 'failure'}"><span class="result-icon" aria-hidden="true">${result.passed ? '✓' : '!'}</span><div><h2>${result.passed ? '检查通过，已登记本节完成' : '检查未通过'}</h2><p>${passed} 项通过 · ${checks.length - passed} 项未通过${ui.staleResult ? ' · 上次结果' : ''}</p></div></div>
    ${result.path ? `<p class="file-label">检查文件 <code>${escapeHtml(result.path)}</code></p>` : ''}
    ${result.learning_feedback ? `<div class="card feedback"><h3>学习反馈</h3>${paragraphs([result.learning_feedback])}</div>` : ''}
    <div class="check-list">${checks.map(check => `<details class="check-item ${check.passed ? 'passed' : 'failed'}"${!check.passed ? ' open' : ''}><summary><span class="check-symbol" aria-hidden="true">${check.passed ? '✓' : '✗'}</span><span>${escapeHtml(check.name)}</span>${badge(check.passed ? '通过' : '未通过', check.passed ? 'positive' : 'negative')}</summary><div class="check-detail">${check.detail ? `<p>${escapeHtml(check.detail)}</p>` : '<p class="muted">本项未返回详细信息。</p>'}</div></details>`).join('')}</div>
    ${result.stdout ? `<details class="output" open><summary>程序输出 <span class="muted">stdout</span></summary>${code(result.stdout)}</details>` : ''}
    ${result.stderr ? `<details class="output" open><summary>错误输出 <span class="muted">stderr</span></summary>${code(result.stderr)}</details>` : ''}</section>`;
}

function teachingActions(item, source, exampleIndex, ui) {
  // 课程已明确标记可独立运行的 Python；不根据语言名推断可运行性。
  if (item.source_kind === 'python' && item.runnable === true) {
    const attributes = `data-example-source="${source}" data-example-index="${exampleIndex}"`;
    return `<div class="example-actions">${button('prepareExample', '在编辑器尝试', {className: 'secondary', disabled: ui.busy, attributes})}${button('runExample', '保存并运行示例', {disabled: ui.busy, attributes})}</div><p class="example-hint muted">先在编辑器修改示例，再保存并运行，到终端观察实际输出。教学示例独立保存，不登记作业进度。</p>`;
  }
  const explanations = {
    file_fragment: '此示例需要项目文件或模块上下文，按讲解在对应项目中尝试。',
    javascript: 'JavaScript 对照示例，可阅读或复制到前端环境中尝试。',
    http: 'HTTP 请求示例，按讲解在对应接口环境中尝试。',
    command: '终端命令示例，按讲解在对应终端中尝试。',
    json_fragment: 'JSON 数据示例，用于对照数据结构，按讲解放入对应文件。',
    contract: '接口或输出契约示例，用于对照结构和行为。',
    python: '此 Python 示例不能作为独立文件运行，按讲解在对应上下文中尝试。'
  };
  return `<p class="example-hint muted">${escapeHtml(explanations[item.source_kind] || '此示例需要课程说明的上下文，请按讲解阅读或复制所需片段。')}</p>`;
}

function renderKnowledge(task, section, ui) {
  const brief = section.practice_first;
  return `<div class="section-intro"><span class="eyebrow">先学知识，再做作业</span><h2>读懂讲解，自己改写并运行示例</h2><p class="muted">先读讲解 → 打开教学示例，在编辑器中改写运行 → 独立完成本节作业。</p><ol class="teaching-flow"><li><strong>理解规则</strong><span>读讲解，观察代码用了哪些语法。</span></li><li><strong>动手尝试</strong><span>先预测输出，再修改参数或变量运行对照。</span></li><li><strong>独立完成</strong><span>理解后进入作业，自己实现并检查。</span></li></ol></div>
    ${brief ? `<div class="card"><h3>本节规则</h3><ul class="rule-list">${(brief.rules || []).map(rule => `<li>${escapeHtml(rule)}</li>`).join('')}</ul>${brief.knowledge_scope?.length ? `<div class="tag-row">${brief.knowledge_scope.map(item => badge(item)).join('')}</div>` : ''}${brief.provided ? `<div class="provided"><strong>课程提供</strong>${paragraphs([brief.provided])}</div>` : ''}</div>
    ${(brief.cards || []).map((card, index) => `<article class="card knowledge-card"><span class="eyebrow">知识 ${String(index + 1).padStart(2, '0')}</span><h3>${escapeHtml(card.title)}</h3><p>${escapeHtml(card.rule)}</p>${code(card.code, card.source_kind === 'python' ? 'Python' : '教学示例', true)}${teachingActions(card, 'card', index, ui)}${predictedOutput(card.output)}</article>`).join('')}` : ''}
    <details class="accordion" open><summary>完整讲解<span class="muted">概念与运行行为</span></summary><div class="accordion-content">${section.syntax ? `<div class="syntax">${escapeHtml(section.syntax)}</div>` : ''}${paragraphs(section.explanation)}</div></details>
    ${section.js_bridge ? `<div class="card bridge"><span class="eyebrow">从前端经验出发</span><h3>JavaScript → Python</h3>${paragraphs([section.js_bridge])}</div>` : ''}
    <details class="accordion"><summary>更多示例与输出<span class="muted">${(section.examples || []).length} 个示例</span></summary><div class="accordion-content">${(section.examples || []).map((item, index) => `<article class="example"><h3>示例 ${index + 1}</h3>${code(item.code, item.language || '教学示例', true)}${teachingActions(item, 'example', index, ui)}${predictedOutput(item.output)}${paragraphs([item.explanation])}</article>`).join('')}</div></details>
    <details class="accordion"><summary>常见错误与提示<span class="muted">遇到报错时再看</span></summary><div class="accordion-content">${section.practice.hints ? `<div class="notice">${paragraphs([section.practice.hints])}</div>` : ''}${(section.common_errors || []).map(item => `<article class="error-explanation"><h3>${escapeHtml(item.error)}</h3><dl><dt>现象</dt><dd>${escapeHtml(item.symptom)}</dd><dt>原因</dt><dd>${escapeHtml(item.cause)}</dd><dt>改法</dt><dd>${escapeHtml(item.fix)}</dd></dl>${item.example?.code ? code(item.example.code, '错误示例') : ''}</article>`).join('')}</div></details>
    ${task.references?.length ? `<div class="references"><h3>官方参考</h3>${task.references.map(item => button('openReference', escapeHtml(item.title), {className: 'reference-button', attributes: `data-url="${escapeHtml(item.url)}"`})).join('')}</div>` : ''}<div class="knowledge-next card"><div><h3>试过示例，就开始自己写</h3><p class="muted">本节作业会独立验收你保存的实现。</p></div><button type="button" data-switch-tab="practice">开始本节作业 →</button></div>`;
}

function predictedOutput(value) {
  return `<details class="predicted-output"><summary>先预测输出，再展开对照</summary>${code(value, '预期输出')}</details>`;
}

// 只给代码围栏增加等宽外观；AI 返回内容始终转义，不能变成可执行 HTML。
function messageText(value) {
  const input = String(value ?? '');
  let output = '';
  let position = 0;
  const fences = /```[^\n`]*\n([\s\S]*?)```/g;
  let match;
  while ((match = fences.exec(input))) {
    output += `<div class="message-text">${escapeHtml(input.slice(position, match.index))}</div>${code(match[1])}`;
    position = fences.lastIndex;
  }
  return `${output}<div class="message-text">${escapeHtml(input.slice(position))}</div>`;
}

function renderAi(section, ui) {
  const ai = ui.ai || {};
  const pending = Boolean(ai.pending || ai.pendingElsewhere);
  const messages = ai.messages || [];
  const keySource = ai.key_source === 'request' ? 'VS Code 密钥库' : ai.key_source === 'env' ? '环境变量' : ai.key_source;
  const context = ai.context;
  const contextSummary = context && typeof context !== 'string' ? [
    context.code_included ? `已保存作业：${context.path}` : '未带上作业代码',
    context.selection_included ? '含选中代码' : '未带上选中代码',
    context.validation_included ? '含检查结果' : '未带上检查结果',
    `代码上下文共 ${context.code_chars} 字符${context.code_truncated ? '，已截取' : ''}`
  ].join(' · ') : context;
  const questions = ['用简单的话解释本节知识', '这段报错应该从哪里排查？', '帮我理解验收要求，不直接给完整答案', '和 JavaScript 的写法有什么区别？'];
  return `<div class="ai-layout"><div class="ai-settings"><div><span class="eyebrow">AI 学习助手</span><h2>有问题，留在编辑器里问</h2><p class="muted">对话绑定当前小节 ${escapeHtml(section.id)}，切换小节后会显示对应记录。</p></div><div class="ai-status">${badge(ai.configured ? 'DeepSeek 已配置' : 'DeepSeek 未配置', ai.configured ? 'positive' : '')}${ai.model ? `<span class="muted">${escapeHtml(ai.model)}</span>` : ''}${keySource ? `<span class="muted">Key 来源：${escapeHtml(keySource)}</span>` : ''}</div><div class="ai-setting-actions">${button('configureAi', ai.configured ? '配置 AI' : '配置 DeepSeek', {className: ai.configured ? 'secondary' : '', disabled: pending})}${button('testAi', '测试连接', {className: 'secondary', disabled: pending || !ai.configured})}${button('removeAi', '移除 Key', {className: 'text-button', disabled: pending || !ai.configured})}</div></div>
    ${ai.pendingElsewhere ? '<div class="notice"><strong>正在回答另一小节</strong><p>可取消当前请求后，在本节提问。</p></div>' : ''}${ai.info ? `<div class="notice positive" role="status"><p class="preserve-text">${escapeHtml(ai.info)}</p></div>` : ''}${ai.error ? `<div class="notice error" role="alert"><strong>AI 请求未完成</strong><p class="preserve-text">${escapeHtml(ai.error)}</p></div>` : ''}
    <div class="chat-head"><h3>本节对话</h3>${button('clearChat', '清空对话', {className: 'text-button', disabled: pending || messages.length === 0})}</div><div class="chat-history" id="chat-history" aria-live="polite">${messages.length === 0 && !ai.pending ? `<div class="chat-empty"><span class="chat-symbol" aria-hidden="true">?</span><h3>从一个具体问题开始</h3><p>询问知识点、理解验收要求，或者带上代码分析错误。</p></div>` : ''}${messages.map(item => `<article class="chat-message ${item.role === 'user' ? 'user' : 'assistant'}"><div class="message-role">${item.role === 'user' ? '你' : '学习助手'}</div><div class="message-bubble">${messageText(item.content)}</div></article>`).join('')}${ai.pending ? `${ai.pendingQuestion ? `<article class="chat-message user"><div class="message-role">你</div><div class="message-bubble">${messageText(ai.pendingQuestion)}</div></article>` : ''}<article class="chat-message assistant pending"><div class="message-role">学习助手</div><div class="message-bubble"><span class="spinner" aria-hidden="true"></span>正在思考…</div></article>` : ''}</div>
    <div class="question-chips" aria-label="常用问题">${questions.map(question => `<button type="button" class="question-chip" data-question="${escapeHtml(question)}"${pending ? ' disabled' : ''}>${escapeHtml(question)}</button>`).join('')}</div>
    <form id="ai-form" class="ai-composer"><label for="ai-question">你的问题</label><textarea id="ai-question" name="question" maxlength="2000" rows="4" placeholder="例如：为什么 import math 后要用 math.ceil？"${pending ? ' disabled' : ''}>${escapeHtml(ai.input || '')}</textarea><div class="composer-options"><label><input type="checkbox" id="include-code"${ai.includeCode !== false ? ' checked' : ''}${pending ? ' disabled' : ''}> 带上已保存作业</label><label><input type="checkbox" id="include-selection"${ai.includeSelection ? ' checked' : ''}${pending ? ' disabled' : ''}> 带上选中代码</label></div><p class="composer-hint muted">勾选内容会随问题发送给 DeepSeek。作业读取已保存的文件；选中代码最多 2000 字符。</p>${section.local_file && !ui.fileExists ? '<p class="composer-hint muted">本节作业文件尚未准备，仍可依据课程内容提问。</p>' : ''}${contextSummary ? `<p class="context-summary muted"><strong>本次上下文</strong><br>${escapeHtml(contextSummary)}</p>` : ''}<div class="composer-footer"><span class="muted"><span id="question-count">${String(ai.input || '').length}</span> / 2000 · Ctrl + Enter 发送</span>${pending ? button('cancelAi', '取消请求', {className: 'secondary'}) : '<button type="submit" id="send-ai">发送问题 <span aria-hidden="true">↑</span></button>'}</div></form></div>`;
}

function renderLesson(payload, section, result, ui = {}) {
  const task = payload.task;
  const lesson = task.lesson;
  const sections = lesson.sections || [];
  const index = sections.findIndex(item => item.id === section.id);
  const locked = Boolean(payload.blocked || section.locked);
  const disabled = locked || Boolean(ui.busy);
  const tabs = [{id: 'knowledge', title: '知识讲解', icon: '01'}, {id: 'practice', title: '本节作业', icon: '02'}, {id: 'result', title: '检查结果', icon: '03'}, {id: 'ai', title: 'AI 答疑', icon: '✦'}];
  const activeTab = tabs.some(tab => tab.id === ui.activeTab) ? ui.activeTab : 'knowledge';
  const content = `<main class="workbench lesson-page"><header class="topbar"><div class="brand"><span class="brand-mark" aria-hidden="true">Py</span><span>Python 学习工作台</span></div><div class="topbar-actions">${button('dashboard', '课程总览', {className: 'text-button'})}${button('chooseTask', '切换课程', {className: 'secondary'})}</div></header>
    <section class="lesson-hero"><div class="lesson-meta"><span class="eyebrow">${escapeHtml(task.id)} · ${escapeHtml(task.title)}</span><div class="tag-row">${badge(section.optional ? '选修' : '必修')}${badge(section.completed ? '已通过' : locked ? '待前置完成' : '学习中', section.completed ? 'positive' : '')}</div></div><h1>${escapeHtml(section.title)}</h1><p class="lesson-objective">${escapeHtml(section.objective)}</p><div class="lesson-progress">${progressBar(lesson.required_completed, lesson.required_sections, '本课必修进度')}<span class="muted">${index >= 0 ? `小节 ${index + 1} / ${sections.length}` : escapeHtml(section.id)}</span></div></section>
    ${payload.blocked ? `<div class="notice warning"><strong>课程前置尚未完成</strong><p>前置未完成：${escapeHtml((payload.missing_prerequisites || []).join('、'))}</p></div>` : ''}${section.lock_reason && !payload.blocked ? `<div class="notice warning"><strong>本节等待前置完成</strong><p>${escapeHtml(section.lock_reason)}</p></div>` : ''}
    <div class="lesson-body"><div class="main-column"><nav class="tabs" role="tablist" aria-label="学习内容">${tabs.map(tab => `<button type="button" id="tab-${tab.id}" class="tab${activeTab === tab.id ? ' active' : ''}" data-tab="${tab.id}" role="tab" aria-controls="panel-${tab.id}" aria-selected="${activeTab === tab.id}"><span class="tab-number" aria-hidden="true">${tab.icon}</span>${tab.title}${tab.id === 'result' && result ? `<span class="tab-dot ${ui.staleResult ? 'warning' : result.passed ? 'positive' : 'negative'}" aria-label="${ui.staleResult ? '需要重新检查' : result.passed ? '检查通过' : '检查未通过'}"></span>` : ''}</button>`).join('')}</nav>
    <section id="panel-knowledge" class="tab-panel" role="tabpanel" aria-labelledby="tab-knowledge"${activeTab !== 'knowledge' ? ' hidden' : ''}>${renderKnowledge(task, section, ui)}</section>
    <section id="panel-practice" class="tab-panel" role="tabpanel" aria-labelledby="tab-practice"${activeTab !== 'practice' ? ' hidden' : ''}><div class="section-intro"><span class="eyebrow">当前任务</span><h2>在编辑器完成本节作业</h2>${section.practice.scenario ? `<p class="muted">${escapeHtml(section.practice.scenario)}</p>` : ''}</div><article class="card assignment-card"><div class="card-title"><span class="card-icon" aria-hidden="true">↗</span><h3>作业要求</h3></div><p class="instructions">${escapeHtml(section.practice.instructions)}</p></article><article class="card acceptance-card"><div class="card-title"><span class="card-icon" aria-hidden="true">✓</span><h3>验收要求</h3></div><p>${escapeHtml(section.practice.expected_behavior)}</p></article>
    ${(section.practice.input_examples || []).length ? `<div class="examples-grid">${section.practice.input_examples.map(item => `<article class="card input-example"><h3>${escapeHtml(item.label)}</h3>${code(item.value, '输入 / 调用', true)}<div class="expected"><span class="eyebrow">预期表现</span><p>${escapeHtml(item.expected)}</p></div></article>`).join('')}</div>` : ''}
    ${section.local_file ? `<div class="card workspace-card"><div class="card-title"><h3>作业文件</h3>${badge(ui.fileExists ? '已存在' : '尚未准备', ui.fileExists ? 'positive' : '')}</div><p class="file-path"><code>${escapeHtml(section.local_file)}</code></p>${payload.project_root ? `<p class="muted">项目目录：${escapeHtml(payload.project_root)}</p>` : ''}<p class="muted">准备只创建缺失文件，不会覆盖已有代码。检查会保存作业目录内已打开的修改文件，再验收磁盘内容。</p>${button('openFile', '打开作业文件', {className: 'secondary', disabled: ui.busy || !ui.fileExists})}</div>` : '<div class="notice"><strong>D01–D06 网页入门练习</strong><p>阅读讲解与 AI 答疑均可在这里进行；从 D07 起，可在此准备和检查本地作业。</p></div>'}
    ${section.guided_practice?.steps?.length ? `<details class="accordion"><summary>操作提示<span class="muted">卡住时展开</span></summary><div class="accordion-content"><ol class="guided-steps">${section.guided_practice.steps.map(step => `<li><p>${escapeHtml(step.action)}</p>${step.expected ? `<span class="muted">观察：${escapeHtml(step.expected)}</span>` : ''}</li>`).join('')}</ol></div></details>` : ''}</section>
    <section id="panel-result" class="tab-panel" role="tabpanel" aria-labelledby="tab-result"${activeTab !== 'result' ? ' hidden' : ''}>${renderResult(result, ui)}</section>
    <section id="panel-ai" class="tab-panel" role="tabpanel" aria-labelledby="tab-ai"${activeTab !== 'ai' ? ' hidden' : ''}>${renderAi(section, ui)}</section></div>
    <aside class="lesson-aside"><div class="aside-card"><span class="eyebrow">本课小节</span><h3>${escapeHtml(task.id)} 学习进度</h3><ol class="section-list">${sections.map((item, itemIndex) => `<li class="${item.id === section.id ? 'current' : ''}"><button type="button" class="section-link" data-action="showSection" data-target-section-id="${escapeHtml(item.id)}"${item.id === section.id ? ' aria-current="step"' : ''}${ui.busy ? ' disabled' : ''}><span class="section-marker ${item.completed ? 'completed' : ''}" aria-hidden="true">${item.completed ? '✓' : String(itemIndex + 1).padStart(2, '0')}</span><span class="section-copy"><span>${escapeHtml(item.title)}</span><small>${item.optional ? '选修' : '必修'}${item.completed ? ' · 已通过' : item.locked ? ' · 待前置' : ''}</small></span></button></li>`).join('')}</ol></div><div class="aside-card workflow-card"><h3>学习循环</h3><ol><li>阅读要求与讲解</li><li>在编辑器中实现</li><li>保存检查，按反馈修改</li><li>有疑问时询问 AI</li></ol><p class="muted">小节检查通过后，再前往下一节。</p></div></aside></div>
    <footer class="action-bar"><div class="knowledge-actions" id="knowledge-actions"${activeTab !== 'knowledge' ? ' hidden' : ''}><span class="muted">先改写运行教学示例，再独立实现作业。</span><button type="button" data-switch-tab="practice"${ui.busy ? ' disabled' : ''}>开始本节作业 →</button></div><div class="primary-actions" id="assignment-actions"${activeTab === 'knowledge' ? ' hidden' : ''}>${section.local_file ? `${button('prepare', '准备并打开作业', {disabled, className: 'secondary'})}${button('check', ui.busy ? '<span class="spinner" aria-hidden="true"></span>处理中…' : '保存并检查', {disabled})}` : '<span class="muted">本节为网页入门练习</span>'}${button('complete', '完成整课', {disabled: ui.busy || lesson.required_completed !== lesson.required_sections, className: 'text-button', title: '全部必修小节检查通过后，填写实际运行证据'})}</div><div class="section-navigation">${button('previous', '← 上一节', {disabled: ui.busy || index <= 0, className: 'secondary'})}${button('next', '下一节 →', {disabled: ui.busy || index < 0 || index >= sections.length - 1, className: 'secondary'})}</div></footer></main>`;
  return documentPage(`${task.id} · ${section.title}`, content, {taskId: task.id, sectionId: section.id}, ui);
}

function renderDashboard(catalog, ui = {}) {
  const tasks = catalog.tasks;
  const current = tasks.find(task => task.id === ui.currentTaskId);
  const requiredCompleted = tasks.reduce((total, task) => total + task.required_completed, 0);
  const requiredSections = tasks.reduce((total, task) => total + task.required_sections, 0);
  const statusText = {done: '已完成', in_progress: '进行中', todo: '未开始'};
  const content = `<main class="workbench dashboard-page"><header class="topbar"><div class="brand"><span class="brand-mark" aria-hidden="true">Py</span><span>Python 学习工作台</span></div><span class="muted">课程总览</span></header><section class="dashboard-hero"><div class="hero-copy"><span class="eyebrow">Python 学习路径</span><h1>一步一步，写出能运行的项目</h1><p>从 Python 基础，到 API 与 AI 应用。在编辑器里学习、检查和提问。</p>${current ? button('chooseTask', `继续学习 ${escapeHtml(current.id)} <span aria-hidden="true">→</span>`, {attributes: `data-task-id="${escapeHtml(current.id)}"`}) : ''}</div><div class="overall-progress"><div class="big-number">${catalog.done_tasks}<span>/ ${catalog.total_tasks}</span></div><p>主线课程已完成</p>${progressBar(requiredCompleted, requiredSections, '必修小节进度')}</div></section>
    ${current ? `<section class="current-course card"><div><span class="eyebrow">当前主线</span><h2>${escapeHtml(current.id)} · ${escapeHtml(current.title)}</h2><p class="muted">必修 ${current.required_completed} / ${current.required_sections}${current.blocked ? ` · 前置未完成：${escapeHtml((current.missing_prerequisites || []).join('、'))}` : ''}</p></div>${button('chooseTask', '打开本课', {className: 'secondary', attributes: `data-task-id="${escapeHtml(current.id)}"`})}</section>` : ''}
    <section class="stages-section"><div class="section-intro"><span class="eyebrow">4 个阶段 · 一条学习主线</span><h2>课程路线</h2><p class="muted">每张卡片都可以阅读。作业检查按照课程前置顺序开放。</p></div>${catalog.stages.map((stage, stageIndex) => `<section class="stage"><div class="stage-heading"><span class="stage-number">${String(stageIndex + 1).padStart(2, '0')}</span><div><h2>${escapeHtml(stage.title)}</h2><p class="muted">${stage.done_count} / ${stage.total_count} 课已完成</p></div><progress max="${stage.total_count}" value="${stage.done_count}" aria-label="${escapeHtml(stage.title)}课程进度"></progress></div><div class="task-grid">${tasks.filter(task => stage.task_ids.includes(task.id)).map(task => `<button type="button" class="task-card${task.id === ui.currentTaskId ? ' current' : ''}${task.status === 'done' ? ' completed' : ''}" data-action="chooseTask" data-task-id="${escapeHtml(task.id)}"><div class="task-card-head"><strong>${escapeHtml(task.id)}</strong>${badge(task.status === 'done' ? '已完成' : task.blocked ? '待前置' : task.id === ui.currentTaskId ? '当前课程' : statusText[task.status] || task.status, task.status === 'done' ? 'positive' : '')}</div><h3>${escapeHtml(task.title)}</h3><div class="task-progress"><progress max="${Math.max(task.required_sections, 1)}" value="${task.required_completed}" aria-label="${escapeHtml(task.id)}必修进度"></progress><span>必修 ${task.required_completed} / ${task.required_sections}</span></div><span class="card-arrow" aria-hidden="true">→</span></button>`).join('')}</div></section>`).join('')}</section><p class="dashboard-footer muted">D01–D06 网页基础 · D07 起本地编辑器 · 每节检查通过后推进主线</p></main>`;
  return documentPage('Python 学习 · 课程总览', content, {taskId: '', sectionId: ''}, ui);
}

module.exports = { escapeHtml, renderLesson, renderDashboard, renderResult };

'use strict';

(() => {
  const vscode = acquireVsCodeApi();
  const body = document.body;
  const taskId = body.dataset.taskId;
  const sectionId = body.dataset.sectionId;
  const stateKey = body.dataset.stateKey;
  const draftRevision = Number(body.dataset.draftRevision);
  const stored = vscode.getState() || {};
  const state = stored.stateKey === stateKey ? stored : {stateKey};
  const question = document.getElementById('ai-question');
  const includeCode = document.getElementById('include-code');
  const includeSelection = document.getElementById('include-selection');
  const count = document.getElementById('question-count');
  const sendButton = document.getElementById('send-ai');
  let draftTimer;

  function saveState() {
    state.stateKey = stateKey;
    vscode.setState(state);
  }

  function post(action, extra = {}) {
    vscode.postMessage({action, taskId, sectionId, ...extra});
  }

  function updateQuestion() {
    if (!question) return;
    count.textContent = String(question.value.length);
    if (sendButton) sendButton.disabled = !question.value.trim();
    state.input = question.value;
    state.includeCode = includeCode.checked;
    state.includeSelection = includeSelection.checked;
    saveState();
  }

  function saveDraft() {
    clearTimeout(draftTimer);
    if (!question) return;
    post('saveChatDraft', {input: question.value, includeCode: includeCode.checked, includeSelection: includeSelection.checked, draftRevision});
  }

  function setTab(id, focus = false, notify = false) {
    const tab = document.querySelector(`[data-tab="${id}"]`);
    if (!tab) return;
    document.querySelectorAll('[data-tab]').forEach(item => {
      const active = item === tab;
      item.classList.toggle('active', active);
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      document.getElementById(`panel-${item.dataset.tab}`).hidden = !active;
    });
    state.activeTab = id;
    const knowledgeActions = document.getElementById('knowledge-actions');
    const assignmentActions = document.getElementById('assignment-actions');
    if (knowledgeActions) knowledgeActions.hidden = id !== 'knowledge';
    if (assignmentActions) assignmentActions.hidden = id === 'knowledge';
    saveState();
    if (notify) post('changeTab', {tab: id});
    if (focus) tab.focus();
  }

  document.querySelectorAll('[data-tab]').forEach(tab => {
    tab.addEventListener('click', () => setTab(tab.dataset.tab, false, true));
    tab.addEventListener('keydown', event => {
      const tabs = Array.from(document.querySelectorAll('[data-tab]'));
      const index = tabs.indexOf(tab);
      let next;
      if (event.key === 'ArrowRight') next = tabs[(index + 1) % tabs.length];
      if (event.key === 'ArrowLeft') next = tabs[(index + tabs.length - 1) % tabs.length];
      if (event.key === 'Home') next = tabs[0];
      if (event.key === 'End') next = tabs[tabs.length - 1];
      if (next) {
        event.preventDefault();
        setTab(next.dataset.tab, true, true);
      }
    });
  });

  document.querySelectorAll('[data-switch-tab]').forEach(item => item.addEventListener('click', () => {
    if (!item.disabled) setTab(item.dataset.switchTab, false, true);
  }));

  document.querySelectorAll('[data-action]').forEach(item => item.addEventListener('click', () => {
    if (item.disabled) return;
    saveDraft();
    const action = item.dataset.action;
    const extra = {};
    if (item.dataset.taskId) extra.taskId = item.dataset.taskId;
    if (item.dataset.targetSectionId) extra.targetSectionId = item.dataset.targetSectionId;
    if (action === 'prepareExample' || action === 'runExample') {
      extra.source = item.dataset.exampleSource;
      extra.exampleIndex = Number(item.dataset.exampleIndex);
    }
    if (action === 'copyCode') extra.code = item.dataset.code;
    if (action === 'openReference') extra.url = item.dataset.url;
    if (action === 'check') setTab('result', false, true);
    if (action === 'clearChat') {
      question.value = '';
      updateQuestion();
      saveDraft();
    }
    post(action, extra);
  }));

  document.querySelectorAll('[data-question]').forEach(chip => chip.addEventListener('click', () => {
    question.value = chip.dataset.question;
    updateQuestion();
    saveDraft();
    question.focus();
  }));

  if (question) {
    // Webview HTML 刷新会重新执行脚本；草稿按课程根目录和小节隔离。
    if (state.draftRevision === draftRevision) {
      if (state.input !== undefined) question.value = state.input;
      if (state.includeCode !== undefined) includeCode.checked = state.includeCode;
      if (state.includeSelection !== undefined) includeSelection.checked = state.includeSelection;
    }
    state.draftRevision = draftRevision;
    updateQuestion();
    question.addEventListener('input', () => {
      updateQuestion();
      clearTimeout(draftTimer);
      draftTimer = setTimeout(saveDraft, 250);
    });
    [includeCode, includeSelection].forEach(input => input.addEventListener('change', () => {
      updateQuestion();
      saveDraft();
    }));
    document.getElementById('ai-form').addEventListener('submit', event => {
      event.preventDefault();
      const input = question.value.trim();
      if (!input || input.length > 2000 || question.disabled) return;
      saveDraft();
      setTab('ai', false, true);
      post('askAi', {question: input, includeCode: includeCode.checked, includeSelection: includeSelection.checked});
    });
    question.addEventListener('keydown', event => {
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing) {
        event.preventDefault();
        document.getElementById('ai-form').requestSubmit();
      }
    });
  }

  setTab(body.dataset.activeTab || state.activeTab || 'knowledge');
  if (state.scrollY > 0) requestAnimationFrame(() => window.scrollTo(0, state.scrollY));
  window.addEventListener('scroll', () => {
    state.scrollY = window.scrollY;
    saveState();
  }, {passive: true});
})();

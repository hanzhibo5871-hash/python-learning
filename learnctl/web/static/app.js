"use strict";

// learnctl 学习工作台 —— 原生 JS，无任何外部依赖。
// 说明：本地验证只在本机 127.0.0.1 执行代码，不会对外发送；
// 只有点击 AI 助教里的 DeepSeek 按钮，才会把当前练习内容发往模型。

const state = {
  route: window.location.hash || "#/dashboard",
  bootstrap: null,
  task: null,
  taskId: null,
  currentSection: null,
  editorValue: "",
  lastValidation: null,
  aiStatus: null,
  aiChats: {},
  aiChatGenerations: {},
  aiChatPending: {},
  aiDrawerOpen: false,
  variationId: null,
  catalogSeries: "",
  catalogQuery: "",
  workspace: null,
  lessonView: "learn",
  editorDirty: false,
  busy: false,
  renderVersion: 0,
};

const $ = (sel) => document.querySelector(sel);
const app = () => $("#app");
const AI_DRAWER_FOCUS_DELAY_MS = 220;
let aiDrawerFocusTimer = null;
let draftTimer = null;
let draftSave = null;

function showError(error) {
  const box = $("#page-feedback");
  box.textContent = error.message;
  box.hidden = false;
}

function clearError() {
  $("#page-feedback").hidden = true;
}

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function statusBadge(status) {
  const map = { todo: "未开始", in_progress: "进行中", done: "已完成", blocked: "前置未完成", learn: "学习中", practice: "练习中", mastered: "已掌握" };
  return `<span class="badge ${escapeHtml(status)}">${escapeHtml(map[status] || status)}</span>`;
}

// ---------------------------------------------------------------- 路由

const ROUTE_NAMES = new Set(["dashboard", "task", "catalog", "diagnostic"]);

function normaliseRoute(hash) {
  const raw = hash || "#/dashboard";
  const parts = raw.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (!parts.length || parts[0] === "dashboard") return "#/dashboard";
  if (parts[0] === "task" && parts.length === 2 && parts[1]) {
    try {
      return `#/task/${encodeURIComponent(decodeURIComponent(parts[1]))}`;
    } catch (_e) {
      return "#/dashboard";
    }
  }
  if (ROUTE_NAMES.has(parts[0]) && parts.length === 1) return `#/${parts[0]}`;
  return "#/dashboard";
}

async function navigate(hash) {
  const target = normaliseRoute(hash);
  // hashchange 是唯一的异步渲染入口；这样按钮导航与 back/forward 共用一条路径。
  if (window.location.hash === target) return;
  if (state.busy) return;
  try {
    await persistDraft();
    window.location.hash = target;
  } catch (error) { showError(error); }
}

window.addEventListener("hashchange", async () => {
  if (state.busy) {
    history.replaceState(null, "", state.route);
    return;
  }
  const target = normaliseRoute(window.location.hash);
  if (window.location.hash !== target) {
    history.replaceState(null, "", "#/dashboard");
  }
  try {
    await persistDraft();
    state.route = target;
    await render();
  } catch (error) {
    history.replaceState(null, "", state.route);
    showError(error);
  }
});

async function render() {
  const version = ++state.renderVersion;
  clearError();
  const route = state.route;
  const parts = route.replace(/^#\//, "").split("/");
  const name = parts[0] || "dashboard";
  document.querySelectorAll("#nav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.route === name);
  });
  if (name !== "task" && state.aiDrawerOpen) {
    state.aiDrawerOpen = false;
    document.body.classList.remove("ai-drawer-open");
  }
  try {
    if (!state.bootstrap) state.bootstrap = await api("GET", "/api/bootstrap");
    if (version !== state.renderVersion) return;
    if (name === "dashboard") return renderDashboard();
    if (name === "task") return await renderTask(parts[1], version);
    if (name === "catalog") return await renderCatalog();
    if (name === "diagnostic") return await renderDiagnostic();
    renderDashboard();
  } catch (error) {
    if (version === state.renderVersion) showError(error);
  }
}

// ---------------------------------------------------------------- 仪表盘

function renderDashboard() {
  const b = state.bootstrap;
  const current = b.current;
  const currentCard = current.all_done
    ? `<div class="panel"><h2>🎉 主线任务已全部完成</h2></div>`
    : `<div class="panel">
        <div class="row">
          <h2 style="margin:0">今日任务：${escapeHtml(current.task.id)} ${escapeHtml(current.task.title)}</h2>
          ${statusBadge(current.task.status)}
        </div>
        ${current.blocked
          ? `<div class="notice warn">当前任务被前置条件阻塞：${escapeHtml((current.missing_prerequisites || []).join("、"))}</div>
             <button data-goto-task="${escapeHtml(current.task.id)}">查看任务详情</button>`
          : `<p>${escapeHtml(current.task.learning_goal)}</p>
             <p>必修练习 ${current.task.lesson.required_completed}/${current.task.lesson.required_sections} 已通过</p>
             <progress value="${current.task.lesson.required_completed}" max="${current.task.lesson.required_sections}" aria-label="当前任务必修练习进度"></progress>
             <div class="row"><button class="primary" data-goto-task="${escapeHtml(current.task.id)}">继续课程</button></div>`}
      </div>`;

  const stagesHtml = b.stages
    .map(
      (stage) => `<details class="card stage-card" ${current.task?.stage_id === stage.id ? "open" : ""}>
        <summary>${escapeHtml(stage.id)} ${escapeHtml(stage.title)} <span class="muted small">${stage.done}/${stage.total} 个任务完成</span></summary>
        <p class="small muted">${escapeHtml(stage.goal)}</p>
        <div class="task-list">
          ${stage.tasks
            .map(
              (task) =>
                `<button class="task-link" data-goto-task="${escapeHtml(task.id)}"><span>${escapeHtml(task.id)} · ${escapeHtml(task.title)}</span><span>${statusBadge(task.status)}${task.blocked ? statusBadge("blocked") : ""}<small>${task.required_completed}/${task.required_sections} 必修练习通过</small></span></button>`
            )
            .join("")}
        </div>
      </details>`
    )
    .join("");

  app().innerHTML = `
    <h1>学习进度 <span class="muted small">${b.progress.done}/${b.progress.total} 个任务完成</span></h1>
    <div class="panel welcome"><h2>从第一行 Python 开始</h2><p>在这里读讲解、写代码、看反馈。每次完成一个小节即可；D02–D09 另有 24 道离线加练，遇到不熟的内容可以反复练习。</p><ol class="milestones"><li><strong>D01–D07 · 写出小程序</strong><br>能使用变量、判断、循环、函数和容器。</li><li><strong>D08–D17 · 处理真实数据</strong><br>能读写文件、编写命令、调用接口并测试。</li><li><strong>D18–D24 · 独立交付项目</strong><br>完成任务管理器，并从空目录重建运行。</li></ol><p class="small muted">学习顺序：读示例并预测输出 → 自己补全代码 → 对照反馈修改 → 再做一道加练。AI 应用在 D24 后继续学习。</p></div>
    ${currentCard}
    <div class="grid">${stagesHtml}</div>
    <details class="panel">
      <summary>知识模块与来源范围</summary>
      <div class="row">
        ${b.modules
          .filter((m) => m.enabled)
          .map((m) => `<span>${escapeHtml(m.title)} ${statusBadge(m.status)}</span>`)
          .join("")}
      </div>
      <p class="small muted">共 ${b.catalog_count} 条来源索引（仅作知识范围标题索引）</p>
    </details>`;
}

document.addEventListener("click", (event) => {
  const routeButton = event.target.closest("[data-route]");
  if (routeButton) {
    navigate(`#/${routeButton.dataset.route}`);
    return;
  }
  const goto = event.target.closest("[data-goto-task]");
  if (goto) navigate(`#/task/${goto.dataset.gotoTask}`);
});

// ---------------------------------------------------------------- 任务页

async function loadTask(taskId) {
  const payload = await api("GET", `/api/tasks/${encodeURIComponent(taskId)}`);
  if (state.route !== `#/task/${taskId}`) return false;
  state.task = payload;
  state.taskId = taskId;
  // 切换任务后旧的变式题绑定失效，必须清除，避免评审时把上一任务的变式题发给当前小节
  state.variationId = null;
  const lesson = state.task.task.lesson;
  state.currentSection = lesson.current_section;
  const section = lesson.sections.find((s) => s.id === state.currentSection);
  state.editorValue = initialContent(section);
  state.editorDirty = false;
  state.lessonView = section.title.startsWith("加练") ? "practice" : "learn";
  return true;
}

async function refreshTaskState() {
  if (!state.taskId) return;
  const taskId = state.taskId;
  const previousSection = state.currentSection;
  // Validation and env actions update progress on the server. Re-read both
  // payloads so locks, counts, current section, and dashboard state agree.
  state.task = await api("GET", `/api/tasks/${encodeURIComponent(taskId)}`);
  state.bootstrap = await api("GET", "/api/bootstrap");
  const lesson = state.task.task.lesson;
  state.currentSection = lesson.sections.some((section) => section.id === previousSection)
    ? previousSection
    : lesson.current_section;
  const section = lesson.sections.find((item) => item.id === state.currentSection);
  if (section) state.editorValue = initialContent(section);
}

function initialContent(section) {
  const practice = section.practice;
  if (practice.kind === "env_action") return "";
  return section.draft !== undefined ? section.draft : practice.starter_content || "";
}

async function renderTask(taskId, version = state.renderVersion) {
  if (state.taskId !== taskId || !state.task) {
    if (!await loadTask(taskId)) return;
  }
  const task = state.task.task;
  const isProjectTask = /^D(?:1[89]|2[0-4])$/.test(task.id);
  // 只有真实项目阶段显示工作区；基础语法页不把 15 个项目文件塞到学习主线里。
  if (isProjectTask) {
    state.workspace = await api("GET", "/api/workspace");
  } else {
    state.workspace = null;
  }
  if (version !== state.renderVersion || state.route !== `#/task/${taskId}`) return;
  const lesson = task.lesson;
  const section = lesson.sections.find((s) => s.id === state.currentSection);

  const navHtml = `<nav class="section-nav" aria-label="本任务课程目录">
    ${lesson.sections
      .map(
        (s, i) =>
          `<button data-section="${escapeHtml(s.id)}" ${s.id === state.currentSection ? 'aria-current="step"' : ''} class="${s.completed ? "completed" : ""} ${s.id === state.currentSection ? "active" : ""}">
            ${i + 1}. ${escapeHtml(s.title)}<small>${s.completed ? "已通过 ✓" : s.locked ? "前置未完成" : "待练习"}${s.optional ? " · 选修加练" : " · 必修"}</small>
          </button>`
      )
      .join("")}
  </nav>`;

  const prev = lesson.sections.findIndex((s) => s.id === state.currentSection);
  const pager = `<div class="row">
      <button data-section-step="-1" ${prev <= 0 ? "disabled" : ""}>上一节</button>
      <span class="muted small">${prev + 1}/${lesson.sections.length}</span>
      <button data-section-step="1" ${prev >= lesson.sections.length - 1 ? "disabled" : ""}>下一节</button>
      <span class="spacer"></span>
      <span class="muted small">已验证必修小节 ${lesson.required_completed}/${lesson.required_sections}</span>
    </div>`;

  const blockedHtml = task
    ? task.status !== "done" && lesson.required_completed >= lesson.required_sections
      ? `<div class="notice info">本任务必修练习已全部通过。可以继续选修加练，也可以在“实践与验收”中填写证据并完成任务。</div>`
      : ""
    : "";

  app().innerHTML = `
    <div class="row"><button data-route="dashboard">← 仪表盘</button></div>
    <h1>${escapeHtml(task.id)} ${escapeHtml(task.title)} ${statusBadge(task.status)}</h1>
    <p class="muted">${escapeHtml(task.learning_goal)}</p>
    <div class="notice info">${task.id === "D01"
      ? "<strong>今天只做一件事：</strong>让这台电脑能运行后面的练习。先写一句学习目标，再按顺序检测环境、创建项目专用环境、安装工具、最终检查。每步完成后继续下一节；全部通过后在页面底部填写证据。"
      : "<strong>本任务怎样做：</strong>选中小节，先读目标和示例，再在本页的实践区输入并运行验证。保存草稿只保留输入；验证通过才完成小节；全部必修小节通过后，在页面底部填写证据并标记任务完成。"}</div>
    ${task.modules.length ? `<p class="small">知识模块：${task.modules.map((m) => `${escapeHtml(m.title)} ${statusBadge(m.status)}${m.supplemental ? " 补充" : ""}`).join("，")}</p>` : ""}
    ${blockedHtml}
    <progress value="${lesson.completed_count}" max="${lesson.total_sections}" aria-label="任务小节完成进度"></progress>
    <p class="small muted">共 ${lesson.completed_count}/${lesson.total_sections} 节通过 · 含 ${lesson.total_sections - lesson.required_sections} 节选修加练</p>
    <div class="lesson-layout"><aside class="lesson-toc"><h2>课程目录</h2>${navHtml}</aside>
    <div class="panel lesson-panel">
      ${pager}
      <div id="section-body">${renderSection(section)}</div>
      ${pager}
    </div></div>
    ${renderAiDrawer(section)}
    ${isProjectTask ? renderWorkspacePanel() : ""}
    ${isProjectTask ? renderFilesPanel() : ""}
    <div class="panel">
      <h2>实践与验收</h2>
      <p class="small muted">${isProjectTask ? '产物文件' : '拓展练习文件（按需创建，本页代码保存在小节草稿中）'}：${task.artifacts.map((a) => escapeHtml(a)).join("、")}</p>
      <p class="small muted">验收：${task.acceptance.map((a) => escapeHtml(a)).join("；")}</p>
      <div class="row">
        <button id="mark-inprogress">标记为进行中</button>
        <button id="mark-done" ${lesson.required_completed < lesson.required_sections ? "disabled" : ""}>标记为完成（需证据）</button>
        <span class="small muted">已验证必修小节 ${lesson.required_completed}/${lesson.required_sections}（后端权威，全部通过才能完成）</span>
      </div>
      <div class="row" style="margin-top:8px">
        <label for="done-evidence">我的完成证据</label><input type="text" id="done-evidence" placeholder="例如：独立完成购物车汇总，空列表检查通过" style="flex:1">
      </div>
      ${task.status === "done" && !state.bootstrap.current.all_done ? `<button class="primary" data-goto-task="${escapeHtml(state.bootstrap.current.task.id)}">继续下一任务 ${escapeHtml(state.bootstrap.current.task.id)}</button>` : ""}
    </div>`;
  syncAiDrawerUi();
}

function renderSection(section) {
  const practice = section.practice;
  const kind = practice.kind;
  const locked = Boolean(section.locked);
  const actionFirst = section.id.startsWith("D01-");
  const d01Action = {
    "D01-onboarding": "写一句你想用 Python 做的事，然后点击“保存目标并验证”。通过后点“下一节”。",
    "D01-detect": "点击“检测我的环境”。先看当前状态；此时有工具尚未安装是正常的。",
    "D01-create-venv": "点击“创建项目专用环境（.venv）”。成功后点“下一节”。",
    "D01-install": "点击“安装学习工具与测试依赖”，确认后等待结果。这一步可能需要联网。",
    "D01-verify": "点击“检查环境是否准备完成”。全部通过后，在页面底部填写证据并标记 D01 完成。",
  }[section.id];
  const storedResult = state.lastValidation?.section_id === section.id ? state.lastValidation : null;
  let editorHtml = "";
  if (kind === "env_action") {
    editorHtml = renderEnvActions(practice, locked);
  } else {
    const placeholder = kind === "command" ? "在此输入命令…" : "在此输入内容…";
    const control = kind === "command"
      ? `<input type="text" class="mono" id="editor" aria-label="本节练习输入" value="${escapeHtml(state.editorValue)}" placeholder="${placeholder}" ${locked ? "disabled" : ""}>`
      : `<textarea class="mono" id="editor" aria-label="本节练习代码或文字" spellcheck="false" autocapitalize="off" placeholder="${placeholder}" ${locked ? "disabled" : ""}>${escapeHtml(state.editorValue)}</textarea>`;
    const fileLabel = practice.file_name ? `<p class="small muted">提交文件：${escapeHtml(practice.file_name)}</p>` : "";
    editorHtml = `
      ${fileLabel}
      ${control}
      <div class="row small muted"><span id="editor-lines">${state.editorValue.split("\n").length} 行</span><span id="draft-status" role="status">${state.editorDirty ? "有未保存内容" : "停止输入后自动保存草稿"}</span></div>
      <div class="row" style="margin-top:8px">
        <button id="save-draft" data-save-draft ${locked ? "disabled" : ""}>保存草稿</button>
        <button id="run-validate" class="primary" data-validate ${locked ? "disabled" : ""}>${section.id === "D01-onboarding" ? "保存目标并验证" : "运行并验证"}</button>
        <button id="reset-content" data-reset ${locked ? "disabled" : ""}>重置为起始内容</button>
      </div>
      <p class="small muted">Ctrl+S 保存 · Ctrl+Enter 运行验证。Tab 可正常移动到下一个控件。</p>
      <p class="small muted" style="margin-top:6px">${section.id === "D01-onboarding" ? "这一步只记录目标；电脑是否准备好由后面四个环境动作检查。" : "本地验证在本机执行你的代码（仅 127.0.0.1），不会对外发送；失败会保留草稿，验证通过才会完成本节。"}</p>`;
  }

  const examples = (practice.input_examples || [])
    .map((e) => `<div class="catalog-item small">${escapeHtml(e.label)}：<code class="mono">${escapeHtml(e.value)}</code></div>`)
    .join("");

  return `
    <h2 id="lesson-heading" tabindex="-1">${escapeHtml(section.title)}</h2>
    ${locked ? `<div class="notice warn"><strong>本节已锁定：</strong>${escapeHtml(section.lock_reason || "请先完成前置必修小节")}</div>` : ""}
    ${actionFirst ? `<div class="notice info"><strong>现在做什么：</strong>${escapeHtml(d01Action)}</div><div id="practice-editor" data-practice-kind="${kind}">${editorHtml}</div><div id="validation-result">${renderValidationResult(storedResult, kind)}</div><details><summary>查看详细说明与出错时的处理办法</summary>` : ""}
    ${actionFirst ? "" : `<div class="lesson-tabs" role="tablist" aria-label="学习与实践"><button role="tab" id="learn-tab" aria-controls="lesson-theory" aria-selected="${state.lessonView === 'learn'}" data-lesson-view="learn">1. 讲解与示例</button><button role="tab" id="practice-tab" aria-controls="lesson-practice" aria-selected="${state.lessonView === 'practice'}" data-lesson-view="practice">2. 动手练习</button></div><div id="lesson-theory" role="tabpanel" aria-labelledby="learn-tab" ${state.lessonView !== 'learn' ? 'hidden' : ''}>`}
    ${section.optional ? '<span class="badge">选修巩固 · 不阻塞主线</span>' : ""}
    ${section.supplemental ? `<span class="badge supplemental">真实开发补充</span> <p class="small muted">${escapeHtml(section.supplemental_note || "")}</p>` : ""}
    ${(section.catalog_refs || []).length ? `<p class="small muted">知识范围标题：${section.catalog_refs.map((r) => escapeHtml(r)).join("、")}</p>` : ""}
    <div class="lesson-objective"><h3>本节目标</h3><p>${escapeHtml(section.objective || "")}</p></div>
    ${section.explanation.map((p) => `<p>${escapeHtml(p)}</p>`).join("")}
    <h3>Python 语法规则</h3>
    <pre class="syntax-note">${escapeHtml(section.syntax || "")}</pre>
    <h3>关键点</h3>
    <ul>${section.key_points.map((k) => `<li>${escapeHtml(k)}</li>`).join("")}</ul>
    <details><summary>如果你了解 JavaScript：辅助对照</summary>
    <p class="small">${escapeHtml(section.js_bridge)}</p></details>
    <h3>逐步示例</h3>
    ${(section.examples || [section.example]).map((example, index) => `<div class="lesson-example"><h4>示例 ${index + 1}</h4><pre>${escapeHtml(example.code)}</pre><p><strong>${example.runnable ? '预期输出' : '片段用途'}：</strong></p><pre class="expected-output">${escapeHtml(example.output)}</pre><p class="small muted">${escapeHtml(example.explanation)}</p></div>`).join("")}
    <details><summary>常见错误与修改方法</summary>
    <ul class="lesson-errors">${(section.common_errors || []).map((error) => `<li><strong>${escapeHtml(error.error)}</strong><pre>${escapeHtml(error.example?.code || "")}</pre><p><strong>看到：</strong>${escapeHtml(error.symptom || "")}</p><p><strong>原因：</strong>${escapeHtml(error.cause || "")}</p><p><strong>修正：</strong>${escapeHtml(error.fix || error.example?.fix || "")}</p></li>`).join("")}</ul>
    </details><h3>引导练习</h3>
    ${section.guided_practice && !Array.isArray(section.guided_practice) ? `<div class="guided-practice"><p><strong>目标：</strong>${escapeHtml(section.guided_practice.goal)}</p><pre>${escapeHtml(section.guided_practice.starter)}</pre><ol>${(section.guided_practice.steps || []).map((step) => `<li><strong>操作：</strong>${escapeHtml(step.action)}<br><strong>预期：</strong>${escapeHtml(step.expected)}</li>`).join("")}</ol><p class="small muted"><strong>检查：</strong>${escapeHtml(section.guided_practice.check)}</p></div>` : `<ol>${(section.guided_practice || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>`}
    ${actionFirst ? "<hr>" : `<button class="primary" data-lesson-view="practice">读完了，开始动手练习 →</button></div><div id="lesson-practice" role="tabpanel" aria-labelledby="practice-tab" ${state.lessonView !== 'practice' ? 'hidden' : ''}>`}
    <h3>实践任务</h3>
    <p><strong>场景：</strong>${escapeHtml(practice.scenario)}</p>
    <p><strong>要求：</strong>${escapeHtml(practice.instructions)}</p>
    ${actionFirst ? "" : `<div id="practice-editor" data-practice-kind="${kind}">${editorHtml}</div>`}
    ${projectArtifactNote(section)}
    <p><strong>独立练习的预期行为：</strong>${escapeHtml(practice.expected_behavior)}</p>
    ${examples ? `<p><strong>可运行输入示例：</strong></p>${(practice.input_examples || []).map((e) => `<div class="catalog-item small"><strong>${escapeHtml(e.label)}</strong><pre>${escapeHtml(e.value)}</pre><p><strong>预期：</strong>${escapeHtml(e.expected || "")}</p></div>`).join("")}` : ""}
    ${practice.hints ? `<div class="notice info">💡 提示：${escapeHtml(practice.hints)}</div>` : ""}
    ${actionFirst ? "</details>" : `<div id="validation-result" role="status">${renderValidationResult(storedResult, kind)}</div></div>`}`;
}

function renderValidationResult(result, kind = "code") {
  if (!result) return "";
  const checks = (result.checks || [])
    .map((c) => `<li class="${c.passed ? "pass" : "fail"}">${c.passed ? "✓" : "✗"} ${escapeHtml(c.name)}${c.detail ? ` — ${escapeHtml(c.detail)}` : ""}</li>`)
    .join("");
  const command = kind === "env_action" && result.command
    ? `<h4>固定命令</h4><pre class="env-command mono">${escapeHtml(result.command)}</pre>`
    : "";
  const output = kind === "env_action"
    ? `<h4>stdout</h4><pre>${escapeHtml(result.stdout || "（空）")}</pre>
       <h4>stderr</h4><pre>${escapeHtml(result.stderr || "（空）")}</pre>`
    : (result.stdout || result.stderr)
      ? `<pre>${escapeHtml((result.stdout || "") + (result.stderr ? "\n" + result.stderr : ""))}</pre>`
      : "";
  return `<div class="result-box ${result.passed ? "passed" : "failed"}">
    <p><strong>${result.passed ? (kind === "env_action" ? "✅ 动作完成" : "✅ 验证通过") : (kind === "env_action" ? "❌ 动作未通过" : "❌ 验证未通过")}</strong>${result.completed ? "（本节已标记完成）" : ""} exit_code=${escapeHtml(result.exit_code ?? "—")}</p>
    ${result.learning_feedback ? `<p class="notice info">${escapeHtml(result.learning_feedback)}</p>` : ""}
    ${command}<ul class="check-list">${checks}</ul>${output}
    ${result.passed ? '<p>这次练习已通过。试着用自己的话解释为什么，再继续下一节。</p>' : ''}
  </div>`;
}

function projectArtifactNote(section) {
  const pf = section.practice.project_file;
  if (!pf) return "";
  const base = "learner_workspace/task-manager/";
  const copy = section.practice.continues_file
    ? `本节是在前一节真实产物 <code class="mono">${escapeHtml(base + pf)}</code> 上继续编辑；本地验证通过后仍会原子落盘回该真实文件。`
    : `本地验证通过后，本节真实产物会原子落盘到工作区文件 <code class="mono">${escapeHtml(base + pf)}</code>。`;
  return `<div class="notice info project-artifact"><strong>本节真实产物：</strong><code class="mono">${escapeHtml(base + pf)}</code><p class="small muted">${copy}</p></div>`;
}

function renderEnvActions(practice, locked = false) {
  // Keep the Windows path visible in source and in the rendered command hints;
  // the server still owns the fixed command and never executes browser text.
  // Windows path reference: .venv\Scripts\python.exe
  const action = practice.action;
  const labels = {
    detect: "检测我的环境",
    create_venv: "创建项目专用环境（.venv）",
    install: "安装学习工具与测试依赖",
    verify: "检查环境是否准备完成",
  };
  const notes = {
    detect: "查看本机 Python 和项目位置；部分工具尚未安装是正常的。",
    create_venv: "为本项目准备独立的 Python 环境；已有环境会复用。",
    install: "安装课程和测试所需工具；这一步可能需要联网。",
    verify: "检查 Python、课程工具和测试入口是否都已准备好。",
  };
  const commandHints = {
    detect: "where.exe python\npython --version\npython -c \"import sys; print(sys.executable)\"\nGet-Location",
    create_venv: "python -m venv .venv\nTest-Path .\\.venv\\Scripts\\python.exe\n.\\.venv\\Scripts\\python.exe --version",
    install: ".\\.venv\\Scripts\\python.exe -m pip --version\n.\\.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"",
    verify: ".\\.venv\\Scripts\\python.exe -m pytest -q tool_tests\n$LASTEXITCODE",
  };
  return `
    <div class="panel env-wizard">
      <h3>${escapeHtml(labels[action] || action)}</h3>
      <p class="small muted">${escapeHtml(notes[action] || "")}</p>
      <div class="row">
        <button class="primary" data-env-action="${escapeHtml(action)}" ${locked ? "disabled" : ""}>${escapeHtml(labels[action] || action)}</button>
      </div>
      <details><summary>查看执行的命令</summary><pre class="env-command mono">${escapeHtml(commandHints[action] || "")}</pre>
        ${action === "create_venv" ? '<p class="small muted">如果 PowerShell 的 ExecutionPolicy 阻止激活脚本，仍可直接使用 .venv\\Scripts\\python.exe；无需更改系统策略。</p>' : ""}
      </details>
      <p class="small muted" style="margin-top:6px">完成后查看页面中的通过或失败结果；失败时可展开详细报告。</p>
    </div>`;
}

function renderFilesPanel() {
  const files = state.task.editable_files || [];
  return `<div class="panel" id="files-panel">
      <h2>可编辑文件</h2>
      <div class="row">
        ${files
          .map((f) => `<button data-open-file="${escapeHtml(f.path)}">${escapeHtml(f.path)}${f.exists ? "" : "（新建）"}</button>`)
          .join("")}
      </div>
      <div id="file-editor" style="margin-top:10px"></div>
    </div>`;
}

function workspacePanelHtml(ws) {
  if (!ws || !ws.files || ws.files.length === 0) return "";
  const exists = ws.files.filter((f) => f.exists).length;
  const treeItems = ws.files
    .map(
      (f) =>
        `<div class="catalog-item small" data-ws-file="${escapeHtml(f.path)}" style="cursor:pointer">
          ${f.exists ? "📄" : "📝"} ${escapeHtml(f.path)}
          <span class="muted">${f.exists ? `${f.size} B` : "（未创建）"}</span>
        </div>`
    )
    .join("");
  return `<h2>📁 项目文件区 <span class="muted small">${exists}/${ws.files.length} 个文件已创建</span></h2>
      <p class="small muted">工作区根目录：${escapeHtml(ws.workspace_root)}/</p>
      <div id="workspace-tree">${treeItems}</div>`;
}

function renderWorkspacePanel() {
  const html = workspacePanelHtml(state.workspace);
  if (!html) return "";
  return `<div class="panel" id="workspace-panel">
      ${html}
      <div id="ws-file-viewer" style="margin-top:10px"></div>
    </div>`;
}

// ---------------------------------------------------------------- AI 助教

function renderAiDrawer(section) {
  const status = state.aiStatus;
  const target = state.variationId ? "生成的变式题" : "原始课程练习";
  const messages = currentAiMessages();
  const drawerOpen = state.aiDrawerOpen;
  return `<button type="button" id="ai-tutor-trigger" class="ai-tutor-trigger" aria-controls="ai-tutor-drawer" aria-expanded="${drawerOpen}">🤖 AI 助教</button>
    <div id="ai-tutor-backdrop" class="ai-tutor-backdrop ${drawerOpen ? "open" : ""}" aria-hidden="true"></div>
    <aside id="ai-tutor-drawer" class="ai-tutor-drawer ai-panel ${drawerOpen ? "open" : ""}" role="dialog" aria-modal="true" aria-labelledby="ai-tutor-title" aria-hidden="${!drawerOpen}" ${drawerOpen ? "" : "inert"}>
      <div class="ai-tutor-drawer-header">
        <div>
          <h2 id="ai-tutor-title">🤖 AI 助教</h2>
          <p class="small muted">DeepSeek · 当前小节辅助</p>
        </div>
        <button type="button" id="ai-tutor-close" class="ghost" aria-label="关闭 AI 助教">✕</button>
      </div>
      <div class="ai-tutor-drawer-body">
        <p class="small muted">本地验证不会对外发送；只有点击下方 DeepSeek 按钮，才会把当前练习内容发往模型。Key 只保存在本次服务内存，不写磁盘、不进日志。</p>
        <p id="ai-review-target" class="small"><strong>当前批改对象：</strong>${target}</p>
        <div id="ai-status">${status ? renderAiStatus(status) : '<span class="muted">读取状态…</span>'}</div>
        <div id="ai-actions" style="margin-top:10px">
          <div class="row">
            <input type="password" id="ai-key" placeholder="本次服务 API Key（可选）" style="flex:1; max-width:360px">
            <button id="ai-save-key">保存本次 Key</button>
            <button id="ai-test">测试连接（联网）</button>
          </div>
          <div class="row" style="margin-top:8px">
            <button id="ai-generate">生成变式练习</button>
            <button id="ai-review">评审我的练习</button>
          </div>
        </div>
        <div class="ai-chat" style="margin-top:14px">
          <div class="row"><h3 style="margin:0">💬 当前小节对话</h3><span class="spacer"></span><button id="ai-chat-clear" class="ghost" ${messages.length ? "" : "disabled"}>清空对话</button></div>
          <p class="small muted">自动携带“${escapeHtml(section.title)}”的教学、示例和练习上下文。切换小节后会自动切换对话上下文；最近 8 条消息会发给 DeepSeek。</p>
          <div id="ai-chat-messages" class="ai-chat-messages">${renderAiChatMessages(messages)}</div>
          <textarea id="ai-chat-input" placeholder="例如：我不理解为什么这里要缩进四个空格，请结合当前示例解释。" maxlength="2000" style="min-height:88px"></textarea>
          <div class="row" style="margin-top:8px"><button id="ai-chat-send" class="primary" ${currentAiChatBusy() ? "disabled" : ""}>${currentAiChatBusy() ? "正在回答…" : "发送问题"}</button><span class="small muted">联网调用 DeepSeek；不会改变本节完成状态。</span></div>
          <div id="ai-chat-error"></div>
        </div>
        <div id="ai-result"></div>
      </div>
    </aside>`;
}

function syncAiDrawerUi() {
  const open = state.aiDrawerOpen;
  const trigger = $("#ai-tutor-trigger");
  const drawer = $("#ai-tutor-drawer");
  const backdrop = $("#ai-tutor-backdrop");
  document.body.classList.toggle("ai-drawer-open", open);
  if (trigger) trigger.setAttribute("aria-expanded", String(open));
  if (drawer) {
    drawer.classList.toggle("open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    drawer.toggleAttribute("inert", !open);
  }
  if (backdrop) backdrop.classList.toggle("open", open);
}

function openAiTutorDrawer() {
  state.aiDrawerOpen = true;
  syncAiDrawerUi();
  // 等抽屉动画结束再聚焦，避开浏览器或自动化点击的焦点收尾。
  if (aiDrawerFocusTimer !== null) window.clearTimeout(aiDrawerFocusTimer);
  aiDrawerFocusTimer = window.setTimeout(() => {
    aiDrawerFocusTimer = null;
    if (!state.aiDrawerOpen) return;
    const input = $("#ai-chat-input");
    if (input) input.focus({ preventScroll: true });
  }, AI_DRAWER_FOCUS_DELAY_MS);
}

function closeAiTutorDrawer() {
  if (!state.aiDrawerOpen) return;
  if (aiDrawerFocusTimer !== null) {
    window.clearTimeout(aiDrawerFocusTimer);
    aiDrawerFocusTimer = null;
  }
  state.aiDrawerOpen = false;
  syncAiDrawerUi();
  const trigger = $("#ai-tutor-trigger");
  if (trigger) trigger.focus();
}

function aiChatKey() {
  return `${state.taskId}:${state.currentSection}`;
}

function currentAiMessages() {
  return state.aiChats[aiChatKey()] || [];
}

function currentAiChatBusy() {
  return state.aiChatPending[aiChatKey()] !== undefined;
}

function setCurrentAiChatControlsBusy(busy) {
  const input = $("#ai-chat-input");
  const button = $("#ai-chat-send");
  if (input) input.disabled = busy;
  if (button) {
    button.disabled = busy;
    button.textContent = busy ? "正在回答…" : "发送问题";
  }
}

function renderAiChatMessages(messages) {
  if (!messages.length) return '<p class="small muted">还没有对话。遇到不懂的概念、代码或报错，可以直接在下面提问。</p>';
  return messages
    .map((message) => `<div class="ai-message ${message.role}"><strong>${message.role === "user" ? "你" : "AI 助教"}</strong><p>${escapeHtml(message.content)}</p></div>`)
    .join("");
}

function renderAiStatus(status) {
  const source = status.key_source === "session" ? "本次会话 Key" : status.key_source === "env" ? "环境变量" : "未配置";
  return `<div class="row small">
      <span>Provider：<code>${escapeHtml(status.provider)}</code></span>
      <span>模型：<code>${escapeHtml(status.model)}</code></span>
      <span>状态：${status.configured ? `<span class="badge done">已配置（${escapeHtml(source)}）</span>` : '<span class="badge todo">未配置</span>'}</span>
    </div>`;
}

// ---------------------------------------------------------------- 目录

async function renderCatalog() {
  const series = state.catalogSeries;
  const q = state.catalogQuery;
  const data = await api("GET", `/api/catalog?series=${encodeURIComponent(series)}&q=${encodeURIComponent(q)}`);
  if (state.route !== "#/catalog" || q !== state.catalogQuery || series !== state.catalogSeries) return;
  app().innerHTML = `
    <h1>来源索引</h1>
    <p class="small muted">131 条来源仅作为知识范围标题索引，工具不会打开或抓取来源内容。共 ${data.total} 条匹配。</p>
    <div class="panel">
      <div class="row">
        <input type="text" id="catalog-q" placeholder="关键词（标题或 ID）" value="${escapeHtml(q)}" style="flex:1; max-width:360px">
        <input type="text" id="catalog-series" placeholder="系列（如 Python）" value="${escapeHtml(series)}" style="max-width:200px">
        <button id="catalog-search" class="primary">筛选</button>
      </div>
    </div>
    <div class="panel">
      ${data.items
        .map((item) => `<div class="catalog-item"><code>${escapeHtml(item.id)}</code> — ${escapeHtml(item.title)}</div>`)
        .join("") || '<span class="muted">无匹配</span>'}
    </div>`;
}

// ---------------------------------------------------------------- 诊断

async function renderDiagnostic() {
  const questions = await api("GET", "/api/diagnostic/questions");
  if (state.route !== "#/diagnostic") return;
  const answerInputs = questions.diagnostics
    .map(
      (d) => `<div class="card">
        <h3>${escapeHtml(d.id)} ${escapeHtml(d.title)}</h3>
        ${d.cases
          .map((c) => `<p class="small">${escapeHtml(c.prompt)}</p><input type="text" class="mono" data-answer="${escapeHtml(d.id)}:${escapeHtml(c.id)}" placeholder="你的回答">`)
          .join("")}
      </div>`
    )
    .join("");
  app().innerHTML = `
    <h1>能力诊断（可选工具）</h1>
    <p class="small muted">诊断不是主线前置。D0 会在隔离临时目录创建一次 venv 以检查环境。</p>
    ${answerInputs}
    <div class="row" style="margin-top:12px"><button id="diagnostic-run" class="primary">运行诊断</button></div>
    <div id="diagnostic-result"></div>`;
}

// ---------------------------------------------------------------- 事件

document.addEventListener("pointerdown", (event) => {
  if (event.target.closest("#ai-tutor-trigger, #ai-tutor-close")) event.preventDefault();
}, true);

document.addEventListener("click", async (event) => {
  try {
    const aiTutorTrigger = event.target.closest("#ai-tutor-trigger");
    if (aiTutorTrigger) {
      event.preventDefault();
      openAiTutorDrawer();
      return;
    }
    const aiTutorClose = event.target.closest("#ai-tutor-close, #ai-tutor-backdrop");
    if (aiTutorClose) {
      event.preventDefault();
      closeAiTutorDrawer();
      return;
    }
    const sectionBtn = event.target.closest("[data-section]");
    if (sectionBtn) {
      await selectSection(sectionBtn.dataset.section);
      return;
    }
    const viewButton = event.target.closest("[data-lesson-view]");
    if (viewButton) {
      if (state.busy) return;
      state.lessonView = viewButton.dataset.lessonView;
      await renderTask(state.taskId);
      $("#lesson-heading")?.focus({preventScroll: true});
      return;
    }
    const prevBtn = event.target.closest('[data-section-step="-1"]');
    const nextBtn = event.target.closest('[data-section-step="1"]');
    if (prevBtn || nextBtn) {
      const sections = state.task.task.lesson.sections;
      const index = sections.findIndex((s) => s.id === state.currentSection);
      const next = prevBtn ? index - 1 : index + 1;
      if (next >= 0 && next < sections.length) {
        await selectSection(sections[next].id);
      }
      return;
    }
    const openFile = event.target.closest("[data-open-file]");
    if (openFile) {
      await openFileEditor(openFile.dataset.openFile);
      return;
    }
    const wsFile = event.target.closest("[data-ws-file]");
    if (wsFile) {
      await viewWorkspaceFile(wsFile.dataset.wsFile);
      return;
    }
    const envAction = event.target.closest("[data-env-action]");
    if (envAction) {
      const action = envAction.dataset.envAction;
      if (action === "install") {
        // 取消则不发起请求；确认后由后端强制校验 confirmed: true
        if (!window.confirm("安装学习工具与测试依赖需要联网执行：.venv Python -m pip install -e .[dev]。是否继续？")) {
          return;
        }
        await runTaskAction(() => runEnvAction(action, { confirmed: true }));
      } else {
        await runTaskAction(() => runEnvAction(action));
      }
      return;
    }
    const saveDraft = event.target.closest("[data-save-draft]");
    if (saveDraft) {
      await runTaskAction(saveDraftSection);
      return;
    }
    const validate = event.target.closest("[data-validate]");
    if (validate) {
      await runTaskAction(validateSection);
      return;
    }
    const reset = event.target.closest("[data-reset]");
    if (reset) {
      await runTaskAction(resetContent);
      return;
    }
    const markIn = event.target.closest("#mark-inprogress");
    if (markIn) {
      await runTaskAction(() => setTaskStatus("in_progress", ""));
      return;
    }
    const markDone = event.target.closest("#mark-done");
    if (markDone) {
      const evidence = $("#done-evidence")?.value?.trim();
      await runTaskAction(() => setTaskStatus("done", evidence));
      return;
    }
    const aiSaveKey = event.target.closest("#ai-save-key");
    if (aiSaveKey) {
      await saveAiKey();
      return;
    }
    const aiTest = event.target.closest("#ai-test");
    if (aiTest) {
      await testAi();
      return;
    }
    const aiGenerate = event.target.closest("#ai-generate");
    if (aiGenerate) {
      await generateVariation();
      return;
    }
    const aiReview = event.target.closest("#ai-review");
    if (aiReview) {
      await reviewSubmission();
      return;
    }
    const aiChatSend = event.target.closest("#ai-chat-send");
    if (aiChatSend) {
      await sendTutorQuestion();
      return;
    }
    const aiChatClear = event.target.closest("#ai-chat-clear");
    if (aiChatClear) {
      const key = aiChatKey();
      state.aiChats[key] = [];
      // 清空同时使该小节尚未返回的请求失效，避免旧回答恢复已清空的对话。
      state.aiChatGenerations[key] = (state.aiChatGenerations[key] || 0) + 1;
      delete state.aiChatPending[key];
      setCurrentAiChatControlsBusy(false);
      const input = $("#ai-chat-input");
      if (input) input.value = "";
      const messages = $("#ai-chat-messages");
      if (messages) messages.innerHTML = renderAiChatMessages([]);
      aiChatClear.disabled = true;
      return;
    }
    const catalogSearch = event.target.closest("#catalog-search");
    if (catalogSearch) {
      state.catalogQuery = $("#catalog-q")?.value || "";
      state.catalogSeries = $("#catalog-series")?.value || "";
      await renderCatalog();
      return;
    }
    const diagnosticRun = event.target.closest("#diagnostic-run");
    if (diagnosticRun) {
      await runDiagnostic();
      return;
    }
  } catch (error) { showError(error); }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.aiDrawerOpen) {
    event.preventDefault();
    closeAiTutorDrawer();
  }
  if (event.target.matches("#editor") && (event.ctrlKey || event.metaKey)) {
    if (event.key.toLowerCase() === "s" || event.key === "Enter") {
      event.preventDefault();
      runTaskAction(event.key === "Enter" ? validateSection : saveDraftSection);
    }
  }
});

document.addEventListener("input", (event) => {
  if (!event.target.matches("#editor")) return;
  state.editorValue = event.target.value;
  state.editorDirty = true;
  state.lastValidation = null;
  $("#editor-lines").textContent = `${state.editorValue.split("\n").length} 行`;
  $("#draft-status").textContent = "有修改，正在等待自动保存…";
  $("#validation-result").textContent = "内容已修改，重新运行可检查本次结果。";
  window.clearTimeout(draftTimer);
  draftTimer = window.setTimeout(() => persistDraft().catch(showError), 800);
});

window.addEventListener("beforeunload", (event) => {
  if (!state.editorDirty && !draftSave) return;
  event.preventDefault();
  event.returnValue = "";
});

// ---------------------------------------------------------------- 任务操作

async function saveSectionPosition(sectionId) {
  await api("POST", `/api/tasks/${encodeURIComponent(state.taskId)}/lesson-position`, { section_id: sectionId });
}

async function selectSection(sectionId) {
  if (state.busy || sectionId === state.currentSection) return;
  state.busy = true;
  try {
    await persistDraft();
    await saveSectionPosition(sectionId);
    state.currentSection = sectionId;
    const section = state.task.task.lesson.sections.find((s) => s.id === sectionId);
    state.editorValue = initialContent(section);
    state.editorDirty = false;
    state.lessonView = section.title.startsWith("加练") ? "practice" : "learn";
    state.variationId = null;
    clearError();
    await renderTask(state.taskId);
    $("#lesson-heading")?.focus();
  } finally { state.busy = false; }
}

async function persistDraft() {
  window.clearTimeout(draftTimer);
  if (draftSave) await draftSave;
  if (!state.editorDirty) return;
  const taskId = state.taskId;
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  const content = state.editorValue;
  const status = $("#draft-status");
  if (status) status.textContent = "保存中…";
  // 保存串行进行。切换前等待完成，并同步内存草稿，防止返回小节时显示旧内容。
  draftSave = api("PUT", `/api/tasks/${encodeURIComponent(taskId)}/sections/${encodeURIComponent(section.id)}/draft`, {content});
  try {
    await draftSave;
    section.draft = content;
    if (state.editorValue === content) state.editorDirty = false;
    if (status) status.textContent = state.editorDirty ? "有新修改，尚未保存" : "草稿已保存";
  } catch (error) {
    if (status) status.textContent = "保存未完成，请重试";
    throw error;
  } finally { draftSave = null; }
}

async function runTaskAction(action) {
  if (state.busy) return;
  state.busy = true;
  clearError();
  const controls = [...document.querySelectorAll('#editor, [data-validate], [data-save-draft], [data-reset], [data-env-action]')];
  const disabled = controls.map((control) => control.disabled);
  controls.forEach((control) => { control.disabled = true; });
  try { await action(); }
  catch (error) { showError(error); setResult(escapeHtml(error.message), "failed"); }
  finally {
    state.busy = false;
    controls.forEach((control, index) => { control.disabled = disabled[index]; });
  }
}

function readEditor() {
  const editor = $("#editor");
  return editor ? editor.value : "";
}

function setResult(html, cls) {
  const box = $("#validation-result");
  if (box) box.innerHTML = `<div class="result-box ${cls}">${html}</div>`;
}

function setValidationResult(result, kind) {
  const box = $("#validation-result");
  if (box) box.innerHTML = renderValidationResult(result, kind);
}

async function saveDraftSection() {
  state.editorValue = readEditor();
  state.editorDirty = true;
  await persistDraft();
}

async function validateSection() {
  await persistDraft();
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  const kind = section.practice.kind;
  const resultBox = $("#validation-result");
  if (resultBox) resultBox.innerHTML = '<span class="muted">验证中…（本地执行）</span>';
  let result;
  if (kind === "env_action") {
    result = await api("POST", "/api/env/action", { action: section.practice.action });
  } else {
    const content = readEditor();
    result = await api("POST", `/api/tasks/${encodeURIComponent(state.taskId)}/sections/${encodeURIComponent(state.currentSection)}/validate`, { content });
  }
  state.lastValidation = { section_id: section.id, ...result };
  setValidationResult(state.lastValidation, kind);
  if (result.passed) {
    await refreshTaskState();
    await renderTask(state.taskId);
  }
}

async function resetContent() {
  if (!window.confirm("将本节草稿重置为起始内容？当前编辑内容将被替换。")) return;
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  state.editorValue = section.practice.starter_content || "";
  const editor = $("#editor");
  if (editor) editor.value = state.editorValue;
  state.editorDirty = true;
  state.lastValidation = null;
  await persistDraft();
  await renderTask(state.taskId);
}

async function setTaskStatus(status, evidence) {
  try {
    await persistDraft();
    await api("POST", `/api/tasks/${encodeURIComponent(state.taskId)}/status`, { status, evidence });
    const fresh = await api("GET", `/api/tasks/${encodeURIComponent(state.taskId)}`);
    state.task = fresh;
    state.bootstrap = await api("GET", "/api/bootstrap");
    await renderTask(state.taskId);
  } catch (error) {
    showError(error);
  }
}

async function runEnvAction(action, extra) {
  const box = $("#validation-result");
  if (box) box.innerHTML = '<span class="muted">正在执行固定动作…</span>';
  try {
    const result = await api("POST", "/api/env/action", { action, ...(extra || {}) });
    state.lastValidation = { section_id: state.currentSection, ...result };
    setValidationResult(state.lastValidation, "env_action");
    if (result.passed) {
      await refreshTaskState();
      await renderTask(state.taskId);
    }
  } catch (error) {
    setResult(`<span class="muted">${escapeHtml(error.message)}</span>`, "failed");
  }
}

async function openFileEditor(path) {
  const box = $("#file-editor");
  const data = await api("GET", `/api/files?task_id=${encodeURIComponent(state.taskId)}&path=${encodeURIComponent(path)}`);
  box.innerHTML = `
    <p class="small muted">${escapeHtml(data.path)}（${data.kind}）</p>
    <textarea class="mono" id="file-content" style="min-height:120px">${escapeHtml(data.content)}</textarea>
    <div class="row" style="margin-top:8px"><button id="file-save" data-file-path="${escapeHtml(data.path)}" class="primary">保存文件</button></div>`;
}

async function viewWorkspaceFile(relPath) {
  const box = $("#ws-file-viewer");
  try {
    const data = await api("GET", `/api/workspace/files/${encodeURIComponent(relPath)}`);
    const hint = data.exists
      ? `该文件已由本地验证原子落盘；可在此继续手动编辑。`
      : `该文件尚未创建。建议优先按课程章节完成验证以自动生成真实产物；此处手动保存仅供继续编辑，不会自动完成章节。`;
    box.innerHTML = `
      <p class="small muted">📄 ${escapeHtml(data.path)}${data.exists ? "" : "（未创建）"}</p>
      <p class="small muted">${escapeHtml(hint)}</p>
      <textarea class="mono ws-editor" id="ws-file-content" style="min-height:160px">${escapeHtml(data.content)}</textarea>
      <div class="row" style="margin-top:8px">
        <button id="save-workspace-file" data-ws-path="${escapeHtml(data.path)}" class="primary">保存项目文件</button>
        <span id="ws-save-result" class="small muted"></span>
      </div>`;
  } catch (error) {
    box.innerHTML = `<span class="muted">${escapeHtml(error.message)}</span>`;
  }
}

async function saveWorkspaceFile(path) {
  const content = $("#ws-file-content")?.value || "";
  const resultBox = $("#ws-save-result");
  if (resultBox) resultBox.textContent = "保存中…";
  try {
    const result = await api("PUT", `/api/workspace/files/${encodeURIComponent(path)}`, { content });
    // 刷新工作区文件树与当前内容（后端已原子落盘）
    try { state.workspace = await api("GET", "/api/workspace"); } catch (_e) { /* 忽略刷新失败 */ }
    const panel = $("#workspace-panel");
    if (panel) panel.innerHTML = workspacePanelHtml(state.workspace) + `<div id="ws-file-viewer" style="margin-top:10px"></div>`;
    await viewWorkspaceFile(path);
    const box2 = $("#ws-save-result");
    if (box2) box2.textContent = `✅ 已保存（${result.bytes} 字节）`;
  } catch (error) {
    if (resultBox) resultBox.innerHTML = `<span class="muted">${escapeHtml(error.message)}</span>`;
  }
}

document.addEventListener("click", async (event) => {
  const fileSave = event.target.closest("#file-save");
  if (fileSave) {
    const content = $("#file-content")?.value || "";
    const path = fileSave.dataset.filePath;
    await api("PUT", "/api/files", { task_id: state.taskId, path, content });
    alert("文件已保存");
    await openFileEditor(path);
  }
  const wsSave = event.target.closest("#save-workspace-file");
  if (wsSave) {
    await saveWorkspaceFile(wsSave.dataset.wsPath);
  }
});

// ---------------------------------------------------------------- AI 操作

async function loadAiStatus() {
  try {
    state.aiStatus = await api("GET", "/api/ai/status");
  } catch (_e) {
    state.aiStatus = { provider: "deepseek", configured: false, key_source: null };
  }
}

async function saveAiKey() {
  const key = $("#ai-key")?.value?.trim();
  const result = $("#ai-result");
  if (!key) {
    alert("请输入 Key");
    return;
  }
  try {
    await api("POST", "/api/ai/session-key", { key });
    $("#ai-key").value = "";
    state.aiStatus = await api("GET", "/api/ai/status");
    const box = $("#ai-status");
    if (box) box.innerHTML = renderAiStatus(state.aiStatus);
    if (result) result.innerHTML = '<span class="muted">Key 已保存到本次服务内存。</span>';
  } catch (error) {
    if (result) result.innerHTML = `<div class="result-box failed">${escapeHtml(error.message)}</div>`;
  }
}

async function testAi() {
  const result = $("#ai-result");
  if (result) result.innerHTML = '<span class="muted">测试连接中…（将访问 DeepSeek）</span>';
  try {
    const data = await api("POST", "/api/ai/test", {});
    if (result) result.innerHTML = `<div class="result-box passed"><p>✅ 连接成功</p><pre>${escapeHtml(data.content)}</pre></div>`;
  } catch (error) {
    if (result) result.innerHTML = `<div class="result-box failed">${escapeHtml(error.message)}</div>`;
  }
}

async function generateVariation() {
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  const result = $("#ai-result");
  if (result) result.innerHTML = '<span class="muted">正在生成变式练习（联网）…</span>';
  try {
    // 完成状态由服务端从当前进度派生，客户端不再发送 completed
    const data = await api("POST", "/api/ai/generate", {
      task_id: state.taskId,
      section_id: section.id,
    });
    const v = data.variation;
    // 变式题 id 只由服务端权威保存；前端只保留对当前小节的绑定，评审时仅回传 id
    state.variationId = data.variation_id;
    const targetBox = $("#ai-review-target");
    if (targetBox) targetBox.innerHTML = "<strong>当前批改对象：</strong>生成的变式题";
    const html = `<div class="result-box passed">
      <h3>🧩 变式练习（独立编辑器，不影响本节完成）</h3>
      <p><strong>${escapeHtml(v.title)}</strong></p>
      <p><strong>场景：</strong>${escapeHtml(v.scenario)}</p>
      <p><strong>要求：</strong>${escapeHtml(v.instructions)}</p>
      <p class="small muted"><strong>起始内容：</strong></p>
      <pre>${escapeHtml(v.starter_content)}</pre>
      <p class="small muted"><strong>评审标准：</strong>${escapeHtml(v.review_rubric)}</p>
      <p class="small muted">本变式题已保存在本次服务内存；点击“评审我的练习”将按该变式题评审。</p>
      <p class="small muted">索引标题仅代表知识范围，不代表视频正文。</p>
    </div>`;
    if (result) result.innerHTML = html;
  } catch (error) {
    if (result) result.innerHTML = `<div class="result-box failed">${escapeHtml(error.message)}</div>`;
  }
}

async function reviewSubmission() {
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  const content = readEditor();
  const result = $("#ai-result");
  if (result) result.innerHTML = '<span class="muted">正在评审（联网）…</span>';
  const summary = summarizeValidation();
  const variation_id = state.variationId;
  const target = variation_id ? "变式练习" : "原始课程练习";
  try {
    const body = {
      task_id: state.taskId,
      section_id: section.id,
      content,
      validation_summary: summary,
    };
    if (variation_id) body.variation_id = variation_id;
    const data = await api("POST", "/api/ai/review", body);
    const r = data.review;
    const html = `<div class="result-box passed">
      <h3>📋 评审结果</h3>
      <p class="small"><strong>评审对象：</strong>${target}</p>
      <p><strong>总结：</strong>${escapeHtml(r.summary)}</p>
      <p><strong>优点：</strong>${Array.isArray(r.strengths) ? r.strengths.map((s) => escapeHtml(s)).join("；") : escapeHtml(r.strengths)}</p>
      <p><strong>问题：</strong>${Array.isArray(r.issues) ? r.issues.map((s) => escapeHtml(s)).join("；") : escapeHtml(r.issues)}</p>
      <p><strong>下一步：</strong>${Array.isArray(r.next_steps) ? r.next_steps.map((s) => escapeHtml(s)).join("；") : escapeHtml(r.next_steps)}</p>
      <p class="small muted">评审只用于指导；本地验证通过才是完成本节的唯一依据。</p>
    </div>`;
    if (result) result.innerHTML = html;
  } catch (error) {
    if (result) result.innerHTML = `<div class="result-box failed">${escapeHtml(error.message)}</div>`;
  }
}

async function sendTutorQuestion() {
  const key = aiChatKey();
  if (state.aiChatPending[key] !== undefined) return;
  const input = $("#ai-chat-input");
  const question = input?.value?.trim() || "";
  const errorBox = $("#ai-chat-error");
  if (!question) {
    if (errorBox) errorBox.innerHTML = '<div class="result-box failed">请输入你对当前小节的问题。</div>';
    return;
  }
  const history = currentAiMessages().slice(-8);
  const requestTaskId = state.taskId;
  const requestSectionId = state.currentSection;
  const requestGeneration = (state.aiChatGenerations[key] || 0) + 1;
  state.aiChatGenerations[key] = requestGeneration;
  state.aiChatPending[key] = requestGeneration;
  setCurrentAiChatControlsBusy(true);
  if (errorBox) errorBox.innerHTML = '<span class="muted">正在向 DeepSeek 请教当前小节…</span>';
  try {
    const data = await api("POST", "/api/ai/chat", {
      task_id: requestTaskId,
      section_id: requestSectionId,
      question,
      history,
    });
    if (!data.ok) throw new Error(data.error || "AI 助教回答失败");
    if (state.aiChatGenerations[key] !== requestGeneration) return;
    // 发送给模型和保存在浏览器中的历史使用同一个 8 条上限。
    state.aiChats[key] = [...history, { role: "user", content: question }, { role: "assistant", content: data.answer }].slice(-8);
    delete state.aiChatPending[key];
    if (aiChatKey() !== key) return;
    setCurrentAiChatControlsBusy(false);
    const messagesBox = $("#ai-chat-messages");
    if (messagesBox) {
      messagesBox.innerHTML = renderAiChatMessages(state.aiChats[key]);
      messagesBox.scrollTop = messagesBox.scrollHeight;
    }
    const currentInput = $("#ai-chat-input");
    if (currentInput) {
      currentInput.value = "";
      currentInput.focus();
    }
    const clear = $("#ai-chat-clear");
    if (clear) clear.disabled = false;
    const currentErrorBox = $("#ai-chat-error");
    if (currentErrorBox) currentErrorBox.innerHTML = "";
  } catch (error) {
    if (state.aiChatGenerations[key] !== requestGeneration) return;
    delete state.aiChatPending[key];
    if (aiChatKey() !== key) return;
    setCurrentAiChatControlsBusy(false);
    const currentErrorBox = $("#ai-chat-error");
    if (currentErrorBox) currentErrorBox.innerHTML = `<div class="result-box failed">${escapeHtml(error.message)}</div>`;
    return;
  }
}

function summarizeValidation() {
  if (!state.lastValidation) return "";
  const checks = (state.lastValidation.checks || []).map((c) => `${c.passed ? "通过" : "未通过"}:${c.name}`).join("；");
  return `section=${state.lastValidation.section_id}; passed=${state.lastValidation.passed}; checks=${checks.slice(0, 300)}`;
}

async function runDiagnostic() {
  const answers = {};
  document.querySelectorAll("[data-answer]").forEach((input) => {
    const [d, c] = input.dataset.answer.split(":");
    if (input.value.trim()) {
      answers[d] = answers[d] || {};
      answers[d][c] = input.value.trim();
    }
  });
  const box = $("#diagnostic-result");
  if (box) box.innerHTML = '<span class="muted">运行诊断中…（D0 会创建一次临时 venv）</span>';
  try {
    const report = await api("POST", "/api/diagnostic/run", { answers });
    const rows = report.diagnostics
      .map((d) => `<tr><td>${escapeHtml(d.id)}</td><td>${d.score}%</td><td>${d.critical_passed ? "是" : "否"}</td><td>${escapeHtml(d.level)}</td></tr>`)
      .join("");
    if (box) box.innerHTML = `<table><thead><tr><th>诊断</th><th>得分</th><th>关键用例</th><th>结论</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (error) {
    if (box) box.innerHTML = `<div class="result-box failed">${escapeHtml(error.message)}</div>`;
  }
}

// ---------------------------------------------------------------- 启动

(async function init() {
  const initialRoute = normaliseRoute(window.location.hash);
  if (window.location.hash !== initialRoute) history.replaceState(null, "", initialRoute);
  state.route = initialRoute;
  await loadAiStatus();
  render();
})();

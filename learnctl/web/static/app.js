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
};

const $ = (sel) => document.querySelector(sel);
const app = () => $("#app");
const AI_DRAWER_FOCUS_DELAY_MS = 220;
let aiDrawerFocusTimer = null;

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(path, options);
  let data = {};
  try {
    data = await res.json();
  } catch (_e) {
    data = {};
  }
  if (!res.ok && !data.ok) {
    throw new Error(data.error || `请求失败（HTTP ${res.status}）`);
  }
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
  const map = { todo: "未开始", in_progress: "进行中", done: "已完成" };
  return `<span class="badge ${status}">${map[status] || status}</span>`;
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

function navigate(hash) {
  const target = normaliseRoute(hash);
  // hashchange 是唯一的异步渲染入口；这样按钮导航与 back/forward 共用一条路径。
  if (window.location.hash === target) return;
  window.location.hash = target;
}

window.addEventListener("hashchange", () => {
  const target = normaliseRoute(window.location.hash);
  if (window.location.hash !== target) {
    history.replaceState(null, "", "#/dashboard");
  }
  state.route = target;
  render();
});

async function render() {
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
    if (name === "dashboard") return renderDashboard();
    if (name === "task") return renderTask(parts[1]);
    if (name === "catalog") return renderCatalog();
    if (name === "diagnostic") return renderDiagnostic();
    renderDashboard();
  } catch (error) {
    app().innerHTML = `<div class="notice warn">${escapeHtml(error.message)}</div>`;
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
             <div class="row"><button class="primary" data-goto-task="${escapeHtml(current.task.id)}">继续学习</button></div>`}
      </div>`;

  const stagesHtml = b.stages
    .map(
      (stage) => `<div class="card">
        <h3>${escapeHtml(stage.id)} ${escapeHtml(stage.title)} <span class="muted small">${stage.done}/${stage.total}</span></h3>
        <p class="small muted">${escapeHtml(stage.goal)}</p>
        <div class="row">
          ${stage.tasks
            .map(
              (task) =>
                `<button data-goto-task="${escapeHtml(task.id)}" title="${task.completed_sections} 节已完成">${escapeHtml(task.id)}${task.status === "done" ? " ✓" : ""}</button>`
            )
            .join("")}
        </div>
      </div>`
    )
    .join("");

  app().innerHTML = `
    <h1>学习进度 <span class="muted small">${b.progress.done}/${b.progress.total} 个任务完成</span></h1>
    ${currentCard}
    <div class="grid">${stagesHtml}</div>
    <div class="panel">
      <h2>知识模块</h2>
      <div class="row">
        ${b.modules
          .filter((m) => m.enabled)
          .map((m) => `<span class="badge ${m.status}">${escapeHtml(m.id)} ${escapeHtml(m.status)}${m.supplemental ? " ⚡补充" : ""}</span>`)
          .join("")}
      </div>
      <p class="small muted">共 ${b.catalog_count} 条来源索引（仅作知识范围标题索引）</p>
    </div>`;
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
  state.task = await api("GET", `/api/tasks/${encodeURIComponent(taskId)}`);
  state.taskId = taskId;
  // 切换任务后旧的变式题绑定失效，必须清除，避免评审时把上一任务的变式题发给当前小节
  state.variationId = null;
  const lesson = state.task.task.lesson;
  if (!state.currentSection || !lesson.sections.some((s) => s.id === state.currentSection)) {
    state.currentSection = lesson.current_section;
  }
  const section = lesson.sections.find((s) => s.id === state.currentSection);
  state.editorValue = initialContent(section);
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

async function renderTask(taskId) {
  if (state.taskId !== taskId || !state.task) await loadTask(taskId);
  const task = state.task.task;
  const isProjectTask = /^D(?:1[89]|2[0-4])$/.test(task.id);
  // 只有真实项目阶段显示工作区；基础语法页不把 15 个项目文件塞到学习主线里。
  if (isProjectTask) {
    try { state.workspace = await api("GET", "/api/workspace"); } catch (_e) { state.workspace = null; }
  } else {
    state.workspace = null;
  }
  const lesson = task.lesson;
  const section = lesson.sections.find((s) => s.id === state.currentSection);

  const navHtml = `<div class="section-nav">
    ${lesson.sections
      .map(
        (s, i) =>
          `<button data-section="${escapeHtml(s.id)}" class="${s.completed ? "completed" : ""} ${s.id === state.currentSection ? "active" : ""}">
            ${i + 1}. ${escapeHtml(s.title)}${s.completed ? " ✓" : ""}
          </button>`
      )
      .join("")}
  </div>`;

  const prev = lesson.sections.findIndex((s) => s.id === state.currentSection);
  const pager = `<div class="row">
      <button id="prev-section" ${prev <= 0 ? "disabled" : ""}>上一节</button>
      <span class="muted small">${prev + 1}/${lesson.sections.length}</span>
      <button id="next-section" ${prev >= lesson.sections.length - 1 ? "disabled" : ""}>下一节</button>
      <span class="spacer"></span>
      <span class="muted small">已验证必修小节 ${lesson.required_completed}/${lesson.required_sections}</span>
    </div>`;

  const blockedHtml = task
    ? task.status === "todo" && lesson.completed_count >= lesson.total_sections
      ? `<div class="notice info">本任务全部小节已通过本地验证。请在“实践与验收”中填写证据并把任务标记为完成。</div>`
      : ""
    : "";

  app().innerHTML = `
    <div class="row"><button data-route="dashboard">← 仪表盘</button></div>
    <h1>${escapeHtml(task.id)} ${escapeHtml(task.title)} ${statusBadge(task.status)}</h1>
    <p class="muted">${escapeHtml(task.learning_goal)}</p>
    <div class="notice info">${task.id === "D01"
      ? "<strong>今天只做一件事：</strong>让这台电脑能运行后面的练习。先写一句学习目标，再按顺序检测环境、创建项目专用环境、安装工具、最终检查。每步完成后继续下一节；全部通过后在页面底部填写证据。"
      : "<strong>本任务怎样做：</strong>选中小节，先读目标和示例，再在本页的实践区输入并运行验证。保存草稿只保留输入；验证通过才完成小节；全部必修小节通过后，在页面底部填写证据并标记任务完成。"}</div>
    ${task.modules.length ? `<p class="small">知识模块：${task.modules.map((m) => `${escapeHtml(m.id)} [${escapeHtml(m.status)}]${m.supplemental ? " ⚡补充" : ""}`).join("，")}</p>` : ""}
    ${blockedHtml}
    ${navHtml}
    <div class="panel lesson-panel">
      ${pager}
      <div id="section-body">${renderSection(section)}</div>
      ${pager}
    </div>
    ${renderAiDrawer(section)}
    ${isProjectTask ? renderWorkspacePanel() : ""}
    ${isProjectTask ? renderFilesPanel() : ""}
    <div class="panel">
      <h2>实践与验收</h2>
      <p class="small muted">产物文件：${task.artifacts.map((a) => escapeHtml(a)).join("、")}</p>
      <p class="small muted">验收：${task.acceptance.map((a) => escapeHtml(a)).join("；")}</p>
      <div class="row">
        <button id="mark-inprogress">标记为进行中</button>
        <button id="mark-done" ${lesson.required_completed < lesson.required_sections ? "disabled" : ""}>标记为完成（需证据）</button>
        <span class="small muted">已验证必修小节 ${lesson.required_completed}/${lesson.required_sections}（后端权威，全部通过才能完成）</span>
      </div>
      <div class="row" style="margin-top:8px">
        <input type="text" id="done-evidence" placeholder="完成证据（pytest 通过 / 本地验证通过 等）" style="flex:1">
      </div>
    </div>`;
  syncAiDrawerUi();
}

function experimentKey(sectionId, mode, index) {
  return `${state.taskId}/${sectionId}/${mode}/${index}`;
}
const experimentDrafts = new Map();
const experimentResults = new Map();

function experimentBlock(section, item, mode, index) {
  const key = experimentKey(section.id, mode, index);
  const source = experimentDrafts.has(key) ? experimentDrafts.get(key) : (item.starter ?? item.code ?? "");
  const title = item.title || (mode === "example" ? `示例 ${index + 1}` : `练习 ${index + 1}`);
  const result = experimentResults.get(key);
  if (!item.runnable || item.source_kind !== "python") {
    return `<details class="mini-example"><summary>${escapeHtml(title)} · 文件/命令片段</summary><p>操作位置：${escapeHtml(item.target_path || "按题目指定位置")}</p><pre>${escapeHtml(source)}</pre><h4>预期效果（不是实际执行结果）</h4><pre>${escapeHtml(item.output || "")}</pre></details>`;
  }
  return `<details class="mini-example" ${mode === "card" ? "open" : ""} data-experiment-key="${escapeHtml(key)}">
    <summary>${escapeHtml(title)}${mode === "card" ? " · 先补这个知识" : " · 可编辑运行"}</summary>
    <p>${escapeHtml(item.rule || item.instructions || "先运行原例子，再改一个值观察结果；不覆盖下方正式作业。")}</p>
    <div class="experiment-grid"><div><label class="small">独立实验代码<textarea class="mono experiment-editor" data-experiment-editor="${escapeHtml(key)}" spellcheck="false">${escapeHtml(source)}</textarea></label>
    <button type="button" data-run-experiment data-mode="${mode}" data-index="${index}" data-section-id="${escapeHtml(section.id)}">${mode === "drill" ? "运行这道练习" : "运行并观察"}</button></div>
    <div><h4>预期输出（参考）</h4><pre class="expected-output">${escapeHtml(item.output ?? "")}</pre><div data-experiment-result aria-live="polite">${result ? renderExperimentResult(result) : '<p class="muted">尚未运行；实际输出将在这里出现。</p>'}</div></div></div>
  </details>`;
}

function renderExperimentResult(result) {
  return `<div class="result-box ${result.passed ? "passed" : "failed"}"><strong>${result.passed ? "✓ 输出符合预期" : "输出有差异或运行失败"}</strong>
    <p>${escapeHtml(result.message || "")}</p><h4>实际输出 stdout</h4><pre>${escapeHtml(result.stdout || "（没有打印输出）")}</pre>
    ${result.stderr ? `<h4>错误输出 stderr</h4><pre>${escapeHtml(result.stderr)}</pre>` : ""}
    ${result.diff ? `<details open><summary>逐行差异</summary><pre>${escapeHtml(result.diff)}</pre></details>` : ""}
    <p class="small muted">退出码 ${escapeHtml(result.exit_code)} · ${escapeHtml(result.duration_ms)} ms · 不计入主作业完成</p></div>`;
}

function renderSection(section) {
  const p = section.practice;
  const kind = p.kind;
  const locked = Boolean(section.locked);
  const pf = section.practice_first || {};
  const storedResult = state.lastValidation?.section_id === section.id ? state.lastValidation : null;
  const isEnvironment = kind === "env_action";
  const isOnboarding = section.id === "D01-onboarding";
  const editor = isEnvironment ? renderEnvActions(p, locked) : `
    <label for="editor">${kind === "code" ? "在这里编写正式作业" : kind === "command" ? "在这里编写命令说明（不执行）" : "在这里填写本节内容"}</label>
    ${p.file_name ? `<p class="small muted">提交文件：${escapeHtml(p.file_name)}</p>` : ""}
    <textarea class="mono" id="editor" spellcheck="false" ${locked ? "disabled" : ""}>${escapeHtml(state.editorValue)}</textarea>
    <div class="row"><button id="run-validate" class="primary" data-validate ${locked ? "disabled" : ""}>${isOnboarding ? "保存目标并验证" : "验证正式作业"}</button><button id="save-draft" data-save-draft ${locked ? "disabled" : ""}>保存草稿</button><button data-reset ${locked ? "disabled" : ""}>重置为起始内容</button></div>`;
  const inputExamples = (p.input_examples || []).map(x => `<tr><td><pre>${escapeHtml(x.value)}</pre></td><td><pre>${escapeHtml(x.expected)}</pre></td></tr>`).join("");
  const prereqs = (pf.prerequisites || []).map(id => `<button type="button" data-review-section="${escapeHtml(id)}">复习 ${escapeHtml(id)}</button>`).join("");
  return `<h2>${escapeHtml(section.title)}</h2>
    ${section.optional ? '<p class="badge">选修巩固 · 不阻塞主线</p>' : ""}
    ${locked ? `<div class="notice warn">正式作业未解锁：${escapeHtml(section.lock_reason)}。仍可阅读和运行独立示例。</div>` : ""}
    <div class="brief-rules"><p><strong>现在做什么：</strong>${escapeHtml(pf.goal || p.instructions)}</p>
    <p class="small">${escapeHtml((pf.rules || [section.syntax]).slice(0, 2).join("\n"))}</p>
    ${pf.provided ? `<p class="small muted">${escapeHtml(pf.provided)}</p>` : ""}
    ${prereqs ? `<details><summary>需要回顾的前置知识</summary><div class="row">${prereqs}</div></details>` : ""}</div>
    ${(pf.cards || []).map((x,i) => experimentBlock(section,x,"card",i)).join("")}
    <div class="practice-grid"><div class="practice-writing">
      <h3>${isEnvironment ? "环境操作" : "独立作业"}</h3><div id="practice-editor" data-practice-kind="${kind}">${editor}</div>
      ${projectArtifactNote(section)}
      <p class="small muted">Python 代码会在本机执行，不是安全沙箱。不要运行不可信代码或填写真实密钥。命令文本不在这里执行。</p>
      <details><summary>卡住时看提示</summary><p>${escapeHtml(p.hints || "对比输入与预期，再检查最先失败的一项。")}</p></details>
    </div><aside class="practice-output"><h3>结果对照</h3>
      <div id="validation-result" aria-live="polite">${storedResult ? renderValidationResult(storedResult, kind) : '<p class="muted">尚未验证。下方是目标，不是你的实际运行结果。</p>'}</div>
      <details ${storedResult ? "" : "open"}><summary>本题输入与预期</summary><div class="table-scroll"><table class="case-table"><thead><tr><th>输入 / 操作</th><th>预期返回、输出或异常</th></tr></thead><tbody>${inputExamples}</tbody></table></div></details>
    </aside></div>
    ${(pf.drills || []).length ? `<section class="drill-section"><h3>多写几次：补全与改写</h3><p class="small muted">独立编辑器，不覆盖正式作业。先补全再换输入；不同输出不一定是错误。</p>${pf.drills.map((x,i) => experimentBlock(section,x,"drill",i)).join("")}</section>` : ""}
    <details class="examples-reference"><summary>查看并运行完整示例</summary>${(section.examples || []).map((x,i) => experimentBlock(section,x,"example",i)).join("")}</details>
    <details class="long-reference"><summary>详细原理、常见错误与 JavaScript 对照（按需阅读）</summary>
      <h3>本节目标</h3><p>${escapeHtml(section.objective)}</p>
      ${(section.explanation || []).map(x=>`<p>${escapeHtml(x)}</p>`).join("")}
      <h3>语法与关键点</h3><pre>${escapeHtml(section.syntax)}</pre><ul>${(section.key_points || []).map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>
      <h3>JavaScript 对照（仅辅助）</h3><p>${escapeHtml(section.frontend_bridge)}</p>
      <h3>常见错误</h3>${(section.common_errors || []).map(x=>`<h4>${escapeHtml(x.error)}</h4><pre>${escapeHtml(x.example?.code || "")}</pre><p>${escapeHtml(x.symptom)} ${escapeHtml(x.cause)}</p><p>修正：${escapeHtml(x.fix)}</p>`).join("")}
      <h3>引导步骤</h3><ol>${(section.guided_practice?.steps || []).map(x=>`<li>${escapeHtml(x.action)} → ${escapeHtml(x.expected)}</li>`).join("")}</ol>
      <p class="small muted">来源标题只作知识范围索引：${(section.catalog_refs || []).map(escapeHtml).join("、")}</p>
    </details>`;
}

function renderValidationResult(result, kind = "code") {
  if (!result) return "";
  const cases = result.cases || [];
  const table = cases.length ? `<div class="table-scroll"><table class="case-table"><thead><tr><th>测试输入</th><th>预期</th><th>实际</th><th>结果</th></tr></thead><tbody>${cases.map(c => `<tr><td><pre>${escapeHtml(c.input || c.name)}</pre></td><td><pre>${escapeHtml(c.expected)}</pre></td><td><pre>${escapeHtml(c.actual)}</pre></td><td>${c.passed ? "✓" : "✗"}</td></tr>`).join("")}</tbody></table></div>` : "";
  const checks = (result.checks || []).map(c => `<li class="${c.passed ? "pass" : "fail"}">${c.passed ? "✓" : "✗"} ${escapeHtml(c.name)}${c.detail ? ` — ${escapeHtml(c.detail)}` : ""}</li>`).join("");
  return `<div class="result-box ${result.passed ? "passed" : "failed"}">
    <p><strong>${result.passed ? "✓ 验证通过" : "✗ 验证未通过"}</strong>${result.completed ? " · 本节已记录完成" : ""}</p>
    ${table}<p class="small muted">预期要求抛异常时，正确抛出也算通过；返回值与 print 输出是不同的结果。</p>
    <h4>控制台输出 stdout</h4><pre>${escapeHtml(result.stdout || "（没有 print 输出；返回值请看上方对照或检查项）")}</pre>
    ${result.stderr ? `<details ${result.passed ? "" : "open"}><summary>错误输出 stderr</summary><pre>${escapeHtml(result.stderr)}</pre></details>` : ""}
    <details ${!cases.length || !result.passed ? "open" : ""}><summary>逐项检查与运行信息</summary><ul class="check-list">${checks}</ul><p>exit_code=${escapeHtml(result.exit_code ?? "—")}</p>${result.command ? `<pre>${escapeHtml(result.command)}</pre>` : ""}</details>
  </div>`;
}

document.addEventListener("input", event => {
  const el = event.target;
  if (el.matches("[data-experiment-editor]")) experimentDrafts.set(el.dataset.experimentEditor, el.value);
  if (el.id === "editor") state.editorValue = el.value;
});
document.addEventListener("click", async event => {
  const review = event.target.closest("[data-review-section]");
  if (review) {
    const sid = review.dataset.reviewSection;
    state.currentSection = sid;
    if (state.taskId === sid.slice(0,3)) {
      const section = state.task.task.lesson.sections.find(x => x.id === sid);
      state.editorValue = initialContent(section);
      await renderTask(state.taskId);
    } else navigate(`#/task/${sid.slice(0,3)}`);
    return;
  }
  const button = event.target.closest("[data-run-experiment]");
  if (!button || button.disabled) return;
  const block = button.closest("[data-experiment-key]");
  const key = block.dataset.experimentKey;
  const output = block.querySelector("[data-experiment-result]");
  const taskId = state.taskId;
  const sectionId = button.dataset.sectionId;
  const mode = button.dataset.mode;
  const index = Number(button.dataset.index);
  const content = block.querySelector("textarea").value;
  experimentDrafts.set(key, content);
  button.disabled = true;
  output.innerHTML = '<p role="status">正在运行这份代码…</p>';
  try {
    const result = await api("POST", `/api/tasks/${encodeURIComponent(taskId)}/sections/${encodeURIComponent(sectionId)}/experiment`, {mode,index,content});
    experimentResults.set(key, result);
    if (output.isConnected) output.innerHTML = renderExperimentResult(result);
  } catch (error) {
    if (output.isConnected) output.innerHTML = `<div class="notice warn">${escapeHtml(error.message)}</div>`;
  } finally { button.disabled = false; }
});

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
    state.currentSection = sectionBtn.dataset.section;
    const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
    state.editorValue = initialContent(section);
    // 切换小节后上一小节的变式题不再适用，立即清除陈旧 id
    state.variationId = null;
    saveSectionPosition(state.currentSection);
    renderTask(state.taskId);
    return;
  }
  const prevBtn = event.target.closest("#prev-section");
  const nextBtn = event.target.closest("#next-section");
  if (prevBtn || nextBtn) {
    const sections = state.task.task.lesson.sections;
    const index = sections.findIndex((s) => s.id === state.currentSection);
    const next = prevBtn ? index - 1 : index + 1;
    if (next >= 0 && next < sections.length) {
      state.currentSection = sections[next].id;
      state.editorValue = initialContent(sections[next]);
      state.variationId = null;
      saveSectionPosition(state.currentSection);
      renderTask(state.taskId);
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
      await runEnvAction(action, { confirmed: true });
    } else {
      await runEnvAction(action);
    }
    return;
  }
  const saveDraft = event.target.closest("[data-save-draft]");
  if (saveDraft) {
    await saveDraftSection();
    return;
  }
  const validate = event.target.closest("[data-validate]");
  if (validate) {
    await validateSection();
    return;
  }
  const reset = event.target.closest("[data-reset]");
  if (reset) {
    resetContent();
    return;
  }
  const markIn = event.target.closest("#mark-inprogress");
  if (markIn) {
    await setTaskStatus("in_progress", "");
    return;
  }
  const markDone = event.target.closest("#mark-done");
  if (markDone) {
    const evidence = $("#done-evidence")?.value?.trim();
    await setTaskStatus("done", evidence);
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
    renderCatalog();
    return;
  }
  const diagnosticRun = event.target.closest("#diagnostic-run");
  if (diagnosticRun) {
    await runDiagnostic();
    return;
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.aiDrawerOpen) {
    event.preventDefault();
    closeAiTutorDrawer();
  }
});

// ---------------------------------------------------------------- 任务操作

async function saveSectionPosition(sectionId) {
  try {
    await api("POST", `/api/tasks/${encodeURIComponent(state.taskId)}/lesson-position`, { section_id: sectionId });
  } catch (_e) {
    // 忽略定位保存失败
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
  const content = readEditor();
  const result = await api("PUT", `/api/tasks/${encodeURIComponent(state.taskId)}/sections/${encodeURIComponent(state.currentSection)}/draft`, { content });
  setResult(`<span class="muted">草稿已保存（${escapeHtml(result.updated_at)}）</span>`, "passed");
}

async function validateSection() {
  const taskId = state.taskId;
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  const kind = section.practice.kind;
  const content = readEditor();
  const button = $("[data-validate]");
  if (button?.disabled) return;
  if (button) button.disabled = true;
  const resultBox = $("#validation-result");
  if (resultBox) resultBox.innerHTML = '<p role="status">正在验证本节作业…</p>';
  try {
    const result = kind === "env_action"
      ? await api("POST", "/api/env/action", { action: section.practice.action })
      : await api("POST", `/api/tasks/${encodeURIComponent(taskId)}/sections/${encodeURIComponent(section.id)}/validate`, { content });
    // Do not show a slow result in a different lesson after navigation.
    if (state.taskId !== taskId || state.currentSection !== section.id) { state.bootstrap = null; return; }
    state.lastValidation = { section_id: section.id, ...result };
    setValidationResult(state.lastValidation, kind);
    if (result.passed) {
      await refreshTaskState();
      state.editorValue = content;
      await renderTask(state.taskId);
    }
  } catch (error) {
    if (state.taskId === taskId && state.currentSection === section.id) {
      setResult(escapeHtml(error.message), "failed");
    }
  } finally { if (button?.isConnected) button.disabled = false; }
}

function resetContent() {
  const section = state.task.task.lesson.sections.find((s) => s.id === state.currentSection);
  state.editorValue = section.practice.starter_content || "";
  const editor = $("#editor");
  if (editor) editor.value = state.editorValue;
}

async function setTaskStatus(status, evidence) {
  try {
    await api("POST", `/api/tasks/${encodeURIComponent(state.taskId)}/status`, { status, evidence });
    const fresh = await api("GET", `/api/tasks/${encodeURIComponent(state.taskId)}`);
    state.task = fresh;
    state.bootstrap = await api("GET", "/api/bootstrap");
    renderTask(state.taskId);
  } catch (error) {
    alert(error.message);
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

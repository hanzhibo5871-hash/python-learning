"use strict";

// Presentational enhancement only: keep the existing editors, result nodes and
// delegated run/validate handlers. No requests, code execution or progress writes.
// renderTask replaces #section-body; a WeakSet makes each new body a one-time
// enhancement and avoids repeated work when only a running result changes.
(() => {
  const enhanced = new WeakSet();

  function enhance(app) {
    const body = app.querySelector("#section-body");
    const selected = app.querySelector(".section-nav [data-section].active");
    if (!body || !selected || enhanced.has(body)) return false;
    const sectionId = selected.dataset.section;
    const teaching = LESSON_TEACHING[sectionId];
    const practice = body.querySelector(".practice-grid");
    if (!teaching || !practice) return false;
    enhanced.add(body);

    const intro = document.createElement("section");
    intro.className = "lesson-intro";
    intro.dataset.teachingSection = sectionId;
    intro.setAttribute("aria-labelledby", "lesson-intro-title");
    const title = document.createElement("h3");
    title.id = "lesson-intro-title";
    title.textContent = "先学这一点";
    intro.append(title);
    const labels = ["用来做什么", "一般用在哪里", "怎么用"];
    teaching.forEach((text, i) => {
      const row = document.createElement("p");
      const label = document.createElement("strong");
      label.textContent = `${labels[i]}：`;
      row.append(label, document.createTextNode(text));
      intro.append(row);
    });
    const brief = body.querySelector(".brief-rules");
    body.insertBefore(intro, brief || practice);

    // Demonstration comes BEFORE tasks, with one complete example visible.
    // Move original nodes rather than cloning them: experiment IDs, draft values,
    // pending output nodes and mode/index routing therefore remain unchanged.
    const examples = body.querySelector(".examples-reference");
    if (examples) {
      examples.open = true;
      const summary = examples.querySelector(":scope > summary");
      if (summary) summary.textContent = "看懂一个完整示例，再开始练习";
      const first = examples.querySelector(".mini-example");
      if (first) first.open = true;
      body.insertBefore(examples, practice);
    }
    const drills = body.querySelector(".drill-section");
    if (drills) {
      const heading = drills.querySelector("h3");
      if (heading) heading.textContent = "先跟着写：补全与改写";
      const first = drills.querySelector(".mini-example");
      if (first) first.open = true;
      body.insertBefore(drills, practice);
    }
    // The exact assignment contract still appears next to the independent task.
    if (brief) body.insertBefore(brief, practice);
    const heading = practice.querySelector(".practice-writing > h3");
    if (heading && heading.textContent === "独立作业") {
      heading.textContent = "最后自己写：独立作业";
    }
    return true;
  }

  const app = document.querySelector("#app");
  if (!app) return;
  const observer = new MutationObserver(() => enhance(app));
  observer.observe(app, {childList: true, subtree: true});
  enhance(app);
})();

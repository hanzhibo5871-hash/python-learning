"""本地编辑器课程的浏览器回归；使用临时学习记录和现有 Node Playwright。"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learnctl import ai
from learnctl.curriculum import load_curriculum
from learnctl.progress import initial_progress, save_progress
from learnctl.web.server import create_server


BROWSER_TEST = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const [base, root, screenshot, packagePath, executable] = process.argv.slice(1);
const {chromium} = require(packagePath);

(async () => {
  const launch = {headless: true, args: ['--no-sandbox']};
  if (executable) launch.executablePath = executable;
  const browser = await chromium.launch(launch);
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    const visit = async taskId => {
      await page.goto(`${base}/#/task/${taskId}`);
      await page.waitForFunction(id => typeof state !== 'undefined' && state.taskId === id
        && document.querySelector('#practice-editor'), taskId);
    };
    const resultContains = text => page.waitForFunction(value =>
      document.querySelector('#validation-result')?.textContent.includes(value), text,
      {timeout: 30000});

    for (const taskId of ['D01', 'D02', 'D03', 'D04', 'D05', 'D06']) {
      await visit(taskId);
      assert.equal(await page.locator('#editor').count(), 1, `${taskId} retains its Web assignment editor`);
      assert.equal(await page.locator('[data-prepare-local]').count(), 0);
    }
    await visit('D07');
    assert.equal(await page.locator('#editor').count(), 0);
    assert.equal(await page.locator('[data-prepare-local]').count(), 1);
    assert.equal(await page.locator('[data-validate]').count(), 1);
    const relative = await page.evaluate(() => state.task.task.lesson.sections
      .find(section => section.id === state.currentSection).local_file);
    assert.equal(relative, 'learner_workspace/lessons/D07/D07-import/main.py');
    assert((await page.locator('#practice-editor').innerText()).includes(relative));
    await page.locator('[data-prepare-local]').click();
    await resultContains('已准备文件');
    const target = path.join(root, relative);
    assert(fs.existsSync(target));
    const correct = 'from pathlib import Path\nimport math\n\ndef show_path(value):\n    return Path(value).suffix, math.sqrt(9)\n';
    fs.writeFileSync(target, correct, 'utf8');
    await page.locator('[data-validate]').click();
    await resultContains('验证通过');
    await page.waitForFunction(() => state.task.task.lesson.completed_sections.includes('D07-import'));
    assert.equal(fs.readFileSync(target, 'utf8'), correct);
    const progress = JSON.parse(fs.readFileSync(path.join(root, '.learn/progress.json'), 'utf8'));
    assert(progress.lesson_progress.D07.completed_sections.includes('D07-import'));
    assert.equal(progress.tasks.D07.status, 'in_progress');

    // 对话必须重新读取编辑器刚保存的磁盘内容，HTTP 拦截阻止真实 AI 调用。
    const latest = correct + '# 对话发送前刚保存的内容\n';
    fs.writeFileSync(target, latest, 'utf8');
    let chatBody;
    await page.route('**/api/ai/chat', async route => {
      chatBody = route.request().postDataJSON();
      await route.fulfill({status: 200, contentType: 'application/json',
        body: JSON.stringify({ok: true, answer: '浏览器测试的离线回复'})});
    });
    await page.locator('#ai-tutor-trigger').click();
    await page.locator('#ai-chat-input').fill('请解释当前代码中的模块导入');
    await page.locator('#ai-chat-send').click();
    await page.waitForFunction(() => document.querySelector('#ai-chat-messages')
      ?.textContent.includes('浏览器测试的离线回复'));
    assert.equal(chatBody.task_id, 'D07');
    assert.equal(chatBody.section_id, 'D07-import');
    assert.equal(chatBody.learner_context.content, latest);
    assert.equal(fs.readFileSync(target, 'utf8'), latest);
    await page.locator('#ai-tutor-close').click();
    await page.locator('#ai-tutor-drawer').waitFor({state: 'hidden'});
    await page.screenshot({path: screenshot, fullPage: true});

    await visit('D12');
    const missingRelative = await page.evaluate(() => state.task.task.lesson.sections
      .find(section => section.id === state.currentSection).local_file);
    assert(!fs.existsSync(path.join(root, missingRelative)));
    chatBody = undefined;
    await page.locator('#ai-tutor-trigger').click();
    await page.locator('#ai-chat-input').fill('还没准备文件，请解释本节应该先做什么');
    await page.locator('#ai-chat-send').click();
    await page.waitForFunction(() => document.querySelector('#ai-chat-messages')
      ?.textContent.includes('浏览器测试的离线回复'));
    assert.equal(chatBody.task_id, 'D12');
    assert.equal(chatBody.section_id, 'D12-request');
    assert.equal(Object.hasOwn(chatBody.learner_context, 'content'), false);
    assert(!fs.existsSync(path.join(root, missingRelative)));
    await page.locator('#ai-tutor-close').click();
    await page.locator('#ai-tutor-drawer').waitFor({state: 'hidden'});

    await visit('D18');
    assert.equal(await page.locator('#editor').count(), 0);
    assert.equal(await page.locator('.examples-reference').getAttribute('open'), null);
    assert.equal(await page.locator('.long-reference').getAttribute('open'), null);
    const projectRelative = await page.evaluate(() => state.task.task.lesson.sections
      .find(section => section.id === state.currentSection).local_file);
    assert.equal(projectRelative, 'learner_workspace/task-manager/docs/requirements.md');
    await page.locator('[data-prepare-local]').click();
    await resultContains('已准备文件');
    const projectFile = path.join(root, projectRelative);
    const existing = '# 浏览器回归使用的项目范围\n';
    fs.writeFileSync(projectFile, existing, 'utf8');
    await page.locator('[data-section="D18-acceptance"]').click();
    await page.waitForFunction(() => state.currentSection === 'D18-acceptance'
      && document.querySelector('#practice-editor')?.textContent.includes('D18-acceptance'));
    assert.equal(await page.evaluate(() => state.task.task.lesson.sections
      .find(section => section.id === state.currentSection).local_file), projectRelative);
    await page.locator('[data-prepare-local]').click();
    await resultContains('已保留现有文件');
    assert.equal(fs.readFileSync(projectFile, 'utf8'), existing);
    assert.equal(await page.locator('.examples-reference').getAttribute('open'), null);
    assert.deepEqual(errors, []);
    console.log('PASS: D01-D06 Web editor; D07 disk prepare/check/completion; fresh AI chat content; unprepared lesson chat; D18 continuous file; folded examples; no JS errors');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="已有 Node 可执行文件")
    parser.add_argument("--playwright", type=Path, required=True, help="已有 Node playwright 包的绝对路径")
    parser.add_argument("--executable", type=Path, help="已有 Chromium 可执行文件")
    parser.add_argument("--screenshot", type=Path, default=ROOT / "browser-editor.png")
    args = parser.parse_args()
    temporary_root = ROOT / ".test-tmp"
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="editor-browser-", dir=temporary_root) as directory:
        root = Path(directory)
        (root / "data").mkdir()
        shutil.copyfile(ROOT / "data/curriculum.json", root / "data/curriculum.json")
        curriculum = load_curriculum(root / "data/curriculum.json")
        progress = initial_progress(curriculum)
        # 所有门禁证据都只属于这个临时工作区；不读取学习者真实进度。
        progress["tasks"] = {task["id"]: {"status": "done", "evidence": ["browser fixture"]}
                             for task in curriculum["tasks"]}
        for task_id in ("D07", "D18"):
            progress["tasks"][task_id]["status"] = "in_progress"
        progress["lesson_progress"]["D18"]["completed_sections"] = ["D18-scope"]
        save_progress(root / ".learn/progress.json", progress)
        server = create_server(root, port=0)
        server.ai_session.get_key = lambda: server.ai_session._key
        original_request = ai._request

        def reject_live_ai(*args, **kwargs):
            raise RuntimeError("浏览器回归禁止真实 AI 请求")

        ai._request = reject_live_ai
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run([
                args.node, "-e", BROWSER_TEST,
                f"http://127.0.0.1:{server.server_port}", str(root), str(args.screenshot.resolve()),
                str(args.playwright.resolve()), str(args.executable.resolve()) if args.executable else "",
            ], cwd=ROOT, timeout=120)
            if result.returncode:
                raise SystemExit(result.returncode)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            ai._request = original_request


if __name__ == "__main__":
    main()

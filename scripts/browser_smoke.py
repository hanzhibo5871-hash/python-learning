"""Browser regression for the practice-first UI, using only a temporary workspace.

Run after installing Playwright and its Chromium: python scripts/browser_smoke.py.
--bridge is a local test adapter for environments that prohibit browser loopback
navigation. It still calls the real HTTP server, through Python's HTTP client.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learnctl.curriculum import load_curriculum
from learnctl.progress import initial_progress, save_progress
from learnctl.web.server import create_server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge', action='store_true')
    parser.add_argument('--executable')
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    from playwright.sync_api import expect, sync_playwright
    with tempfile.TemporaryDirectory(prefix='learnctl-browser-test-') as directory:
        root = Path(directory)
        (root / 'data').mkdir()
        shutil.copy(ROOT / 'data/curriculum.json', root / 'data/curriculum.json')
        curriculum = load_curriculum(root / 'data/curriculum.json')
        state = initial_progress(curriculum)
        for task in curriculum['tasks'][:3]:
            state['tasks'][task['id']] = {'status': 'done', 'evidence': ['browser test fixture']}
            state['lesson_progress'][task['id']]['completed_sections'] = [s['id'] for s in task['lesson']]
        save_progress(root / '.learn/progress.json', state)
        server = create_server(root, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as playwright:
                launch = {'headless': True, 'args': ['--no-sandbox']}
                if args.executable:
                    launch['executable_path'] = args.executable
                browser = playwright.chromium.launch(**launch)
                page = browser.new_page(viewport={'width': 1440, 'height': 1050})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                if args.bridge:
                    def bridge(path, options):
                        if not isinstance(path, str) or not path.startswith('/api/'):
                            raise ValueError('Only the local test API is available')
                        raw = options.get('body')
                        req = urllib.request.Request(base + path,
                            data=raw.encode('utf-8') if raw is not None else None,
                            method=options.get('method', 'GET'),
                            headers={'Content-Type': 'application/json', 'Origin': base})
                        try:
                            response = urllib.request.urlopen(req, timeout=60)
                        except urllib.error.HTTPError as error:
                            response = error
                        with response:
                            return {'status': response.status, 'body': json.loads(response.read())}
                    page.expose_function('localTestRequest', bridge)
                    html = (ROOT / 'learnctl/web/static/index.html').read_text(encoding='utf-8')
                    html = html.replace('<link rel="stylesheet" href="/static/styles.css">', '')
                    html = html.replace('<script src="/static/app.js"></script>', '')
                    page.set_content(html)
                    page.add_style_tag(content=(ROOT / 'learnctl/web/static/styles.css').read_text(encoding='utf-8'))
                    page.evaluate("""() => {
                        window.location.hash = '#/task/D04';
                        window.fetch = async (path, options={}) => {
                            const result = await window.localTestRequest(path, options);
                            return {ok:result.status>=200 && result.status<300,
                                    status:result.status, json:async()=>result.body};
                        };
                    }""")
                    page.add_script_tag(content=(ROOT / 'learnctl/web/static/app.js').read_text(encoding='utf-8'))
                else:
                    page.goto(base + '/#/task/D04')
                page.locator('#editor').wait_for()
                wrong = 'def rectangle_area(width, height):\n    return 0\n'
                page.locator('#editor').fill(wrong)
                page.locator('[data-validate]').click()
                expect(page.locator("#validation-result")).to_contain_text("验证未通过", timeout=30000)
                assert '12' in page.locator('#validation-result').inner_text()
                assert page.locator('#editor').input_value() == wrong
                page.locator('[data-run-experiment]').first.click()
                expect(page.locator("[data-experiment-result]").first).to_contain_text("输出符合预期", timeout=30000)
                assert page.locator('#editor').input_value() == wrong
                if args.screenshots:
                    args.screenshots.mkdir(parents=True, exist_ok=True)
                    page.locator('.practice-grid').screenshot(path=str(args.screenshots / 'output-comparison.png'))
                    page.screenshot(path=str(args.screenshots / 'desktop.png'), full_page=True)
                correct = 'def rectangle_area(width, height):\n    return width * height\n'
                page.locator('#editor').fill(correct)
                page.locator('[data-validate]').click()
                expect(page.locator("#validation-result")).to_contain_text("验证通过", timeout=30000)
                # Refresh task data from the server without changing the code buffer.
                page.evaluate('async () => { await refreshTaskState(); await renderTask("D04"); }')
                assert page.locator('#editor').input_value() == correct
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth + 2')
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / 'mobile.png'), full_page=True)
                assert not errors, errors
                browser.close()
            print('PASS: wrong/correct output, isolated experiment, saved solution, mobile width, no JS errors')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    main()

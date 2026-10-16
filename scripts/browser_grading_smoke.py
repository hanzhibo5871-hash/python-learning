"""Real UI + real local validators; provider transport is mocked, no paid API."""
import json
import threading
from unittest.mock import patch

from learnctl import ai


def assert_ai_grading(page, expect, server):
    calls = []
    entered, release = threading.Event(), threading.Event()
    release.set()
    mode = "wrong"
    variation = {"title":"独立变式", "scenario":"练习函数", "instructions":"按本题规则实现函数", "starter_content":"def variant(value):\n    pass", "review_rubric":"核对输入和返回行为"}

    def provider(url, payload, api_key, timeout=60):
        nonlocal mode
        assert api_key == "browser-test-only"
        calls.append(payload)
        entered.set()
        assert release.wait(15), "test must release response"
        if mode == "http":
            return 429, b"{}"
        if "judgement" not in payload["messages"][0]["content"]:
            response = variation
        else:
            data = json.loads(payload["messages"][-1]["content"])
            local = data["local_evidence"].get("passed")
            passed = mode == "conflict" or local is True
            title = data["lesson"].get("title", "当前练习")
            refs = [f"submission:{min(2,len(data['submission'].splitlines()))}"]
            response = {"judgement":"passed" if passed else "needs_work", "requirements":[
                {"id":r["id"],"requirement":("函数接口与返回行为符合当前题意" if index == 0 else "遵守本课输入范围与能力边界"),
                 "status":"met" if passed or (index > 0 and local is False) else "unmet" if local is False else "uncertain",
                 "explanation":("当前提交返回固定值，未满足当前题目的返回行为要求。" if not passed and index == 0 else "当前代码没有添加本题未要求的限制。" if not passed else "本项已对照当前代码和真实结果核查。"), "evidence":refs}
                for index,r in enumerate(data["requirements"])], "issues":[] if passed else [{
                "requirement_ids":[data["requirements"][0]["id"]],
                "cause":f"{title}：结果没有随输入变化，请核对本题规定的参数与返回关系。", "evidence":refs,
                "hints":["比较本题两组输入时，实际结果是否跟着变化？", "追踪当前输入，在哪一步停止影响返回值？", "对照本题的失败用例，返回位置是否仍然使用固定值？"]}], "limitations":[]}
        if mode == "snippet":
            response["issues"][0]["cause"] = "正确代码是 return width * height"
        if mode == "html":
            response["issues"][0]["cause"] = '引用 <img src=x onerror="window.__gradingXss=1"><script>window.__gradingXss=2</script>仅为文本。'
        if mode == "secret":
            response["issues"][0]["cause"] = "核对 browser-test-only；Bearer abc-private；api_key=another-private"
        if mode == "compat":
            response["issues"][0]["cause"] = "`rectangle_area(width, height)` 的 `return` 语句只提供固定结果。\n当前输入未影响返回值。"
            response["issues"][0]["hints"][0] = "检查当前输入是否进入 return 语句。"
        if mode == "missing":
            response["requirements"].pop()
        return 200, json.dumps({"choices":[{"message":{"content":json.dumps(response)}}]}).encode()

    page.evaluate('() => { closeAiTutorDrawer(); navigate("#/task/D04"); }')
    page.locator('#editor').wait_for()
    page.wait_for_function('() => state.taskId === "D04"')
    page.locator('[data-section="D04-def-return"]').click()
    main = page.locator('[data-grading-key="main:D04/D04-def-return"]')
    server.ai_session.set_key("browser-test-only")
    page.evaluate('() => loadAiStatus()')
    with patch.object(ai, '_request', provider):
        try:
            wrong = 'def rectangle_area(width, height):\n    return 0\n'
            page.locator('#editor').fill(wrong)
            before = len(calls)
            page.evaluate('() => { void validateSection(); void validateSection(); }')
            expect(main).to_contain_text('结果没有随输入变化')
            assert len(calls) == before + 1
            assert 'width * height' not in main.inner_text()
            expect(main).to_contain_text('main.py 第 2 行')
            expect(main).to_contain_text('题目要求核对')
            expect(main.locator('[data-analysis-version]')).to_have_attribute('data-analysis-version', '2')
            main.locator('.grading-issue .grading-evidence').first.locator('summary').click()
            expect(main.locator('.grading-issue .grading-evidence').first).to_contain_text('return 0')
            expect(main.locator('[data-requirement-status]').first).to_be_visible()
            assert main.locator('[data-requirement-status]').count() == len(json.loads(calls[-1]['messages'][-1]['content'])['requirements'])
            first_hint = main.inner_text()
            main.locator('[data-grade-hint]').click()
            expect(main).to_contain_text('提示 2/3')
            assert main.inner_text() != first_hint
            main.locator('[data-grade-hint]').click()
            expect(main).to_contain_text('提示 3/3')
            assert len(calls) == before + 1

            # AI may be wrong, but local failure stays authoritative.
            mode = 'conflict'
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('以本地验证为准')
            expect(page.locator('#validation-result')).to_contain_text('验证未通过')

            # Network failure retries once. Teaching snippets are usable text.
            mode = 'http'
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('HTTP 429')
            mode = 'snippet'
            main.locator('[data-grade-retry]').click()
            expect(main).to_contain_text('return width * height')
            assert 'grading_safety' not in main.inner_text()
            expect(main.locator('[data-grade-retry]')).to_have_count(0)
            mode = 'html'
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('<img src=x')
            assert main.locator('img, script').count() == 0
            assert page.evaluate('() => window.__gradingXss') is None
            mode = 'secret'
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('已隐藏')
            assert all(value not in main.inner_text() for value in ['browser-test-only','abc-private','another-private'])
            mode = 'compat'
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('rectangle_area(width, height)')
            expect(main).to_contain_text('检查当前输入是否进入 return 语句。')
            assert 'width * height' not in main.inner_text()
            mode = 'missing'
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('AI 未分析这一项要求')
            expect(main.locator('[data-requirement-status="uncertain"]')).to_have_count(1)
            assert main.locator('[data-requirement-status]').count() == 2
            mode = 'wrong'

            # Modifying during a response invalidates and aborts its display.
            release.clear(); entered.clear()
            page.locator('[data-validate]').click()
            assert entered.wait(5)
            page.locator('#editor').fill(wrong + '# changed')
            expect(main).to_contain_text('提交已修改')
            release.set()
            page.wait_for_timeout(250)
            expect(main).to_contain_text('提交已修改')
            assert 'AI 当前作业解析' not in main.inner_text()

            # A slow deterministic run must not overwrite newly typed content.
            import learnctl.web.server as web
            local_entered, local_release = threading.Event(), threading.Event()
            original_validation = web.run_validation
            def slow_validation(*args):
                local_entered.set()
                assert local_release.wait(10)
                return original_validation(*args)
            before = len(calls)
            with patch.object(web, 'run_validation', slow_validation):
                page.locator('[data-validate]').click()
                assert local_entered.wait(5)
                page.locator('#editor').fill(wrong + '# typed during local run')
                local_release.set()
                page.wait_for_function('() => localGradingPending.size === 0')
            assert page.locator('#editor').input_value().endswith('# typed during local run')
            expect(page.locator('#validation-result')).to_contain_text('提交已修改')
            assert len(calls) == before

            # Exercise the browser timeout without waiting 65 seconds.
            release.clear(); entered.clear()
            page.evaluate("""() => {
                window.gradingTestTimeout = window.setTimeout;
                window.setTimeout = (fn, ms, ...args) => window.gradingTestTimeout(fn, ms === 65000 ? 250 : ms, ...args);
            }""")
            page.locator('[data-validate]').click()
            assert entered.wait(5)
            expect(main).to_contain_text('AI 判题超时')
            release.set()
            page.evaluate('() => { window.setTimeout = window.gradingTestTimeout; delete window.gradingTestTimeout; }')
            page.wait_for_timeout(300)
            main.locator('[data-grade-retry]').click()
            expect(main).to_contain_text('结果没有随输入变化')

            # Next-section navigation cancels reception, including returning back.
            release.clear(); entered.clear()
            page.locator('[data-validate]').click()
            assert entered.wait(5)
            page.locator('#next-section').first.click()
            page.wait_for_function('() => state.currentSection !== "D04-def-return"')
            release.set()
            page.locator('[data-section="D04-def-return"]').click()
            expect(main).to_contain_text('已取消')
            assert '结果没有随输入变化' not in main.inner_text()

            # All completion drills share the real experiment path and own editor.
            drill = page.locator('.drill-section .mini-example').first
            drill.locator('summary').click() if drill.get_attribute('open') is None else None
            drill.locator('[data-run-experiment]').click()
            expect(drill.locator('[data-grading-key]')).to_contain_text('AI 当前作业解析')
            assert calls[-1]['messages'][-1]['role'] == 'user'
            assert json.loads(calls[-1]['messages'][-1]['content'])['lesson']['exercise']['mode'] == 'drill'
            assert page.locator('#editor').input_value().startswith('def rectangle_area')

            # Correctness is concise; no standard answer is appended.
            correct = 'def rectangle_area(width, height):\n    return width * height\n'
            page.locator('#editor').fill(correct)
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('AI 未发现明显问题')
            assert 'width * height' not in main.inner_text()

            # Independent variation answer never uses the main editor.
            page.locator('#ai-tutor-trigger').click()
            page.locator('#ai-generate').click()
            expect(page.locator('#variation-editor')).to_be_visible()
            page.locator('#variation-editor').fill('def variant(value):\n    pass')
            page.locator('#variation-submit').click()
            variation_box = page.locator('#ai-result [data-grading-key]')
            expect(variation_box).to_contain_text('暂无本地行为测试')
            data = json.loads(calls[-1]['messages'][-1]['content'])
            assert data['submission'] == 'def variant(value):\n    pass'
            assert data['lesson']['exercise']['title'] == '独立变式'
            assert page.locator('#editor').input_value() == correct
            page.locator('#ai-tutor-close').click()

            # Unconfigured never invokes a model and can be retried after setup.
            server.ai_session.clear_key()
            page.evaluate('() => loadAiStatus()')
            before = len(calls)
            page.locator('#editor').fill(wrong)
            page.locator('[data-validate]').click()
            expect(main).to_contain_text('AI 未配置')
            assert len(calls) == before
            server.ai_session.set_key('browser-test-only')
            main.locator('[data-grade-retry]').click()
            expect(main).to_contain_text('结果没有随输入变化')
            assert 'browser-test-only' not in page.locator('body').inner_text()
        finally:
            release.set()
            server.ai_session.clear_key()
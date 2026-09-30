"""Exercise real chat UI/API with mocked provider transport; no key or network."""
import json
import threading
from unittest.mock import patch

from learnctl import ai


def assert_tutor_chat(page, expect, server):
    calls = []
    entered = threading.Event()
    release = threading.Event()
    release.set()
    fail_next = False

    def provider(url, payload, api_key, timeout=60):
        nonlocal fail_next
        assert api_key == 'browser-test-only'
        calls.append(payload)
        number = len(calls)
        entered.set()
        assert release.wait(10), 'test did not release the pending response'
        if fail_next:
            fail_next = False
            return 429, b'{"error":{"message":"test rate limit"}}'
        return 200, json.dumps({'choices': [{'message': {'content': f'简短答复 {number}'}}]}).encode()

    server.ai_session.set_key('browser-test-only')
    with patch.object(ai, '_request', provider):
        try:
            page.locator('#ai-tutor-trigger').click()
            for i in range(4):
                page.locator('#ai-chat-input').fill(f'问题 {i}')
                page.locator('#ai-chat-send').click()
                expect(page.locator('#ai-chat-messages')).to_contain_text(f'简短答复 {i + 1}')
                messages = calls[-1]['messages']
                assert len(messages[1:-1]) == min(i, 3) * 2
                assert messages[-1]['content'].startswith(f'问题 {i}\n')
                assert 'rectangle_area' in messages[-1]['content']
                assert 'D04-def-return' in messages[0]['content']
                assert all(m['content'] != f'问题 {i}' for m in messages[1:-1])
            assert [m['role'] for m in calls[-1]['messages'][1:]] == ['user', 'assistant'] * 3 + ['user']
            assert page.evaluate('() => currentAiMessages().length') == 6

            # Failure leaves the input and successful history intact; retry sends
            # the same request once, even if send is invoked twice in one tick.
            fail_next = True
            page.locator('#ai-chat-input').fill('重试问题')
            page.locator('#ai-chat-send').click()
            expect(page.locator('#ai-chat-error')).to_contain_text('HTTP 429')
            expect(page.locator('#ai-chat-input')).to_have_value('重试问题')
            before = len(calls)
            page.evaluate('() => { void sendTutorQuestion(); void sendTutorQuestion(); }')
            expect(page.locator('#ai-chat-messages')).to_contain_text(f'简短答复 {before + 1}')
            assert len(calls) == before + 1
            assert calls[-1] == calls[-2]

            # A response for the previous lesson must not appear in the new one.
            release.clear()
            entered.clear()
            page.locator('#ai-chat-input').fill('切换前的问题')
            page.locator('#ai-chat-send').click()
            assert entered.wait(5)
            page.wait_for_function('() => currentAiChatBusy()')
            page.evaluate('() => navigate("#/task/D12")')
            expect(page.locator('.lesson-intro')).to_contain_text('用来做什么')
            page.wait_for_function('() => state.taskId === "D12" && state.currentSection.startsWith("D12-")')
            assert page.evaluate('() => currentAiMessages().length') == 0
            release.set()
            page.wait_for_function('() => state.aiChatPending["D04:D04-def-return"] === undefined')
            assert page.evaluate('() => currentAiMessages().length') == 0
            page.evaluate('() => openAiTutorDrawer()')
            page.locator('#ai-chat-input').fill('新课问题')
            before = len(calls)
            page.locator('#ai-chat-send').click()
            expect(page.locator('#ai-chat-messages')).to_contain_text(f'简短答复 {before + 1}')
            assert len(calls[-1]['messages']) == 2
            assert 'D12-request' in calls[-1]['messages'][0]['content']
            assert 'D04-def-return' not in calls[-1]['messages'][-1]['content']

            # Clear also invalidates the first in-flight response of a new session.
            page.locator('#ai-chat-clear').click()
            release.clear()
            entered.clear()
            page.locator('#ai-chat-input').fill('稍后丢弃的问题')
            page.locator('#ai-chat-send').click()
            assert entered.wait(5)
            page.wait_for_function('() => currentAiChatBusy()')
            page.locator('#ai-chat-clear').click()
            release.set()
            expect(page.locator('#ai-chat-messages')).to_contain_text('还没有对话')
            page.locator('#ai-chat-input').fill('新的会话')
            before = len(calls)
            page.locator('#ai-chat-send').click()
            expect(page.locator('#ai-chat-messages')).to_contain_text(f'简短答复 {before + 1}')
            assert len(calls[-1]['messages']) == 2
            assert page.evaluate('() => currentAiMessages().length') == 2
            assert page.locator('#ai-chat-messages .ai-message').count() == 2
            assert 'browser-test-only' not in json.dumps(calls)
        finally:
            release.set()
            server.ai_session.clear_key()

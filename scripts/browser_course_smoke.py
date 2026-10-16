"""Read-only full course UI audit on browser_smoke's disposable server."""
from learnctl.curriculum import load_curriculum
from browser_smoke import ROOT, assert_teaching


def assert_course_readiness(page, expect, screenshots=None):
    course = load_curriculum(ROOT / "data/curriculum.json")
    reviewed = 0
    for task in course['tasks']:
        if task['id'] < 'D05':
            continue
        page.evaluate('(id) => navigate(`#/task/${id}`)', task['id'])
        for section in task['lesson']:
            page.locator(f'[data-section="{section["id"]}"]').click()
            expect(page.locator('.lesson-intro')).to_have_attribute('data-teaching-section', section['id'])
            assert_teaching(page, expect, task['id'])
            assert ' '.join(section['syntax'].split()) in ' '.join(page.locator('.lesson-intro').inner_text().split())
            expect(page.locator('.examples-reference summary').filter(has_text='为什么是这个结果').first).to_be_attached()
            for width in (1440, 390):
                page.set_viewport_size({'width': width, 'height': 1000})
                assert page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth + 2'), section['id']
            reviewed += 1
    page.evaluate('() => navigate("#/task/D05")')
    page.locator('[data-section="D05-list-tuple"]').click()
    for name in ('len', 'raise', 'ValueError', 'tuple'):
        assert name in page.locator('[data-run-experiment][data-mode="card"]').evaluate_all('(buttons) => buttons.map(button => button.closest(".mini-example").innerText).join("\\n")')
    if screenshots:
        page.set_viewport_size({'width':1440,'height':1050})
        page.screenshot(path=str(screenshots / 'd05-before-practice.png'), full_page=True)
        page.evaluate('() => navigate("#/task/D29")')
        page.locator('[data-section="D29-tools"]').click()
        page.screenshot(path=str(screenshots / 'agent-tools.png'), full_page=True)
    return reviewed

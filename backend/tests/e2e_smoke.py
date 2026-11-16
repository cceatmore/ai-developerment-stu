"""浏览器冒烟测试：用真实课程内容走一遍 Day 1（讲解 → 测试 → 面试题 → 总结），并截图主要页面。

用法（会用独立的 data-smoke 目录，不影响真实学习记录）：
    set STUPY_DATA_DIR=..\\data-smoke & set STUPY_PORT=8770 & uv run python -m app.main
    uv run --with playwright python tests/e2e_smoke.py
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE = os.getenv("SMOKE_BASE", "http://127.0.0.1:8770")
SHOTS = Path(__file__).resolve().parent / "_shots"
SHOTS.mkdir(exist_ok=True)


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False)


def answer_session(page: Page, sid: int, wrong_first: bool = False) -> None:
    s = page.request.get(f"{BASE}/api/sessions/{sid}").json()
    for n, q in enumerate(s["questions"]):
        full = page.request.get(f"{BASE}/api/questions/{q['id']}").json()
        page.locator(".qnav button").nth(n).click()
        card = page.locator(".qcard")
        if full["type"] == "judge":
            want = full["answer"] if not (wrong_first and n == 0) else not full["answer"]
            card.get_by_role("button", name="✓ 正确" if want else "✗ 错误").click()
        else:
            idx = full["answer"] if not (wrong_first and n == 0) else [i for i in range(len(full["options"])) if i not in full["answer"]][:1]
            for i in idx:
                card.locator(".opt").nth(i).click()
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="交卷").click()


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1366, "height": 860})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(BASE + "/")
        expect(page.locator(".hero .title")).not_to_be_empty()
        shot(page, "01-dashboard")
        page.locator(".hero .btn.primary").click()
        expect(page.locator("h1")).to_be_visible()

        # 讲解
        page.locator(".stepper .step").nth(1).click()
        shot(page, "02-lesson")
        while True:
            btn = page.locator(".pager .btn.primary")
            label = btn.inner_text()
            btn.click()
            if "当天测试" in label:
                break
            page.wait_for_timeout(300)

        # 当天测试：第 1 题故意答错，看错题和解析
        page.get_by_role("button", name="开始测试").click()
        expect(page.locator(".qcard")).to_be_visible()
        shot(page, "03-test")
        sid = page.request.get(f"{BASE}/api/days/1").json()["state"]["pending_test"]
        answer_session(page, sid, wrong_first=True)
        expect(page.locator(".bigscore")).to_be_visible()
        expect(page.locator("text=已通过").first).to_be_visible()
        shot(page, "04-test-result")

        # 面试题
        page.get_by_role("button", name="去做面试题 →").click()
        page.locator("textarea.answer").fill("先说结论，再讲原理和在项目里的做法。")
        page.get_by_role("button", name="写好了，对照要点自评").click()
        for seg in page.locator(".kpcheck .seg").all():
            seg.locator("button").last.click()
        page.get_by_role("button", name="确认自评").click()
        expect(page.locator(".verdict")).to_be_visible()
        shot(page, "05-interview")

        page.locator(".stepper .step").nth(4).click()
        expect(page.locator("text=总结 ·").first).to_be_visible()
        shot(page, "06-summary")

        for path, name in [("/", "07-dashboard-after"), ("/review", "08-review"), ("/exams", "09-exams"),
                           ("/projects/p1", "10-projects"), ("/mock", "11-mock"), ("/reports", "12-reports"),
                           ("/day/2", "13-day2")]:
            page.goto(BASE + path)
            page.wait_for_timeout(600)
            shot(page, name)

        browser.close()
        if errors:
            print("页面报错：", *errors, sep="\n")
            return 1
        print("冒烟测试通过，截图在", SHOTS)
        return 0


if __name__ == "__main__":
    sys.exit(main())

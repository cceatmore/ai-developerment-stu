"""校验课程内容。

用法（在 backend 目录下）：
    uv run python -m app.validate              # 校验全部
    uv run python -m app.validate 5 6 7        # 只校验 Day 05~07
    uv run python -m app.validate p1           # 只校验项目 p1
"""

from __future__ import annotations

import re
import sys
from collections import Counter

from .config import settings
from .content import ContentError, load_course, load_day, load_project
from .content_schema import TOTAL_DAYS, Day

MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)
MERMAID_OK = re.compile(r"^(flowchart|graph|sequenceDiagram|stateDiagram-v2|classDiagram|erDiagram)\b")


def _mermaid_count(text: str | None, where: str, warns: list[str]) -> int:
    blocks = MERMAID_RE.findall(text or "")
    for block in blocks:
        first = block.strip().splitlines()[0] if block.strip() else ""
        if not MERMAID_OK.match(first):
            warns.append(f"{where}: mermaid 图类型不在白名单内：{first!r}")
    return len(blocks)


def day_warnings(d: Day) -> list[str]:
    """不阻断加载、但应该修正的质量问题。"""
    warns: list[str] = []
    diagrams = 0
    for k in d.knowledge_points:
        for f in ("principle", "scenarios", "code", "pitfalls", "project_example"):
            diagrams += _mermaid_count(getattr(k, f), k.id, warns)
    if diagrams < 2:
        warns.append(f"Day {d.day}: 只有 {diagrams} 张图，至少 2 张")

    singles = [q.answer[0] for q in d.test + d.exam if q.type in ("single", "case")]
    if singles:
        pos, n = Counter(singles).most_common(1)[0]
        if n / len(singles) > 0.45:
            warns.append(f"Day {d.day}: 单选题答案过于集中在选项 {pos}（{n}/{len(singles)}）")
    for q in d.test + d.exam:
        if q.type in ("single", "case") and q.options:
            lens = [len(o) for o in q.options]
            if lens[q.answer[0]] == max(lens) and max(lens) > 1.6 * sorted(lens)[-2]:
                warns.append(f"{q.id}: 正确选项明显比其他选项长，容易被猜中")

    test_q = {q.question.strip() for q in d.test}
    for q in d.exam:
        if q.question.strip() in test_q:
            warns.append(f"{q.id}: 与 test 中的题目重复")
    for r in d.resources:
        if not r.url.startswith(("http://", "https://")):
            warns.append(f"Day {d.day}: 资源链接格式不对 {r.url}")
    return warns


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if argv:
        ok = True
        for a in argv:
            try:
                if a.startswith("p"):
                    p = load_project(settings.content_dir / "projects" / f"{a}.yaml")
                    print(f"OK  {a}.yaml: {len(p.modules)} 模块, {len(p.deep_dive)} 深挖题")
                    continue
                path = settings.content_dir / "days" / f"day{int(a):02d}.yaml"
                d = load_day(path)
                print(f"OK  {path.name}: {len(d.knowledge_points)} 知识点, 测试 {len(d.test)}, 卷 {len(d.exam)}, 面试 {len(d.interview)}")
                for w in day_warnings(d):
                    print("WARN", w)
            except (ContentError, FileNotFoundError) as e:
                ok = False
                print(f"ERR {e}")
        return 0 if ok else 1

    c = load_course(settings.content_dir)
    for e in c.errors:
        print("ERR", e)
    for d in c.days.values():
        for w in day_warnings(d):
            print("WARN", w)
    missing = sorted(set(range(1, TOTAL_DAYS + 1)) - set(c.days))
    print(f"天数 {len(c.days)}/{TOTAL_DAYS}  知识点 {len(c.kps)}  题目 {len(c.questions)}")
    print(f"项目 {sorted(c.projects)}  模块 {len(c.modules)}")
    if missing:
        print("缺少天数:", missing)
    return 1 if c.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""学习报告：每日总结、模拟面试报告、最终能力报告。

所有结论只基于作答记录计算，不做任何「鼓励性」加分。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from .content import Course
from .content_schema import CATEGORY_LABELS, OBJECTIVE, PASS_SCORE, PHASES, TOTAL_DAYS
from .learning import LEVEL_NAMES, get_kp, latest_attempts
from .models import Attempt, DayProgress, KpProgress, MockSession, ProjectProgress, QuizSession, WrongItem

PHASE_GOALS = {
    1: ["能对照 JS/TS 读懂常见 Python 代码", "能解释 async/await 与并发选择", "能看懂一个 FastAPI 接口的完整链路",
        "能解释事务、索引、缓存与任务队列", "能用 Docker Compose 跑起后端依赖"],
    2: ["能讲清大模型工作原理与能力边界", "能解释 Token、上下文窗口与成本", "能讲清一次 LLM API 调用（含流式与错误处理）",
        "能用结构化输出和 Function Calling 做可靠调用", "能说明上下文工程的基本做法"],
    3: ["能从零讲清 RAG 完整流程", "能比较切片与检索策略并说明取舍", "能分析检索不准与幻觉的原因",
        "能用评测指标证明 RAG 效果", "能设计带权限隔离的企业知识库"],
    4: ["能手写并解释 Agent 循环", "能设计可靠的工具（校验、超时、幂等）", "能解释 LangGraph 的状态、断点与人工审批",
        "能讲清 MCP 的架构与用途", "能判断何时用多 Agent、何时不用", "能讲清 Agent 运行时（Harness）的组成"],
    5: ["能为 AI 应用设计评测集与回归门禁", "能用 Trace 定位 Agent 问题", "能讲清 Prompt Injection 与工具权限防护",
        "能做鉴权、多租户、性能与成本设计", "能完整讲解一个项目并应对深挖"],
}

SELF_ASSESS_NOTE = (
    "面试题分数来自你对照评分要点的自评，通常偏乐观；"
    "拿不准时用「复制给 AI 评审」做一次外部校准。选择题分数是系统判分。"
)


def _avg(xs) -> float | None:
    xs = list(xs)
    return round(mean(xs), 1) if xs else None


def _excerpt(text: str, n: int = 60) -> str:
    t = " ".join(text.split())
    return t if len(t) <= n else t[:n] + "…"


# ---------- 每日总结（当天测试通过时生成） ----------


def build_daily_report(db: Session, course: Course, day: int, s: QuizSession) -> dict:
    d = course.days[day]
    prog = db.get(DayProgress, day)
    kps = []
    for k in d.knowledge_points:
        row = get_kp(db, k.id)
        kps.append({"id": k.id, "name": k.name, "level": k.level, "mastery": row.level,
                    "mastery_name": LEVEL_NAMES[row.level],
                    "next_review": row.next_review.isoformat() if row.next_review else None})
    items = (s.result or {}).get("items", {})
    wrong = [{"question_id": qid, "text": _excerpt(course.questions[qid].question), "score": it["score"]}
             for qid, it in items.items() if it["score"] < 100]
    test_kp = {k["id"]: k["avg"] for k in (s.result or {}).get("kps", [])}
    iv = latest_attempts(db, [q.id for q in d.interview], "interview")
    nxt = course.days.get(day + 1)
    return {
        "day": day,
        "title": d.title,
        "test_score": s.score,
        "tests_taken": prog.tests_taken if prog else 1,
        "kps": [k | {"test_avg": test_kp.get(k["id"])} for k in kps],
        "weak": [k["name"] for k in kps if (test_kp.get(k["id"]) or 0) < 70],
        "wrong": wrong,
        "interview_done": len(iv),
        "interview_total": len(d.interview),
        "minutes": round(sum((prog.stage_seconds or {}).values()) / 60) if prog else 0,
        "tomorrow": {"day": day + 1, "title": nxt.title, "goals": nxt.goals} if nxt else None,
        "exam_next": day % 10 == 0,
        "projects": [{"id": m.id, "name": m.name, "minutes": m.minutes} for m in course.modules_for_day(day)],
    }


# ---------- 模拟面试 ----------


def build_mock_report(db: Session, course: Course, s: MockSession) -> dict:
    atts = db.scalars(select(Attempt).where(Attempt.session_id == s.id, Attempt.context == "mock")
                      .order_by(Attempt.id)).all()
    latest = {a.question_id: a for a in atts}
    answered = list(latest.values())
    by_cat: dict[str, list[float]] = defaultdict(list)
    for a in answered:
        by_cat[a.category].append(a.score)
    expr = [a.expression for a in answered if a.expression]
    weak = []
    for a in answered:
        if a.score < 70:
            q = course.questions[a.question_id]
            weak.append({"question": _excerpt(q.question), "score": a.score,
                         "name": course.kps[q.kp].name if q.kp in course.kps else None,
                         "day": course.question_day.get(a.question_id)})
    overall = _avg(a.score for a in answered)
    return {
        "mode": s.mode,
        "total": len(s.question_ids),
        "answered": len(answered),
        "overall": overall,
        "categories": {CATEGORY_LABELS[c]: _avg(v) for c, v in by_cat.items()},
        "expression": round(mean(expr) * 20, 1) if expr else None,
        "weak": weak,
        "verdict": _verdict(overall, len(answered), len(s.question_ids)),
        "note": SELF_ASSESS_NOTE,
    }


def _verdict(overall: float | None, answered: int, total: int) -> str:
    if overall is None:
        return "没有作答，无法评估。"
    tail = "" if answered == total else f"（只完成了 {answered}/{total} 题，结论仅供参考）"
    if overall >= 85:
        return "表现扎实：大部分题目能讲清原理并结合工程实践。" + tail
    if overall >= 70:
        return "基本达标：核心概念正确，但部分题目缺少原理深度或工程细节。" + tail
    if overall >= 50:
        return "未达标：能说出部分概念，但原理和工程思维明显不足，需要回到对应天数复习。" + tail
    return "差距较大：多数题目没有答到关键点，建议先完成相关天数的复习再来模拟。" + tail


def phase_mastery(db: Session, course: Course, phase: int) -> dict:
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress))}
    kps = []
    for day in range((phase - 1) * 10 + 1, phase * 10 + 1):
        d = course.days.get(day)
        if not d:
            continue
        for k in d.knowledge_points:
            r = rows.get(k.id)
            m = r.level if r else 0
            kps.append({"id": k.id, "name": k.name, "day": day, "level": k.level, "mastery": m,
                        "mastery_name": LEVEL_NAMES[m], "last_score": r.last_score if r else None})
    dist = defaultdict(int)
    for k in kps:
        dist[LEVEL_NAMES[k["mastery"]]] += 1
    return {"kps": kps, "distribution": dict(dist)}


# ---------- 总体能力（驾驶舱与最终报告共用） ----------


def ability(db: Session, course: Course) -> dict:
    atts = db.scalars(select(Attempt)).all()
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress))}
    by_cat: dict[str, list[float]] = defaultdict(list)
    for a in atts:
        by_cat[a.category].append(a.score)
    learned = [k for k in course.kps if rows.get(k) and rows[k].level >= 1]
    mastered = [k for k in learned if rows[k].level >= 3]
    interview = [a for a in atts if a.qtype not in OBJECTIVE]
    return {
        "attempts": len(atts),
        "objective_accuracy": _avg(a.score for a in atts if a.qtype in OBJECTIVE),
        "interview_score": _avg(a.score for a in interview[-30:]),
        "scenario": _avg(a.score for a in interview if a.qtype in ("scenario", "design")),
        "categories": {c: _avg(by_cat.get(c, [])) for c in CATEGORY_LABELS},
        "learned": len(learned),
        "mastered": len(mastered),
        "total_kps": len(course.kps),
    }


ROLE_RULES = [
    ("AI 应用开发工程师", ["python_backend", "llm", "rag", "eval", "engineering"]),
    ("AI Agent 开发工程师", ["llm", "agent", "eval", "engineering"]),
    ("大模型应用 / RAG 方向", ["llm", "rag", "eval"]),
    ("Agent 运行时 / Coding Agent 方向", ["agent", "engineering", "architecture"]),
]


def build_final_report(db: Session, course: Course) -> dict:
    ab = ability(db, course)
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress))}
    mastered, not_mastered = [], []
    for kid, k in course.kps.items():
        r = rows.get(kid)
        item = {"id": kid, "name": k.name, "level": k.level, "day": course.kp_day[kid],
                "mastery": r.level if r else 0, "mastery_name": LEVEL_NAMES[r.level if r else 0],
                "last_score": r.last_score if r else None, "wrong_count": r.wrong_count if r else 0}
        (mastered if item["mastery"] >= 3 else not_mastered).append(item)
    not_mastered.sort(key=lambda x: ({"P0": 0, "P1": 1, "P2": 2}[x["level"]], x["day"]))

    exams = {}
    for s in db.scalars(select(QuizSession).where(QuizSession.kind == "exam", QuizSession.submitted_at.is_not(None))):
        exams[s.ref] = max(exams.get(s.ref, 0), s.score or 0)

    cats = ab["categories"]
    weak_cats = [CATEGORY_LABELS[c] for c, v in cats.items() if v is None or v < 60]
    roles = []
    for name, need in ROLE_RULES:
        vals = [cats.get(c) for c in need]
        if any(v is None for v in vals):
            continue
        score = mean(vals)
        if score >= 70 and min(vals) >= 60:
            roles.append({"role": name, "score": round(score, 1)})
    roles.sort(key=lambda r: -r["score"])

    projects = []
    done_mods = {r.module_id for r in db.scalars(select(ProjectProgress).where(ProjectProgress.completed_at.is_not(None)))}
    for p in course.projects.values():
        n = sum(m.id in done_mods for m in p.modules)
        projects.append({"id": p.id, "title": p.title, "done": n, "total": len(p.modules)})

    p0_gap = [k for k in not_mastered if k["level"] == "P0"]
    last = db.get(DayProgress, TOTAL_DAYS)
    wrong_open = db.query(WrongItem).filter(WrongItem.resolved.is_(False)).count()
    shortfalls = []
    if weak_cats:
        shortfalls.append("能力维度低于 60 分或尚无数据：" + "、".join(weak_cats))
    if p0_gap:
        shortfalls.append(f"仍有 {len(p0_gap)} 个 P0 知识点未达到「基本掌握」")
    low_exams = [f"第 {p} 阶段 {v} 分" for p, v in sorted(exams.items()) if v < 80]
    if low_exams:
        shortfalls.append("阶段卷低于 80 分：" + "、".join(low_exams))
    missing_exams = [str(p) for p in range(1, 6) if p not in exams]
    if missing_exams:
        shortfalls.append("还没参加的阶段卷：第 " + "、".join(missing_exams) + " 阶段")
    if (ab["scenario"] or 0) < 70:
        shortfalls.append("场景/设计类面试题平均分低于 70：面试官最爱问的题型还不稳")
    for p in projects:
        if p["done"] < p["total"]:
            shortfalls.append(f"项目「{p['title']}」完成 {p['done']}/{p['total']} 个模块，简历上只写已完成的部分")
    if wrong_open:
        shortfalls.append(f"错题本还有 {wrong_open} 道未纠正")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "finished_course": bool(last and last.completed_at),
        "ability": ab,
        "exams": {str(k): v for k, v in sorted(exams.items())},
        "projects": projects,
        "mastered": mastered,
        "not_mastered": not_mastered,
        "shortfalls": shortfalls,
        "roles": roles,
        "roles_note": "只推荐相关维度平均 ≥70 且单项 ≥60 的方向；没有满足条件的方向时说明当前还不建议投递。",
        "before_interview": [f"Day {k['day']:02d} · {k['name']}（{k['mastery_name']}）" for k in p0_gap[:15]],
        "note": SELF_ASSESS_NOTE,
        "pass_score": PASS_SCORE,
        "phases": PHASES,
    }

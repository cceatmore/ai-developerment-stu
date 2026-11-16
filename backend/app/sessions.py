"""解锁规则，以及三种整组提交的客观题：每日复习、当天测试、阶段卷。"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .content import Course
from .content_schema import EXAM_PAPER, PASS_SCORE, TOTAL_DAYS, Question
from .learning import (
    LEVEL_NAMES,
    get_kp,
    last_study_date_before,
    question_payload,
    record_objective,
    schedule_first_review,
    today,
)
from .models import Attempt, DayProgress, KpProgress, QuizSession, Report, WrongItem

TEST_SIZE = 12
REVIEW_BASE, REVIEW_PER_GAP_DAY, REVIEW_MAX = 8, 4, 20
OLD_DAYS = 7  # 超过这么多天没碰过的知识点，复习时随机抽查，防止遗忘
LEVEL_ORDER = {"P0": 0, "P1": 1, "P2": 2}


# ---------- 解锁规则 ----------


def completed_days(db: Session) -> set[int]:
    return {p.day for p in db.scalars(select(DayProgress).where(DayProgress.completed_at.is_not(None)))}


def exam_passed(db: Session, phase: int) -> bool:
    return db.scalar(select(QuizSession.id).where(
        QuizSession.kind == "exam", QuizSession.ref == phase, QuizSession.passed.is_(True))) is not None


def day_available(db: Session, course: Course, day: int) -> tuple[bool, str]:
    if day not in course.days:
        return False, f"Day {day:02d} 的课程内容缺失或校验未通过"
    if day == 1:
        return True, ""
    if (day - 1) not in completed_days(db):
        return False, f"Day {day - 1:02d} 的当天测试达到 {PASS_SCORE} 分后解锁"
    if (day - 1) % 10 == 0 and not exam_passed(db, (day - 1) // 10):
        return False, f"第 {(day - 1) // 10} 阶段卷达到 {PASS_SCORE} 分后解锁"
    return True, ""


def require_day(db: Session, course: Course, day: int) -> None:
    ok, why = day_available(db, course, day)
    if not ok:
        raise HTTPException(404 if day not in course.days else 403, why)


def exam_available(db: Session, course: Course, phase: int) -> tuple[bool, str]:
    if not 1 <= phase <= 5:
        return False, "阶段不存在"
    if phase * 10 not in completed_days(db):
        return False, f"完成 Day {phase * 10:02d} 后开放"
    if len(course.phase_exam_pool(phase)) < sum(n for n, _ in EXAM_PAPER.values()):
        return False, "本阶段卷题库不完整（有天数内容缺失）"
    return True, ""


def current_day(db: Session, course: Course) -> int:
    done = completed_days(db)
    for d in range(1, TOTAL_DAYS + 1):
        if d not in done:
            return d
    return TOTAL_DAYS


def max_unlocked_day(db: Session, course: Course) -> int:
    best = 0
    for d in range(1, TOTAL_DAYS + 1):
        if day_available(db, course, d)[0]:
            best = d
        elif d not in course.days:
            continue
        else:
            break
    return best


# ---------- 选题 ----------


def _history(db: Session, qids: list[str]) -> dict[str, list[Attempt]]:
    out: dict[str, list[Attempt]] = defaultdict(list)
    if qids:
        for a in db.scalars(select(Attempt).where(Attempt.question_id.in_(qids)).order_by(Attempt.id)):
            out[a.question_id].append(a)
    return out


def _pick_for_kp(course: Course, kp_id: str, hist: dict[str, list[Attempt]], exclude: set[str]) -> str | None:
    """从当天测试题池里给某个知识点挑一道：先挑没做过的，再挑最久没做、做错过的。"""
    pool = [q.id for q in course.days[course.kp_day[kp_id]].test if q.kp == kp_id and q.id not in exclude]
    if not pool:
        return None
    random.shuffle(pool)

    def key(qid):
        h = hist.get(qid, [])
        if not h:
            return (0, datetime.min, 0)
        return (1, h[-1].created_at, -min(a.score for a in h))

    return sorted(pool, key=key)[0]


def review_size(db: Session) -> tuple[int, int]:
    """返回 (题量, 距上次学习的天数)。隔得越久（周一、休假回来）复习越多。"""
    last = last_study_date_before(db, today())
    if last is None:
        return 0, 0
    gap = (today() - last).days
    return min(REVIEW_MAX, REVIEW_BASE + REVIEW_PER_GAP_DAY * max(gap - 1, 0)), gap


def build_review(db: Session, course: Course) -> tuple[list[str], dict]:
    size, gap = review_size(db)
    t = today()
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress).where(KpProgress.learned_at.is_not(None)))}
    learned = [k for k in rows if k in course.kps and rows[k].learned_at.date() < t]
    if not size or not learned:
        return [], {"gap": gap, "size": 0}

    all_test = [q.id for k in learned for q in course.days[course.kp_day[k]].test if q.kp == k]
    hist = _history(db, all_test)
    picked: list[str] = []
    reasons: dict[str, str] = {}
    per_kp: dict[str, int] = defaultdict(int)

    def add(qid: str | None, why: str) -> None:
        if qid and qid not in picked and len(picked) < size:
            q = course.questions[qid]
            if per_kp[q.kp] >= 2:
                return
            picked.append(qid)
            reasons[qid] = why
            per_kp[q.kp] += 1

    # 1. 错题（当天测试题直接重做；阶段卷错题换同知识点的另一道，保持卷子新鲜）
    wrong = db.scalars(select(WrongItem).where(WrongItem.resolved.is_(False))
                       .order_by(WrongItem.updated_at.desc())).all()
    for w in wrong[: max(2, int(size * 0.4))]:
        src = course.question_source.get(w.question_id)
        if src == "test" and w.kp_id in learned:
            add(w.question_id, "错题重做")
        elif src in ("exam", "review") and w.kp_id in learned:
            add(_pick_for_kp(course, w.kp_id, hist, set(picked)), "错题同类题")

    # 2. 到期复习（P0 优先、掌握度低优先）
    due = [k for k in learned if rows[k].next_review and rows[k].next_review <= t]
    due.sort(key=lambda k: (LEVEL_ORDER[course.kps[k].level], rows[k].level, rows[k].next_review))
    reserve_old = 2
    for k in due:
        if len(picked) >= size - reserve_old:
            break
        add(_pick_for_kp(course, k, hist, set(picked)), "到期复习")

    # 3. 掌握不扎实（初步理解及以下）
    weak = [k for k in learned if rows[k].level <= 2 and k not in due]
    weak.sort(key=lambda k: (LEVEL_ORDER[course.kps[k].level], rows[k].level, -course.kp_day[k]))
    for k in weak:
        if len(picked) >= size - reserve_old:
            break
        add(_pick_for_kp(course, k, hist, set(picked)), "掌握不扎实")

    # 4. 很久没碰过的旧知识随机抽查
    last_touch = {}
    for qid, h in hist.items():
        k = course.questions[qid].kp
        last_touch[k] = max(last_touch.get(k, datetime.min), h[-1].created_at)
    old = [k for k in learned if per_kp[k] == 0
           and last_touch.get(k, rows[k].learned_at) < datetime.now() - timedelta(days=OLD_DAYS)]
    random.shuffle(old)
    for k in old:
        add(_pick_for_kp(course, k, hist, set(picked)), "防遗忘抽查")

    # 5. 还没满就按掌握度从低到高补齐
    rest = sorted(learned, key=lambda k: (rows[k].level, LEVEL_ORDER[course.kps[k].level], random.random()))
    for k in rest:
        add(_pick_for_kp(course, k, hist, set(picked)), "巩固")
    random.shuffle(picked)
    return picked, {"gap": gap, "size": len(picked), "reasons": reasons}


def build_test(db: Session, course: Course, day: int) -> list[str]:
    d = course.days[day]
    pool = d.test
    prev = db.scalars(select(QuizSession).where(QuizSession.kind == "test", QuizSession.ref == day,
                                                QuizSession.submitted_at.is_not(None))).all()
    seen = {q for s in prev for q in s.question_ids}
    wrong_kps = defaultdict(int)
    for s in prev[-1:]:
        for qid, r in (s.result or {}).get("items", {}).items():
            if r["score"] < 100:
                wrong_kps[course.questions[qid].kp] += 1

    kps = [k.id for k in d.knowledge_points]
    quota = {k: TEST_SIZE // len(kps) for k in kps}
    order = sorted(kps, key=lambda k: (-wrong_kps[k], LEVEL_ORDER[course.kps[k].level]))
    for k in order[: TEST_SIZE - sum(quota.values())]:
        quota[k] += 1
    if wrong_kps:  # 重测：从答对的知识点各匀一题给出错最多的知识点
        good = [k for k in kps if not wrong_kps[k] and quota[k] > 2]
        for k in good:
            quota[k] -= 1
            quota[order[0]] += 1

    picked: list[str] = []
    for k in kps:
        cands = [q for q in pool if q.kp == k]
        random.shuffle(cands)
        cands.sort(key=lambda q: q.id in seen)
        picked += [q.id for q in cands[: quota[k]]]
    if len(picked) < TEST_SIZE:
        rest = [q.id for q in pool if q.id not in picked]
        random.shuffle(rest)
        picked += rest[: TEST_SIZE - len(picked)]
    if not any(course.questions[q].code for q in picked):
        code_q = [q for q in pool if q.code and q.id not in picked]
        if code_q:
            cq = random.choice(code_q)
            same = [p for p in picked if course.questions[p].kp == cq.kp] or picked
            picked[picked.index(same[-1])] = cq.id
    random.shuffle(picked)
    return picked


def build_exam(db: Session, course: Course, phase: int) -> list[str]:
    pool = course.phase_exam_pool(phase)
    prev = db.scalars(select(QuizSession).where(QuizSession.kind == "exam", QuizSession.ref == phase)).all()
    seen = {q for s in prev for q in s.question_ids}
    picked: list[str] = []
    for qtype, (n, _) in EXAM_PAPER.items():
        cands = [q for q in pool if q.type == qtype]
        random.shuffle(cands)
        # 先保证每天都覆盖到，再优先没考过的
        by_day: dict[int, list[Question]] = defaultdict(list)
        for q in sorted(cands, key=lambda q: q.id in seen):
            by_day[course.question_day[q.id]].append(q)
        chosen: list[Question] = []
        while len(chosen) < n and any(by_day.values()):
            for dd in sorted(by_day):
                if by_day[dd] and len(chosen) < n:
                    chosen.append(by_day[dd].pop(0))
        chosen.sort(key=lambda q: course.question_day[q.id])
        picked += [q.id for q in chosen]
    return picked


# ---------- 会话 ----------


def open_session(db: Session, kind: str, ref: int, builder) -> QuizSession:
    """同一类型未提交的会话直接续上（碎片时间中断后回来接着做）。"""
    s = db.scalars(select(QuizSession).where(QuizSession.kind == kind, QuizSession.ref == ref,
                                             QuizSession.submitted_at.is_(None))
                   .order_by(QuizSession.id.desc())).first()
    if kind == "review" and s and s.created_at.date() != today():
        db.delete(s)
        s = None
    if s:
        return s
    qids = builder()
    if not qids:
        raise HTTPException(400, "没有可出的题目")
    s = QuizSession(kind=kind, ref=ref, question_ids=qids, answers={})
    db.add(s)
    db.flush()
    return s


def review_done_today(db: Session) -> bool:
    start = datetime.combine(today(), datetime.min.time())
    return db.scalar(select(QuizSession.id).where(QuizSession.kind == "review",
                                                  QuizSession.submitted_at >= start)) is not None


def session_out(course: Course, s: QuizSession, extra: dict | None = None) -> dict:
    done = s.submitted_at is not None
    return {
        "id": s.id, "kind": s.kind, "ref": s.ref,
        "created_at": s.created_at.isoformat(timespec="seconds"),
        "submitted": done, "answers": s.answers or {},
        "score": s.score, "passed": s.passed, "result": s.result,
        "pass_score": PASS_SCORE,
        "points": {t: p for t, (_, p) in EXAM_PAPER.items()} if s.kind == "exam" else None,
        "questions": [question_payload(course, q, reveal=done) for q in s.question_ids],
        **(extra or {}),
    }


def submit_session(db: Session, course: Course, s: QuizSession) -> dict:
    if s.submitted_at:
        raise HTTPException(400, "已经交卷")
    items, by_kp = {}, defaultdict(list)
    total = got = 0.0
    for qid in s.question_ids:
        q = course.questions.get(qid)
        if q is None:
            continue
        ans = (s.answers or {}).get(qid)
        r = record_objective(db, course, qid, ans, s.kind, s.id)
        weight = EXAM_PAPER[q.type][1] if s.kind == "exam" else 1.0
        total += weight
        got += weight * r["score"] / 100
        by_kp[q.kp].append(r["score"])
        items[qid] = {"score": r["score"], "answer": ans, "correct": r["correct"], "points": weight,
                      "got": round(weight * r["score"] / 100, 1)}
    score = round(got / total * 100, 1) if total else 0.0
    s.score = score
    s.passed = score >= PASS_SCORE
    s.submitted_at = datetime.now()

    kps = []
    for k, scores in by_kp.items():
        row = get_kp(db, k)
        kps.append({"id": k, "name": course.kps[k].name, "level": course.kps[k].level,
                    "day": course.kp_day[k], "avg": round(sum(scores) / len(scores), 1),
                    "mastery": row.level, "mastery_name": LEVEL_NAMES[row.level]})
    kps.sort(key=lambda x: x["avg"])
    s.result = {"items": items, "kps": kps, "weak": [k for k in kps if k["avg"] < 70]}
    if s.kind == "exam":
        by_type = defaultdict(lambda: [0.0, 0.0])
        for qid, it in items.items():
            t = course.questions[qid].type
            by_type[t][0] += it["got"]
            by_type[t][1] += it["points"]
        s.result["by_type"] = {t: {"got": round(a, 1), "total": b} for t, (a, b) in by_type.items()}
    db.flush()

    if s.kind == "test":
        _after_test(db, course, s)
    elif s.kind == "exam":
        db.add(Report(kind="phase", ref=s.ref, data={"session_id": s.id, "score": score, "passed": s.passed,
                                                     "result": s.result}))
    return session_out(course, s)


def _after_test(db: Session, course: Course, s: QuizSession) -> None:
    from .reports import build_daily_report

    prog = db.get(DayProgress, s.ref)
    prog.tests_taken = (prog.tests_taken or 0) + 1
    prog.best_score = max(prog.best_score or 0, s.score)
    if s.passed and prog.completed_at is None:
        prog.completed_at = datetime.now()
        for k in course.days[s.ref].knowledge_points:
            schedule_first_review(get_kp(db, k.id))
    db.flush()
    if s.passed:
        db.add(Report(kind="daily", ref=s.ref, data=build_daily_report(db, course, s.ref, s)))

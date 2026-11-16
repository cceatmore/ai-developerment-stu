"""评分、掌握等级、间隔复习、错题本 —— 系统里所有「能力判断」都在这里。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .content import Course
from .content_schema import OBJECTIVE, SUBJECTIVE, Question
from .models import Attempt, KpProgress, StudyDate, WrongItem

LEVEL_NAMES = ["未学习", "已学习", "初步理解", "基本掌握", "熟练掌握"]
# 复习间隔（距上次复习的天数），按时复习时对应学习后的第 1、3、7、14、30 天
REVIEW_GAPS = [1, 2, 4, 7, 16]
PASS = 60  # 低于此分进入错题本
GOOD = 80  # 错题连续两次达到此分视为已纠正
CONTEXTS = {"review", "test", "exam", "interview", "wrong", "mock", "project"}


def today() -> date:
    return date.today()


def touch_study_date(db: Session) -> None:
    """记录今天有学习行为（学习日统计、复习间隔都依赖它）。"""
    t = today()
    row = db.get(StudyDate, t)
    if row is None:
        row = StudyDate(date=t, first_at=datetime.now(), actions=0)
        db.add(row)
    row.actions += 1


def last_study_date_before(db: Session, d: date) -> date | None:
    return db.scalar(select(StudyDate.date).where(StudyDate.date < d).order_by(StudyDate.date.desc()))


# ---------- 题目 ----------


def get_question(course: Course, qid: str) -> Question:
    q = course.questions.get(qid)
    if q is None:
        raise HTTPException(404, f"题目不存在：{qid}")
    return q


def question_payload(course: Course, qid: str, reveal: bool = True) -> dict:
    q = get_question(course, qid)
    data = q.model_dump()
    kp = q.kp
    data["kp_name"] = course.kps[kp].name if kp and kp in course.kps else None
    data["kp_level"] = course.kps[kp].level if kp and kp in course.kps else None
    data["day"] = course.question_day.get(qid)
    data["source"] = course.question_source.get(qid)
    data["category"] = course.category(qid)
    if not reveal:
        for k in ("answer", "explain", "key_points", "reference", "oral"):
            data[k] = None
    return data


# ---------- 评分 ----------


class AttemptIn(BaseModel):
    question_id: str
    context: str = "interview"
    session_id: int | None = None
    answer: str | list[int] | bool | None = None
    checks: list[float] | None = None  # 主观题：每个评分要点 0 / 0.5 / 1
    expression: int | None = None  # 主观题：表达清晰度 1~5
    gave_up: bool = False


def score_objective(q: Question, answer) -> float:
    if answer is None:
        return 0.0
    if q.type == "judge":
        return 100.0 if answer is q.answer else 0.0
    if not isinstance(answer, list):
        return 0.0
    picked = set(answer)
    right = set(q.answer)
    if picked == right:
        return 100.0
    if q.type == "multi" and picked and picked < right:
        return 50.0  # 少选不错选给一半
    return 0.0


def score_subjective(q: Question, checks: list[float], expression: int | None) -> tuple[float, dict]:
    if len(checks) != len(q.key_points):
        raise HTTPException(400, f"评分要点数量不符：需要 {len(q.key_points)} 项")
    if any(c not in (0, 0.5, 1) for c in checks):
        raise HTTPException(400, "评分要点只能是 0、0.5、1")
    by_dim: dict[str, list[float]] = {}
    for kp, c in zip(q.key_points, checks):
        by_dim.setdefault(kp.dim, []).append(c)
    dims = {d: round(mean(v) * 100) for d, v in by_dim.items()}
    content = mean(checks) * 100
    if expression is not None:
        if not 1 <= expression <= 5:
            raise HTTPException(400, "表达评分为 1~5")
        dims["expression"] = expression * 20
        score = content * 0.85 + expression * 20 * 0.15
    else:
        score = content
    return round(score, 1), dims


# ---------- 掌握等级 ----------


def compute_level(learned: bool, attempts: list[Attempt]) -> int:
    """当天答得好只说明「刚学完记得」，必须隔天仍答得对才算掌握。"""
    if not attempts:
        return 1 if learned else 0
    scores = [a.score for a in attempts]
    recent = mean(scores[-5:])
    days = {a.created_at.date() for a in attempts}
    subj = [a.score for a in attempts if a.qtype in SUBJECTIVE][-3:]
    if len(attempts) >= 4 and len(days) >= 3 and recent >= 85 and (not subj or max(subj) >= 75):
        return 4
    if len(attempts) >= 3 and len(days) >= 2 and recent >= 70:
        return 3
    if recent >= 50 or max(scores) >= 60:
        return 2
    return 1


def get_kp(db: Session, kp_id: str) -> KpProgress:
    row = db.get(KpProgress, kp_id)
    if row is None:
        row = KpProgress(kp_id=kp_id, attempts=0, wrong_count=0, level=0, interval_idx=-1, note="")
        db.add(row)
        db.flush()
    return row


def mark_learned(db: Session, kp_id: str) -> KpProgress:
    row = get_kp(db, kp_id)
    if row.learned_at is None:
        row.learned_at = datetime.now()
        if row.level == 0:
            row.level = 1
    return row


def schedule_first_review(row: KpProgress) -> None:
    if row.interval_idx < 0:
        row.interval_idx = 0
        row.next_review = today() + timedelta(days=REVIEW_GAPS[0])


def _update_schedule(row: KpProgress, context: str, score: float) -> None:
    t = today()
    if context == "review":
        if row.last_review == t:
            if score < PASS:  # 同一天复习再次答错，仍安排明天
                row.interval_idx, row.next_review = 0, t + timedelta(days=1)
            return
        idx = max(row.interval_idx, 0)
        if score >= 85:
            idx = min(idx + 1, len(REVIEW_GAPS) - 1)
        elif score < PASS:
            idx = 0
        row.interval_idx = idx
        row.next_review = t + timedelta(days=REVIEW_GAPS[idx])
        row.last_review = t
    elif score < PASS and row.interval_idx >= 0:
        row.interval_idx = 0
        row.next_review = t + timedelta(days=1)


def _update_wrong(db: Session, qid: str, kp_id: str | None, answer_text: str, score: float) -> bool:
    item = db.get(WrongItem, qid)
    if score < PASS:
        if item is None:
            item = WrongItem(question_id=qid, kp_id=kp_id, wrong_count=0, right_streak=0)
            db.add(item)
        item.wrong_count += 1
        item.right_streak = 0
        item.resolved = False
        item.last_answer = answer_text
        item.last_score = score
        item.updated_at = datetime.now()
        return True
    if item is not None and not item.resolved:
        item.last_score = score
        item.last_answer = answer_text
        item.updated_at = datetime.now()
        if score >= GOOD:
            item.right_streak += 1
            if item.right_streak >= 2:
                item.resolved = True
    return False


def _save(db: Session, course: Course, q: Question, context: str, session_id: int | None, answer_text: str,
          score: float, checks=None, expression=None, dims=None, gave_up=False) -> tuple[Attempt, bool, int | None]:
    att = Attempt(
        question_id=q.id, kp_id=q.kp, qtype=q.type, category=course.category(q.id), context=context,
        session_id=session_id, answer=answer_text, checks=checks, expression=expression, score=score,
        dims=dims, gave_up=gave_up,
    )
    db.add(att)
    db.flush()
    wrong = _update_wrong(db, q.id, q.kp, answer_text, score)
    level = None
    if q.kp:
        row = get_kp(db, q.kp)
        if row.first_score is None:
            row.first_score = score
        row.last_score = score
        row.attempts += 1
        if score < PASS:
            row.wrong_count += 1
        _update_schedule(row, context, score)
        history = db.scalars(
            select(Attempt).where(Attempt.kp_id == q.kp).order_by(Attempt.created_at, Attempt.id)
        ).all()
        row.level = compute_level(row.learned_at is not None, list(history))
        level = row.level
    touch_study_date(db)
    return att, wrong, level


def record_objective(db: Session, course: Course, qid: str, answer, context: str,
                     session_id: int | None = None) -> dict:
    q = get_question(course, qid)
    if q.type not in OBJECTIVE:
        raise HTTPException(400, f"{qid} 不是客观题")
    score = score_objective(q, answer)
    text = "（未作答）" if answer is None else str(answer)
    att, wrong, level = _save(db, course, q, context, session_id, text, score, gave_up=answer is None)
    return {"attempt_id": att.id, "score": score, "correct": score == 100, "wrong": wrong, "level": level,
            "answer": q.answer, "explain": q.explain}


def record_attempt(db: Session, course: Course, data: AttemptIn) -> dict:
    if data.context not in CONTEXTS:
        raise HTTPException(400, "未知的作答场景")
    q = get_question(course, data.question_id)
    if q.type in OBJECTIVE:
        if data.answer is None and not data.gave_up:
            raise HTTPException(400, "请先作答")
        res = record_objective(db, course, q.id, None if data.gave_up else data.answer, data.context,
                               data.session_id)
        res["level_name"] = LEVEL_NAMES[res["level"]] if res["level"] is not None else None
        return res

    answer_text = data.answer if isinstance(data.answer, str) else ""
    if data.gave_up:
        checks = [0.0] * len(q.key_points)
        expression = 1 if data.expression is not None else None
    else:
        if not answer_text.strip():
            raise HTTPException(400, "请先写下你的回答，再对照要点自评；不会可以点「不会，看答案」")
        if data.checks is None:
            raise HTTPException(400, "请对照评分要点完成自评")
        checks, expression = data.checks, data.expression
    score, dims = score_subjective(q, checks, expression)
    att, wrong, level = _save(db, course, q, data.context, data.session_id, answer_text, score,
                              checks=checks, expression=expression, dims=dims, gave_up=data.gave_up)
    return {"attempt_id": att.id, "score": score, "dims": dims, "wrong": wrong, "level": level,
            "level_name": LEVEL_NAMES[level] if level is not None else None}


def latest_attempts(db: Session, qids: list[str], context: str | None = None) -> dict[str, Attempt]:
    if not qids:
        return {}
    stmt = select(Attempt).where(Attempt.question_id.in_(qids)).order_by(Attempt.id)
    if context:
        stmt = stmt.where(Attempt.context == context)
    out: dict[str, Attempt] = {}
    for a in db.scalars(stmt):
        out[a.question_id] = a
    return out


def attempt_dict(a: Attempt) -> dict:
    return {
        "id": a.id,
        "question_id": a.question_id,
        "answer": a.answer,
        "checks": a.checks,
        "expression": a.expression,
        "score": a.score,
        "dims": a.dims,
        "gave_up": a.gave_up,
        "context": a.context,
        "created_at": a.created_at.isoformat(timespec="seconds"),
    }

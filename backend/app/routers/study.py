"""驾驶舱、每日学习（复习 → 讲解 → 测试 → 面试题）、作答、错题、知识点、草稿。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..content import Course, get_course
from ..content_schema import PASS_SCORE, PHASES, TOTAL_DAYS
from ..db import DB
from ..learning import (
    LEVEL_NAMES,
    AttemptIn,
    attempt_dict,
    get_kp,
    latest_attempts,
    mark_learned,
    question_payload,
    record_attempt,
    today,
    touch_study_date,
)
from ..models import Attempt, DayProgress, Draft, KpProgress, ProjectProgress, QuizSession, Report, StudyDate, WrongItem
from ..reports import ability
from ..sessions import (
    build_review,
    build_test,
    completed_days,
    current_day,
    day_available,
    exam_available,
    exam_passed,
    max_unlocked_day,
    open_session,
    require_day,
    review_done_today,
    review_size,
    session_out,
    submit_session,
)

router = APIRouter(prefix="/api")
STAGES = ["review", "lesson", "test", "interview", "summary"]


def course_dep() -> Course:
    c = get_course()
    if not c.days:
        raise HTTPException(503, "课程内容为空或全部校验失败，请在「数据与设置」页查看内容校验结果")
    return c


def _day_progress(db: Session, day: int) -> DayProgress:
    prog = db.get(DayProgress, day)
    if prog is None:
        prog = DayProgress(day=day, learned_kps=[], stage_seconds={}, tests_taken=0)
        db.add(prog)
    return prog


def review_state(db: Session) -> dict:
    size, gap = review_size(db)
    done = review_done_today(db)
    pending = db.scalars(select(QuizSession).where(QuizSession.kind == "review",
                                                   QuizSession.submitted_at.is_(None))
                         .order_by(QuizSession.id.desc())).first()
    start = datetime.combine(today(), datetime.min.time())
    has_learned = db.scalar(select(func.count()).select_from(KpProgress)
                            .where(KpProgress.learned_at.is_not(None), KpProgress.learned_at < start)) or 0
    needed = bool(size and has_learned and not done)
    return {"needed": needed, "done": done, "size": size, "gap": gap,
            "pending_id": pending.id if pending and pending.created_at.date() == today() else None}


def day_state(db: Session, course: Course, day: int, rv: dict | None = None) -> dict:
    d = course.days[day]
    prog = db.get(DayProgress, day)
    learned = set(prog.learned_kps) if prog else set()
    rv = rv or review_state(db)
    iv = latest_attempts(db, [q.id for q in d.interview], "interview")
    passed = bool(prog and prog.completed_at)
    done = {
        "review": not rv["needed"],
        "lesson": all(k.id in learned for k in d.knowledge_points),
        "test": passed,
        "interview": len(iv) == len(d.interview),
        "summary": passed,
    }
    if passed:
        stage = "interview" if not done["interview"] else "summary"
    else:
        stage = next(s for s in ("review", "lesson", "test") if not done[s])
    pending = db.scalars(select(QuizSession).where(QuizSession.kind == "test", QuizSession.ref == day,
                                                   QuizSession.submitted_at.is_(None))).first()
    return {
        "day": day,
        "started": bool(prog and prog.started_at),
        "completed": passed,
        "completed_at": prog.completed_at.isoformat(timespec="seconds") if passed else None,
        "best_score": prog.best_score if prog else None,
        "tests_taken": prog.tests_taken if prog else 0,
        "pending_test": pending.id if pending else None,
        "stage": stage,
        "done": done,
        "learned": sorted(learned),
        "interview_done": len(iv),
        "interview_total": len(d.interview),
        "review": rv,
        "seconds": (prog.stage_seconds or {}) if prog else {},
    }


def _project_steps(db: Session, course: Course) -> dict:
    top = max_unlocked_day(db, course)
    done = {r.module_id for r in db.scalars(select(ProjectProgress).where(ProjectProgress.completed_at.is_not(None)))}
    todo = [m for m in course.modules.values() if m.unlock_day <= top and m.id not in done]
    todo.sort(key=lambda m: (m.unlock_day, m.id))
    nxt = todo[0] if todo else None
    return {
        "next": {"id": nxt.id, "name": nxt.name, "minutes": nxt.minutes,
                 "project": course.projects[course.module_project[nxt.id]].title} if nxt else None,
        "behind": len(todo),
        "done": len(done & set(course.modules)),
        "total": len(course.modules),
    }


# ---------- 驾驶舱 ----------


@router.get("/dashboard")
def dashboard(db: DB, course: Course = Depends(course_dep)):
    completed = completed_days(db)
    cur = current_day(db, course)
    best = {p.day: p.best_score for p in db.scalars(select(DayProgress))}
    rv = review_state(db)

    roadmap = []
    for n in range(1, TOTAL_DAYS + 1):
        d = course.days.get(n)
        if d is None:
            status = "missing"
        elif n in completed:
            status = "weak" if (best.get(n) or 0) < 80 else "done"
        elif day_available(db, course, n)[0]:
            status = "current"
        else:
            status = "locked"
        roadmap.append({"day": n, "phase": (n - 1) // 10 + 1, "title": d.title if d else "（内容缺失）",
                        "status": status, "best": best.get(n)})

    exams = []
    for ph in range(1, 6):
        ok, why = exam_available(db, course, ph)
        best_exam = db.scalar(select(func.max(QuizSession.score)).where(
            QuizSession.kind == "exam", QuizSession.ref == ph, QuizSession.submitted_at.is_not(None)))
        exams.append({"phase": ph, "title": PHASES[ph], "available": ok, "why": why,
                      "passed": exam_passed(db, ph), "best": best_exam})

    pending_iv = 0
    for n in completed:
        if n in course.days:
            qs = [q.id for q in course.days[n].interview]
            pending_iv += len(qs) - len(latest_attempts(db, qs, "interview"))

    d = course.days.get(cur)
    ok, why = day_available(db, course, cur) if d else (False, "")
    return {
        "current_day": cur,
        "current": {"day": cur, "title": d.title, "goals": d.goals, "phase": d.phase, "minutes": d.minutes,
                    "phase_title": PHASES[d.phase], "available": ok, "why": why,
                    "kps": [{"name": k.name, "level": k.level} for k in d.knowledge_points],
                    "state": day_state(db, course, cur, rv)} if d else None,
        "completed_days": len(completed),
        "study_dates": db.scalar(select(func.count()).select_from(StudyDate)) or 0,
        "review": rv,
        "wrong_open": db.query(WrongItem).filter(WrongItem.resolved.is_(False)).count(),
        "interview_pending": pending_iv,
        "projects": _project_steps(db, course),
        "ability": ability(db, course),
        "exams": exams,
        "roadmap": roadmap,
        "pass_score": PASS_SCORE,
        "content_errors": len(course.errors),
    }


# ---------- 每日学习 ----------


@router.get("/days/{day}")
def get_day(day: int, db: DB, course: Course = Depends(course_dep)):
    if day not in course.days:
        raise HTTPException(404, f"Day {day:02d} 的课程内容缺失或校验未通过")
    d = course.days[day]
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress).where(
        KpProgress.kp_id.in_([k.id for k in d.knowledge_points])))}
    kps = []
    for k in d.knowledge_points:
        r = rows.get(k.id)
        kps.append(k.model_dump() | {"mastery": r.level if r else 0,
                                     "mastery_name": LEVEL_NAMES[r.level if r else 0],
                                     "note": r.note if r else "", "outdated": r.outdated if r else False})
    report = db.scalars(select(Report).where(Report.kind == "daily", Report.ref == day)
                        .order_by(Report.id.desc())).first()
    ok, why = day_available(db, course, day)
    iv_atts = latest_attempts(db, [q.id for q in d.interview], "interview")
    return {
        "day": d.day, "phase": d.phase, "phase_title": PHASES[d.phase], "title": d.title, "goals": d.goals,
        "minutes": d.minutes,
        "resources": [r.model_dump() for r in d.resources],
        "sources": [s.model_dump() for s in d.sources],
        "knowledge_points": kps,
        "test_pool": len(d.test),
        "interview": [question_payload(course, q.id) for q in d.interview],
        "interview_attempts": {k: attempt_dict(v) for k, v in iv_atts.items()},
        "projects": [{"id": m.id, "name": m.name, "minutes": m.minutes,
                      "project": course.projects[course.module_project[m.id]].title}
                     for m in course.modules_for_day(day)],
        "available": ok,
        "why": why,
        "state": day_state(db, course, day),
        "report": report.data if report else None,
    }


class LearnIn(BaseModel):
    kp_id: str


@router.post("/days/{day}/learn")
def learn_kp(day: int, body: LearnIn, db: DB, course: Course = Depends(course_dep)):
    require_day(db, course, day)
    if review_state(db)["needed"]:
        raise HTTPException(403, "请先完成今天的复习")
    if body.kp_id not in {k.id for k in course.days[day].knowledge_points}:
        raise HTTPException(400, "知识点不属于这一天")
    prog = _day_progress(db, day)
    prog.started_at = prog.started_at or datetime.now()
    if body.kp_id not in prog.learned_kps:
        prog.learned_kps = [*prog.learned_kps, body.kp_id]
    mark_learned(db, body.kp_id)
    touch_study_date(db)
    db.flush()
    return day_state(db, course, day)


class TimeIn(BaseModel):
    stage: str
    seconds: int


@router.post("/days/{day}/time")
def add_time(day: int, body: TimeIn, db: DB, course: Course = Depends(course_dep)):
    if body.stage not in STAGES or not 0 < body.seconds <= 1800:
        raise HTTPException(400, "无效的计时数据")
    if day not in course.days:
        raise HTTPException(404, "天数不存在")
    prog = _day_progress(db, day)
    sec = dict(prog.stage_seconds or {})
    sec[body.stage] = sec.get(body.stage, 0) + body.seconds
    prog.stage_seconds = sec
    return {"ok": True}


@router.post("/days/{day}/test")
def start_test(day: int, db: DB, course: Course = Depends(course_dep)):
    require_day(db, course, day)
    st = day_state(db, course, day)
    if not st["done"]["review"]:
        raise HTTPException(403, "请先完成今天的复习")
    if not st["done"]["lesson"]:
        raise HTTPException(403, "请先读完今天的全部知识点")
    s = open_session(db, "test", day, lambda: build_test(db, course, day))
    return session_out(course, s)


# ---------- 每日复习 ----------


@router.get("/review")
def review_info(db: DB, course: Course = Depends(course_dep)):
    t = today()
    upcoming = db.scalars(select(KpProgress).where(KpProgress.next_review > t)
                          .order_by(KpProgress.next_review).limit(20)).all()
    due = db.scalar(select(func.count()).select_from(KpProgress).where(
        KpProgress.next_review.is_not(None), KpProgress.next_review <= t)) or 0
    history = db.scalars(select(QuizSession).where(QuizSession.kind == "review", QuizSession.submitted_at.is_not(None))
                         .order_by(QuizSession.id.desc()).limit(10)).all()
    pending_iv = []
    for n in sorted(completed_days(db)):
        d = course.days.get(n)
        if d:
            done = len(latest_attempts(db, [q.id for q in d.interview], "interview"))
            if done < len(d.interview):
                pending_iv.append({"day": n, "title": d.title, "done": done, "total": len(d.interview)})
    return {
        **review_state(db),
        "current_day": current_day(db, course),
        "interview_pending": pending_iv,
        "due_kps": due,
        "upcoming": [{"kp_name": course.kps[u.kp_id].name, "date": u.next_review.isoformat()}
                     for u in upcoming if u.kp_id in course.kps],
        "history": [{"id": s.id, "date": s.created_at.date().isoformat(), "score": s.score,
                     "total": len(s.question_ids)} for s in history],
    }


@router.post("/review/start")
def start_review(db: DB, course: Course = Depends(course_dep)):
    info = {}

    def builder():
        qids, meta = build_review(db, course)
        info.update(meta)
        return qids

    s = open_session(db, "review", 0, builder)
    if not s.result:
        s.result = {"reasons": info.get("reasons", {}), "gap": info.get("gap")}
    return session_out(course, s, {"reasons": (s.result or {}).get("reasons", {})})


# ---------- 整组提交的题目（复习 / 测试 / 阶段卷） ----------


def _get_session(db: Session, sid: int) -> QuizSession:
    s = db.get(QuizSession, sid)
    if s is None:
        raise HTTPException(404, "记录不存在")
    return s


@router.get("/sessions/{sid}")
def get_session(sid: int, db: DB, course: Course = Depends(course_dep)):
    s = _get_session(db, sid)
    return session_out(course, s, {"reasons": (s.result or {}).get("reasons", {})})


class AnswerIn(BaseModel):
    question_id: str
    answer: list[int] | bool | None = None


@router.put("/sessions/{sid}/answer")
def save_answer(sid: int, body: AnswerIn, db: DB):
    s = _get_session(db, sid)
    if s.submitted_at:
        raise HTTPException(400, "已经交卷，不能再修改")
    if body.question_id not in s.question_ids:
        raise HTTPException(400, "题目不属于本次测试")
    answers = dict(s.answers or {})
    if body.answer is None or body.answer == []:
        answers.pop(body.question_id, None)
    else:
        answers[body.question_id] = body.answer
    s.answers = answers
    return {"ok": True, "answered": len(answers)}


@router.post("/sessions/{sid}/submit")
def submit(sid: int, db: DB, course: Course = Depends(course_dep)):
    s = _get_session(db, sid)
    keep = (s.result or {}).get("reasons", {})
    out = submit_session(db, course, s)
    if s.kind == "review":
        s.result = {**(s.result or {}), "reasons": keep}
        out["reasons"] = keep
    return out


# ---------- 单题作答（面试题、错题重做、项目复述、模拟面试） ----------


@router.post("/attempts")
def submit_attempt(body: AttemptIn, db: DB, course: Course = Depends(course_dep)):
    if body.context == "interview":
        day = course.question_day.get(body.question_id)
        if day:
            ok, why = day_available(db, course, day)
            if not ok:
                raise HTTPException(403, why)
    if body.context in ("review", "test", "exam"):
        raise HTTPException(400, "复习、测试和阶段卷需要整组交卷")
    result = record_attempt(db, course, body)
    draft_key = f"{body.context}{body.session_id or ''}:{body.question_id}"
    db.query(Draft).filter(Draft.key == draft_key).delete(synchronize_session=False)
    return result


@router.get("/questions/{qid}")
def get_question(qid: str, course: Course = Depends(course_dep)):
    return question_payload(course, qid)


@router.get("/questions/{qid}/history")
def question_history(qid: str, db: DB):
    rows = db.scalars(select(Attempt).where(Attempt.question_id == qid).order_by(Attempt.id.desc())).all()
    return [attempt_dict(a) for a in rows]


# ---------- 错题本 ----------


@router.get("/wrong")
def wrong_book(db: DB, resolved: bool = False, course: Course = Depends(course_dep)):
    rows = db.scalars(select(WrongItem).where(WrongItem.resolved.is_(resolved))
                      .order_by(WrongItem.updated_at.desc())).all()
    return [{"question_id": w.question_id, "wrong_count": w.wrong_count, "right_streak": w.right_streak,
             "last_answer": w.last_answer, "last_score": w.last_score,
             "updated_at": w.updated_at.isoformat(timespec="seconds"),
             "question": question_payload(course, w.question_id)}
            for w in rows if w.question_id in course.questions]


# ---------- 知识点掌握情况 ----------


@router.get("/kps")
def kp_list(db: DB, course: Course = Depends(course_dep)):
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress))}
    out = []
    for kid, k in course.kps.items():
        r = rows.get(kid)
        out.append({
            "id": kid, "name": k.name, "level": k.level, "day": course.kp_day[kid],
            "learned": bool(r and r.learned_at), "tested": bool(r and r.attempts),
            "first_score": r.first_score if r else None, "last_score": r.last_score if r else None,
            "attempts": r.attempts if r else 0, "wrong_count": r.wrong_count if r else 0,
            "mastery": r.level if r else 0, "mastery_name": LEVEL_NAMES[r.level if r else 0],
            "next_review": r.next_review.isoformat() if r and r.next_review else None,
            "outdated": bool(r and r.outdated), "note": r.note if r else "",
        })
    return out


class KpNoteIn(BaseModel):
    note: str | None = None
    outdated: bool | None = None


@router.put("/kps/{kp_id}")
def update_kp(kp_id: str, body: KpNoteIn, db: DB, course: Course = Depends(course_dep)):
    if kp_id not in course.kps:
        raise HTTPException(404, "知识点不存在")
    row = get_kp(db, kp_id)
    if body.note is not None:
        row.note = body.note[:5000]
    if body.outdated is not None:
        row.outdated = body.outdated
    return {"ok": True}


# ---------- 草稿（防止刷新丢失未提交的回答） ----------


class DraftIn(BaseModel):
    text: str


@router.get("/drafts/{key}")
def get_draft(key: str, db: DB):
    d = db.get(Draft, key)
    return {"text": d.text if d else ""}


@router.put("/drafts/{key}")
def put_draft(key: str, body: DraftIn, db: DB):
    if len(key) > 96:
        raise HTTPException(400, "key 过长")
    d = db.get(Draft, key)
    if d is None:
        d = Draft(key=key)
        db.add(d)
    d.text = body.text[:20000]
    d.updated_at = datetime.now()
    return {"ok": True}

"""阶段卷、模拟面试、实践项目。"""

from __future__ import annotations

import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content import Course
from ..content_schema import CATEGORY_LABELS, EXAM_PAPER, PASS_SCORE, PHASES
from ..db import DB
from ..learning import attempt_dict, latest_attempts, question_payload
from ..models import Attempt, MockSession, ProjectProgress, QuizSession
from ..reports import PHASE_GOALS, build_mock_report, phase_mastery
from ..sessions import (
    build_exam,
    completed_days,
    exam_available,
    exam_passed,
    max_unlocked_day,
    open_session,
    session_out,
)
from .study import course_dep

router = APIRouter(prefix="/api")


# ---------- 阶段卷 ----------


@router.get("/exams")
def exams(db: DB, course: Course = Depends(course_dep)):
    out = []
    for ph in range(1, 6):
        ok, why = exam_available(db, course, ph)
        rows = db.scalars(select(QuizSession).where(QuizSession.kind == "exam", QuizSession.ref == ph)
                          .order_by(QuizSession.id.desc())).all()
        out.append({
            "phase": ph, "title": PHASES[ph], "goals": PHASE_GOALS[ph], "available": ok, "why": why,
            "passed": exam_passed(db, ph),
            "pending": next((s.id for s in rows if s.submitted_at is None), None),
            "history": [{"id": s.id, "score": s.score, "passed": s.passed,
                         "date": s.submitted_at.date().isoformat()} for s in rows if s.submitted_at],
        })
    return {"phases": out, "pass_score": PASS_SCORE,
            "paper": {t: {"count": n, "points": p} for t, (n, p) in EXAM_PAPER.items()}}


@router.post("/exams/{phase}")
def start_exam(phase: int, db: DB, course: Course = Depends(course_dep)):
    ok, why = exam_available(db, course, phase)
    if not ok:
        raise HTTPException(403, why)
    s = open_session(db, "exam", phase, lambda: build_exam(db, course, phase))
    return session_out(course, s, {"title": f"第 {phase} 阶段卷 · {PHASES[phase]}"})


@router.get("/exams/{phase}/mastery")
def exam_mastery(phase: int, db: DB, course: Course = Depends(course_dep)):
    return phase_mastery(db, course, phase)


# ---------- 模拟面试 ----------

MODES = {
    "mixed": "综合面试（已学内容）",
    "p1": "项目深挖：企业知识库问答",
    "p2": "项目深挖：智慧园区运营 Agent",
    "p3": "项目深挖：前端 Coding Agent",
}
MOCK_SIZE = 6


def _build_mock(db: Session, course: Course, mode: str) -> list[str]:
    done = completed_days(db)
    if mode == "mixed":
        pool = [q for d in sorted(done) if d in course.days for q in course.days[d].interview]
        if len(pool) < 3:
            raise HTTPException(400, "至少完成 1 天的学习后才能模拟面试（只从已学内容出题）")
        random.shuffle(pool)
        by_cat: dict[str, list] = {}
        for q in pool:
            by_cat.setdefault(course.category(q.id), []).append(q)
        picked = []
        while len(picked) < MOCK_SIZE and any(by_cat.values()):
            for cat in list(by_cat):
                if by_cat[cat] and len(picked) < MOCK_SIZE:
                    picked.append(by_cat[cat].pop())
        picked.sort(key=lambda q: q.difficulty or 1)
        return [q.id for q in picked]
    p = course.projects.get(mode)
    if p is None:
        raise HTTPException(400, "未知的面试模式")
    if p.modules[0].unlock_day > max_unlocked_day(db, course):
        raise HTTPException(403, f"学到 Day {p.modules[0].unlock_day:02d} 后开放这个项目的深挖面试")
    qs = list(p.deep_dive)
    random.shuffle(qs)
    return [q.id for q in sorted(qs[:MOCK_SIZE], key=lambda q: q.difficulty or 1)]


class MockIn(BaseModel):
    mode: str


def _mock_out(db: Session, course: Course, s: MockSession) -> dict:
    hide = not s.locked
    atts = db.scalars(select(Attempt).where(Attempt.session_id == s.id, Attempt.context == "mock")
                      .order_by(Attempt.id)).all()
    p = course.projects.get(s.mode)
    return {
        "id": s.id, "mode": s.mode, "mode_name": MODES.get(s.mode, s.mode),
        "created_at": s.created_at.isoformat(timespec="seconds"),
        "finished": s.finished_at is not None, "locked": s.locked,
        "answers": s.answers or {},
        "questions": [question_payload(course, q, reveal=not hide) for q in s.question_ids],
        "attempts": {a.question_id: attempt_dict(a) for a in atts},
        "report": s.report,
        "background": p.intro if p else None,
    }


@router.post("/mock")
def create_mock(body: MockIn, db: DB, course: Course = Depends(course_dep)):
    qids = _build_mock(db, course, body.mode)
    s = MockSession(mode=body.mode, question_ids=qids, answers={}, locked=False)
    db.add(s)
    db.flush()
    return _mock_out(db, course, s)


@router.get("/mock")
def list_mock(db: DB):
    rows = db.scalars(select(MockSession).order_by(MockSession.id.desc()).limit(50)).all()
    return [{"id": s.id, "mode": s.mode, "mode_name": MODES.get(s.mode, s.mode),
             "created_at": s.created_at.isoformat(timespec="seconds"),
             "finished": s.finished_at is not None, "total": len(s.question_ids),
             "overall": (s.report or {}).get("overall")} for s in rows]


def _get_mock(db: Session, sid: int) -> MockSession:
    s = db.get(MockSession, sid)
    if s is None:
        raise HTTPException(404, "面试记录不存在")
    return s


@router.get("/mock/{sid}")
def get_mock(sid: int, db: DB, course: Course = Depends(course_dep)):
    return _mock_out(db, course, _get_mock(db, sid))


class MockAnswerIn(BaseModel):
    question_id: str
    text: str


@router.put("/mock/{sid}/answer")
def save_mock_answer(sid: int, body: MockAnswerIn, db: DB):
    s = _get_mock(db, sid)
    if s.locked or s.finished_at:
        raise HTTPException(400, "已交卷，不能再修改回答")
    if body.question_id not in s.question_ids:
        raise HTTPException(400, "题目不属于本场面试")
    s.answers = {**(s.answers or {}), body.question_id: body.text[:20000]}
    return {"ok": True}


@router.post("/mock/{sid}/lock")
def lock_mock(sid: int, db: DB, course: Course = Depends(course_dep)):
    s = _get_mock(db, sid)
    s.locked = True
    db.flush()
    return _mock_out(db, course, s)


@router.post("/mock/{sid}/finish")
def finish_mock(sid: int, db: DB, course: Course = Depends(course_dep)):
    s = _get_mock(db, sid)
    s.locked = True
    s.finished_at = s.finished_at or datetime.now()
    s.report = build_mock_report(db, course, s)
    db.flush()
    return _mock_out(db, course, s)


@router.get("/meta")
def meta():
    return {"modes": MODES, "categories": CATEGORY_LABELS, "phases": PHASES, "pass_score": PASS_SCORE}


# ---------- 实践项目 ----------


class ProjectIn(BaseModel):
    checks: dict[str, list[int]] | None = None
    note: str | None = None


def _module_status(db: Session, m, row: ProjectProgress | None, unlocked: bool) -> dict:
    checks = (row.checks if row else {}) or {}
    total = sum(len(v) for v in m.tests.values())
    done = sum(len(set(checks.get(k, [])) & set(range(len(v)))) for k, v in m.tests.items())
    retell = latest_attempts(db, [m.retell.id]).get(m.retell.id)
    return {"checks": checks, "note": row.note if row else "", "done": done, "total": total,
            "retell": attempt_dict(retell) if retell else None, "unlocked": unlocked,
            "completed": bool(row and row.completed_at)}


@router.get("/projects")
def projects(db: DB, course: Course = Depends(course_dep)):
    top = max_unlocked_day(db, course)
    rows = {r.module_id: r for r in db.scalars(select(ProjectProgress))}
    out = []
    for p in course.projects.values():
        done = sum(bool(rows.get(m.id) and rows[m.id].completed_at) for m in p.modules)
        unlocked = sum(m.unlock_day <= top for m in p.modules)
        out.append({"id": p.id, "title": p.title, "role": p.role, "done": done, "unlocked": unlocked,
                    "total": len(p.modules), "first_day": p.modules[0].unlock_day})
    return out


@router.get("/projects/{pid}")
def project(pid: str, db: DB, course: Course = Depends(course_dep)):
    p = course.projects.get(pid)
    if p is None:
        raise HTTPException(404, "项目内容缺失")
    top = max_unlocked_day(db, course)
    rows = {r.module_id: r for r in db.scalars(select(ProjectProgress))}
    modules = []
    for m in p.modules:
        d = m.model_dump(exclude={"retell"})
        d["retell"] = question_payload(course, m.retell.id)
        d["status"] = _module_status(db, m, rows.get(m.id), m.unlock_day <= top)
        modules.append(d)
    return p.model_dump(exclude={"modules", "deep_dive"}) | {
        "modules": modules, "deep_dive_count": len(p.deep_dive)}


@router.put("/projects/module/{mid}")
def update_module(mid: str, body: ProjectIn, db: DB, course: Course = Depends(course_dep)):
    m = course.modules.get(mid)
    if m is None:
        raise HTTPException(404, "模块不存在")
    unlocked = m.unlock_day <= max_unlocked_day(db, course)
    if not unlocked:
        raise HTTPException(403, f"学到 Day {m.unlock_day:02d} 后解锁")
    row = db.get(ProjectProgress, mid)
    if row is None:
        row = ProjectProgress(module_id=mid, checks={}, note="")
        db.add(row)
    if body.checks is not None:
        row.checks = {k: sorted(set(v)) for k, v in body.checks.items() if k in m.tests}
    if body.note is not None:
        row.note = body.note[:10000]
    st = _module_status(db, m, row, unlocked)
    retell_ok = st["retell"] is not None and st["retell"]["score"] >= 60
    row.completed_at = (row.completed_at or datetime.now()) if st["done"] == st["total"] and retell_ok else None
    db.flush()
    return _module_status(db, m, row, unlocked)

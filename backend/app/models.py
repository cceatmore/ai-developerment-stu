from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

SCHEMA_VERSION = "2"


def now() -> datetime:
    return datetime.now()


class DayProgress(Base):
    __tablename__ = "day_progress"

    day: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)  # 当天测试 ≥70 分的时间
    learned_kps: Mapped[list] = mapped_column(JSON, default=list)
    stage_seconds: Mapped[dict] = mapped_column(JSON, default=dict)
    best_score: Mapped[float | None] = mapped_column(Float)
    tests_taken: Mapped[int] = mapped_column(Integer, default=0)


class StudyDate(Base):
    """有学习行为的日期，用于统计「学习日」和计算距上次学习隔了几天。"""

    __tablename__ = "study_dates"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    first_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    actions: Mapped[int] = mapped_column(Integer, default=0)


class QuizSession(Base):
    """一组一起提交的客观题：每日复习 / 当天测试 / 阶段卷。"""

    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(8), index=True)  # review / test / exam
    ref: Mapped[int] = mapped_column(Integer, default=0)  # test: 天；exam: 阶段；review: 0
    question_ids: Mapped[list] = mapped_column(JSON)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float | None] = mapped_column(Float)
    passed: Mapped[bool | None] = mapped_column(Boolean)
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[str] = mapped_column(String(64), index=True)
    kp_id: Mapped[str | None] = mapped_column(String(32), index=True)
    qtype: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(24))
    context: Mapped[str] = mapped_column(String(16), index=True)  # review/test/exam/interview/wrong/mock/project
    session_id: Mapped[int | None] = mapped_column(Integer, index=True)
    answer: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[list | None] = mapped_column(JSON)
    expression: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    dims: Mapped[dict | None] = mapped_column(JSON)
    gave_up: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class KpProgress(Base):
    __tablename__ = "kp_progress"

    kp_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    learned_at: Mapped[datetime | None] = mapped_column(DateTime)
    first_score: Mapped[float | None] = mapped_column(Float)
    last_score: Mapped[float | None] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    interval_idx: Mapped[int] = mapped_column(Integer, default=-1)
    next_review: Mapped[date | None] = mapped_column(Date, index=True)
    last_review: Mapped[date | None] = mapped_column(Date)
    outdated: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")


class WrongItem(Base):
    __tablename__ = "wrong_items"

    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kp_id: Mapped[str | None] = mapped_column(String(32))
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    right_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_answer: Mapped[str] = mapped_column(Text, default="")
    last_score: Mapped[float] = mapped_column(Float, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class MockSession(Base):
    __tablename__ = "mock_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))  # mixed / p1 / p2 / p3
    question_ids: Mapped[list] = mapped_column(JSON)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)  # 交卷后才显示答案
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    report: Mapped[dict | None] = mapped_column(JSON)


class ProjectProgress(Base):
    __tablename__ = "project_progress"

    module_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    checks: Mapped[dict] = mapped_column(JSON, default=dict)  # {"functional": [0, 2], ...}
    note: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)  # daily/phase
    ref: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    data: Mapped[dict] = mapped_column(JSON)


class Draft(Base):
    __tablename__ = "drafts"

    key: Mapped[str] = mapped_column(String(96), primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

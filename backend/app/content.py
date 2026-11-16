"""加载并索引 content/ 下的课程内容。"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from .config import settings
from .content_schema import Day, KnowledgePoint, Project, ProjectModule, Question, default_category


class ContentError(Exception):
    pass


def _read_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ContentError(f"{path.name}: YAML 语法错误\n{e}") from e


def _load(path: Path, model):
    try:
        return model.model_validate(_read_yaml(path))
    except ContentError:
        raise
    except Exception as e:
        raise ContentError(f"{path.name}: 内容校验失败\n{e}") from e


def load_day(path: Path) -> Day:
    return _load(path, Day)


def load_project(path: Path) -> Project:
    return _load(path, Project)


@dataclass
class Course:
    days: dict[int, Day] = field(default_factory=dict)
    kps: dict[str, KnowledgePoint] = field(default_factory=dict)
    kp_day: dict[str, int] = field(default_factory=dict)
    questions: dict[str, Question] = field(default_factory=dict)
    question_day: dict[str, int] = field(default_factory=dict)
    question_source: dict[str, str] = field(default_factory=dict)  # test/exam/interview/project/deep_dive
    projects: dict[str, Project] = field(default_factory=dict)
    modules: dict[str, ProjectModule] = field(default_factory=dict)
    module_project: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def category(self, qid: str) -> str:
        q = self.questions[qid]
        if q.category:
            return q.category
        day = self.question_day.get(qid)
        return default_category(day) if day else "architecture"

    def _add_q(self, q: Question, day: int | None, source: str) -> None:
        self.questions[q.id] = q
        if day:
            self.question_day[q.id] = day
        self.question_source[q.id] = source

    def phase_exam_pool(self, phase: int) -> list[Question]:
        days = range((phase - 1) * 10 + 1, phase * 10 + 1)
        return [q for d in days if d in self.days for q in self.days[d].exam]

    def modules_for_day(self, day: int) -> list[ProjectModule]:
        return [m for m in self.modules.values() if m.unlock_day == day]


def load_course(root: Path) -> Course:
    c = Course()
    for path in sorted((root / "days").glob("day*.yaml")):
        try:
            d = load_day(path)
        except ContentError as e:
            c.errors.append(str(e))
            continue
        c.days[d.day] = d
        for k in d.knowledge_points:
            c.kps[k.id] = k
            c.kp_day[k.id] = d.day
        for src in ("test", "exam", "interview"):
            for q in getattr(d, src):
                c._add_q(q, d.day, src)

    for path in sorted((root / "projects").glob("p*.yaml")):
        try:
            p = load_project(path)
        except ContentError as e:
            c.errors.append(str(e))
            continue
        c.projects[p.id] = p
        for m in p.modules:
            c.modules[m.id] = m
            c.module_project[m.id] = p.id
            c._add_q(m.retell, m.unlock_day, "project")
        for q in p.deep_dive:
            c._add_q(q, None, "deep_dive")
    return c


@lru_cache
def get_course() -> Course:
    return load_course(settings.content_dir)


def reload_course() -> Course:
    get_course.cache_clear()
    return get_course()

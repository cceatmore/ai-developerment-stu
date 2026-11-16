"""课程内容的数据结构与质量校验。

内容文件位于 content/ 目录，使用 YAML 编写；加载时用这里的模型校验，
不合格的内容（缺字段、过于简略、题目不足）会直接报错，而不是悄悄进入系统。
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Level = Literal["P0", "P1", "P2"]
Dim = Literal["concept", "principle", "project", "engineering"]
Category = Literal["python_backend", "llm", "rag", "agent", "eval", "engineering", "architecture"]
QType = Literal["single", "multi", "judge", "case", "short", "scenario", "design", "oral"]

OBJECTIVE = {"single", "multi", "judge", "case"}
SUBJECTIVE = {"short", "scenario", "design", "oral"}

CATEGORY_LABELS = {
    "python_backend": "Python 与后端",
    "llm": "大模型应用",
    "rag": "RAG",
    "agent": "Agent",
    "eval": "评测与可观测",
    "engineering": "生产工程与安全",
    "architecture": "架构与求职",
}

PHASES = {
    1: "Python 与后端速通",
    2: "大模型应用基础",
    3: "RAG 与知识系统",
    4: "Agent 核心",
    5: "评测、生产化与求职",
}

TOTAL_DAYS = 50
PASS_SCORE = 70

# 阶段卷：每天的 exam 题池固定 4 单选 + 2 多选 + 2 判断 + 1 案例；
# 组卷时从 10 天的题池里抽 20/10/10/4 道，分值 2/3/1/5，合计 100 分。
EXAM_POOL_PER_DAY = {"single": 4, "multi": 2, "judge": 2, "case": 1}
EXAM_PAPER = {"single": (20, 2.0), "multi": (10, 3.0), "judge": (10, 1.0), "case": (4, 5.0)}


def default_category(day: int) -> Category:
    if day <= 10:
        return "python_backend"
    if day <= 20:
        return "llm"
    if day <= 30:
        return "rag"
    if day <= 40:
        return "agent"
    if day <= 44:
        return "eval"
    if day <= 47:
        return "engineering"
    return "architecture"


def _min_len(value: str | None, n: int, field: str) -> None:
    if value is None or len(value.strip()) < n:
        got = 0 if value is None else len(value.strip())
        raise ValueError(f"{field} 过于简略：至少 {n} 字，当前 {got} 字")


class Source(BaseModel):
    title: str
    url: str


class Resource(BaseModel):
    """配套的外部课程/文章/视频。只放真实存在、检索核实过的链接。"""

    title: str
    url: str
    kind: Literal["video", "article", "doc", "course", "repo"]
    lang: Literal["zh", "en"] = "zh"
    minutes: int | None = Field(default=None, ge=1, le=240)
    note: str = Field(min_length=8)  # 看哪一部分、为什么看


class KeyPoint(BaseModel):
    text: str = Field(min_length=4)
    dim: Dim


class Question(BaseModel):
    id: str
    kp: str | None = None
    type: QType
    question: str = Field(min_length=8)
    code: str | None = None  # 读代码题：展示在题干下方的代码
    lang: str = "python"
    options: list[str] | None = None
    answer: list[int] | bool | None = None
    explain: str | None = None
    key_points: list[KeyPoint] = []
    reference: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=4)
    oral: str | None = None
    category: Category | None = None

    @property
    def objective(self) -> bool:
        return self.type in OBJECTIVE

    @model_validator(mode="after")
    def _check(self) -> "Question":
        t = self.type
        if t in ("single", "multi", "case"):
            if not self.options or not (3 <= len(self.options) <= 6):
                raise ValueError(f"{self.id}: 选择题需要 3~6 个选项")
            if not isinstance(self.answer, list) or not self.answer:
                raise ValueError(f"{self.id}: 选择题 answer 必须是选项下标列表")
            if any(i < 0 or i >= len(self.options) for i in self.answer):
                raise ValueError(f"{self.id}: answer 下标越界")
            if t in ("single", "case") and len(self.answer) != 1:
                raise ValueError(f"{self.id}: 单选/案例题只能有一个答案")
            if t == "multi" and len(self.answer) < 2:
                raise ValueError(f"{self.id}: 多选题至少两个正确答案")
            _min_len(self.explain, 40, f"{self.id}.explain")
            if t == "case":
                _min_len(self.question, 80, f"{self.id}.question（案例题需要完整场景）")
        elif t == "judge":
            if not isinstance(self.answer, bool):
                raise ValueError(f"{self.id}: 判断题 answer 必须是 true/false")
            _min_len(self.explain, 40, f"{self.id}.explain")
        else:
            if len(self.key_points) < 3:
                raise ValueError(f"{self.id}: 主观题至少 3 个评分要点")
            _min_len(self.reference, 120, f"{self.id}.reference")
        if self.code is not None and self.code.count("\n") < 3:
            raise ValueError(f"{self.id}: code 至少 4 行，否则直接写进题干")
        return self


class InterviewAsk(BaseModel):
    """讲解里「面试官可能这样问」：问题后面直接给能说出口的短答案。"""

    question: str = Field(min_length=4)
    answer: str = Field(min_length=12)


class KnowledgePoint(BaseModel):
    id: str
    name: str
    level: Level
    summary: str = Field(min_length=8, max_length=120)
    analogy: str | None = None  # 用前端/JS/TS/Vue 经验做类比
    why: str
    problem: str
    principle: str
    scenarios: str
    code: str | None = None
    pitfalls: str
    interview_asks: list[InterviewAsk | str] = Field(min_length=2)
    project_example: str
    freshness: str | None = None
    sources: list[Source] = []

    @model_validator(mode="after")
    def _depth(self) -> "KnowledgePoint":
        need = {"P0": 400, "P1": 250, "P2": 120}[self.level]
        _min_len(self.why, 50, f"{self.id}.why")
        _min_len(self.problem, 50, f"{self.id}.problem")
        _min_len(self.principle, need, f"{self.id}.principle")
        _min_len(self.scenarios, 60, f"{self.id}.scenarios")
        _min_len(self.pitfalls, 80, f"{self.id}.pitfalls")
        _min_len(self.project_example, 80, f"{self.id}.project_example")
        return self


class Day(BaseModel):
    day: int = Field(ge=1, le=TOTAL_DAYS)
    phase: int = Field(ge=1, le=5)
    title: str
    goals: list[str] = Field(min_length=2, max_length=4)
    minutes: int = Field(default=60, ge=30, le=120)
    resources: list[Resource] = Field(min_length=1, max_length=4)
    knowledge_points: list[KnowledgePoint] = Field(min_length=3, max_length=4)
    test: list[Question] = Field(min_length=16, max_length=22)
    exam: list[Question] = Field(min_length=9, max_length=9)
    interview: list[Question] = Field(min_length=3, max_length=3)
    sources: list[Source] = []

    @field_validator("phase")
    @classmethod
    def _phase(cls, v: int, info) -> int:
        day = info.data.get("day")
        if day and v != (day - 1) // 10 + 1:
            raise ValueError(f"Day {day} 的 phase 应为 {(day - 1) // 10 + 1}")
        return v

    @model_validator(mode="after")
    def _check(self) -> "Day":
        prefix = f"d{self.day:02d}-"
        kp_ids = [k.id for k in self.knowledge_points]
        all_ids = kp_ids + [q.id for q in self.test + self.exam + self.interview]
        for i in all_ids:
            if not i.startswith(prefix):
                raise ValueError(f"id {i} 必须以 {prefix} 开头")
        dup = {i for i in all_ids if all_ids.count(i) > 1}
        if dup:
            raise ValueError(f"重复 id: {dup}")
        if not any(k.level == "P0" for k in self.knowledge_points):
            raise ValueError("每天至少一个 P0 知识点")

        for q in self.test + self.exam + self.interview:
            if not q.kp:
                raise ValueError(f"{q.id}: 必须填写 kp（关联知识点）")
            if q.kp not in kp_ids:
                raise ValueError(f"{q.id}: 引用了不存在的知识点 {q.kp}")

        # 当天测试：全部客观题，每个知识点至少 3 题，保证重测时有新题
        types = [q.type for q in self.test]
        if any(t not in ("single", "multi", "judge") for t in types):
            raise ValueError("test 只能是 single/multi/judge")
        if types.count("single") < 7 or types.count("multi") < 3 or types.count("judge") < 3:
            raise ValueError(
                f"test 需要 ≥7 单选、≥3 多选、≥3 判断（当前 {types.count('single')}/{types.count('multi')}/{types.count('judge')}）"
            )
        for k in kp_ids:
            n = sum(q.kp == k for q in self.test)
            if n < 3:
                raise ValueError(f"test 中知识点 {k} 只有 {n} 题，至少 3 题")
        if not any(q.code for q in self.test):
            raise ValueError("test 至少包含 1 道读代码选择题（填写 code 字段）")

        # 阶段卷题池
        got = {t: sum(q.type == t for q in self.exam) for t in EXAM_POOL_PER_DAY}
        if got != EXAM_POOL_PER_DAY:
            raise ValueError(f"exam 需要 4 单选 + 2 多选 + 2 判断 + 1 案例（当前 {got}）")

        # 面试官 3 题：主观题，场景题为主，难度递增
        diffs = []
        for q in self.interview:
            if q.objective:
                raise ValueError(f"{q.id}: 面试题必须是主观题")
            if q.difficulty is None:
                raise ValueError(f"{q.id}: 面试题必须标注 difficulty")
            if len(q.key_points) < 4:
                raise ValueError(f"{q.id}: 面试题至少 4 个评分要点")
            _min_len(q.reference, 200, f"{q.id}.reference")
            _min_len(q.oral, 120, f"{q.id}.oral")
            diffs.append(q.difficulty)
        if diffs != sorted(diffs):
            raise ValueError("面试题难度需要逐渐增加（difficulty 非递减）")
        if sum(q.type in ("scenario", "design") for q in self.interview) < 2:
            raise ValueError("面试 3 题中至少 2 道场景题或设计题")
        return self


class ProjectModule(BaseModel):
    id: str
    name: str
    unlock_day: int = Field(ge=1, le=TOTAL_DAYS)
    minutes: int = Field(ge=20, le=180)
    features: list[str] = Field(min_length=1)
    goal: str
    design: str
    data_flow: str
    key_code: str
    ai_prompt: str  # 交给 AI 编程工具的需求说明
    tests: dict[Literal["functional", "api", "exception", "review"], list[str]]
    retell: Question

    @model_validator(mode="after")
    def _check(self) -> "ProjectModule":
        _min_len(self.design, 200, f"{self.id}.design")
        _min_len(self.data_flow, 80, f"{self.id}.data_flow")
        _min_len(self.key_code, 200, f"{self.id}.key_code")
        _min_len(self.ai_prompt, 120, f"{self.id}.ai_prompt")
        if set(self.tests) != {"functional", "api", "exception", "review"}:
            raise ValueError(f"{self.id}: tests 需要包含 functional/api/exception/review 四类")
        if self.retell.objective:
            raise ValueError(f"{self.id}: retell 必须是主观题")
        return self


class Project(BaseModel):
    id: Literal["p1", "p2", "p3"]
    title: str
    role: str  # 对应岗位
    intro: str
    market: str  # 为什么市场需要、能命中哪些 JD 要求
    tech_stack: str
    architecture: str
    resume: str  # 简历写法模板（指标留空让学员用自己的评测结果填）
    modules: list[ProjectModule] = Field(min_length=6)
    deep_dive: list[Question] = Field(min_length=8)  # 面试官针对本项目的深挖题
    materials: dict[Literal["architecture_doc", "deployment", "interview_pitch"], str]

    @model_validator(mode="after")
    def _check(self) -> "Project":
        for m in self.modules:
            if not m.id.startswith(self.id + "-"):
                raise ValueError(f"模块 id {m.id} 必须以 {self.id}- 开头")
        for q in self.deep_dive:
            if not q.id.startswith(self.id + "-"):
                raise ValueError(f"深挖题 id {q.id} 必须以 {self.id}- 开头")
            if q.objective:
                raise ValueError(f"{q.id}: 深挖题必须是主观题")
        days = [m.unlock_day for m in self.modules]
        if days != sorted(days):
            raise ValueError(f"{self.id}: 模块 unlock_day 需要递增")
        return self


ID_RE = re.compile(r"^d(\d{2})-")

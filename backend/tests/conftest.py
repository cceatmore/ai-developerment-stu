import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

_tmp = Path(tempfile.mkdtemp(prefix="stupy-test-"))
os.environ["STUPY_CONTENT_DIR"] = str(_tmp / "content")
os.environ["STUPY_DATA_DIR"] = str(_tmp / "data")
os.environ["STUPY_FRONTEND_DIST"] = str(_tmp / "dist")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LONG = "这是一段用于测试的足够长的讲解内容。" * 40
CODE = "def f(x):\n    y = x + 1\n    return y\n\nprint(f(1))"


def kp(day: int, n: int, level: str = "P0") -> dict:
    return {
        "id": f"d{day:02d}-k{n}", "name": f"知识点{day}-{n}", "level": level,
        "summary": "一句话总结，便于记忆的要点", "why": LONG, "problem": LONG, "principle": LONG,
        "scenarios": LONG, "pitfalls": LONG, "interview_asks": ["问题一？", "问题二？"],
        "project_example": LONG,
    }


def single(qid: str, kp_id: str, ans: int = 1, **extra) -> dict:
    return {"id": qid, "kp": kp_id, "type": "single", "question": f"单选题 {qid} 的题干内容",
            "options": ["选项甲", "选项乙", "选项丙", "选项丁"], "answer": [ans], "explain": LONG, **extra}


def multi(qid: str, kp_id: str) -> dict:
    return {"id": qid, "kp": kp_id, "type": "multi", "question": f"多选题 {qid} 的题干内容",
            "options": ["选项甲", "选项乙", "选项丙", "选项丁"], "answer": [0, 2], "explain": LONG}


def judge(qid: str, kp_id: str) -> dict:
    return {"id": qid, "kp": kp_id, "type": "judge", "question": f"判断题 {qid} 的题干内容",
            "answer": False, "explain": LONG}


def case(qid: str, kp_id: str) -> dict:
    return single(qid, kp_id, 2, type="case", question="案例：" + "某公司上线了一个知识库问答系统，用户反馈答非所问。" * 4)


def subj(qid: str, kp_id: str, qtype: str = "scenario", **extra) -> dict:
    return {
        "id": qid, "kp": kp_id, "type": qtype, "question": "请分析这个场景并给出你的方案",
        "key_points": [{"text": "要点一：概念", "dim": "concept"}, {"text": "要点二：原理", "dim": "principle"},
                       {"text": "要点三：工程", "dim": "engineering"}, {"text": "要点四：项目", "dim": "project"}],
        "reference": LONG, "oral": LONG, **extra,
    }


def make_day(day: int) -> dict:
    p = f"d{day:02d}"
    kps = [kp(day, 1), kp(day, 2), kp(day, 3, "P1")]
    test = []
    n = 0
    for k in (1, 2, 3):
        kid = f"{p}-k{k}"
        for j in range(4):
            n += 1
            extra = {"code": CODE} if (k, j) == (1, 0) else {}
            test.append(single(f"{p}-t{n}", kid, (n + j) % 4, **extra))
        n += 1
        test.append(multi(f"{p}-t{n}", kid))
        n += 1
        test.append(judge(f"{p}-t{n}", kid))
    exam = [single(f"{p}-e{i}", f"{p}-k{i % 3 + 1}", i % 4) for i in range(1, 5)]
    exam += [multi(f"{p}-e5", f"{p}-k1"), multi(f"{p}-e6", f"{p}-k2"),
             judge(f"{p}-e7", f"{p}-k3"), judge(f"{p}-e8", f"{p}-k1"), case(f"{p}-e9", f"{p}-k2")]
    return {
        "day": day, "phase": (day - 1) // 10 + 1, "title": f"第{day}天主题", "goals": ["目标一", "目标二"],
        "resources": [{"title": "官方文档", "url": "https://example.com/doc", "kind": "doc",
                       "note": "看第一章，了解基本概念"}],
        "knowledge_points": kps,
        "test": test,
        "exam": exam,
        "interview": [subj(f"{p}-i1", f"{p}-k1", difficulty=1),
                      subj(f"{p}-i2", f"{p}-k2", difficulty=2),
                      subj(f"{p}-i3", f"{p}-k3", "design", difficulty=3)],
    }


def make_project() -> dict:
    mods = []
    for i, day in enumerate([2, 3, 4, 5, 6, 7], start=1):
        mods.append({
            "id": f"p1-m{i}", "name": f"模块{i}", "unlock_day": day, "minutes": 45, "features": ["功能"],
            "goal": "目标", "design": LONG, "data_flow": LONG, "key_code": LONG, "ai_prompt": LONG,
            "tests": {"functional": ["功能检查"], "api": ["接口检查"], "exception": ["异常检查"], "review": ["审查"]},
            "retell": subj(f"p1-m{i}-r", None, "short"),
        })
    return {
        "id": "p1", "title": "测试项目", "role": "AI 应用", "intro": "介绍", "market": "市场", "tech_stack": "栈",
        "architecture": "架构", "resume": "简历", "modules": mods,
        "deep_dive": [subj(f"p1-d{i}", None, "design", difficulty=min(4, i)) for i in range(1, 9)],
        "materials": {"architecture_doc": "a", "deployment": "b", "interview_pitch": "c"},
    }


def write_course(days: list[int]) -> None:
    root = Path(os.environ["STUPY_CONTENT_DIR"])
    (root / "days").mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)
    for d in days:
        (root / "days" / f"day{d:02d}.yaml").write_text(
            yaml.safe_dump(make_day(d), allow_unicode=True), encoding="utf-8")
    (root / "projects" / "p1.yaml").write_text(yaml.safe_dump(make_project(), allow_unicode=True), encoding="utf-8")


write_course(list(range(1, 12)))


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c

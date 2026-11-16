from datetime import date

import pytest
import yaml
from freezegun import freeze_time

from conftest import make_day


def course():
    from app.content import get_course

    return get_course()


def right(qid: str):
    q = course().questions[qid]
    return q.answer


def wrong(qid: str):
    q = course().questions[qid]
    if q.type == "judge":
        return not q.answer
    return [next(i for i in range(len(q.options)) if i not in q.answer)]


def answer_all(client, s: dict, fn) -> dict:
    for q in s["questions"]:
        r = client.put(f"/api/sessions/{s['id']}/answer", json={"question_id": q["id"], "answer": fn(q["id"])})
        assert r.status_code == 200, r.text
    r = client.post(f"/api/sessions/{s['id']}/submit")
    assert r.status_code == 200, r.text
    return r.json()


def learn_day(client, day: int) -> None:
    for k in course().days[day].knowledge_points:
        r = client.post(f"/api/days/{day}/learn", json={"kp_id": k.id})
        assert r.status_code == 200, r.text


def pass_day(client, day: int) -> dict:
    learn_day(client, day)
    s = client.post(f"/api/days/{day}/test").json()
    return answer_all(client, s, right)


def do_review_if_needed(client) -> None:
    rv = client.get("/api/review").json()
    if rv["needed"]:
        s = client.post("/api/review/start").json()
        answer_all(client, s, right)


# ---------- 内容校验 ----------


def test_schema_rejects_thin_day():
    from app.content_schema import Day

    d = make_day(1)
    d["test"] = d["test"][:10]
    with pytest.raises(Exception):
        Day.model_validate(d)
    d = make_day(1)
    d["interview"][0]["type"] = "oral"
    d["interview"][1]["type"] = "oral"
    with pytest.raises(Exception, match="场景题"):
        Day.model_validate(d)
    d = make_day(1)
    d["exam"] = d["exam"][:8] + [d["exam"][0] | {"id": "d01-e99"}]
    with pytest.raises(Exception, match="exam"):
        Day.model_validate(d)


def test_course_loaded():
    c = course()
    assert len(c.days) == 11 and not c.errors
    assert len(c.phase_exam_pool(1)) == 90
    assert "p1" in c.projects


# ---------- 解锁与当天测试 ----------


def test_day_locked_until_test_passed(client):
    assert client.post("/api/days/2/learn", json={"kp_id": "d02-k1"}).status_code == 403
    assert client.post("/api/days/1/test").status_code == 403  # 讲解没读完
    learn_day(client, 1)
    s = client.post("/api/days/1/test").json()
    assert len(s["questions"]) == 12
    assert all(q["answer"] is None for q in s["questions"])  # 交卷前不泄露答案
    assert any(q["code"] for q in s["questions"])
    kp_count = {}
    for q in s["questions"]:
        kp_count[q["kp"]] = kp_count.get(q["kp"], 0) + 1
    assert min(kp_count.values()) >= 3

    res = answer_all(client, s, wrong)
    assert res["score"] == 0 and res["passed"] is False
    assert res["questions"][0]["answer"] is not None  # 交卷后显示答案与解析
    assert client.get("/api/dashboard").json()["roadmap"][1]["status"] == "locked"

    s2 = client.post("/api/days/1/test").json()
    assert s2["id"] != s["id"]
    unseen = set(s2["question_ids"] if "question_ids" in s2 else [q["id"] for q in s2["questions"]]) - {
        q["id"] for q in s["questions"]}
    assert len(unseen) >= 6  # 重测优先换没做过的题
    res2 = answer_all(client, s2, right)
    assert res2["passed"] and res2["score"] == 100
    day1 = client.get("/api/days/1").json()
    assert day1["state"]["completed"] and day1["report"]["test_score"] == 100
    assert client.get("/api/days/2").json()["available"]


def test_pending_test_resumes(client):
    learn_day(client, 1)
    s = client.post("/api/days/1/test").json()
    qid = s["questions"][0]["id"]
    client.put(f"/api/sessions/{s['id']}/answer", json={"question_id": qid, "answer": right(qid)})
    again = client.post("/api/days/1/test").json()
    assert again["id"] == s["id"] and again["answers"][qid] == right(qid)


# ---------- 每日复习 ----------


def test_review_gate_next_day(client):
    with freeze_time("2026-11-02 09:00"):  # 周一
        pass_day(client, 1)
        assert not client.get("/api/review").json()["needed"]  # 同一天不需要复习
        learn_day(client, 2)
    with freeze_time("2026-11-03 09:00"):
        rv = client.get("/api/review").json()
        assert rv["needed"] and rv["size"] == 8 and rv["gap"] == 1
        assert client.post("/api/days/2/learn", json={"kp_id": "d02-k1"}).status_code == 403
        st = client.get("/api/days/2").json()["state"]
        assert st["stage"] == "review"
        s = client.post("/api/review/start").json()
        assert 1 <= len(s["questions"]) <= 8
        assert {q["day"] for q in s["questions"]} <= {1, 2}
        days_q = {q["kp"] for q in s["questions"]}
        assert all(k.startswith(("d01", "d02")) for k in days_q)
        res = answer_all(client, s, right)
        assert res["submitted"]
        assert not client.get("/api/review").json()["needed"]
        assert client.post("/api/days/2/learn", json={"kp_id": "d02-k1"}).status_code == 200


def test_review_grows_after_weekend(client):
    with freeze_time("2026-11-06 20:00"):  # 周五
        pass_day(client, 1)
    with freeze_time("2026-11-09 08:00"):  # 周一
        rv = client.get("/api/review").json()
        assert rv["gap"] == 3 and rv["size"] == 16


def test_review_prioritizes_wrong(client):
    with freeze_time("2026-11-02 09:00"):
        learn_day(client, 1)
        s = client.post("/api/days/1/test").json()
        bad = s["questions"][0]["id"]
        answer_all(client, s, lambda q: wrong(q) if q == bad else right(q))
    with freeze_time("2026-11-03 09:00"):
        s = client.post("/api/review/start").json()
        assert bad in [q["id"] for q in s["questions"]]
        assert s["reasons"][bad] == "错题重做"


# ---------- 掌握度 ----------


def test_mastery_needs_multiple_dates(client):
    with freeze_time("2026-11-02 09:00"):
        pass_day(client, 1)
        kps = {k["id"]: k for k in client.get("/api/kps").json()}
        assert kps["d01-k1"]["mastery"] == 2  # 刚学完答得好，只算初步理解
    with freeze_time("2026-11-03 09:00"):
        do_review_if_needed(client)
        kps = {k["id"]: k for k in client.get("/api/kps").json()}
        reviewed = [k for k in kps.values() if k["day"] == 1 and k["attempts"] > 4]
        assert reviewed and all(k["mastery"] == 3 for k in reviewed)


# ---------- 阶段卷 ----------


def test_phase_exam_gates_next_phase(client):
    for d in range(1, 11):
        pass_day(client, d)
    assert not client.get("/api/days/11").json()["available"]
    exams = client.get("/api/exams").json()
    assert exams["phases"][0]["available"] and not exams["phases"][1]["available"]

    s = client.post("/api/exams/1").json()
    types = [course().questions[q["id"]].type for q in s["questions"]]
    assert (types.count("single"), types.count("multi"), types.count("judge"), types.count("case")) == (20, 10, 10, 4)
    assert len({q["day"] for q in s["questions"]}) == 10  # 每天都覆盖到

    only_single = lambda q: right(q) if course().questions[q].type == "single" else wrong(q)  # noqa: E731
    res = answer_all(client, s, only_single)
    assert res["score"] == 40.0 and not res["passed"]
    assert not client.get("/api/days/11").json()["available"]

    s2 = client.post("/api/exams/1").json()
    res2 = answer_all(client, s2, right)
    assert res2["score"] == 100.0 and res2["passed"]
    assert client.get("/api/days/11").json()["available"]
    assert any(r["kind"] == "phase" for r in client.get("/api/reports").json())


def test_multi_partial_credit(client):
    from app.learning import score_objective

    q = course().questions["d01-t5"]
    assert q.type == "multi"
    assert score_objective(q, [0]) == 50.0
    assert score_objective(q, [0, 1]) == 0.0
    assert score_objective(q, [0, 2]) == 100.0


# ---------- 面试题、错题、项目 ----------


def test_interview_self_assessment(client):
    pass_day(client, 1)
    r = client.post("/api/attempts", json={"question_id": "d01-i1", "context": "interview",
                                           "answer": "我的回答", "checks": [1, 1, 0.5, 0], "expression": 4})
    assert r.status_code == 200
    assert r.json()["score"] == round(62.5 * 0.85 + 80 * 0.15, 1)
    assert client.post("/api/attempts", json={"question_id": "d01-i2", "context": "interview",
                                              "answer": "", "checks": [1, 1, 1, 1]}).status_code == 400
    assert client.post("/api/attempts", json={"question_id": "d01-t1", "context": "test",
                                              "answer": [0]}).status_code == 400
    st = client.get("/api/days/1").json()["state"]
    assert st["interview_done"] == 1 and st["stage"] == "interview"


def test_wrong_book_resolution(client):
    learn_day(client, 1)
    s = client.post("/api/days/1/test").json()
    bad = s["questions"][0]["id"]
    answer_all(client, s, lambda q: wrong(q) if q == bad else right(q))
    assert [w["question_id"] for w in client.get("/api/wrong").json()] == [bad]
    for _ in range(2):
        client.post("/api/attempts", json={"question_id": bad, "context": "wrong", "answer": right(bad)})
    assert client.get("/api/wrong").json() == []
    assert len(client.get("/api/wrong?resolved=true").json()) == 1


def test_project_module_unlock_and_complete(client):
    assert client.put("/api/projects/module/p1-m1", json={"note": "x"}).status_code == 403
    pass_day(client, 1)
    dash = client.get("/api/dashboard").json()
    assert dash["projects"]["next"]["id"] == "p1-m1"
    r = client.put("/api/projects/module/p1-m1",
                   json={"checks": {"functional": [0], "api": [0], "exception": [0], "review": [0]}})
    assert r.status_code == 200 and not r.json()["completed"]  # 还没复述
    client.post("/api/attempts", json={"question_id": "p1-m1-r", "context": "project",
                                       "answer": "复述", "checks": [1, 1, 1, 0]})
    r = client.put("/api/projects/module/p1-m1", json={})
    assert r.json()["completed"]
    assert client.get("/api/projects").json()[0]["done"] == 1


def test_mock_hides_answers_until_locked(client):
    assert client.post("/api/mock", json={"mode": "mixed"}).status_code == 400
    pass_day(client, 1)
    m = client.post("/api/mock", json={"mode": "mixed"}).json()
    assert len(m["questions"]) == 3 and all(q["reference"] is None for q in m["questions"])
    m = client.post(f"/api/mock/{m['id']}/lock").json()
    assert all(q["reference"] for q in m["questions"])
    p = client.post("/api/mock", json={"mode": "p1"}).json()
    assert len(p["questions"]) == 6


# ---------- 报告、数据 ----------


def test_final_report_is_honest(client):
    pass_day(client, 1)
    rep = client.get("/api/reports/final").json()
    assert rep["roles"] == []  # 只学了一天，不推荐任何岗位
    assert any("阶段卷" in s for s in rep["shortfalls"])


def test_export_import_roundtrip(client):
    pass_day(client, 1)
    data = client.get("/api/export").json()
    assert data["version"] == 2
    client.post("/api/import", json=data)
    assert client.get("/api/days/1").json()["state"]["completed"]
    assert client.post("/api/import", json={"version": 1, "tables": {}}).status_code == 400


def test_drafts(client):
    client.put("/api/drafts/interview:d01-i1", json={"text": "草稿"})
    assert client.get("/api/drafts/interview:d01-i1").json()["text"] == "草稿"


def test_old_schema_is_archived(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, text

    import app.db as dbm

    f = tmp_path / "study.db"
    eng = create_engine(f"sqlite:///{f}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE day_progress (day INTEGER PRIMARY KEY)"))
    eng.dispose()
    monkeypatch.setattr(dbm, "engine", eng)
    monkeypatch.setattr(dbm.settings, "data_dir", tmp_path)
    dbm._archive_old_schema()
    assert not f.exists()
    assert list((tmp_path / "backups").glob("study-v1-*.db"))


def test_daily_backup_keeps_archives(tmp_path, monkeypatch):
    import sqlite3

    import app.main as m

    monkeypatch.setattr(m.settings, "data_dir", tmp_path)
    c = sqlite3.connect(tmp_path / "study.db")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE t (x)")
    c.execute("INSERT INTO t VALUES (1)")
    c.commit()
    b = tmp_path / "backups"
    b.mkdir()
    (b / "study-v1-20260101.db").write_text("old")
    for i in range(1, 17):
        (b / f"study-2026-01-{i:02d}.db").write_text("x")
    m._daily_backup()
    c.close()
    names = sorted(p.name for p in b.iterdir())
    assert "study-v1-20260101.db" in names
    assert len([n for n in names if n.startswith("study-20")]) == 14
    today = sqlite3.connect(b / f"study-{date.today().isoformat()}.db")
    assert today.execute("SELECT x FROM t").fetchone() == (1,)
    today.close()


def test_access_code_guard(client, monkeypatch):
    from app.main import settings

    monkeypatch.setattr(settings, "access_code", "s3cret")
    assert client.get("/api/dashboard").status_code == 401
    r = client.get("/api/dashboard?code=s3cret", follow_redirects=False)
    assert r.status_code == 303 and "stupy_access" in r.cookies
    assert client.get("/api/dashboard").status_code == 200
    client.cookies.clear()
    assert client.get("/api/dashboard").status_code == 401


def test_content_files_are_valid_yaml():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "content"
    for f in list((root / "days").glob("*.yaml")) + list((root / "projects").glob("*.yaml")):
        yaml.safe_load(f.read_text(encoding="utf-8"))
    assert date.today()

"""学习报告、数据导出/导入、内容管理。"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content import Course, get_course, reload_course
from ..db import DB, Base
from ..learning import LEVEL_NAMES
from ..models import Attempt, KpProgress, Report
from ..reports import build_final_report
from .study import course_dep

router = APIRouter(prefix="/api")


@router.get("/reports")
def list_reports(db: DB):
    rows = db.scalars(select(Report).order_by(Report.id.desc())).all()
    seen, out = set(), []
    for r in rows:  # 同一天/阶段只保留最新一份
        if (r.kind, r.ref) in seen:
            continue
        seen.add((r.kind, r.ref))
        out.append({"id": r.id, "kind": r.kind, "ref": r.ref,
                    "created_at": r.created_at.isoformat(timespec="seconds"), "data": r.data})
    return out


@router.get("/reports/final")
def final_report(db: DB, course: Course = Depends(course_dep)):
    return build_final_report(db, course)


# ---------- 导出 / 导入 ----------


def _ser(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _parse(col, v):
    if v is None:
        return None
    t = col.type.python_type if hasattr(col.type, "python_type") else None
    if t is datetime:
        return datetime.fromisoformat(v)
    if t is date:
        return date.fromisoformat(v)
    return v


@router.get("/export")
def export_all(db: DB):
    data = {"version": 2, "exported_at": datetime.now().isoformat(timespec="seconds"), "tables": {}}
    for table in Base.metadata.sorted_tables:
        rows = db.execute(table.select()).mappings().all()
        data["tables"][table.name] = [{k: _ser(v) for k, v in r.items()} for r in rows]
    name = f"study-backup-{date.today().isoformat()}.json"
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/import")
def import_all(payload: dict, db: DB):
    tables = payload.get("tables")
    if payload.get("version") != 2 or not isinstance(tables, dict):
        raise HTTPException(400, "不是本系统（v2）导出的备份文件")
    known = {t.name: t for t in Base.metadata.sorted_tables}
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    for name, rows in tables.items():
        table = known.get(name)
        if table is None:
            continue
        for r in rows:
            vals = {c.name: _parse(c, r.get(c.name)) for c in table.columns if c.name in r}
            db.execute(table.insert().values(**vals))
    return {"ok": True, "tables": {k: len(v) for k, v in tables.items()}}


@router.get("/export/markdown", response_class=PlainTextResponse)
def export_markdown(db: DB, course: Course = Depends(course_dep)):
    rep = build_final_report(db, course)
    rows = {r.kp_id: r for r in db.scalars(select(KpProgress))}
    ab = rep["ability"]
    exams = "、".join(f"第 {p} 阶段 {v} 分" for p, v in rep["exams"].items()) or "暂无"
    lines = [f"# 学习记录（导出于 {rep['generated_at']}）", "",
             f"- 已学知识点：{ab['learned']}/{ab['total_kps']}，基本掌握及以上：{ab['mastered']}",
             f"- 作答次数：{ab['attempts']}；选择题正确率：{ab['objective_accuracy']}",
             f"- 面试题自评平均分：{ab['interview_score']}；场景/设计题：{ab['scenario']}",
             f"- 阶段卷最高分：{exams}",
             "- 项目：" + "；".join(f"{p['title']} {p['done']}/{p['total']}" for p in rep["projects"]), "",
             "## 知识点掌握情况", "", "| 天 | 知识点 | 等级 | 掌握 | 首次 | 最近 | 错误次数 | 下次复习 |",
             "|---|---|---|---|---|---|---|---|"]
    for kid, k in course.kps.items():
        r = rows.get(kid)
        lv = r.level if r else 0
        lines.append(f"| {course.kp_day[kid]:02d} | {k.name} | {k.level} | {LEVEL_NAMES[lv]} | "
                     f"{r.first_score if r and r.first_score is not None else '-'} | "
                     f"{r.last_score if r and r.last_score is not None else '-'} | "
                     f"{r.wrong_count if r else 0} | {r.next_review if r and r.next_review else '-'} |")
    lines += ["", "## 短板", ""] + [f"- {s}" for s in rep["shortfalls"]] + ["", f"> {rep['note']}"]
    notes = [(kid, r.note) for kid, r in rows.items() if r.note and kid in course.kps]
    if notes:
        lines += ["", "## 我的笔记", ""]
        for kid, n in notes:
            lines += [f"### {course.kps[kid].name}", "", n, ""]
    total = db.query(Attempt).count()
    lines += ["", f"共 {total} 条作答记录，完整数据请使用 JSON 导出。"]
    return "\n".join(lines)


# ---------- 内容管理 ----------


@router.get("/content/status")
def content_status():
    c = get_course()
    return {"days": sorted(c.days), "kps": len(c.kps), "questions": len(c.questions),
            "projects": sorted(c.projects), "modules": len(c.modules), "errors": c.errors}


@router.post("/content/reload")
def content_reload():
    c = reload_course()
    return {"days": len(c.days), "errors": c.errors}

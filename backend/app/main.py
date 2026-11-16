from __future__ import annotations

import hashlib
import hmac
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .content import get_course
from .db import init_db
from .routers import data, practice, study

log = logging.getLogger("stupy")


def _setup_logging() -> None:
    logs = settings.data_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(logs / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("stupy")
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)
        root.addHandler(logging.StreamHandler())


def _daily_backup() -> None:
    db_file = settings.data_dir / "study.db"
    if not db_file.exists():
        return
    backups = settings.data_dir / "backups"
    backups.mkdir(exist_ok=True)
    target = backups / f"study-{date.today().isoformat()}.db"
    if not target.exists():
        src, dst = sqlite3.connect(db_file), sqlite3.connect(target)
        try:
            src.backup(dst)  # 连同 WAL 里尚未合并的写入一起备份
        finally:
            src.close()
            dst.close()
    for old in sorted(backups.glob("study-20*.db"))[:-14]:
        old.unlink()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _setup_logging()
    _daily_backup()
    init_db()
    c = get_course()
    log.info("课程内容加载完成：%d 天，%d 个知识点，%d 道题", len(c.days), len(c.kps), len(c.questions))
    for e in c.errors:
        log.error("内容校验失败：%s", e.splitlines()[0])
    yield


app = FastAPI(title="AI 应用 + Agent 开发工程师 50 天训练系统", lifespan=lifespan)
app.include_router(study.router)
app.include_router(practice.router)
app.include_router(data.router)


_LOGIN_PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>访问码</title><body style="font-family:sans-serif;background:#f6f7f9;display:flex;justify-content:center;padding-top:20vh">
<form method="get" style="background:#fff;padding:24px;border-radius:12px;border:1px solid #e6e8ec">
<div style="margin-bottom:10px">请输入启动时设置的访问码</div>
<input name="code" type="password" autofocus style="padding:8px;font-size:16px">
<button style="padding:8px 16px;font-size:16px">进入</button></form>"""


def _code_token() -> str:
    return hashlib.sha256(("stupy:" + settings.access_code).encode()).hexdigest()


@app.middleware("http")
async def access_guard(request: Request, call_next):
    """局域网访问时要求访问码；本机访问和未设置访问码时不拦截。"""
    host = request.client.host if request.client else ""
    if not settings.access_code or host in ("127.0.0.1", "::1"):
        return await call_next(request)
    if hmac.compare_digest(request.cookies.get("stupy_access", ""), _code_token()):
        return await call_next(request)
    code = request.query_params.get("code")
    if code and hmac.compare_digest(code, settings.access_code):
        resp = RedirectResponse(request.url.path or "/", status_code=303)
        resp.set_cookie("stupy_access", _code_token(), httponly=True, samesite="lax", max_age=30 * 86400)
        return resp
    log.warning("拒绝未授权访问：%s %s", host, request.url.path)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "需要访问码"}, status_code=401)
    return HTMLResponse(_LOGIN_PAGE, status_code=401)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        log.error("%s %s -> %s %s", request.method, request.url.path, exc.status_code, exc.detail)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("未处理异常 %s %s", request.method, request.url.path)
    return JSONResponse({"detail": f"服务器内部错误：{type(exc).__name__}，详情见 data/logs/app.log"}, status_code=500)


@app.get("/api/health")
def health():
    return {"ok": True}


dist = settings.frontend_dist
if (dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "接口不存在")
    file = dist / path
    if path and file.is_file() and dist in file.resolve().parents:
        return FileResponse(file)
    index = dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"detail": "前端尚未构建：请在 frontend 目录执行 npm run build"}, status_code=503)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()

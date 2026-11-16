from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


settings.data_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(conn, _):
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _archive_old_schema() -> None:
    """旧版本的数据库结构不兼容时，整体移到 backups 再新建，旧记录不会丢。"""
    from sqlalchemy import inspect, text

    from .models import SCHEMA_VERSION

    insp = inspect(engine)
    if not insp.has_table("day_progress"):
        return
    version = None
    if insp.has_table("settings"):
        with engine.connect() as conn:
            version = conn.execute(text("SELECT value FROM settings WHERE key='schema_version'")).scalar()
    if version == SCHEMA_VERSION:
        return
    engine.dispose()
    db_file = settings.data_dir / "study.db"
    backups = settings.data_dir / "backups"
    backups.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for suffix in ("", "-wal", "-shm"):
        f = db_file.with_name(db_file.name + suffix)
        if f.exists():
            f.rename(backups / f"study-v{version or 1}-{stamp}.db{suffix}")


def init_db() -> None:
    from . import models

    if settings.db_url.startswith("sqlite:///"):
        _archive_old_schema()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(models.Setting, "schema_version") is None:
            db.add(models.Setting(key="schema_version", value=models.SCHEMA_VERSION))
            db.commit()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# scope="function"：在返回响应之前提交事务，前端紧接着刷新时一定能读到刚写入的数据
DB = Annotated[Session, Depends(get_db, scope="function")]

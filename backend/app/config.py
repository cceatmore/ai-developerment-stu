from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]


class Settings:
    content_dir = Path(os.getenv("STUPY_CONTENT_DIR", ROOT / "content"))
    data_dir = Path(os.getenv("STUPY_DATA_DIR", ROOT / "data"))
    frontend_dist = Path(os.getenv("STUPY_FRONTEND_DIST", ROOT / "frontend" / "dist"))
    host = os.getenv("STUPY_HOST", "127.0.0.1")
    port = int(os.getenv("STUPY_PORT", "8765"))
    access_code = os.getenv("STUPY_ACCESS_CODE", "")

    @property
    def db_url(self) -> str:
        return os.getenv("STUPY_DB_URL", f"sqlite:///{(self.data_dir / 'study.db').as_posix()}")


settings = Settings()

from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-only-change-this",
    )

    # Canonical local runtime database. The repository-root data/ database is legacy only.
    DATABASE_PATH = Path(
        os.getenv(
            "DATABASE_PATH",
            BASE_DIR / "data" / "upnext.db",
        )
    )

    FRONTEND_ORIGIN = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173",
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    EXPOSE_DB_INFO = os.getenv("EXPOSE_DB_INFO", "0") == "1"

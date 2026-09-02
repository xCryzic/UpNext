from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def resolve_database_path(value=None):
    """Resolve relative database paths from the backend directory, never CWD."""
    configured_value = value if value is not None else os.getenv("DATABASE_PATH")
    path = Path(configured_value).expanduser() if configured_value else BASE_DIR / "data" / "upnext.db"
    if path.is_absolute():
        return path
    # Support the legacy project-root-relative spelling without making CWD part
    # of path selection. New configuration should use data/upnext.db.
    if path.parts and path.parts[0].casefold() == "backend":
        path = Path(*path.parts[1:])
    return BASE_DIR / path


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-only-change-this",
    )

    # Canonical local runtime database. Relative overrides are backend-relative.
    DATABASE_PATH = resolve_database_path()

    FRONTEND_ORIGIN = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173",
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    EXPOSE_DB_INFO = os.getenv("EXPOSE_DB_INFO", "0") == "1"
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_OAUTH_CALLBACK_URL = os.getenv("GITHUB_OAUTH_CALLBACK_URL", "")
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_OAUTH_CALLBACK_URL = os.getenv("SPOTIFY_OAUTH_CALLBACK_URL", "")

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


def validate_configuration(app_env, secret_key, configured_database_path):
    if app_env not in {"development", "production"}:
        raise RuntimeError("APP_ENV must be development or production.")
    if app_env == "production" and not secret_key:
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production.")
    if app_env == "production":
        # Accept POSIX deployment paths such as /data/upnext.db even when this
        # configuration is inspected on a Windows development machine.
        is_absolute = configured_database_path and (
            Path(configured_database_path).expanduser().is_absolute()
            or str(configured_database_path).startswith("/")
        )
        if not is_absolute:
            raise RuntimeError("DATABASE_PATH must be an explicit absolute path when APP_ENV=production.")


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    SECRET_KEY = os.getenv("SECRET_KEY") or ("dev-only-change-this" if APP_ENV == "development" else "")

    # Canonical local runtime database. Relative overrides are backend-relative.
    DATABASE_PATH = resolve_database_path()

    FRONTEND_ORIGIN = os.getenv("FRONTEND_URL", os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")).rstrip("/")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = APP_ENV == "production" or os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    DEBUG = APP_ENV == "development" and os.getenv("FLASK_DEBUG", "0") == "1"
    EXPOSE_DB_INFO = os.getenv("EXPOSE_DB_INFO", "0") == "1"
    ADMIN_EMAILS = frozenset(email.strip().lower() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip())
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1") != "0"
    RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
    RATE_LIMIT_SIGNUP_PER_MINUTE = int(os.getenv("RATE_LIMIT_SIGNUP_PER_MINUTE", "5"))
    RATE_LIMIT_REPORTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REPORTS_PER_MINUTE", "5"))
    RATE_LIMIT_OAUTH_PER_MINUTE = int(os.getenv("RATE_LIMIT_OAUTH_PER_MINUTE", "10"))
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_OAUTH_CALLBACK_URL = os.getenv("GITHUB_OAUTH_CALLBACK_URL", "")
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_OAUTH_CALLBACK_URL = os.getenv("SPOTIFY_OAUTH_CALLBACK_URL", "")


validate_configuration(Config.APP_ENV, os.getenv("SECRET_KEY"), os.getenv("DATABASE_PATH"))

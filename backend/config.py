from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def normalize_database_url(value):
    """Normalize provider PostgreSQL URLs for SQLAlchemy's psycopg driver."""
    if value and value.startswith("postgres://"):
        return "postgresql+psycopg://" + value.removeprefix("postgres://")
    if value and value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


def validate_configuration(app_env, secret_key, database_url):
    if app_env not in {"development", "production"}:
        raise RuntimeError("APP_ENV must be development or production.")
    if app_env == "production" and not secret_key:
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production.")
    if app_env == "production" and not database_url:
        raise RuntimeError("DATABASE_URL must be set when APP_ENV=production.")


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    SECRET_KEY = os.getenv("SECRET_KEY") or ("dev-only-change-this" if APP_ENV == "development" else "")

    DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))
    # Vercel Functions do not share a stable process-wide connection pool.
    SQLALCHEMY_SERVERLESS = os.getenv("VERCEL", "") == "1"
    # Flask startup never changes schema; isolated tests opt in explicitly.
    AUTO_CREATE_SCHEMA = False

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


validate_configuration(Config.APP_ENV, os.getenv("SECRET_KEY"), Config.DATABASE_URL)

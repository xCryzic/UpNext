"""SQLAlchemy runtime access. PostgreSQL is mandatory in production."""
from sqlalchemy import create_engine,event
from sqlalchemy.orm import scoped_session,sessionmaker
from sqlalchemy.pool import NullPool
from config import BASE_DIR, Config
from models import Base
_engine=None;_sessions=None
def database_url(config=None):
 settings=config or Config;url=settings.get("DATABASE_URL") if hasattr(settings,"get") else settings.DATABASE_URL
 if url:return url
 env=settings.get("APP_ENV") if hasattr(settings,"get") else settings.APP_ENV
 if env=="production":raise RuntimeError("DATABASE_URL must be set when APP_ENV=production.")
 return f"sqlite:///{BASE_DIR / 'data' / 'upnext-dev.db'}"
def configure_sqlalchemy(config=None):
 global _engine,_sessions
 settings=config or Config
 serverless=settings.get("SQLALCHEMY_SERVERLESS",False) if hasattr(settings,"get") else getattr(settings,"SQLALCHEMY_SERVERLESS",False)
 url=database_url(settings);sqlite=url.startswith("sqlite");_engine=create_engine(url,future=True,pool_pre_ping=True,connect_args={"check_same_thread":False} if sqlite else {},**({"poolclass":NullPool} if sqlite or serverless else {}))
 if sqlite:
  @event.listens_for(_engine,"connect")
  def foreign_keys(connection,_record):connection.execute("PRAGMA foreign_keys=ON")
 _sessions=scoped_session(sessionmaker(bind=_engine,autoflush=False,expire_on_commit=False,future=True));return _engine
def sqlalchemy_session():
 if _sessions is None:configure_sqlalchemy()
 return _sessions()
def remove_sqlalchemy_session():
 if _sessions is not None:_sessions.remove()
def init_db(config=None):
 engine=configure_sqlalchemy(config) if config else (_engine or configure_sqlalchemy());Base.metadata.create_all(engine)

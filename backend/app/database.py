"""Database engine, session factory and the get_db dependency."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    # SQLite needs this because FastAPI may use the connection from different threads
    connect_args={"check_same_thread": False} if is_sqlite else {},
)

if is_sqlite:
    # SQLite ignores foreign keys unless this is switched on for every connection
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        """Turn on foreign key enforcement for a new SQLite connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class every SQLAlchemy model inherits from."""
    pass


def get_db():
    """FastAPI dependency: one database session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

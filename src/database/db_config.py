"""Database engine, session factory and declarative Base.

The database URL comes from `config.settings.database_url` (configurable via
`.env`). Relative SQLite paths are resolved against the project root so the
same DB file is used regardless of the current working directory.
"""

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from sqlalchemy import DateTime, MetaData, create_engine, event, func
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from config import BASE_DIR, settings

# Deterministic constraint names: required for reliable Alembic migrations,
# especially SQLite "batch" mode which recreates tables.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds `created_at` / `updated_at`, populated in Python and as a DB fallback."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Engine / session
# ---------------------------------------------------------------------------


def resolve_database_url(url: str | URL) -> URL:
    """Make relative SQLite file paths absolute (relative to project root)."""
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        db = parsed.database
        if db and db != ":memory:" and not db.startswith("file:"):
            path = Path(db)
            if not path.is_absolute():
                path = (BASE_DIR / path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            parsed = parsed.set(database=str(path))
    return parsed


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite ignores FOREIGN KEY constraints unless enabled per connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_engine(url: str | URL | None = None, **kwargs) -> Engine:
    resolved = resolve_database_url(url or settings.database_url)
    if resolved.get_backend_name() == "sqlite":
        # Allow use across FastAPI's threadpool.
        kwargs.setdefault("connect_args", {"check_same_thread": False})
    return create_engine(resolved, **kwargs)


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

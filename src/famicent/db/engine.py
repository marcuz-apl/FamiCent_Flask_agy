"""SQLAlchemy engine and session management.

Creates the SQLite engine with WAL mode (R16) and provides a scoped session
factory for use across the application.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Default database path — data/ subdirectory next to the project root
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "famicent.db"

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _enable_wal(dbapi_conn: object, _connection_record: object) -> None:
    """Enable WAL mode on every new SQLite connection (R16)."""
    cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(db_path: Path | str | None = None, echo: bool = False) -> Engine:
    """Return the singleton SQLAlchemy engine, creating it if needed.

    Args:
        db_path: Path to the SQLite file. Defaults to ``famicent.db`` in project root.
            Use ``:memory:`` for testing.
        echo: If True, log all SQL statements.

    Returns:
        The SQLAlchemy ``Engine`` instance.
    """
    global _engine
    if _engine is not None:
        return _engine

    if db_path is None:
        db_path = _DEFAULT_DB_PATH

    url = f"sqlite:///{db_path}" if str(db_path) != ":memory:" else "sqlite:///:memory:"
    _engine = create_engine(url, echo=echo)
    event.listen(_engine, "connect", _enable_wal)
    logger.info("Database engine created: %s", url)
    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return the singleton session factory.

    Args:
        engine: Optional engine override. Uses the global engine if omitted.

    Returns:
        A ``sessionmaker`` bound to the engine.
    """
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory

    if engine is None:
        engine = get_engine()

    _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    return _SessionFactory


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Open a new database session as a context manager.

    Usage::

        with get_session() as db:
            db.add(obj)
            db.commit()

    Args:
        engine: Optional engine override.

    Yields:
        A ``Session`` instance that is closed automatically on exit.
    """
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose the current engine and clear singletons (useful in tests)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None

from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Generator, Iterable
from typing import Any

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

DbConnection = Any


def _make_sqlite_connection() -> sqlite3.Connection:
    path = settings.database_file
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    logger.debug("Opened SQLite connection to %s", path)
    return conn


def _make_postgres_connection() -> Any:
    import psycopg2
    import psycopg2.extras

    try:
        from pgvector.psycopg2 import register_vector
    except ImportError:
        register_vector = None

    conn = psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
        options="-c search_path=public",
    )
    conn.autocommit = False
    if register_vector:
        register_vector(conn)
    logger.debug("Opened Postgres connection")
    return conn


def get_db_connection() -> DbConnection:
    if settings.use_postgres:
        return _make_postgres_connection()
    return _make_sqlite_connection()


def get_db_path():
    """Backward-compatible helper for logging."""
    return settings.database_file


def adapt_sql(sql: str) -> str:
    """Translate Postgres-oriented SQL for SQLite when needed."""
    if settings.use_postgres:
        return sql
    out = sql.replace("%s", "?")
    out = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", out, flags=re.IGNORECASE)
    return out


def db_execute(conn: DbConnection, sql: str, params: tuple | list | None = None) -> Any:
    sql = adapt_sql(sql)
    params = params or ()
    if settings.use_postgres:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)


def db_executemany(conn: DbConnection, sql: str, params_seq: list[tuple]) -> None:
    sql = adapt_sql(sql)
    if settings.use_postgres:
        cur = conn.cursor()
        cur.executemany(sql, params_seq)
    else:
        conn.executemany(sql, params_seq)


def insert_returning_id(conn: DbConnection, sql: str, params: tuple) -> int:
    if settings.use_postgres:
        if "RETURNING" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        cur = db_execute(conn, sql, params)
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT did not return id")
        return int(row["id"])
    sql_sqlite = re.sub(r"\s+RETURNING\s+id\s*;?\s*$", "", sql, flags=re.IGNORECASE)
    cur = db_execute(conn, sql_sqlite, params)
    return int(cur.lastrowid)


def is_integrity_error(exc: BaseException) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    try:
        import psycopg2

        return isinstance(exc, psycopg2.IntegrityError)
    except ImportError:
        return False


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [row_to_dict(r) for r in rows if r is not None]


def get_db() -> Generator[DbConnection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
        logger.debug("Committed transaction")
    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            logger.debug("Rolled back transaction (HTTP %s)", e.status_code)
        else:
            logger.warning("Rolled back transaction due to error", exc_info=True)
        raise
    finally:
        conn.close()
        logger.debug("Closed DB connection")

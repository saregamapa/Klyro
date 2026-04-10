from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    return settings.database_file


def get_db_connection() -> sqlite3.Connection:
    """
    Return a new SQLite connection with row access by column name and FK enforcement.
    Prefer the FastAPI dependency ``get_db`` for request-scoped connections (commit/rollback/close).
    """
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    logger.debug("Opened SQLite connection to %s", path)
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(r) for r in rows if r is not None]


def get_db() -> Generator[sqlite3.Connection, None, None]:
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
        logger.debug("Closed SQLite connection")

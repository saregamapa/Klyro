from __future__ import annotations

import logging
import sqlite3
from typing import Any

from app.db.database import row_to_dict

logger = logging.getLogger(__name__)


def create_user(conn: sqlite3.Connection, email: str, password_hash: str) -> int:
    logger.debug("create_user email=%s", email)
    cur = conn.execute(
        """
        INSERT INTO users (email, password_hash)
        VALUES (?, ?)
        """,
        (email, password_hash),
    )
    new_id = int(cur.lastrowid)
    logger.info("Created user id=%s", new_id)
    return new_id


def get_user_by_email(conn: sqlite3.Connection, email: str) -> dict[str, Any] | None:
    logger.debug("get_user_by_email email=%s", email)
    cur = conn.execute(
        """
        SELECT id, email, password_hash, created_at
        FROM users
        WHERE email = ?
        """,
        (email,),
    )
    row = cur.fetchone()
    return row_to_dict(row)


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    logger.debug("get_user_by_id id=%s", user_id)
    cur = conn.execute(
        """
        SELECT id, email, password_hash, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    return row_to_dict(cur.fetchone())

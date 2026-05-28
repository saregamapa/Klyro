from __future__ import annotations

import logging
from typing import Any

from app.db.database import db_execute, insert_returning_id, row_to_dict

logger = logging.getLogger(__name__)


def create_user(conn: Any, email: str, password_hash: str) -> int:
    logger.debug("create_user email=%s", email)
    new_id = insert_returning_id(
        conn,
        "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
        (email, password_hash),
    )
    logger.info("Created user id=%s", new_id)
    return new_id


def get_user_by_email(conn: Any, email: str) -> dict[str, Any] | None:
    cur = db_execute(
        conn,
        "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
        (email,),
    )
    return row_to_dict(cur.fetchone())


def get_user_by_id(conn: Any, user_id: int) -> dict[str, Any] | None:
    cur = db_execute(
        conn,
        "SELECT id, email, password_hash, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    return row_to_dict(cur.fetchone())

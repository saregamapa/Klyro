from __future__ import annotations

import logging
import sqlite3
from typing import Any

from app.db.database import row_to_dict, rows_to_dicts

logger = logging.getLogger(__name__)


def create_chatbot(
    conn: sqlite3.Connection,
    user_id: int,
    name: str,
    website_url: str | None,
) -> int:
    logger.debug("create_chatbot user_id=%s name=%s", user_id, name)
    cur = conn.execute(
        """
        INSERT INTO chatbots (user_id, name, website_url)
        VALUES (?, ?, ?)
        """,
        (user_id, name, website_url),
    )
    new_id = int(cur.lastrowid)
    logger.info("Created chatbot id=%s", new_id)
    return new_id


def get_chatbots_by_user(conn: sqlite3.Connection, user_id: int) -> list[dict[str, Any]]:
    logger.debug("get_chatbots_by_user user_id=%s", user_id)
    cur = conn.execute(
        """
        SELECT id, user_id, name, website_url, created_at
        FROM chatbots
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,),
    )
    return rows_to_dicts(cur.fetchall())


def get_chatbot_by_id(conn: sqlite3.Connection, chatbot_id: int) -> dict[str, Any] | None:
    logger.debug("get_chatbot_by_id id=%s", chatbot_id)
    cur = conn.execute(
        """
        SELECT id, user_id, name, website_url, created_at
        FROM chatbots
        WHERE id = ?
        """,
        (chatbot_id,),
    )
    return row_to_dict(cur.fetchone())


def delete_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> bool:
    logger.debug("delete_chatbot id=%s", chatbot_id)
    cur = conn.execute("DELETE FROM chatbots WHERE id = ?", (chatbot_id,))
    deleted = cur.rowcount > 0
    if deleted:
        logger.info("Deleted chatbot id=%s", chatbot_id)
    else:
        logger.info("No chatbot deleted for id=%s", chatbot_id)
    return deleted

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from app.db.database import rows_to_dicts

logger = logging.getLogger(__name__)


def create_lead(
    conn: sqlite3.Connection,
    chatbot_id: int,
    name: str | None,
    email: str | None,
    message: str | None,
) -> int:
    logger.debug("create_lead chatbot_id=%s", chatbot_id)
    cur = conn.execute(
        """
        INSERT INTO leads (chatbot_id, name, email, message)
        VALUES (?, ?, ?, ?)
        """,
        (chatbot_id, name, email, message),
    )
    new_id = int(cur.lastrowid)
    logger.info("Created lead id=%s chatbot_id=%s", new_id, chatbot_id)
    return new_id


def list_leads_for_chatbot(
    conn: sqlite3.Connection,
    chatbot_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT id, chatbot_id, name, email, message
        FROM leads
        WHERE chatbot_id = ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (chatbot_id, limit, offset),
    )
    return rows_to_dicts(cur.fetchall())


def count_leads_for_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) AS c FROM leads WHERE chatbot_id = ?",
        (chatbot_id,),
    )
    row = cur.fetchone()
    return int(row["c"])

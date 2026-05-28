from __future__ import annotations

import logging
import sqlite3
from typing import Any

from app.db.database import rows_to_dicts

logger = logging.getLogger(__name__)


def save_conversation(
    conn: sqlite3.Connection,
    chatbot_id: int,
    user_message: str,
    bot_response: str,
    *,
    session_id: str | None = None,
) -> int:
    logger.debug("save_conversation chatbot_id=%s session_id=%s", chatbot_id, session_id)
    sid = (session_id or "").strip()
    cur = conn.execute(
        """
        INSERT INTO conversations (chatbot_id, session_id, user_message, bot_response)
        VALUES (?, ?, ?, ?)
        """,
        (chatbot_id, sid, user_message, bot_response),
    )
    new_id = int(cur.lastrowid)
    logger.info("Saved conversation id=%s chatbot_id=%s", new_id, chatbot_id)
    return new_id


def count_conversations_for_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) AS c FROM conversations WHERE chatbot_id = ?",
        (chatbot_id,),
    )
    row = cur.fetchone()
    return int(row["c"])


def top_questions_for_chatbot(
    conn: sqlite3.Connection,
    chatbot_id: int,
    *,
    limit: int = 15,
) -> list[tuple[str, int]]:
    """
    Group by normalized (lower + trim) user_message; return (representative question, count).
    Representative is MIN(user_message) for stable ordering.
    """
    cur = conn.execute(
        """
        SELECT MIN(user_message) AS question, COUNT(*) AS cnt
        FROM conversations
        WHERE chatbot_id = ?
        GROUP BY LOWER(TRIM(user_message))
        ORDER BY cnt DESC, question ASC
        LIMIT ?
        """,
        (chatbot_id, limit),
    )
    return [(str(r["question"]), int(r["cnt"])) for r in cur.fetchall()]


def get_session_history(
    conn: sqlite3.Connection,
    chatbot_id: int,
    session_id: str,
    *,
    limit: int = 10,
) -> list[dict[str, str]]:
    """
    Return the last `limit` exchanges for a session as OpenAI-style role/content dicts.
    """
    sid = session_id.strip()
    if not sid:
        return []
    cur = conn.execute(
        """
        SELECT user_message, bot_response
        FROM conversations
        WHERE chatbot_id = ? AND session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (chatbot_id, sid, limit),
    )
    rows = cur.fetchall()
    messages: list[dict[str, str]] = []
    for row in reversed(rows):
        messages.append({"role": "user", "content": row["user_message"]})
        messages.append({"role": "assistant", "content": row["bot_response"]})
    return messages


def stats_for_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> dict[str, object]:
    cur = conn.execute(
        """
        SELECT
            COUNT(*) AS total_exchanges,
            COUNT(DISTINCT CASE
                WHEN session_id IS NOT NULL AND TRIM(session_id) != ''
                THEN session_id
                ELSE 'row-' || id
            END) AS total_conversations,
            MAX(created_at) AS last_activity
        FROM conversations
        WHERE chatbot_id = ?
        """,
        (chatbot_id,),
    )
    row = cur.fetchone()
    exchanges = int(row["total_exchanges"] or 0)
    return {
        "total_conversations": int(row["total_conversations"] or 0),
        "total_messages": exchanges * 2,
        "last_activity": row["last_activity"],
    }


def get_conversations_by_chatbot(
    conn: sqlite3.Connection,
    chatbot_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    logger.debug("get_conversations_by_chatbot chatbot_id=%s limit=%s offset=%s", chatbot_id, limit, offset)
    cur = conn.execute(
        """
        SELECT id, chatbot_id, session_id, user_message, bot_response, created_at
        FROM conversations
        WHERE chatbot_id = ?
        ORDER BY id ASC
        LIMIT ? OFFSET ?
        """,
        (chatbot_id, limit, offset),
    )
    return rows_to_dicts(cur.fetchall())

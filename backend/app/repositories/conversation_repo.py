from __future__ import annotations

import logging
from typing import Any

from app.db.database import db_execute, insert_returning_id, rows_to_dicts

logger = logging.getLogger(__name__)


def save_conversation(
    conn: Any,
    chatbot_id: int,
    user_message: str,
    bot_response: str,
    *,
    session_id: str | None = None,
) -> int:
    sid = (session_id or "").strip()
    return insert_returning_id(
        conn,
        """
        INSERT INTO conversations (chatbot_id, session_id, user_message, bot_response)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (chatbot_id, sid, user_message, bot_response),
    )


def count_conversations_for_chatbot(conn: Any, chatbot_id: int) -> int:
    cur = db_execute(
        conn,
        "SELECT COUNT(*) AS c FROM conversations WHERE chatbot_id = %s",
        (chatbot_id,),
    )
    row = cur.fetchone()
    return int(row["c"])


def top_questions_for_chatbot(
    conn: Any,
    chatbot_id: int,
    *,
    limit: int = 15,
) -> list[tuple[str, int]]:
    cur = db_execute(
        conn,
        """
        SELECT MIN(user_message) AS question, COUNT(*) AS cnt
        FROM conversations
        WHERE chatbot_id = %s
        GROUP BY LOWER(TRIM(user_message))
        ORDER BY cnt DESC, question ASC
        LIMIT %s
        """,
        (chatbot_id, limit),
    )
    return [(str(r["question"]), int(r["cnt"])) for r in cur.fetchall()]


def get_session_history(
    conn: Any,
    chatbot_id: int,
    session_id: str,
    *,
    limit: int = 10,
) -> list[dict[str, str]]:
    sid = session_id.strip()
    if not sid:
        return []
    cur = db_execute(
        conn,
        """
        SELECT user_message, bot_response
        FROM conversations
        WHERE chatbot_id = %s AND session_id = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (chatbot_id, sid, limit),
    )
    rows = cur.fetchall()
    messages: list[dict[str, str]] = []
    for row in reversed(rows):
        messages.append({"role": "user", "content": row["user_message"]})
        messages.append({"role": "assistant", "content": row["bot_response"]})
    return messages


def stats_for_chatbot(conn: Any, chatbot_id: int) -> dict[str, object]:
    cur = db_execute(
        conn,
        """
        SELECT
            COUNT(*) AS total_exchanges,
            COUNT(DISTINCT CASE
                WHEN session_id IS NOT NULL AND TRIM(session_id) != ''
                THEN session_id
                ELSE 'row-' || CAST(id AS TEXT)
            END) AS total_conversations,
            MAX(created_at) AS last_activity
        FROM conversations
        WHERE chatbot_id = %s
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
    conn: Any,
    chatbot_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    cur = db_execute(
        conn,
        """
        SELECT id, chatbot_id, session_id, user_message, bot_response, created_at
        FROM conversations
        WHERE chatbot_id = %s
        ORDER BY id ASC
        LIMIT %s OFFSET %s
        """,
        (chatbot_id, limit, offset),
    )
    return rows_to_dicts(cur.fetchall())

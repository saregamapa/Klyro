from __future__ import annotations

import logging
from typing import Any

from app.db.database import db_execute, insert_returning_id, row_to_dict, rows_to_dicts

logger = logging.getLogger(__name__)


def create_chatbot(
    conn: Any,
    user_id: int,
    name: str,
    website_url: str | None,
) -> int:
    logger.debug("create_chatbot user_id=%s name=%s", user_id, name)
    new_id = insert_returning_id(
        conn,
        """
        INSERT INTO chatbots (user_id, name, website_url, system_prompt, accent_color)
        VALUES (%s, %s, %s, '', '#6366f1')
        RETURNING id
        """,
        (user_id, name, website_url),
    )
    logger.info("Created chatbot id=%s", new_id)
    return new_id


def get_chatbots_by_user(conn: Any, user_id: int) -> list[dict[str, Any]]:
    cur = db_execute(
        conn,
        """
        SELECT id, user_id, name, website_url, system_prompt, accent_color,
               scraped_content, created_at
        FROM chatbots
        WHERE user_id = %s
        ORDER BY id DESC
        """,
        (user_id,),
    )
    return rows_to_dicts(cur.fetchall())


def get_chatbot_by_id(conn: Any, chatbot_id: int) -> dict[str, Any] | None:
    cur = db_execute(
        conn,
        """
        SELECT id, user_id, name, website_url, system_prompt, accent_color,
               scraped_content, created_at
        FROM chatbots
        WHERE id = %s
        """,
        (chatbot_id,),
    )
    return row_to_dict(cur.fetchone())


def update_chatbot(
    conn: Any,
    chatbot_id: int,
    user_id: int,
    *,
    name: str | None = None,
    website_url: str | None = None,
    system_prompt: str | None = None,
    accent_color: str | None = None,
) -> bool:
    row = get_chatbot_by_id(conn, chatbot_id)
    if row is None or row["user_id"] != user_id:
        return False

    fields: list[str] = []
    values: list[object] = []
    if name is not None:
        fields.append("name = %s")
        values.append(name)
    if website_url is not None:
        fields.append("website_url = %s")
        values.append(website_url)
    if system_prompt is not None:
        fields.append("system_prompt = %s")
        values.append(system_prompt)
    if accent_color is not None:
        fields.append("accent_color = %s")
        values.append(accent_color)
    if not fields:
        return True

    values.extend([chatbot_id, user_id])
    cur = db_execute(
        conn,
        f"UPDATE chatbots SET {', '.join(fields)} WHERE id = %s AND user_id = %s",
        tuple(values),
    )
    return cur.rowcount > 0


def update_scraped_content(conn: Any, chatbot_id: int, content: str) -> None:
    db_execute(
        conn,
        "UPDATE chatbots SET scraped_content = %s WHERE id = %s",
        (content, chatbot_id),
    )


def delete_chatbot(conn: Any, chatbot_id: int) -> bool:
    cur = db_execute(conn, "DELETE FROM chatbots WHERE id = %s", (chatbot_id,))
    return cur.rowcount > 0

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
        INSERT INTO chatbots (user_id, name, website_url, system_prompt, accent_color)
        VALUES (?, ?, ?, '', '#6366f1')
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
        SELECT id, user_id, name, website_url, system_prompt, accent_color,
               scraped_content, created_at
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
        SELECT id, user_id, name, website_url, system_prompt, accent_color,
               scraped_content, created_at
        FROM chatbots
        WHERE id = ?
        """,
        (chatbot_id,),
    )
    return row_to_dict(cur.fetchone())


def update_chatbot(
    conn: sqlite3.Connection,
    chatbot_id: int,
    user_id: int,
    *,
    name: str | None = None,
    website_url: str | None = None,
    system_prompt: str | None = None,
    accent_color: str | None = None,
) -> bool:
    """Update owned chatbot fields. Returns False if not found or not owned."""
    row = get_chatbot_by_id(conn, chatbot_id)
    if row is None or row["user_id"] != user_id:
        return False

    fields: list[str] = []
    values: list[object] = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if website_url is not None:
        fields.append("website_url = ?")
        values.append(website_url)
    if system_prompt is not None:
        fields.append("system_prompt = ?")
        values.append(system_prompt)
    if accent_color is not None:
        fields.append("accent_color = ?")
        values.append(accent_color)
    if not fields:
        return True

    values.extend([chatbot_id, user_id])
    cur = conn.execute(
        f"UPDATE chatbots SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
        values,
    )
    return cur.rowcount > 0


def update_scraped_content(
    conn: sqlite3.Connection, chatbot_id: int, content: str
) -> None:
    conn.execute(
        "UPDATE chatbots SET scraped_content = ? WHERE id = ?",
        (content, chatbot_id),
    )


def delete_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> bool:
    logger.debug("delete_chatbot id=%s", chatbot_id)
    cur = conn.execute("DELETE FROM chatbots WHERE id = ?", (chatbot_id,))
    deleted = cur.rowcount > 0
    if deleted:
        logger.info("Deleted chatbot id=%s", chatbot_id)
    else:
        logger.info("No chatbot deleted for id=%s", chatbot_id)
    return deleted

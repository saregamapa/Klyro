from __future__ import annotations

import logging
from typing import Any

from app.db.database import db_execute, insert_returning_id, rows_to_dicts

logger = logging.getLogger(__name__)


def create_lead(
    conn: Any,
    chatbot_id: int,
    name: str | None,
    email: str | None,
    message: str | None,
    *,
    phone: str | None = None,
) -> int:
    return insert_returning_id(
        conn,
        """
        INSERT INTO leads (chatbot_id, name, email, message, phone)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (chatbot_id, name, email, message, phone),
    )


def list_leads_for_chatbot(
    conn: Any,
    chatbot_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    cur = db_execute(
        conn,
        """
        SELECT id, chatbot_id, name, email, message, phone, created_at
        FROM leads
        WHERE chatbot_id = %s
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (chatbot_id, limit, offset),
    )
    return rows_to_dicts(cur.fetchall())


def upsert_lead_email(
    conn: Any,
    chatbot_id: int,
    email: str,
    *,
    name: str | None = None,
    phone: str | None = None,
) -> int:
    em = email.strip().lower()
    cur = db_execute(
        conn,
        """
        SELECT id FROM leads
        WHERE chatbot_id = %s AND LOWER(TRIM(email)) = %s
        ORDER BY id DESC LIMIT 1
        """,
        (chatbot_id, em),
    )
    existing = cur.fetchone()
    if existing:
        lead_id = int(existing["id"])
        if name or phone:
            db_execute(
                conn,
                """
                UPDATE leads
                SET name = COALESCE(%s, name),
                    phone = COALESCE(%s, phone)
                WHERE id = %s
                """,
                (name, phone, lead_id),
            )
        return lead_id
    lead_id = create_lead(conn, chatbot_id, name, em, None)

    try:
        import threading

        from app.db.database import db_execute, row_to_dict

        cur = db_execute(
            conn,
            """
            SELECT c.name, u.email FROM chatbots c
            JOIN users u ON u.id = c.user_id
            WHERE c.id = %s
            """,
            (chatbot_id,),
        )
        meta = row_to_dict(cur.fetchone())
        if meta:
            from app.services.email import send_lead_notification

            threading.Thread(
                target=send_lead_notification,
                args=(meta["email"], meta["name"], email, name or ""),
                daemon=True,
            ).start()
    except Exception:
        pass

    return lead_id


def count_leads_for_chatbot(conn: Any, chatbot_id: int) -> int:
    cur = db_execute(
        conn,
        "SELECT COUNT(*) AS c FROM leads WHERE chatbot_id = %s",
        (chatbot_id,),
    )
    row = cur.fetchone()
    return int(row["c"])

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.core.config import settings
from app.db.database import db_execute

logger = logging.getLogger(__name__)


def _current_period() -> date:
    today = datetime.now(tz=timezone.utc).date()
    return today.replace(day=1)


def _period_key() -> str:
    return _current_period().isoformat()


def get_message_count(conn: Any, user_id: int) -> int:
    period = _period_key()
    cur = db_execute(
        conn,
        "SELECT count FROM message_usage WHERE user_id = %s AND period = %s",
        (user_id, period),
    )
    row = cur.fetchone()
    return int(row["count"]) if row else 0


def increment_message_count(conn: Any, user_id: int, by: int = 1) -> int:
    period = _period_key()
    if settings.use_postgres:
        cur = db_execute(
            conn,
            """
            INSERT INTO message_usage (user_id, period, count)
            VALUES (%s, %s::date, %s)
            ON CONFLICT (user_id, period) DO UPDATE
                SET count = message_usage.count + EXCLUDED.count
            RETURNING count
            """,
            (user_id, period, by),
        )
        row = cur.fetchone()
        return int(row["count"]) if row else by

    db_execute(
        conn,
        """
        INSERT INTO message_usage (user_id, period, count)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, period) DO UPDATE
            SET count = count + %s
        """,
        (user_id, period, by, by),
    )
    return get_message_count(conn, user_id)


def get_chatbot_count(conn: Any, user_id: int) -> int:
    cur = db_execute(
        conn,
        "SELECT COUNT(*) AS n FROM chatbots WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    return int(row["n"]) if row else 0

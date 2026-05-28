from __future__ import annotations

import json
import logging
from typing import Any

from app.db.database import db_execute, insert_returning_id, row_to_dict

logger = logging.getLogger(__name__)


def enqueue(
    conn: Any,
    chatbot_id: int,
    job_type: str,
    payload: dict | None = None,
) -> int:
    """Insert a pending job and return its id."""
    payload_str = json.dumps(payload or {})
    job_id = insert_returning_id(
        conn,
        """
        INSERT INTO ingest_jobs (chatbot_id, job_type, payload)
        VALUES (%s, %s, %s) RETURNING id
        """,
        (chatbot_id, job_type, payload_str),
    )
    logger.info("Enqueued job id=%s type=%s chatbot_id=%s", job_id, job_type, chatbot_id)
    return job_id


def get_job(conn: Any, job_id: int) -> dict[str, Any] | None:
    cur = db_execute(conn, "SELECT * FROM ingest_jobs WHERE id = %s", (job_id,))
    return row_to_dict(cur.fetchone())


def claim_next_pending(conn: Any) -> dict[str, Any] | None:
    """
    Atomically claim the oldest pending job using SELECT FOR UPDATE SKIP LOCKED.
    Returns None if no pending jobs exist.
    SQLite fallback: simple SELECT + UPDATE (single worker, race condition acceptable).
    """
    from app.core.config import settings

    if settings.use_postgres:
        cur = db_execute(
            conn,
            """
            UPDATE ingest_jobs
            SET status = 'running', started_at = NOW()
            WHERE id = (
                SELECT id FROM ingest_jobs
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *
            """,
            (),
        )
        return row_to_dict(cur.fetchone())

    cur = db_execute(
        conn,
        "SELECT * FROM ingest_jobs WHERE status='pending' ORDER BY created_at LIMIT 1",
        (),
    )
    row = row_to_dict(cur.fetchone())
    if row is None:
        return None
    db_execute(
        conn,
        "UPDATE ingest_jobs SET status='running', started_at=CURRENT_TIMESTAMP WHERE id=%s",
        (row["id"],),
    )
    conn.commit()
    return row


def mark_done(conn: Any, job_id: int, result: dict) -> None:
    db_execute(
        conn,
        "UPDATE ingest_jobs SET status='done', finished_at=NOW(), result=%s WHERE id=%s",
        (json.dumps(result), job_id),
    )


def mark_error(conn: Any, job_id: int, error: str) -> None:
    db_execute(
        conn,
        "UPDATE ingest_jobs SET status='error', finished_at=NOW(), error=%s WHERE id=%s",
        (error[:2000], job_id),
    )

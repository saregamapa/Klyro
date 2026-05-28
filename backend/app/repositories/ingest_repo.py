from __future__ import annotations

import logging
from typing import Any

from app.db.database import db_execute, db_executemany

logger = logging.getLogger(__name__)


def delete_chunks_for_chatbot(conn: Any, chatbot_id: int) -> None:
    db_execute(conn, "DELETE FROM ingest_chunks WHERE chatbot_id = %s", (chatbot_id,))


def max_chunk_index(conn: Any, chatbot_id: int) -> int:
    cur = db_execute(
        conn,
        "SELECT COALESCE(MAX(chunk_index), -1) AS m FROM ingest_chunks WHERE chatbot_id = %s",
        (chatbot_id,),
    )
    row = cur.fetchone()
    return int(row["m"])


def insert_chunks(
    conn: Any,
    chatbot_id: int,
    rows: list[tuple[str, int, str]],
) -> int:
    if not rows:
        return 0
    params = [(chatbot_id, url, i, content) for url, i, content in rows]
    db_executemany(
        conn,
        """
        INSERT INTO ingest_chunks (chatbot_id, source_url, chunk_index, content)
        VALUES (%s, %s, %s, %s)
        """,
        params,
    )
    return len(rows)

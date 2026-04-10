from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def delete_chunks_for_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> None:
    logger.debug("delete_chunks_for_chatbot chatbot_id=%s", chatbot_id)
    conn.execute("DELETE FROM ingest_chunks WHERE chatbot_id = ?", (chatbot_id,))


def max_chunk_index(conn: sqlite3.Connection, chatbot_id: int) -> int:
    cur = conn.execute(
        "SELECT COALESCE(MAX(chunk_index), -1) AS m FROM ingest_chunks WHERE chatbot_id = ?",
        (chatbot_id,),
    )
    row = cur.fetchone()
    return int(row["m"])


def insert_chunks(
    conn: sqlite3.Connection,
    chatbot_id: int,
    rows: list[tuple[str, int, str]],
) -> int:
    """
    rows: (source_url, chunk_index, content)
    """
    if not rows:
        return 0
    logger.debug("insert_chunks chatbot_id=%s count=%s", chatbot_id, len(rows))
    conn.executemany(
        """
        INSERT INTO ingest_chunks (chatbot_id, source_url, chunk_index, content)
        VALUES (?, ?, ?, ?)
        """,
        [(chatbot_id, url, i, content) for url, i, content in rows],
    )
    return len(rows)

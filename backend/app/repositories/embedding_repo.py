from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


def list_ingest_chunks_for_chatbot(
    conn: sqlite3.Connection,
    chatbot_id: int,
) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT id, chatbot_id, source_url, chunk_index, content
        FROM ingest_chunks
        WHERE chatbot_id = ?
        ORDER BY chunk_index ASC
        """,
        (chatbot_id,),
    )
    rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "chatbot_id": r["chatbot_id"],
            "source_url": r["source_url"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
        }
        for r in rows
    ]


def delete_sqlite_embeddings_for_chatbot(conn: sqlite3.Connection, chatbot_id: int) -> None:
    logger.debug("delete_sqlite_embeddings_for_chatbot chatbot_id=%s", chatbot_id)
    conn.execute("DELETE FROM chunk_embeddings WHERE chatbot_id = ?", (chatbot_id,))


def get_chunks_content_map(
    conn: sqlite3.Connection,
    chatbot_id: int,
    ingest_chunk_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not ingest_chunk_ids:
        return {}
    placeholders = ",".join("?" * len(ingest_chunk_ids))
    cur = conn.execute(
        f"""
        SELECT id, source_url, chunk_index, content
        FROM ingest_chunks
        WHERE chatbot_id = ? AND id IN ({placeholders})
        """,
        (chatbot_id, *ingest_chunk_ids),
    )
    return {
        int(r["id"]): {
            "id": r["id"],
            "source_url": r["source_url"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
        }
        for r in cur.fetchall()
    }

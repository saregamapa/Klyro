from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.db.database import db_execute

logger = logging.getLogger(__name__)


def list_ingest_chunks_for_chatbot(conn: Any, chatbot_id: int) -> list[dict[str, Any]]:
    cur = db_execute(
        conn,
        """
        SELECT id, chatbot_id, source_url, chunk_index, content
        FROM ingest_chunks
        WHERE chatbot_id = %s
        ORDER BY chunk_index ASC
        """,
        (chatbot_id,),
    )
    return [
        {
            "id": r["id"],
            "chatbot_id": r["chatbot_id"],
            "source_url": r["source_url"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
        }
        for r in cur.fetchall()
    ]


def delete_sqlite_embeddings_for_chatbot(conn: Any, chatbot_id: int) -> None:
    db_execute(conn, "DELETE FROM chunk_embeddings WHERE chatbot_id = %s", (chatbot_id,))


def get_chunks_content_map(
    conn: Any,
    chatbot_id: int,
    ingest_chunk_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not ingest_chunk_ids:
        return {}
    if settings.use_postgres:
        cur = db_execute(
            conn,
            """
            SELECT id, source_url, chunk_index, content
            FROM ingest_chunks
            WHERE chatbot_id = %s AND id = ANY(%s)
            """,
            (chatbot_id, ingest_chunk_ids),
        )
    else:
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

from __future__ import annotations

import logging
from typing import Any

from psycopg2.extras import execute_values

from app.services.vector_store.base import VectorQueryResult

logger = logging.getLogger(__name__)


class PgVectorStore:
    """pgvector-backed vector store (cosine distance)."""

    backend_name = "pgvector"

    def delete_for_chatbot(self, chatbot_id: int, conn: Any = None) -> None:
        if conn is None:
            raise ValueError("PgVectorStore requires a DB connection")
        cur = conn.cursor()
        cur.execute("DELETE FROM chunk_embeddings WHERE chatbot_id = %s", (chatbot_id,))
        logger.debug("PgVectorStore deleted chatbot_id=%s", chatbot_id)

    def upsert(
        self,
        chatbot_id: int,
        items: list[tuple[int, list[float]]],
        *,
        model: str,
        dimension: int,
        conn: Any = None,
    ) -> None:
        if conn is None:
            raise ValueError("PgVectorStore requires a DB connection")
        if not items:
            return
        rows = [
            (ingest_chunk_id, chatbot_id, vec, model, dimension)
            for ingest_chunk_id, vec in items
        ]
        execute_values(
            conn.cursor(),
            """
            INSERT INTO chunk_embeddings (ingest_chunk_id, chatbot_id, embedding, model, dimension)
            VALUES %s
            ON CONFLICT (ingest_chunk_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                model = EXCLUDED.model,
                dimension = EXCLUDED.dimension,
                chatbot_id = EXCLUDED.chatbot_id
            """,
            rows,
            template="(%s, %s, %s::vector, %s, %s)",
        )
        logger.debug("PgVectorStore upsert chatbot_id=%s rows=%s", chatbot_id, len(items))

    def search(
        self,
        chatbot_id: int,
        query_embedding: list[float],
        top_k: int,
        conn: Any = None,
    ) -> list[VectorQueryResult]:
        if conn is None:
            raise ValueError("PgVectorStore requires a DB connection")
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ingest_chunk_id,
                   1 - (embedding <=> %s::vector) AS score
            FROM   chunk_embeddings
            WHERE  chatbot_id = %s
            ORDER  BY embedding <=> %s::vector
            LIMIT  %s
            """,
            (query_embedding, chatbot_id, query_embedding, top_k),
        )
        return [
            VectorQueryResult(ingest_chunk_id=int(r["ingest_chunk_id"]), score=float(r["score"]))
            for r in cur.fetchall()
        ]

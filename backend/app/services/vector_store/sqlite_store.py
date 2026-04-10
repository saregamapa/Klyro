from __future__ import annotations

import logging
import sqlite3

import numpy as np

from app.services.vector_store.base import VectorQueryResult

logger = logging.getLogger(__name__)


class SqliteVectorStore:
    backend_name = "sqlite"

    def delete_for_chatbot(self, chatbot_id: int, conn: sqlite3.Connection | None = None) -> None:
        if conn is None:
            raise ValueError("SqliteVectorStore requires a DB connection")
        conn.execute("DELETE FROM chunk_embeddings WHERE chatbot_id = ?", (chatbot_id,))

    def upsert(
        self,
        chatbot_id: int,
        items: list[tuple[int, list[float]]],
        *,
        model: str,
        dimension: int,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        if conn is None:
            raise ValueError("SqliteVectorStore requires a DB connection")
        for ingest_chunk_id, vec in items:
            if len(vec) != dimension:
                raise ValueError(f"Embedding dim mismatch: expected {dimension}, got {len(vec)}")
            blob = np.asarray(vec, dtype=np.float32).tobytes()
            conn.execute(
                """
                INSERT INTO chunk_embeddings (ingest_chunk_id, chatbot_id, embedding, model, dimension)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ingest_chunk_id) DO UPDATE SET
                    embedding = excluded.embedding,
                    model = excluded.model,
                    dimension = excluded.dimension,
                    chatbot_id = excluded.chatbot_id
                """,
                (ingest_chunk_id, chatbot_id, blob, model, dimension),
            )
        logger.debug("SqliteVectorStore upsert chatbot_id=%s rows=%s", chatbot_id, len(items))

    def search(
        self,
        chatbot_id: int,
        query_embedding: list[float],
        top_k: int,
        conn: sqlite3.Connection | None = None,
    ) -> list[VectorQueryResult]:
        if conn is None:
            raise ValueError("SqliteVectorStore requires a DB connection")
        q = np.asarray(query_embedding, dtype=np.float32)
        qn = float(np.linalg.norm(q))
        if qn > 0:
            q = q / qn
        cur = conn.execute(
            """
            SELECT ingest_chunk_id, embedding
            FROM chunk_embeddings
            WHERE chatbot_id = ?
            """,
            (chatbot_id,),
        )
        scored: list[tuple[int, float]] = []
        for row in cur.fetchall():
            cid = int(row["ingest_chunk_id"])
            v = np.frombuffer(row["embedding"], dtype=np.float32)
            vn = float(np.linalg.norm(v))
            if vn > 0:
                v = v / vn
            scored.append((cid, float(np.dot(q, v))))
        scored.sort(key=lambda x: -x[1])
        return [VectorQueryResult(ingest_chunk_id=a, score=b) for a, b in scored[:top_k]]

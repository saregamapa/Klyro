from __future__ import annotations

import logging
from typing import Any

import sqlite3

from app.core.config import settings
from app.services.vector_store.base import VectorQueryResult

logger = logging.getLogger(__name__)


def _vector_id(chatbot_id: int, ingest_chunk_id: int) -> str:
    return f"c{chatbot_id}_ic{ingest_chunk_id}"


class PineconeVectorStore:
    backend_name = "pinecone"

    def __init__(self) -> None:
        from pinecone import Pinecone  # noqa: PLC0415

        if not settings.pinecone_api_key.strip() or not settings.pinecone_index_name.strip():
            raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX_NAME are required for pinecone backend")
        pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index = pc.Index(settings.pinecone_index_name)

    def delete_for_chatbot(self, chatbot_id: int, conn: sqlite3.Connection | None = None) -> None:
        try:
            self._index.delete(filter={"chatbot_id": {"$eq": int(chatbot_id)}})
        except Exception:
            logger.exception("Pinecone delete_for_chatbot failed chatbot_id=%s", chatbot_id)
            raise

    def upsert(
        self,
        chatbot_id: int,
        items: list[tuple[int, list[float]]],
        *,
        model: str,
        dimension: int,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        _ = conn
        vectors: list[dict[str, Any]] = []
        for ingest_chunk_id, vec in items:
            if len(vec) != dimension:
                raise ValueError(f"Embedding dim mismatch: expected {dimension}, got {len(vec)}")
            vectors.append(
                {
                    "id": _vector_id(chatbot_id, ingest_chunk_id),
                    "values": vec,
                    "metadata": {
                        "chatbot_id": chatbot_id,
                        "ingest_chunk_id": ingest_chunk_id,
                        "model": model[:256],
                    },
                }
            )
        batch = 100
        for i in range(0, len(vectors), batch):
            self._index.upsert(vectors=vectors[i : i + batch])
        logger.debug("PineconeVectorStore upsert chatbot_id=%s rows=%s", chatbot_id, len(items))

    def search(
        self,
        chatbot_id: int,
        query_embedding: list[float],
        top_k: int,
        conn: sqlite3.Connection | None = None,
    ) -> list[VectorQueryResult]:
        _ = conn
        res = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_values=False,
            filter={"chatbot_id": {"$eq": int(chatbot_id)}},
        )
        out: list[VectorQueryResult] = []
        for m in res.matches or []:
            score = float(m.score) if m.score is not None else 0.0
            icid = None
            if m.metadata and "ingest_chunk_id" in m.metadata:
                icid = int(m.metadata["ingest_chunk_id"])
            else:
                parts = str(m.id).split("_ic")
                if len(parts) == 2 and parts[1].isdigit():
                    icid = int(parts[1])
            if icid is not None:
                out.append(VectorQueryResult(ingest_chunk_id=icid, score=score))
        return out

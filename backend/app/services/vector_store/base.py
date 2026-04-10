from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import sqlite3


@dataclass(frozen=True)
class VectorQueryResult:
    ingest_chunk_id: int
    score: float


class VectorStore(Protocol):
    """Pluggable vector storage (SQLite blobs + numpy, or Pinecone)."""

    backend_name: str

    def delete_for_chatbot(self, chatbot_id: int, conn: sqlite3.Connection | None = None) -> None:
        """Remove all vectors for a chatbot before re-embedding."""

    def upsert(
        self,
        chatbot_id: int,
        items: list[tuple[int, list[float]]],
        *,
        model: str,
        dimension: int,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """items: (ingest_chunk_id, embedding) — embeddings must be L2-normalized."""

    def search(
        self,
        chatbot_id: int,
        query_embedding: list[float],
        top_k: int,
        conn: sqlite3.Connection | None = None,
    ) -> list[VectorQueryResult]:
        """Return top_k results by similarity (higher score = more similar)."""

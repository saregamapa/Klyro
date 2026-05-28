from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class VectorQueryResult:
    ingest_chunk_id: int
    score: float


class VectorStore(Protocol):
    backend_name: str

    def delete_for_chatbot(self, chatbot_id: int, conn: Any | None = None) -> None: ...

    def upsert(
        self,
        chatbot_id: int,
        items: list[tuple[int, list[float]]],
        *,
        model: str,
        dimension: int,
        conn: Any | None = None,
    ) -> None: ...

    def search(
        self,
        chatbot_id: int,
        query_embedding: list[float],
        top_k: int,
        conn: Any | None = None,
    ) -> list[VectorQueryResult]: ...

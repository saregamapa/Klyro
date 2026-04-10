from __future__ import annotations

from app.core.config import settings
from app.services.vector_store.base import VectorStore
from app.services.vector_store.pinecone_store import PineconeVectorStore
from app.services.vector_store.sqlite_store import SqliteVectorStore

_pinecone_singleton: PineconeVectorStore | None = None


def get_vector_store() -> VectorStore:
    global _pinecone_singleton
    backend = (settings.vector_backend or "sqlite").strip().lower()
    if backend == "pinecone":
        if _pinecone_singleton is None:
            _pinecone_singleton = PineconeVectorStore()
        return _pinecone_singleton
    return SqliteVectorStore()

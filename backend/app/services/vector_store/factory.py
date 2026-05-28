from __future__ import annotations

from app.core.config import settings
from app.services.vector_store.base import VectorStore

_pinecone_singleton = None
_pgvector_singleton = None


def get_vector_store() -> VectorStore:
    global _pinecone_singleton, _pgvector_singleton
    backend = (settings.vector_backend or "pgvector").strip().lower()

    if backend == "pinecone":
        from app.services.vector_store.pinecone_store import PineconeVectorStore

        if _pinecone_singleton is None:
            _pinecone_singleton = PineconeVectorStore()
        return _pinecone_singleton

    if backend == "pgvector":
        if not settings.use_postgres:
            from app.services.vector_store.sqlite_store import SqliteVectorStore

            return SqliteVectorStore()
        from app.services.vector_store.pgvector_store import PgVectorStore

        if _pgvector_singleton is None:
            _pgvector_singleton = PgVectorStore()
        return _pgvector_singleton

    from app.services.vector_store.sqlite_store import SqliteVectorStore

    return SqliteVectorStore()

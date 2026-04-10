from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.core.config import settings
from app.repositories import embedding_repo
from app.schemas.rag import EmbedResponse, RetrieveHit, RetrieveRequest, RetrieveResponse
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["rag"])


def _require_openai() -> None:
    if not settings.openai_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI is not configured (set OPENAI_API_KEY)",
        )


@router.post(
    "/{chatbot_id}/embed",
    status_code=status.HTTP_200_OK,
    response_model=EmbedResponse,
)
def embed_chatbot_chunks(
    chatbot_id: Annotated[int, Path(..., ge=1)],
    db: DbConn,
    current_user: CurrentUser,
) -> EmbedResponse:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    _require_openai()

    chunks = embedding_repo.list_ingest_chunks_for_chatbot(db, chatbot_id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ingest chunks found; run POST .../ingest (website) and/or .../ingest-files (documents) first",
        )

    store = get_vector_store()
    embedder = get_embedding_service()

    try:
        store.delete_for_chatbot(chatbot_id, conn=db)
        vectors = embedder.embed_texts([c["content"] for c in chunks])
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("Embedding failed chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider request failed",
        ) from None

    if len(vectors) != len(chunks):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected embedding batch size",
        )

    dim = len(vectors[0])
    items = [(int(c["id"]), vectors[i]) for i, c in enumerate(chunks)]
    try:
        store.upsert(
            chatbot_id,
            items,
            model=settings.openai_embedding_model,
            dimension=dim,
            conn=db,
        )
    except Exception:
        logger.exception("Vector upsert failed chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Vector store write failed",
        ) from None

    logger.info("Embedded chatbot_id=%s chunks=%s backend=%s", chatbot_id, len(chunks), store.backend_name)
    return EmbedResponse(
        chunks_embedded=len(chunks),
        model=settings.openai_embedding_model,
        vector_backend=store.backend_name,
        embedding_dimension=dim,
    )


@router.post(
    "/{chatbot_id}/retrieve",
    status_code=status.HTTP_200_OK,
    response_model=RetrieveResponse,
)
def retrieve_chatbot_chunks(
    chatbot_id: Annotated[int, Path(..., ge=1)],
    db: DbConn,
    current_user: CurrentUser,
    body: RetrieveRequest,
) -> RetrieveResponse:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    _require_openai()

    store = get_vector_store()
    embedder = get_embedding_service()

    try:
        qvec = embedder.embed_query(body.query)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("Query embedding failed chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider request failed",
        ) from None

    try:
        hits = store.search(chatbot_id, qvec, top_k=body.top_k, conn=db)
    except Exception:
        logger.exception("Vector search failed chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Vector search failed",
        ) from None

    ids = [h.ingest_chunk_id for h in hits]
    meta = embedding_repo.get_chunks_content_map(db, chatbot_id, ids)
    results: list[RetrieveHit] = []
    for h in hits:
        row = meta.get(h.ingest_chunk_id)
        if row is None:
            continue
        results.append(
            RetrieveHit(
                ingest_chunk_id=h.ingest_chunk_id,
                score=h.score,
                content=row["content"],
                source_url=row["source_url"],
                chunk_index=row["chunk_index"],
            )
        )
    return RetrieveResponse(results=results)

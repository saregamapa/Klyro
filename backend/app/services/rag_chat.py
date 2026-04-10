from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings
from app.repositories import conversation_repo, embedding_repo
from app.services.embedding_service import get_embedding_service
from app.services.lead_intent import should_prompt_lead_capture
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChunkHit:
    ingest_chunk_id: int
    score: float
    content: str
    source_url: str
    chunk_index: int


@dataclass(frozen=True)
class RagChatOutcome:
    reply: str
    conversation_id: int
    chunk_hits: list[ChunkHit]
    show_lead_form: bool
    lead_prompt: str | None


_DEFAULT_LEAD_PROMPT = (
    "Want a personal quote, demo, or someone to follow up? Leave your name and email below."
)


def _build_system_prompt(context_blocks: list[str]) -> str:
    if context_blocks:
        context = "\n\n---\n\n".join(context_blocks)
    else:
        context = "(No matching context was retrieved from the knowledge base.)"
    return (
        "You are a helpful assistant for a website chatbot. "
        "Answer ONLY using the context below. "
        "If the answer is not in the context, say you do not have enough information in the provided sources.\n\n"
        f"Context:\n{context}"
    )


def run_rag_chat(
    conn: sqlite3.Connection,
    chatbot_id: int,
    user_message: str,
    *,
    top_k: int | None = None,
) -> RagChatOutcome:
    """
    Retrieve top chunks, call OpenAI chat with grounded system prompt, save conversation.
    """
    if not settings.openai_api_key.strip():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    k = top_k if top_k is not None else settings.rag_chat_top_k
    embedder = get_embedding_service()
    store = get_vector_store()

    qvec = embedder.embed_query(user_message)
    hits = store.search(chatbot_id, qvec, top_k=k, conn=conn)
    ids = [h.ingest_chunk_id for h in hits]
    meta = embedding_repo.get_chunks_content_map(conn, chatbot_id, ids)

    chunk_hits: list[ChunkHit] = []
    context_blocks: list[str] = []
    for h in hits:
        row = meta.get(h.ingest_chunk_id)
        if row is None:
            continue
        chunk_hits.append(
            ChunkHit(
                ingest_chunk_id=h.ingest_chunk_id,
                score=h.score,
                content=row["content"],
                source_url=row["source_url"],
                chunk_index=row["chunk_index"],
            )
        )
        context_blocks.append(f"[Source: {row['source_url']}]\n{row['content']}")

    system_prompt = _build_system_prompt(context_blocks)
    client = OpenAI(api_key=settings.openai_api_key)

    try:
        completion = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
    except Exception:
        logger.exception("OpenAI chat completion failed chatbot_id=%s", chatbot_id)
        raise

    reply = (completion.choices[0].message.content or "").strip()
    conv_id = conversation_repo.save_conversation(conn, chatbot_id, user_message, reply)
    logger.info("RAG chat saved conversation_id=%s chatbot_id=%s", conv_id, chatbot_id)
    want_lead = should_prompt_lead_capture(user_message)
    return RagChatOutcome(
        reply=reply,
        conversation_id=conv_id,
        chunk_hits=chunk_hits,
        show_lead_form=want_lead,
        lead_prompt=_DEFAULT_LEAD_PROMPT if want_lead else None,
    )

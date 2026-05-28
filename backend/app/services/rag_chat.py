from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.repositories import chatbot_repo, conversation_repo, embedding_repo
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


def _build_system_prompt(
    context_blocks: list[str],
    chatbot: dict[str, object] | None,
) -> str:
    if context_blocks:
        context = "\n\n---\n\n".join(context_blocks)
    else:
        context = "(No matching context was retrieved from the knowledge base.)"

    website = ""
    if chatbot:
        website = str(chatbot.get("website_url") or chatbot.get("name") or "this website")

    custom = ""
    if chatbot:
        custom = str(chatbot.get("system_prompt") or "").strip()

    if custom:
        base = custom
    else:
        base = (
            f"You are a helpful assistant for {website}. "
            "Answer using the context below when possible. "
            "If the answer is not in the context, say you do not have enough information "
            "in the provided sources."
        )

    parts = [base, f"Context:\n{context}"]
    if chatbot:
        scraped = str(chatbot.get("scraped_content") or "").strip()
        if scraped:
            parts.append(f"Website overview:\n{scraped[:2500]}")
    return "\n\n".join(parts)


@dataclass
class RagContext:
    """Everything needed to call the LLM — assembled synchronously."""

    messages: list[dict]
    chatbot_id: int
    user_message: str
    sid: str
    want_lead: bool
    chatbot: dict


def prepare_rag_context(
    conn: Any,
    chatbot_id: int,
    user_message: str,
    *,
    session_id: str | None = None,
    top_k: int | None = None,
) -> RagContext:
    """
    Do all the DB/vector work synchronously and return a RagContext.
    Does NOT call OpenAI chat — that happens in the streaming or non-streaming caller.
    """
    if not settings.openai_api_key.strip():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    chatbot = chatbot_repo.get_chatbot_by_id(conn, chatbot_id)
    if chatbot is None:
        raise ValueError("Chatbot not found")

    k = top_k if top_k is not None else settings.rag_chat_top_k
    embedder = get_embedding_service()
    store = get_vector_store()

    qvec = embedder.embed_query(user_message)
    hits = store.search(chatbot_id, qvec, top_k=k, conn=conn)
    ids = [h.ingest_chunk_id for h in hits]
    meta = embedding_repo.get_chunks_content_map(conn, chatbot_id, ids)

    context_blocks: list[str] = []
    for h in hits:
        row = meta.get(h.ingest_chunk_id)
        if row:
            context_blocks.append(f"[Source: {row['source_url']}]\n{row['content']}")

    system_prompt = _build_system_prompt(context_blocks, chatbot)
    sid = (session_id or "").strip()
    history: list[dict] = []
    if sid:
        history = conversation_repo.get_session_history(conn, chatbot_id, sid, limit=10)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    return RagContext(
        messages=messages,
        chatbot_id=chatbot_id,
        user_message=user_message,
        sid=sid,
        want_lead=should_prompt_lead_capture(user_message),
        chatbot=chatbot,
    )


def run_rag_chat(
    conn: Any,
    chatbot_id: int,
    user_message: str,
    *,
    session_id: str | None = None,
    top_k: int | None = None,
) -> RagChatOutcome:
    """
    Retrieve top chunks, call OpenAI chat with grounded system prompt, save conversation.
    """
    ctx = prepare_rag_context(
        conn, chatbot_id, user_message, session_id=session_id, top_k=top_k
    )

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        completion = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=ctx.messages,
            temperature=0.2,
        )
    except Exception:
        logger.exception("OpenAI chat completion failed chatbot_id=%s", chatbot_id)
        raise

    reply = (completion.choices[0].message.content or "").strip()
    conv_id = conversation_repo.save_conversation(
        conn, chatbot_id, user_message, reply, session_id=ctx.sid or None
    )
    logger.info("RAG chat saved conversation_id=%s chatbot_id=%s", conv_id, chatbot_id)
    return RagChatOutcome(
        reply=reply,
        conversation_id=conv_id,
        chunk_hits=[],
        show_lead_form=ctx.want_lead,
        lead_prompt=_DEFAULT_LEAD_PROMPT if ctx.want_lead else None,
    )

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.schemas.chat_api import ChatRequest, ChatResponse, ChatSource
from app.services.rag_chat import run_rag_chat

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat_rag(
    body: ChatRequest,
    db: DbConn,
    current_user: CurrentUser,
) -> ChatResponse:
    require_owned_chatbot(db, body.chatbot_id, current_user.id)

    try:
        out = run_rag_chat(
            db,
            body.chatbot_id,
            body.user_message,
        )
        reply = out.reply
        conv_id = out.conversation_id
        hits = out.chunk_hits
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("RAG chat failed chatbot_id=%s", body.chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat completion failed",
        ) from None

    sources = [
        ChatSource(
            ingest_chunk_id=h.ingest_chunk_id,
            score=h.score,
            source_url=h.source_url,
            chunk_index=h.chunk_index,
        )
        for h in hits
    ]
    return ChatResponse(
        reply=reply,
        conversation_id=conv_id,
        sources=sources,
        show_lead_form=out.show_lead_form,
        lead_prompt=out.lead_prompt,
    )

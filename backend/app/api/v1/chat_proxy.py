from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, status

from app.api.deps import DbConn, check_owner_message_quota
from app.core.rate_limit import limiter
from app.repositories import chatbot_repo, lead_repo, usage_repo
from app.schemas.chat_proxy import PublicChatRequest, PublicChatResponse
from app.services.rag_chat import run_rag_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["chat"])


@router.post("/{chatbot_id}/chat", response_model=PublicChatResponse)
@limiter.limit("30/minute")
def public_chatbot_chat(
    request: Request,
    chatbot_id: Annotated[int, Path(..., ge=1)],
    body: PublicChatRequest,
    db: DbConn,
) -> PublicChatResponse:
    """
    Public embed endpoint (no JWT). Session-aware RAG chat for third-party widgets.
    """
    row = chatbot_repo.get_chatbot_by_id(db, chatbot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")

    owner_id = int(row["user_id"])
    check_owner_message_quota(db, owner_id)

    try:
        out = run_rag_chat(db, chatbot_id, body.message, session_id=body.session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("Public chat failed chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat failed",
        ) from None

    if body.lead_email:
        try:
            lead_repo.upsert_lead_email(db, chatbot_id, str(body.lead_email))
        except Exception:
            logger.exception("Lead upsert failed chatbot_id=%s", chatbot_id)

    try:
        usage_repo.increment_message_count(db, owner_id)
    except Exception:
        logger.exception("Failed to increment message usage owner_id=%s", owner_id)

    return PublicChatResponse(
        reply=out.reply,
        session_id=body.session_id,
        show_lead_form=out.show_lead_form,
        lead_prompt=out.lead_prompt,
    )

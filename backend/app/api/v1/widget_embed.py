from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import DbConn
from app.repositories import chatbot_repo, lead_repo
from app.schemas.widget import WidgetChatRequest, WidgetChatResponse
from app.schemas.widget_lead import WidgetLeadCreate, WidgetLeadCreated
from app.services.rag_chat import run_rag_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["widget"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat", response_model=WidgetChatResponse)
@limiter.limit("20/minute")
def widget_public_chat(request: Request, body: WidgetChatRequest, db: DbConn) -> WidgetChatResponse:
    """
    Public embed endpoint (no JWT). Validates chatbot exists.
    Restrict exposure in production (HTTPS, rate limits, optional embed tokens).
    """
    row = chatbot_repo.get_chatbot_by_id(db, body.chatbot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")

    try:
        session_id = (body.session_id or "").strip() or None
        out = run_rag_chat(db, body.chatbot_id, body.message, session_id=session_id)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("Widget chat failed chatbot_id=%s", body.chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat failed",
        ) from None

    return WidgetChatResponse(
        reply=out.reply,
        session_id=session_id,
        show_lead_form=out.show_lead_form,
        lead_prompt=out.lead_prompt,
    )


@router.post("/leads", status_code=status.HTTP_201_CREATED, response_model=WidgetLeadCreated)
@limiter.limit("5/minute")
def widget_public_lead(request: Request, body: WidgetLeadCreate, db: DbConn) -> WidgetLeadCreated:
    """Public lead form from embed (no JWT). Validates chatbot exists."""
    row = chatbot_repo.get_chatbot_by_id(db, body.chatbot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")
    new_id = lead_repo.create_lead(
        db,
        body.chatbot_id,
        body.name.strip(),
        str(body.email).strip(),
        body.message.strip() if body.message else None,
    )
    return WidgetLeadCreated(id=new_id)

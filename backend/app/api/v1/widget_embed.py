from __future__ import annotations

import asyncio
import json as _json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.api.deps import DbConn, check_owner_message_quota
from app.api.origin_check import origin_allowed
from app.core.config import settings
from app.core.rate_limit import limiter
from app.repositories import chatbot_repo, lead_repo, usage_repo
from app.schemas.widget import WidgetChatRequest, WidgetChatResponse
from app.schemas.widget_lead import WidgetLeadCreate, WidgetLeadCreated
from app.services.rag_chat import _DEFAULT_LEAD_PROMPT, prepare_rag_context, run_rag_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["widget"])


def _prepare_stream_request(
    chatbot_id: int,
    message: str,
    session_id: str | None,
    origin_str: str | None,
) -> tuple[int, object]:
    """Validate chatbot, origin, quota, and build RAG context (sync, own DB conn)."""
    from app.db.database import get_db_connection

    conn = get_db_connection()
    try:
        row = chatbot_repo.get_chatbot_by_id(conn, chatbot_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")

        if not origin_allowed(row, origin_str):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This domain is not authorised to use this chatbot.",
            )

        owner_id = int(row["user_id"])
        check_owner_message_quota(conn, owner_id)
        ctx = prepare_rag_context(
            conn, chatbot_id, message, session_id=session_id
        )
        return owner_id, ctx
    finally:
        conn.close()


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

    origin_str = request.headers.get("origin")
    if not origin_allowed(row, origin_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This domain is not authorised to use this chatbot. "
            "Add it under chatbot settings → Allowed Origins.",
        )

    owner_id = int(row["user_id"])
    check_owner_message_quota(db, owner_id)

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

    try:
        usage_repo.increment_message_count(db, owner_id)
    except Exception:
        logger.exception("Failed to increment message usage owner_id=%s", owner_id)

    return WidgetChatResponse(
        reply=out.reply,
        session_id=session_id,
        show_lead_form=out.show_lead_form,
        lead_prompt=out.lead_prompt,
    )


@router.post("/stream")
@limiter.limit("20/minute")
async def widget_stream_chat(
    request: Request,
    body: WidgetChatRequest,
) -> StreamingResponse:
    """
    Streaming version of /widget/chat — returns Server-Sent Events.
    Each event: data: {"text": "..."}\n\n
    Final event: data: {"done": true, "show_lead_form": bool}\n\n
    """
    origin_str = request.headers.get("origin")
    session_id = (body.session_id or "").strip() or None

    try:
        owner_id, ctx = await asyncio.to_thread(
            _prepare_stream_request,
            body.chatbot_id,
            body.message,
            session_id,
            origin_str,
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("RAG context preparation failed chatbot_id=%s", body.chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat preparation failed",
        ) from None

    async def generate():
        full_reply_parts: list[str] = []

        try:
            async_client = AsyncOpenAI(api_key=settings.openai_api_key)
            async with async_client.chat.completions.stream(
                model=settings.openai_chat_model,
                messages=ctx.messages,
                temperature=0.2,
            ) as stream:
                async for event in stream:
                    delta = event.choices[0].delta
                    text = delta.content or ""
                    if text:
                        full_reply_parts.append(text)
                        yield f"data: {_json.dumps({'text': text})}\n\n"

        except Exception:
            logger.exception("Streaming failed chatbot_id=%s", body.chatbot_id)
            yield f"data: {_json.dumps({'error': 'Stream failed'})}\n\n"
            return

        full_reply = "".join(full_reply_parts).strip()
        if full_reply:
            try:
                from app.db.database import get_db_connection
                from app.repositories import conversation_repo

                save_conn = get_db_connection()
                try:
                    conversation_repo.save_conversation(
                        save_conn,
                        body.chatbot_id,
                        body.message,
                        full_reply,
                        session_id=ctx.sid or None,
                    )
                    usage_repo.increment_message_count(save_conn, owner_id)
                    save_conn.commit()
                finally:
                    save_conn.close()
            except Exception:
                logger.exception("Post-stream save failed chatbot_id=%s", body.chatbot_id)

        yield f"data: {_json.dumps({'done': True, 'show_lead_form': ctx.want_lead, 'lead_prompt': _DEFAULT_LEAD_PROMPT if ctx.want_lead else None})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
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

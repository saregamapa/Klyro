from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import ChatbotQuotaOk, CurrentUser, DbConn
from app.db.database import is_integrity_error
from app.repositories import chatbot_repo, conversation_repo, lead_repo
from app.schemas.chatbot import (
    ChatbotCreate,
    ChatbotCreated,
    ChatbotPublic,
    ChatbotStats,
    ChatbotUpdate,
)
from app.services.scrape_tasks import scrape_and_update_chatbot
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


def _to_public(row: dict[str, Any]) -> ChatbotPublic:
    return ChatbotPublic(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        website_url=row["website_url"],
        system_prompt=str(row.get("system_prompt") or ""),
        accent_color=str(row.get("accent_color") or "#6366f1"),
        scraped_content=str(row.get("scraped_content") or ""),
        created_at=str(row["created_at"]),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatbotCreated,
)
def create_chatbot(
    body: ChatbotCreate,
    db: DbConn,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    _quota: ChatbotQuotaOk,
) -> ChatbotCreated:
    website_url = str(body.website_url) if body.website_url is not None else None
    try:
        new_id = chatbot_repo.create_chatbot(
            db,
            current_user.id,
            body.name,
            website_url,
        )
    except Exception as e:
        if not is_integrity_error(e):
            raise
        logger.warning("create_chatbot integrity failure user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create chatbot",
        ) from None
    # Commit before background scrape so SQLite is not locked by this request's txn
    db.commit()
    if website_url:
        background_tasks.add_task(scrape_and_update_chatbot, new_id, website_url)
    return ChatbotCreated(id=new_id, user_id=current_user.id, name=body.name)


@router.get("", response_model=list[ChatbotPublic])
def list_chatbots(db: DbConn, current_user: CurrentUser) -> list[ChatbotPublic]:
    rows = chatbot_repo.get_chatbots_by_user(db, current_user.id)
    return [_to_public(r) for r in rows]


@router.get("/{chatbot_id}", response_model=ChatbotPublic)
def get_chatbot(
    chatbot_id: Annotated[int, Path(..., ge=1, description="Chatbot id")],
    db: DbConn,
    current_user: CurrentUser,
) -> ChatbotPublic:
    row = require_owned_chatbot(db, chatbot_id, current_user.id)
    return _to_public(row)


@router.patch("/{chatbot_id}", response_model=ChatbotPublic)
def update_chatbot(
    chatbot_id: Annotated[int, Path(..., ge=1, description="Chatbot id")],
    body: ChatbotUpdate,
    db: DbConn,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> ChatbotPublic:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    website_url = str(body.website_url) if body.website_url is not None else None
    updated = chatbot_repo.update_chatbot(
        db,
        chatbot_id,
        current_user.id,
        name=body.name,
        website_url=website_url,
        system_prompt=body.system_prompt,
        accent_color=body.accent_color,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")
    db.commit()
    if website_url:
        background_tasks.add_task(scrape_and_update_chatbot, chatbot_id, website_url)
    row = chatbot_repo.get_chatbot_by_id(db, chatbot_id)
    assert row is not None
    return _to_public(row)


@router.get("/{chatbot_id}/stats", response_model=ChatbotStats)
def get_chatbot_stats(
    chatbot_id: Annotated[int, Path(..., ge=1, description="Chatbot id")],
    db: DbConn,
    current_user: CurrentUser,
) -> ChatbotStats:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    conv_stats = conversation_repo.stats_for_chatbot(db, chatbot_id)
    total_leads = lead_repo.count_leads_for_chatbot(db, chatbot_id)
    last = conv_stats.get("last_activity")
    return ChatbotStats(
        total_conversations=int(conv_stats["total_conversations"]),
        total_messages=int(conv_stats["total_messages"]),
        total_leads=total_leads,
        last_activity=str(last) if last is not None else None,
    )


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chatbot(
    chatbot_id: Annotated[int, Path(..., ge=1, description="Chatbot id")],
    db: DbConn,
    current_user: CurrentUser,
) -> None:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    try:
        get_vector_store().delete_for_chatbot(chatbot_id, conn=db)
    except Exception:
        logger.exception("Vector store cleanup failed before delete chatbot_id=%s", chatbot_id)
    deleted = chatbot_repo.delete_chatbot(db, chatbot_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")

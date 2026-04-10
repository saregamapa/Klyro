from __future__ import annotations

import logging
import sqlite3
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.repositories import chatbot_repo
from app.schemas.chatbot import ChatbotCreate, ChatbotCreated, ChatbotPublic
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


def _to_public(row: dict[str, Any]) -> ChatbotPublic:
    return ChatbotPublic(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        website_url=row["website_url"],
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
) -> ChatbotCreated:
    website_url = str(body.website_url) if body.website_url is not None else None
    try:
        new_id = chatbot_repo.create_chatbot(
            db,
            current_user.id,
            body.name,
            website_url,
        )
    except sqlite3.IntegrityError:
        logger.warning("create_chatbot integrity failure user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create chatbot",
        ) from None
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

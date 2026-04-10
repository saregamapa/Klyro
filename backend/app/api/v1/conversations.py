from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, status

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.repositories import conversation_repo
from app.schemas.conversation import ConversationCreate, ConversationPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbots", tags=["conversations"])


def _to_public(row: dict) -> ConversationPublic:
    return ConversationPublic(
        id=row["id"],
        chatbot_id=row["chatbot_id"],
        user_message=row["user_message"],
        bot_response=row["bot_response"],
        created_at=str(row["created_at"]),
    )


@router.post(
    "/{chatbot_id}/conversations",
    status_code=status.HTTP_201_CREATED,
)
def add_conversation(
    chatbot_id: int,
    body: ConversationCreate,
    db: DbConn,
    current_user: CurrentUser,
) -> dict:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    try:
        new_id = conversation_repo.save_conversation(
            db,
            chatbot_id,
            body.user_message,
            body.bot_response,
        )
    except sqlite3.IntegrityError:
        logger.warning("save_conversation integrity error chatbot_id=%s", chatbot_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save conversation",
        ) from None
    return {"id": new_id, "chatbot_id": chatbot_id}


@router.get(
    "/{chatbot_id}/conversations",
    response_model=list[ConversationPublic],
)
def list_conversations(
    chatbot_id: int,
    db: DbConn,
    current_user: CurrentUser,
) -> list[ConversationPublic]:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    rows = conversation_repo.get_conversations_by_chatbot(db, chatbot_id)
    return [_to_public(r) for r in rows]

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Path

from app.api.chatbot_access import require_owned_chatbot
from app.api.deps import CurrentUser, DbConn
from app.repositories import conversation_repo
from app.schemas.analytics import AnalyticsResponse, TopQuestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{chatbot_id}", response_model=AnalyticsResponse)
def get_chatbot_analytics(
    chatbot_id: Annotated[int, Path(..., ge=1)],
    db: DbConn,
    current_user: CurrentUser,
) -> AnalyticsResponse:
    require_owned_chatbot(db, chatbot_id, current_user.id)
    total = conversation_repo.count_conversations_for_chatbot(db, chatbot_id)
    rows = conversation_repo.top_questions_for_chatbot(db, chatbot_id, limit=15)
    top = [TopQuestion(question=q, count=c) for q, c in rows]
    return AnalyticsResponse(total_chats=total, top_questions=top)

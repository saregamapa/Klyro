from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.repositories import chatbot_repo


def require_owned_chatbot(
    db: Any,
    chatbot_id: int,
    user_id: int,
) -> dict[str, Any]:
    """
    Return the chatbot dict if it exists and is owned by user_id.
    Raises 404 in both the "not found" and "wrong owner" cases to prevent
    tenant enumeration — callers cannot distinguish the two.
    """
    row = chatbot_repo.get_chatbot_by_id(db, chatbot_id)
    if row is None or row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
    return row

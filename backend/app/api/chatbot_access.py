from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException, status

from app.repositories import chatbot_repo


def require_owned_chatbot(
    db: sqlite3.Connection,
    chatbot_id: int,
    user_id: int,
) -> dict[str, Any]:
    row = chatbot_repo.get_chatbot_by_id(db, chatbot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")
    if row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this chatbot",
        )
    return row

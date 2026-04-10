from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class WidgetLeadCreate(BaseModel):
    chatbot_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    message: Optional[str] = Field(None, max_length=4000)


class WidgetLeadCreated(BaseModel):
    id: int

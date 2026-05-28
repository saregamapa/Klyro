from __future__ import annotations

import html
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class PublicChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=2000)
    lead_email: Optional[EmailStr] = None

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        sanitized = re.sub(r"<[^>]+>", "", v)
        sanitized = html.unescape(sanitized)
        return sanitized.strip()

    @field_validator("session_id")
    @classmethod
    def strip_session(cls, v: str) -> str:
        return v.strip()


class PublicChatResponse(BaseModel):
    reply: str
    session_id: str
    show_lead_form: bool = False
    lead_prompt: Optional[str] = None

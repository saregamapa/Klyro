from __future__ import annotations

import html
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class WidgetChatRequest(BaseModel):
    chatbot_id: int = Field(..., ge=1)
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, max_length=128)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Sanitize user message: strip HTML tags and whitespace."""
        # Remove HTML tags
        sanitized = re.sub(r"<[^>]+>", "", v)
        # Unescape HTML entities
        sanitized = html.unescape(sanitized)
        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()
        return sanitized


class WidgetChatResponse(BaseModel):
    reply: str
    session_id: Optional[str] = None
    show_lead_form: bool = False
    lead_prompt: Optional[str] = Field(
        default=None,
        description="Short CTA when show_lead_form is true",
    )

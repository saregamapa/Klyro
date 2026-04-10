from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class WidgetChatRequest(BaseModel):
    chatbot_id: int = Field(..., ge=1)
    message: str = Field(..., min_length=1, max_length=8000)


class WidgetChatResponse(BaseModel):
    reply: str
    show_lead_form: bool = False
    lead_prompt: Optional[str] = Field(
        default=None,
        description="Short CTA when show_lead_form is true",
    )

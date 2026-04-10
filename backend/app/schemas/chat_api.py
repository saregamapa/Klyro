from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    chatbot_id: int = Field(..., ge=1)
    user_message: str = Field(..., min_length=1, max_length=8000)


class ChatSource(BaseModel):
    ingest_chunk_id: int
    score: float
    source_url: str
    chunk_index: int


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    sources: list[ChatSource] = Field(default_factory=list)
    show_lead_form: bool = False
    lead_prompt: Optional[str] = None

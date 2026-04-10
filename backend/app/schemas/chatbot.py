from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ChatbotCreate(BaseModel):
    """Payload for creating a chatbot (owner is the authenticated user)."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for the chatbot",
    )
    website_url: Optional[HttpUrl] = Field(
        None,
        description="Optional site the bot is trained on or embedded in",
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class ChatbotCreated(BaseModel):
    """Response after successful create."""

    id: int
    user_id: int
    name: str


class ChatbotPublic(BaseModel):
    """Chatbot as returned from the API."""

    id: int
    user_id: int
    name: str
    website_url: Optional[str]
    created_at: str

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


class ChatbotUpdate(BaseModel):
    """Partial update for an owned chatbot."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[HttpUrl] = None
    system_prompt: Optional[str] = Field(None, max_length=8000)
    accent_color: Optional[str] = Field(None, min_length=4, max_length=32)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name_update(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("accent_color")
    @classmethod
    def validate_accent(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v.startswith("#") or len(v) not in (4, 7, 9):
            raise ValueError("accent_color must be a hex color like #6366f1")
        return v


class ChatbotPublic(BaseModel):
    """Chatbot as returned from the API."""

    id: int
    user_id: int
    name: str
    website_url: Optional[str]
    system_prompt: str = ""
    accent_color: str = "#6366f1"
    scraped_content: str = ""
    created_at: str


class ChatbotStats(BaseModel):
    total_conversations: int
    total_messages: int
    total_leads: int
    last_activity: Optional[str] = None

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    user_message: str = Field(..., min_length=1)
    bot_response: str = Field(..., min_length=1)


class ConversationPublic(BaseModel):
    id: int
    chatbot_id: int
    user_message: str
    bot_response: str
    created_at: str

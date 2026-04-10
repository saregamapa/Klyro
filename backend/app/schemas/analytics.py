from pydantic import BaseModel, Field


class TopQuestion(BaseModel):
    question: str = Field(description="Representative text of the question")
    count: int = Field(ge=1)


class AnalyticsResponse(BaseModel):
    total_chats: int = Field(description="Number of stored conversations (user turns)")
    top_questions: list[TopQuestion] = Field(
        default_factory=list,
        description="Most common visitor questions (grouped by normalized text)",
    )

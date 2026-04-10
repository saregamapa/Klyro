from typing import Optional

from pydantic import BaseModel


class LeadCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None


class LeadCreated(BaseModel):
    id: int


class LeadPublic(BaseModel):
    id: int
    chatbot_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None

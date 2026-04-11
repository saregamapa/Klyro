from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    app_name: str
    environment: str
    version: str = Field(default="1.0.0", examples=["1.0.0"])
    timestamp: datetime = Field(..., examples=["2024-04-10T12:00:00Z"])

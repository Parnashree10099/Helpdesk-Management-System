from pydantic import BaseModel, Field
from datetime import datetime


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
from pydantic import BaseModel, Field
from typing import Optional


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    category: str = "Other"
    priority: str = "Medium"


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    created_by: int
    assigned_agent_id: Optional[int] = None

    model_config = {"from_attributes": True}
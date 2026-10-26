from pydantic import BaseModel
from datetime import datetime


class AttachmentResponse(BaseModel):
    id: int
    ticket_id: int
    uploaded_by: int
    filename: str
    stored_filename: str
    file_path: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
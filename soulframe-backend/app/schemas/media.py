from pydantic import BaseModel, UUID4
from datetime import datetime


class MediaResponse(BaseModel):
    id: UUID4
    original_filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    
    class Config:
        from_attributes = True
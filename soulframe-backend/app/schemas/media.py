from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Any, Literal, Optional


MediaStatus = Literal["uploaded", "processing", "ready", "failed"]


class MediaResponse(BaseModel):
    id: UUID4
    original_filename: str
    mime_type: str
    size_bytes: int
    status: MediaStatus
    source_storage_key: Optional[str] = None
    playback_storage_key: Optional[str] = None
    original_mime_type: Optional[str] = None
    playback_mime_type: Optional[str] = None
    original_size_bytes: Optional[int] = None
    playback_size_bytes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    normalized_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    normalization_metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

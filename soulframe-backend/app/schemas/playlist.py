from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List


class PlaylistCreate(BaseModel):
    name: str


class PlaylistItemInput(BaseModel):
    media_id: UUID4
    position: int


class PlaylistUpdate(BaseModel):
    name: str
    items: List[PlaylistItemInput]


class PlaylistItemResponse(BaseModel):
    id: UUID4
    media_id: UUID4
    position: int
    
    class Config:
        from_attributes = True


class PlaylistResponse(BaseModel):
    id: UUID4
    name: str
    created_at: datetime
    items: List[PlaylistItemResponse]
    
    class Config:
        from_attributes = True
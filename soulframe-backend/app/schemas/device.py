from pydantic import BaseModel, UUID4
from datetime import datetime, time
from typing import Optional


class DeviceResponse(BaseModel):
    id: UUID4
    name: str
    last_seen_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeviceUpdate(BaseModel):
    name: str


class DeviceClaimRequest(BaseModel):
    pairing_code: str


class PairingResponse(BaseModel):
    pairing_code: str
    expires_at: datetime
    claim_url: str


class DeviceCheckinRequest(BaseModel):
    app_version: str
    ip: Optional[str] = None
    storage_free_bytes: Optional[int] = None


class DeviceSettingsResponse(BaseModel):
    brightness: int
    orientation: str
    sleep_enabled: bool
    sleep_start: Optional[time]
    sleep_end: Optional[time]
    
    class Config:
        from_attributes = True


class MediaManifestItem(BaseModel):
    media_id: UUID4
    download_url: str
    original_filename: str


class PlaylistItemResponse(BaseModel):
    media_id: UUID4
    position: int


class DeviceCheckinResponsePaired(BaseModel):
    paired: bool = True
    assigned_playlist_id: Optional[UUID4]
    settings: DeviceSettingsResponse
    media_manifest: list[MediaManifestItem]
    playlist_items: list[PlaylistItemResponse]


class DeviceCheckinResponseUnpaired(BaseModel):
    paired: bool = False
    pairing: PairingResponse
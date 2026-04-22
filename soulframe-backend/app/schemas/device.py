from datetime import datetime, time
from typing import Any, Literal, Optional

from pydantic import UUID4, BaseModel, Field


class DeviceResponse(BaseModel):
    id: UUID4
    name: str
    last_seen_at: Optional[datetime]
    created_at: datetime
    state: Literal["unclaimed", "active", "offline"]

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


class DeviceRegistrationRequest(BaseModel):
    name: Optional[str] = None
    app_version: Optional[str] = None


class DeviceRegistrationResponse(BaseModel):
    device_id: UUID4
    device_token: str
    state: Literal["unclaimed"] = "unclaimed"


class DeviceSettingsResponse(BaseModel):
    brightness: int
    orientation: str
    sleep_enabled: bool
    sleep_start: Optional[time]
    sleep_end: Optional[time]

    class Config:
        from_attributes = True


class DeviceRuntimeConfigResponse(BaseModel):
    poll_interval_seconds: int
    sync_interval_seconds: int
    cache_max_bytes: Optional[int]
    playback_mode: str
    fallback_behavior: str
    config_revision: str


class DeviceCommandResponse(BaseModel):
    command_id: UUID4
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: Optional[datetime] = None


class DeviceCommandAckRequest(BaseModel):
    status: Literal["succeeded", "failed"]
    message: Optional[str] = None
    result_payload: Optional[dict[str, Any]] = None


class DeviceQueueCommandRequest(BaseModel):
    command_type: Literal[
        "refresh_now",
        "restart_playback",
        "clear_cache",
        "reboot_client",
        "unassign_content",
        "run_health_check",
        "debug_message",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_in_seconds: Optional[int] = None


class DeviceCommandStatusResponse(BaseModel):
    id: UUID4
    command_type: str
    status: str
    result_status: Optional[str]
    result_message: Optional[str]
    created_at: datetime
    delivered_at: Optional[datetime]
    acknowledged_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceRuntimeStatusResponse(BaseModel):
    app_version: Optional[str]
    local_ip: Optional[str]
    uptime_seconds: Optional[int]
    storage_free_bytes: Optional[int]
    cache_free_bytes: Optional[int]
    current_media_id: Optional[UUID4]
    current_playlist_id: Optional[UUID4]
    health_status: Optional[str]
    last_error: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceHeartbeatRequest(BaseModel):
    app_version: Optional[str] = None
    ip: Optional[str] = None
    uptime_seconds: Optional[int] = None
    storage_free_bytes: Optional[int] = None
    cache_free_bytes: Optional[int] = None
    current_media_id: Optional[UUID4] = None
    current_playlist_id: Optional[UUID4] = None
    health_status: Optional[str] = None
    last_error: Optional[str] = None


class DeviceHeartbeatResponse(BaseModel):
    device_id: UUID4
    state: Literal["unclaimed", "active", "offline"]
    server_time: datetime
    poll_interval_seconds: int


class DeviceSyncRequest(BaseModel):
    app_version: Optional[str] = None
    ip: Optional[str] = None
    uptime_seconds: Optional[int] = None
    storage_free_bytes: Optional[int] = None
    cache_free_bytes: Optional[int] = None
    current_media_id: Optional[UUID4] = None
    current_playlist_id: Optional[UUID4] = None
    health_status: Optional[str] = None
    last_error: Optional[str] = None
    known_content_revision: Optional[str] = None
    known_config_revision: Optional[str] = None
    include_commands: bool = True


class AssignedMediaFile(BaseModel):
    media_id: UUID4
    original_filename: str
    mime_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    checksum: str
    updated_at: datetime
    download_url: str


class AssignedContentResponse(BaseModel):
    assignment_type: Literal["none", "playlist"]
    assigned_playlist_id: Optional[UUID4]
    content_revision: str
    assigned_at: Optional[datetime]
    items: list[AssignedMediaFile]


class DeviceIdentityResponse(BaseModel):
    device_id: UUID4
    device_name: str
    state: Literal["unclaimed", "active", "offline"]
    is_claimed: bool
    last_seen_at: Optional[datetime]


class DeviceSyncResponse(BaseModel):
    server_time: datetime
    device: DeviceIdentityResponse
    account_name: Optional[str] = None
    pairing: Optional[PairingResponse] = None
    has_changes: bool
    content_changed: bool
    config_changed: bool
    assigned_content: AssignedContentResponse
    runtime_config: DeviceRuntimeConfigResponse
    pending_commands: list[DeviceCommandResponse]

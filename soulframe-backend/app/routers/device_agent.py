from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_device
from app.models.models import Device, Media
from app.schemas.device import (
    DeviceCommandAckRequest,
    DeviceCommandStatusResponse,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceIdentityResponse,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceRuntimeConfigResponse,
    DeviceSyncRequest,
    DeviceSyncResponse,
    PairingResponse,
)
from app.services import device as device_service
from app.services.media_processing import READY
from app.utils.storage import get_file_path

router = APIRouter(prefix="/device", tags=["device-agent"])


@router.post("/register", response_model=DeviceRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegistrationRequest,
    db: Session = Depends(get_db),
):
    device = device_service.register_device(db, payload.name, payload.app_version)
    return DeviceRegistrationResponse(
        device_id=device.id,
        device_token=device.device_token,
    )


@router.post("/pair/request", response_model=PairingResponse)
async def request_pairing(
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    return device_service.create_pairing_request(db, current_device)


@router.post("/sync", response_model=DeviceSyncResponse)
async def sync_device(
    payload: DeviceSyncRequest,
    request: Request,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    api_base_url = str(request.base_url).rstrip("/")
    return device_service.build_sync_response(db, current_device, payload, api_base_url)


@router.get("/config", response_model=DeviceRuntimeConfigResponse)
async def get_runtime_config(
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    device_service.update_runtime_status(db, current_device, DeviceHeartbeatRequest())
    return device_service.get_runtime_config(current_device)


@router.get("/identity", response_model=DeviceIdentityResponse)
async def get_device_identity(
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    device_service.update_runtime_status(db, current_device, DeviceHeartbeatRequest())
    return DeviceIdentityResponse(
        device_id=current_device.id,
        device_name=current_device.name,
        state=device_service.get_device_state(current_device),
        is_claimed=current_device.owner_user_id is not None,
        last_seen_at=current_device.last_seen_at,
    )


@router.post("/checkin", response_model=DeviceSyncResponse)
async def legacy_checkin(
    payload: DeviceSyncRequest,
    request: Request,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    api_base_url = str(request.base_url).rstrip("/")
    return device_service.build_sync_response(db, current_device, payload, api_base_url)


@router.post("/heartbeat", response_model=DeviceHeartbeatResponse)
async def heartbeat(
    payload: DeviceHeartbeatRequest,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    return device_service.build_heartbeat_response(db, current_device, payload)


@router.post("/commands/{command_id}/ack", response_model=DeviceCommandStatusResponse)
async def acknowledge_command(
    command_id: UUID,
    payload: DeviceCommandAckRequest,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    command = device_service.acknowledge_command(db, current_device, command_id, payload)
    if not command:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
    return device_service.command_to_status_response(command)


@router.get("/media/{media_id}/download")
async def download_media(
    media_id: UUID,
    response: Response,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    if not device_service.can_device_access_media(db, current_device, media_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media")

    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    if media.status != READY or not media.playback_storage_key:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Media is not ready for playback")

    playback_size_bytes = media.playback_size_bytes or media.size_bytes
    checksum_seed = (
        f"{media.id}|{media.playback_storage_key}|{playback_size_bytes}|"
        f"{media.normalized_at.isoformat() if media.normalized_at else ''}"
    )
    etag = sha256(checksum_seed.encode("utf-8")).hexdigest()
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=31536000"

    return FileResponse(
        path=get_file_path(media.playback_storage_key),
        media_type=media.playback_mime_type or media.mime_type,
        filename=media.original_filename,
    )

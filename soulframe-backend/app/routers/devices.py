from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.models import Device, Media, Playlist, User
from app.schemas.device import (
    DeviceClaimRequest,
    DeviceCommandStatusResponse,
    DeviceQueueCommandRequest,
    DeviceResponse,
    DeviceRuntimeStatusResponse,
    DeviceUpdate,
)
from app.services import device as device_service
from app.services.media_processing import READY
from app.services import playlist as playlist_service

router = APIRouter(prefix="/devices", tags=["devices"])


def _to_device_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        name=device.name,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        state=device_service.get_device_state(device),
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).filter(Device.owner_user_id == current_user.id).all()
    return [_to_device_response(device) for device in devices]


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_data: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id,
    ).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    device.name = device_data.name
    db.commit()
    db.refresh(device)
    return _to_device_response(device)


@router.post("/claim", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
async def claim_device(
    claim_data: DeviceClaimRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = device_service.claim_device(db, claim_data.pairing_code, current_user.id)
    if not device:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired pairing code")
    return _to_device_response(device)


@router.post("/{device_id}/assign/{playlist_id}", status_code=status.HTTP_200_OK)
async def assign_playlist(
    device_id: UUID,
    playlist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id,
    ).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    playlist = db.query(Playlist).filter(
        Playlist.id == playlist_id,
        Playlist.owner_user_id == current_user.id,
    ).first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    unready_media = playlist_service.get_unready_playlist_media(db, playlist_id)
    if unready_media:
        names = ", ".join(media.original_filename for media in unready_media[:3])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Playlist contains media that is not ready for device playback: {names}",
        )

    playlist_service.assign_playlist_to_device(db, device, playlist_id)
    return {"message": "Playlist assigned successfully"}


@router.post("/{device_id}/assign-media/{media_id}", status_code=status.HTTP_200_OK)
async def assign_media(
    device_id: UUID,
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id,
    ).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    media = db.query(Media).filter(
        Media.id == media_id,
        Media.owner_user_id == current_user.id,
    ).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if media.status != READY or not media.playback_storage_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media is not ready for device playback yet",
        )

    playlist_service.assign_media_to_device(db, device, media_id)
    return {"message": "Media assigned successfully"}


@router.post("/{device_id}/commands", response_model=DeviceCommandStatusResponse, status_code=status.HTTP_201_CREATED)
async def queue_device_command(
    device_id: UUID,
    payload: DeviceQueueCommandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id,
    ).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    command = device_service.queue_command(db, device, payload, current_user.id)
    return device_service.command_to_status_response(command)


@router.get("/{device_id}/commands", response_model=list[DeviceCommandStatusResponse])
async def list_device_commands(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id,
    ).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    commands = device_service.list_recent_commands(db, device)
    return [device_service.command_to_status_response(command) for command in commands]


@router.get("/{device_id}/runtime", response_model=DeviceRuntimeStatusResponse)
async def get_device_runtime_status(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id,
    ).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    if not device.runtime_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No runtime telemetry yet")
    assignment = device.assignment
    assignment_type = "none"
    assigned_media_id = None
    assigned_playlist_id = None
    assigned_at = None
    if assignment:
        assignment_type = "media" if assignment.media_id else "playlist"
        assigned_media_id = assignment.media_id
        assigned_playlist_id = assignment.playlist_id
        assigned_at = assignment.assigned_at

    return DeviceRuntimeStatusResponse(
        app_version=device.runtime_status.app_version,
        local_ip=device.runtime_status.local_ip,
        uptime_seconds=device.runtime_status.uptime_seconds,
        storage_free_bytes=device.runtime_status.storage_free_bytes,
        cache_free_bytes=device.runtime_status.cache_free_bytes,
        current_media_id=device.runtime_status.current_media_id,
        current_playlist_id=device.runtime_status.current_playlist_id,
        device_state=device.runtime_status.device_state,
        temperature_c=device.runtime_status.temperature_c,
        cpu_frequency_mhz=device.runtime_status.cpu_frequency_mhz,
        dropped_frames=device.runtime_status.dropped_frames,
        playback_errors=device.runtime_status.playback_errors,
        recent_logs=device.runtime_status.recent_logs or [],
        health_status=device.runtime_status.health_status,
        last_error=device.runtime_status.last_error,
        updated_at=device.runtime_status.updated_at,
        assignment_type=assignment_type,
        assigned_media_id=assigned_media_id,
        assigned_playlist_id=assigned_playlist_id,
        assigned_at=assigned_at,
    )

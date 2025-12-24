from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Union

from app.database import get_db
from app.deps import get_current_device
from app.models.models import Device, Media
from app.schemas.device import (
    PairingResponse,
    DeviceCheckinRequest,
    DeviceCheckinResponsePaired,
    DeviceCheckinResponseUnpaired
)
from app.services import device as device_service
from app.utils.storage import get_file_path

router = APIRouter(prefix="/device", tags=["device-agent"])


@router.post("/pair/request", response_model=PairingResponse)
async def request_pairing(
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db)
):
    """Device requests a pairing code"""
    pairing = device_service.create_pairing_request(db, current_device)
    return pairing


@router.post("/checkin", response_model=Union[DeviceCheckinResponsePaired, DeviceCheckinResponseUnpaired])
async def device_checkin(
    checkin_data: DeviceCheckinRequest,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db)
):
    """Device checks in and gets current state"""
    # TODO: Store checkin data (app_version, ip, storage_free_bytes) if needed
    
    # Update last_seen_at
    device_service.update_device_checkin(db, current_device)
    
    # Get device state
    state = device_service.get_device_state(db, current_device)
    
    if state["paired"]:
        return DeviceCheckinResponsePaired(**state)
    else:
        return DeviceCheckinResponseUnpaired(**state)


@router.get("/media/{media_id}/download")
async def download_media(
    media_id: UUID,
    current_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db)
):
    """Download media file (device must be paired and authorized)"""
    # Check authorization
    if not device_service.can_device_access_media(db, current_device, media_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this media"
        )
    
    # Get media
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Return file
    file_path = get_file_path(media.filename)
    return FileResponse(
        path=file_path,
        media_type=media.mime_type,
        filename=media.original_filename
    )
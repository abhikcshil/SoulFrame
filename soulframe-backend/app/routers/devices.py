from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Device
from app.schemas.device import DeviceResponse, DeviceUpdate, DeviceClaimRequest
from app.services import device as device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all devices owned by current user"""
    devices = db.query(Device).filter(Device.owner_user_id == current_user.id).all()
    return devices


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_data: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update device name"""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    device.name = device_data.name
    db.commit()
    db.refresh(device)
    return device


@router.post("/claim", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
async def claim_device(
    claim_data: DeviceClaimRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Claim a device using pairing code"""
    device = device_service.claim_device(db, claim_data.pairing_code, current_user.id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired pairing code"
        )
    
    return device
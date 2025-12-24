from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
import secrets
import string

from app.config import settings
from app.models.models import Device, DeviceSettings, DeviceAssignment, Playlist, PlaylistItem, Media
from app.schemas.device import PairingResponse, DeviceSettingsResponse, MediaManifestItem, PlaylistItemResponse


def generate_pairing_code(length: int = 8) -> str:
    """Generate a random alphanumeric pairing code (uppercase)"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_device_token() -> str:
    """Generate a secure device token"""
    return secrets.token_urlsafe(32)


def create_pairing_request(db: Session, device: Device) -> PairingResponse:
    """Generate or refresh pairing code for device"""
    # Generate unique pairing code
    while True:
        code = generate_pairing_code(settings.PAIRING_CODE_LENGTH)
        existing = db.query(Device).filter(Device.pairing_code == code).first()
        if not existing:
            break
    
    expires_at = datetime.utcnow() + timedelta(minutes=settings.PAIRING_CODE_EXPIRY_MINUTES)
    
    device.pairing_code = code
    device.pairing_expires_at = expires_at
    db.commit()
    
    claim_url = f"{settings.WEB_BASE_URL}/claim?code={code}"
    
    return PairingResponse(
        pairing_code=code,
        expires_at=expires_at,
        claim_url=claim_url
    )


def claim_device(db: Session, pairing_code: str, user_id) -> Device:
    """Claim a device with pairing code"""
    device = db.query(Device).filter(
        and_(
            Device.pairing_code == pairing_code,
            Device.pairing_expires_at > datetime.utcnow()
        )
    ).first()
    
    if not device:
        return None
    
    device.owner_user_id = user_id
    device.pairing_code = None
    device.pairing_expires_at = None
    
    # Create default settings if not exists
    if not device.settings:
        settings_obj = DeviceSettings(device_id=device.id)
        db.add(settings_obj)
    
    db.commit()
    db.refresh(device)
    return device


def update_device_checkin(db: Session, device: Device) -> None:
    """Update device last_seen_at timestamp"""
    device.last_seen_at = datetime.utcnow()
    db.commit()


def get_device_state(db: Session, device: Device) -> dict:
    """Get complete device state for checkin response"""
    # If device is not paired
    if not device.owner_user_id:
        # Generate or get existing pairing code
        if not device.pairing_code or device.pairing_expires_at < datetime.utcnow():
            pairing = create_pairing_request(db, device)
        else:
            pairing = PairingResponse(
                pairing_code=device.pairing_code,
                expires_at=device.pairing_expires_at,
                claim_url=f"{settings.WEB_BASE_URL}/claim?code={device.pairing_code}"
            )
        
        return {
            "paired": False,
            "pairing": pairing
        }
    
    # Device is paired - get full state
    # Get settings
    if not device.settings:
        settings_obj = DeviceSettings(device_id=device.id)
        db.add(settings_obj)
        db.commit()
        db.refresh(device)
    
    settings_response = DeviceSettingsResponse.model_validate(device.settings)
    
    # Get assigned playlist
    assignment = device.assignment
    assigned_playlist_id = assignment.playlist_id if assignment else None
    
    # Get media manifest and playlist items
    media_manifest = []
    playlist_items = []
    
    if assignment:
        playlist = db.query(Playlist).filter(Playlist.id == assignment.playlist_id).first()
        if playlist:
            items = db.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).order_by(PlaylistItem.position).all()
            
            for item in items:
                media_manifest.append(MediaManifestItem(
                    media_id=item.media_id,
                    download_url=f"/device/media/{item.media_id}/download"
                ))
                playlist_items.append(PlaylistItemResponse(
                    media_id=item.media_id,
                    position=item.position
                ))
    
    return {
        "paired": True,
        "assigned_playlist_id": assigned_playlist_id,
        "settings": settings_response,
        "media_manifest": media_manifest,
        "playlist_items": playlist_items
    }
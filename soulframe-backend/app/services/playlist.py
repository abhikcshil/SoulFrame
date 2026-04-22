from sqlalchemy.orm import Session
from uuid import UUID

from app.models.models import Playlist, PlaylistItem, DeviceAssignment, Device, Media
from app.schemas.playlist import PlaylistItemInput
from app.services.media_processing import READY


def create_playlist(db: Session, user_id: UUID, name: str) -> Playlist:
    """Create a new playlist"""
    playlist = Playlist(owner_user_id=user_id, name=name)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


def update_playlist(
    db: Session,
    playlist: Playlist,
    name: str,
    items: list[PlaylistItemInput]
) -> Playlist:
    """Update playlist name and items"""
    playlist.name = name
    
    # Delete existing items
    db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist.id).delete()
    
    # Add new items
    for item_input in items:
        item = PlaylistItem(
            playlist_id=playlist.id,
            media_id=item_input.media_id,
            position=item_input.position
        )
        db.add(item)
    
    db.commit()
    db.refresh(playlist)
    return playlist


def get_user_playlists(db: Session, user_id: UUID) -> list[Playlist]:
    """Get all playlists for a user"""
    return db.query(Playlist).filter(Playlist.owner_user_id == user_id).all()


def get_unready_playlist_media(db: Session, playlist_id: UUID) -> list[Media]:
    """Return playlist media that cannot be sent to a device yet."""
    return (
        db.query(Media)
        .join(PlaylistItem, PlaylistItem.media_id == Media.id)
        .filter(
            PlaylistItem.playlist_id == playlist_id,
            (Media.status != READY) | (Media.playback_storage_key.is_(None)),
        )
        .all()
    )


def assign_playlist_to_device(db: Session, device: Device, playlist_id: UUID) -> DeviceAssignment:
    """Assign a playlist to a device (replace existing assignment)"""
    # Delete existing assignment
    db.query(DeviceAssignment).filter(DeviceAssignment.device_id == device.id).delete()
    
    # Create new assignment
    assignment = DeviceAssignment(device_id=device.id, playlist_id=playlist_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

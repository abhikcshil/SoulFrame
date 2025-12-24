from sqlalchemy.orm import Session
from uuid import UUID

from app.models.models import Playlist, PlaylistItem, DeviceAssignment, Device
from app.schemas.playlist import PlaylistItemInput


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
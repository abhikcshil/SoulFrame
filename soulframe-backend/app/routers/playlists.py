from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Playlist, Device, Media
from app.schemas.playlist import PlaylistCreate, PlaylistUpdate, PlaylistResponse
from app.services import playlist as playlist_service
from app.services.media_processing import READY

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    playlist_data: PlaylistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new playlist"""
    playlist = playlist_service.create_playlist(db, current_user.id, playlist_data.name)
    return playlist


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all playlists for current user"""
    playlists = playlist_service.get_user_playlists(db, current_user.id)
    return playlists


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: UUID,
    playlist_data: PlaylistUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update playlist name and items"""
    playlist = db.query(Playlist).filter(
        Playlist.id == playlist_id,
        Playlist.owner_user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    # Validate that all media IDs exist and belong to user
    for item in playlist_data.items:
        media = db.query(Media).filter(
            Media.id == item.media_id,
            Media.owner_user_id == current_user.id
        ).first()
        if not media:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Media {item.media_id} not found or not owned by user"
            )
        if media.status != READY or not media.playback_storage_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Media {item.media_id} is not ready for device playback"
            )
    
    playlist = playlist_service.update_playlist(
        db, playlist, playlist_data.name, playlist_data.items
    )
    return playlist


@router.post("/devices/{device_id}/assign/{playlist_id}", status_code=status.HTTP_200_OK)
async def assign_playlist(
    device_id: UUID,
    playlist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign playlist to device"""
    # Verify device ownership
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_user_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Verify playlist ownership
    playlist = db.query(Playlist).filter(
        Playlist.id == playlist_id,
        Playlist.owner_user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    unready_media = playlist_service.get_unready_playlist_media(db, playlist_id)
    if unready_media:
        names = ", ".join(media.original_filename for media in unready_media[:3])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Playlist contains media that is not ready for device playback: {names}"
        )
    
    playlist_service.assign_playlist_to_device(db, device, playlist_id)
    return {"message": "Playlist assigned successfully"}

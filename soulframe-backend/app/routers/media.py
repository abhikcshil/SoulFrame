from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Media
from app.schemas.media import MediaResponse
from app.services import media as media_service
from app.config import settings

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/upload", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a media file"""
    # TODO: Add rate limiting
    
    # Validate mime type
    if file.content_type not in settings.allowed_mime_types_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.ALLOWED_MIME_TYPES}"
        )
    
    # Read file
    content = await file.read()
    size_bytes = len(content)
    
    # Validate size
    if size_bytes > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Create media record
    media = media_service.create_media(
        db=db,
        user_id=current_user.id,
        file_content=content,
        original_filename=file.filename,
        mime_type=file.content_type,
        size_bytes=size_bytes
    )
    
    return media


@router.get("", response_model=list[MediaResponse])
async def list_media(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all media for current user"""
    media_list = media_service.get_user_media(db, current_user.id)
    return media_list


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a media file"""
    media = db.query(Media).filter(
        Media.id == media_id,
        Media.owner_user_id == current_user.id
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    media_service.delete_media(db, media)
    return None
from sqlalchemy.orm import Session
from uuid import UUID
import os

from app.models.models import Media
from app.utils.storage import save_file, delete_file


def create_media(
    db: Session,
    user_id: UUID,
    file_content: bytes,
    original_filename: str,
    mime_type: str,
    size_bytes: int
) -> Media:
    """Create media record and save file"""
    media = Media(
        owner_user_id=user_id,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        filename=""  # Will be set after we have the ID
    )
    db.add(media)
    db.flush()  # Get the ID without committing
    
    # Save file with media ID as filename
    ext = os.path.splitext(original_filename)[1]
    filename = f"{media.id}{ext}"
    save_file(filename, file_content)
    
    media.filename = filename
    db.commit()
    db.refresh(media)
    return media


def delete_media(db: Session, media: Media) -> None:
    """Delete media record and file"""
    # Delete file from storage
    delete_file(media.filename)
    
    # Delete from database
    db.delete(media)
    db.commit()


def get_user_media(db: Session, user_id: UUID) -> list[Media]:
    """Get all media for a user"""
    return db.query(Media).filter(Media.owner_user_id == user_id).all()
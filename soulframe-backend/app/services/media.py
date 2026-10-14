from sqlalchemy.orm import Session
from uuid import UUID
import os

from app.database import SessionLocal
from app.models.models import Media, PlaylistItem
from app.utils.storage import save_file, delete_file
from app.services import media_processing


def create_media(
    db: Session,
    user_id: UUID,
    file_content: bytes,
    original_filename: str,
    mime_type: str,
    size_bytes: int
) -> Media:
    """Persist an upload and return immediately while its rendition is prepared."""
    media = Media(
        owner_user_id=user_id,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        original_mime_type=mime_type,
        original_size_bytes=size_bytes,
        status=media_processing.UPLOADED,
        filename=""  # Will be set after we have the ID
    )
    db.add(media)
    db.flush()  # Get the ID without committing
    
    ext = os.path.splitext(original_filename)[1]
    source_storage_key = f"original/{media.id}{ext}"
    save_file(source_storage_key, file_content)
    
    media.filename = source_storage_key
    media.source_storage_key = source_storage_key
    media.status = media_processing.PROCESSING
    db.commit()
    db.refresh(media)

    return media


def process_media_in_background(media_id: UUID) -> None:
    """Run normalization in an isolated database session after the upload response.

    Keeping this work out of the request lets the UI distinguish a completed file
    transfer from media processing, without introducing a worker service.
    """
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            return

        try:
            media_processing.process_media(media)
        except Exception as exc:
            media_processing.fail_media(media, exc)
        else:
            media.filename = media.playback_storage_key or media.source_storage_key or media.filename
            media.mime_type = media.playback_mime_type or media.original_mime_type or media.mime_type
            media.size_bytes = media.playback_size_bytes or media.original_size_bytes or media.size_bytes

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def delete_media(db: Session, media: Media) -> None:
    """Delete media record and stored source/playback files."""
    db.query(PlaylistItem).filter(PlaylistItem.media_id == media.id).delete()
    delete_file(media.source_storage_key or media.filename)
    if media.playback_storage_key != media.source_storage_key:
        delete_file(media.playback_storage_key)
    if media.thumbnail_storage_key:
        delete_file(media.thumbnail_storage_key)
    
    db.delete(media)
    db.commit()


def get_user_media(db: Session, user_id: UUID) -> list[Media]:
    """Get all media for a user"""
    return db.query(Media).filter(Media.owner_user_id == user_id).all()

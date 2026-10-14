from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status, UploadFile, File
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.deps import get_current_user
from app.models.models import User, Media
from app.schemas.media import MediaAssetUrlsResponse, MediaResponse
from app.services import media as media_service
from app.config import settings
from app.utils.storage import get_file_path

router = APIRouter(prefix="/media", tags=["media"])
ASSET_TOKEN_MINUTES = 5


def _asset_token(media: Media, kind: str) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ASSET_TOKEN_MINUTES)
    token = jwt.encode(
        {"sub": str(media.owner_user_id), "media_id": str(media.id), "kind": kind, "exp": expires_at},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, expires_at


def _require_asset_token(media: Media, kind: str, token: str) -> None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired asset URL")
    if payload.get("sub") != str(media.owner_user_id) or payload.get("media_id") != str(media.id) or payload.get("kind") != kind:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Asset URL is not authorized for this media")


def _owned_media(db: Session, media_id: UUID, user_id) -> Media:
    media = db.query(Media).filter(Media.id == media_id, Media.owner_user_id == user_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    return media


@router.post("/upload", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(media_service.process_media_in_background, media.id)
    return media


@router.get("", response_model=list[MediaResponse])
async def list_media(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all media for current user"""
    media_list = media_service.get_user_media(db, current_user.id)
    return media_list


@router.post("/{media_id}/asset-urls", response_model=MediaAssetUrlsResponse)
async def get_media_asset_urls(
    media_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Issue short-lived browser-safe URLs after enforcing media ownership."""
    media = _owned_media(db, media_id, current_user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ASSET_TOKEN_MINUTES)
    base_url = str(request.base_url).rstrip("/")
    thumbnail_url = None
    preview_url = None
    if media.thumbnail_storage_key:
        thumbnail_token, expires_at = _asset_token(media, "thumbnail")
        thumbnail_url = f"{base_url}/media/{media.id}/thumbnail?token={thumbnail_token}"
    if media.status == media_service.media_processing.READY and media.playback_storage_key:
        preview_token, expires_at = _asset_token(media, "preview")
        preview_url = f"{base_url}/media/{media.id}/preview?token={preview_token}"
    return MediaAssetUrlsResponse(thumbnail_url=thumbnail_url, preview_url=preview_url, expires_at=expires_at)


@router.get("/{media_id}/thumbnail")
async def get_thumbnail(
    media_id: UUID,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media or not media.thumbnail_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available")
    _require_asset_token(media, "thumbnail", token)
    path = get_file_path(media.thumbnail_storage_key)
    if not Path(path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file is unavailable")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


@router.get("/{media_id}/preview")
async def preview_media(
    media_id: UUID,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Serve normalized media; Starlette FileResponse handles byte ranges for seeking."""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media or not media.playback_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview not available")
    _require_asset_token(media, "preview", token)
    path = get_file_path(media.playback_storage_key)
    if not Path(path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview file is unavailable")
    return FileResponse(
        path,
        media_type=media.playback_mime_type or media.mime_type,
        headers={"Cache-Control": "private, max-age=300", "Accept-Ranges": "bytes"},
    )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_media(db, media_id, current_user.id)


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

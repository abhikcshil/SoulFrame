"""Generate missing thumbnails for existing ready video media.

Run from ``soulframe-backend`` after migration: ``python -m app.scripts.backfill_thumbnails``.
The operation is idempotent: existing thumbnail files are retained unless a
database row has no thumbnail key.
"""

from app.database import SessionLocal
from app.models.models import Media
from app.services.media_processing import READY, generate_video_thumbnail, is_video_mime_type
from app.utils.storage import get_file_path
from pathlib import Path


def main() -> int:
    db = SessionLocal()
    generated = failed = skipped = 0
    try:
        candidates = db.query(Media).filter(Media.status == READY).all()
        for media in candidates:
            if not is_video_mime_type(media.original_mime_type or media.mime_type):
                skipped += 1
                continue
            if media.thumbnail_storage_key and Path(get_file_path(media.thumbnail_storage_key)).is_file():
                skipped += 1
                continue
            try:
                generate_video_thumbnail(media)
                generated += 1
            except Exception as exc:
                media.thumbnail_error = str(exc)[:2000]
                failed += 1
            db.commit()
    finally:
        db.close()
    print(f"Thumbnail backfill complete: generated={generated}, skipped={skipped}, failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

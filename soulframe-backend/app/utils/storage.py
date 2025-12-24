import os
from pathlib import Path
from app.config import settings


def ensure_media_dir():
    """Ensure media storage directory exists"""
    Path(settings.MEDIA_STORAGE_PATH).mkdir(parents=True, exist_ok=True)


def save_file(filename: str, content: bytes) -> str:
    """Save file to storage and return filepath"""
    ensure_media_dir()
    filepath = os.path.join(settings.MEDIA_STORAGE_PATH, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath


def delete_file(filename: str) -> None:
    """Delete file from storage"""
    filepath = os.path.join(settings.MEDIA_STORAGE_PATH, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


def get_file_path(filename: str) -> str:
    """Get full path to a file"""
    return os.path.join(settings.MEDIA_STORAGE_PATH, filename)
from pathlib import Path
from app.config import settings


def ensure_media_dir():
    """Ensure media storage directory exists"""
    Path(settings.MEDIA_STORAGE_PATH).mkdir(parents=True, exist_ok=True)


def _resolve_storage_path(storage_key: str) -> Path:
    base_path = Path(settings.MEDIA_STORAGE_PATH).resolve()
    filepath = (base_path / storage_key).resolve()
    if base_path not in filepath.parents and filepath != base_path:
        raise ValueError("Storage key resolves outside media storage path")
    return filepath


def save_file(storage_key: str, content: bytes) -> str:
    """Save file to storage and return filepath"""
    ensure_media_dir()
    filepath = _resolve_storage_path(storage_key)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(content)
    return str(filepath)


def delete_file(storage_key: str | None) -> None:
    """Delete file from storage"""
    if not storage_key:
        return
    filepath = _resolve_storage_path(storage_key)
    if filepath.exists():
        filepath.unlink()


def get_file_path(storage_key: str) -> str:
    """Get full path to a file"""
    return str(_resolve_storage_path(storage_key))

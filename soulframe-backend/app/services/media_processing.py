from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.models.models import Media
from app.utils.storage import get_file_path


READY = "ready"
PROCESSING = "processing"
FAILED = "failed"
UPLOADED = "uploaded"

PLAYBACK_VIDEO_MIME_TYPE = "video/mp4"
VIDEO_MIME_PREFIX = "video/"
IMAGE_MIME_PREFIX = "image/"


class MediaProcessingError(Exception):
    pass


@dataclass
class ProbeMetadata:
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    pixel_format: str | None = None
    raw: dict[str, Any] | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_video_mime_type(mime_type: str | None) -> bool:
    return bool(mime_type and mime_type.startswith(VIDEO_MIME_PREFIX))


def is_image_mime_type(mime_type: str | None) -> bool:
    return bool(mime_type and mime_type.startswith(IMAGE_MIME_PREFIX))


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise MediaProcessingError(f"Required media tool not found: {command[0]}") from exc


def probe_media(path: str) -> ProbeMetadata:
    result = _run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
        ]
    )
    if result.returncode != 0:
        raise MediaProcessingError(result.stderr.strip() or "Unable to inspect media file")

    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    format_info = payload.get("format") or {}

    duration = None
    raw_duration = (video_stream or {}).get("duration") or format_info.get("duration")
    if raw_duration is not None:
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            duration = None

    return ProbeMetadata(
        width=video_stream.get("width") if video_stream else None,
        height=video_stream.get("height") if video_stream else None,
        duration_seconds=duration,
        video_codec=video_stream.get("codec_name") if video_stream else None,
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        pixel_format=video_stream.get("pix_fmt") if video_stream else None,
        raw={
            "format_name": format_info.get("format_name"),
            "bit_rate": format_info.get("bit_rate"),
            "video_codec": video_stream.get("codec_name") if video_stream else None,
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "pixel_format": video_stream.get("pix_fmt") if video_stream else None,
        },
    )


def normalize_video(source_path: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result = _run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            source_path,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            "scale=w=min(1920\\,iw):h=min(1080\\,ih):force_original_aspect_ratio=decrease:force_divisible_by=2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "23",
            "-maxrate",
            "6000k",
            "-bufsize",
            "12000k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_path,
        ]
    )
    if result.returncode != 0:
        raise MediaProcessingError(result.stderr.strip() or "ffmpeg failed to normalize video")


def apply_probe_metadata(media: Media, metadata: ProbeMetadata) -> None:
    media.width = metadata.width
    media.height = metadata.height
    media.duration_seconds = metadata.duration_seconds
    media.normalization_metadata = metadata.raw or {}


def process_media(media: Media) -> None:
    """Create the device playback rendition for an uploaded media record."""
    source_key = media.source_storage_key or media.filename
    source_path = get_file_path(source_key)

    media.status = PROCESSING
    media.processing_error = None

    if is_video_mime_type(media.original_mime_type or media.mime_type):
        playback_key = f"normalized/{media.id}.mp4"
        playback_path = get_file_path(playback_key)
        normalize_video(source_path, playback_path)
        metadata = probe_media(playback_path)
        apply_probe_metadata(media, metadata)
        media.playback_storage_key = playback_key
        media.playback_mime_type = PLAYBACK_VIDEO_MIME_TYPE
        media.playback_size_bytes = Path(playback_path).stat().st_size
        media.normalized_at = utcnow()
        media.status = READY
        return

    if is_image_mime_type(media.original_mime_type or media.mime_type):
        ext = Path(media.original_filename).suffix.lower() or ".img"
        playback_key = f"normalized/{media.id}{ext}"
        playback_path = get_file_path(playback_key)
        Path(playback_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, playback_path)

        try:
            metadata = probe_media(playback_path)
            apply_probe_metadata(media, metadata)
        except MediaProcessingError:
            media.normalization_metadata = {"note": "Image copied without ffprobe metadata"}

        media.playback_storage_key = playback_key
        media.playback_mime_type = media.original_mime_type or media.mime_type
        media.playback_size_bytes = Path(playback_path).stat().st_size
        media.normalized_at = utcnow()
        media.status = READY
        return

    raise MediaProcessingError(f"Unsupported media type: {media.original_mime_type or media.mime_type}")


def fail_media(media: Media, exc: Exception) -> None:
    media.status = FAILED
    media.processing_error = str(exc)[:2000]

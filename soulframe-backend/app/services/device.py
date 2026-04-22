from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Optional
import secrets
import string

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import (
    Device,
    DeviceAssignment,
    DeviceCommand,
    DeviceRuntimeConfig,
    DeviceRuntimeStatus,
    DeviceSettings,
    Media,
    Playlist,
    PlaylistItem,
    User,
)
from app.schemas.device import (
    AssignedContentResponse,
    AssignedMediaFile,
    DeviceCommandAckRequest,
    DeviceCommandResponse,
    DeviceCommandStatusResponse,
    DeviceHeartbeatRequest,
    DeviceIdentityResponse,
    DeviceQueueCommandRequest,
    DeviceRuntimeConfigResponse,
    DeviceSyncRequest,
    DeviceSyncResponse,
    PairingResponse,
)
from app.services.media_processing import READY


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def generate_pairing_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_device_token() -> str:
    return secrets.token_urlsafe(32)


def get_device_state(device: Device) -> str:
    if not device.owner_user_id:
        return "unclaimed"
    if not device.last_seen_at:
        return "offline"
    diff_seconds = (utcnow() - _ensure_aware(device.last_seen_at)).total_seconds()
    return "active" if diff_seconds <= settings.DEVICE_OFFLINE_THRESHOLD_SECONDS else "offline"


def register_device(db: Session, name: Optional[str], app_version: Optional[str]) -> Device:
    token = generate_device_token()
    device = Device(
        name=name or "SoulFrame Device",
        device_token=token,
    )
    db.add(device)
    db.flush()

    db.add(
        DeviceRuntimeStatus(
            device_id=device.id,
            app_version=app_version,
        )
    )
    db.add(
        DeviceRuntimeConfig(
            device_id=device.id,
            poll_interval_seconds=settings.DEVICE_DEFAULT_POLL_INTERVAL_SECONDS,
            sync_interval_seconds=settings.DEVICE_DEFAULT_SYNC_INTERVAL_SECONDS,
            cache_max_bytes=settings.DEVICE_DEFAULT_CACHE_MAX_BYTES,
            playback_mode=settings.DEVICE_DEFAULT_PLAYBACK_MODE,
            fallback_behavior=settings.DEVICE_DEFAULT_FALLBACK_BEHAVIOR,
        )
    )
    db.commit()
    db.refresh(device)
    return device


def create_pairing_request(db: Session, device: Device) -> PairingResponse:
    while True:
        code = generate_pairing_code(settings.PAIRING_CODE_LENGTH)
        existing = db.query(Device).filter(Device.pairing_code == code).first()
        if not existing:
            break

    expires_at = utcnow() + timedelta(minutes=settings.PAIRING_CODE_EXPIRY_MINUTES)
    device.pairing_code = code
    device.pairing_expires_at = expires_at
    if not device.device_token:
        device.device_token = generate_device_token()
    db.commit()

    return PairingResponse(
        pairing_code=code,
        expires_at=expires_at,
        claim_url=f"{settings.WEB_BASE_URL}/claim?code={code}",
    )


def claim_device(db: Session, pairing_code: str, user_id) -> Optional[Device]:
    device = db.query(Device).filter(
        and_(
            Device.pairing_code == pairing_code,
            Device.pairing_expires_at > utcnow(),
        )
    ).first()
    if not device:
        return None

    if not device.device_token:
        device.device_token = generate_device_token()

    device.owner_user_id = user_id
    device.pairing_code = None
    device.pairing_expires_at = None

    if not device.settings:
        db.add(DeviceSettings(device_id=device.id))
    if not device.runtime_status:
        db.add(DeviceRuntimeStatus(device_id=device.id))
    if not device.runtime_config:
        db.add(
            DeviceRuntimeConfig(
                device_id=device.id,
                poll_interval_seconds=settings.DEVICE_DEFAULT_POLL_INTERVAL_SECONDS,
                sync_interval_seconds=settings.DEVICE_DEFAULT_SYNC_INTERVAL_SECONDS,
                cache_max_bytes=settings.DEVICE_DEFAULT_CACHE_MAX_BYTES,
                playback_mode=settings.DEVICE_DEFAULT_PLAYBACK_MODE,
                fallback_behavior=settings.DEVICE_DEFAULT_FALLBACK_BEHAVIOR,
            )
        )

    db.commit()
    db.refresh(device)
    return device


def _ensure_runtime_records(db: Session, device: Device) -> None:
    created = False
    if not device.runtime_status:
        db.add(DeviceRuntimeStatus(device_id=device.id))
        created = True
    if not device.runtime_config:
        db.add(
            DeviceRuntimeConfig(
                device_id=device.id,
                poll_interval_seconds=settings.DEVICE_DEFAULT_POLL_INTERVAL_SECONDS,
                sync_interval_seconds=settings.DEVICE_DEFAULT_SYNC_INTERVAL_SECONDS,
                cache_max_bytes=settings.DEVICE_DEFAULT_CACHE_MAX_BYTES,
                playback_mode=settings.DEVICE_DEFAULT_PLAYBACK_MODE,
                fallback_behavior=settings.DEVICE_DEFAULT_FALLBACK_BEHAVIOR,
            )
        )
        created = True
    if not device.settings:
        db.add(DeviceSettings(device_id=device.id))
        created = True
    if created:
        db.commit()
        db.refresh(device)


def update_runtime_status(db: Session, device: Device, status: DeviceHeartbeatRequest | DeviceSyncRequest) -> None:
    _ensure_runtime_records(db, device)
    runtime_status = device.runtime_status
    now = utcnow()
    device.last_seen_at = now

    if status.app_version is not None:
        runtime_status.app_version = status.app_version
    if status.ip is not None:
        runtime_status.local_ip = status.ip
    if status.uptime_seconds is not None:
        runtime_status.uptime_seconds = status.uptime_seconds
    if status.storage_free_bytes is not None:
        runtime_status.storage_free_bytes = status.storage_free_bytes
    if status.cache_free_bytes is not None:
        runtime_status.cache_free_bytes = status.cache_free_bytes
    if status.current_media_id is not None:
        runtime_status.current_media_id = status.current_media_id
    if status.current_playlist_id is not None:
        runtime_status.current_playlist_id = status.current_playlist_id
    if status.health_status is not None:
        runtime_status.health_status = status.health_status
    if status.last_error is not None:
        runtime_status.last_error = status.last_error

    runtime_status.updated_at = now
    db.commit()


def get_runtime_config(device: Device) -> DeviceRuntimeConfigResponse:
    cfg = device.runtime_config
    revision_source = (
        f"{cfg.poll_interval_seconds}|{cfg.sync_interval_seconds}|{cfg.cache_max_bytes}|"
        f"{cfg.playback_mode}|{cfg.fallback_behavior}|{cfg.updated_at.isoformat() if cfg.updated_at else ''}"
    )
    return DeviceRuntimeConfigResponse(
        poll_interval_seconds=cfg.poll_interval_seconds,
        sync_interval_seconds=cfg.sync_interval_seconds,
        cache_max_bytes=cfg.cache_max_bytes,
        playback_mode=cfg.playback_mode,
        fallback_behavior=cfg.fallback_behavior,
        config_revision=sha256(revision_source.encode("utf-8")).hexdigest()[:16],
    )


def _build_content_items(db: Session, assignment: DeviceAssignment, api_base_url: str) -> tuple[list[AssignedMediaFile], str]:
    playlist = db.query(Playlist).filter(Playlist.id == assignment.playlist_id).first()
    if not playlist:
        return [], "none"

    playlist_items = (
        db.query(PlaylistItem, Media)
        .join(Media, Media.id == PlaylistItem.media_id)
        .filter(
            PlaylistItem.playlist_id == playlist.id,
            Media.status == READY,
            Media.playback_storage_key.isnot(None),
        )
        .order_by(PlaylistItem.position.asc())
        .all()
    )

    items: list[AssignedMediaFile] = []
    revision_bits: list[str] = [str(playlist.id), assignment.assigned_at.isoformat() if assignment.assigned_at else ""]
    for item, media in playlist_items:
        playback_key = media.playback_storage_key or media.filename
        playback_mime_type = media.playback_mime_type or media.mime_type
        playback_size_bytes = media.playback_size_bytes or media.size_bytes
        checksum_seed = (
            f"{media.id}|{playback_key}|{playback_size_bytes}|{media.normalized_at.isoformat() if media.normalized_at else ''}"
        )
        checksum = sha256(checksum_seed.encode("utf-8")).hexdigest()
        revision_bits.append(f"{item.position}:{media.id}:{checksum}")
        items.append(
            AssignedMediaFile(
                media_id=media.id,
                original_filename=media.original_filename,
                mime_type=playback_mime_type,
                size_bytes=playback_size_bytes,
                width=media.width,
                height=media.height,
                duration_seconds=media.duration_seconds,
                checksum=checksum,
                updated_at=media.normalized_at or media.created_at,
                download_url=f"{api_base_url}/device/media/{media.id}/download",
            )
        )

    revision = sha256("|".join(revision_bits).encode("utf-8")).hexdigest()[:16]
    return items, revision


def get_assigned_content(db: Session, device: Device, api_base_url: str) -> AssignedContentResponse:
    assignment = device.assignment
    if not assignment:
        return AssignedContentResponse(
            assignment_type="none",
            assigned_playlist_id=None,
            content_revision="none",
            assigned_at=None,
            items=[],
        )

    items, revision = _build_content_items(db, assignment, api_base_url)
    return AssignedContentResponse(
        assignment_type="playlist",
        assigned_playlist_id=assignment.playlist_id,
        content_revision=revision,
        assigned_at=assignment.assigned_at,
        items=items,
    )


def queue_command(
    db: Session,
    device: Device,
    request: DeviceQueueCommandRequest,
    requested_by_user_id,
) -> DeviceCommand:
    expires_at = None
    if request.expires_in_seconds:
        expires_at = utcnow() + timedelta(seconds=request.expires_in_seconds)
    else:
        expires_at = utcnow() + timedelta(seconds=settings.DEVICE_COMMAND_DEFAULT_EXPIRY_SECONDS)

    command = DeviceCommand(
        device_id=device.id,
        command_type=request.command_type,
        payload=request.payload,
        requested_by_user_id=requested_by_user_id,
        status="queued",
        expires_at=expires_at,
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def list_recent_commands(db: Session, device: Device, limit: int = 20) -> list[DeviceCommand]:
    return (
        db.query(DeviceCommand)
        .filter(DeviceCommand.device_id == device.id)
        .order_by(DeviceCommand.created_at.desc())
        .limit(limit)
        .all()
    )


def get_pending_commands(db: Session, device: Device) -> list[DeviceCommandResponse]:
    now = utcnow()
    commands = (
        db.query(DeviceCommand)
        .filter(
            DeviceCommand.device_id == device.id,
            DeviceCommand.status.in_(["queued", "delivered"]),
        )
        .order_by(DeviceCommand.created_at.asc())
        .all()
    )
    pending: list[DeviceCommandResponse] = []
    for command in commands:
        if command.expires_at and _ensure_aware(command.expires_at) < now:
            command.status = "expired"
            continue
        if command.status == "queued":
            command.status = "delivered"
            command.delivered_at = now
        pending.append(
            DeviceCommandResponse(
                command_id=command.id,
                command_type=command.command_type,
                payload=command.payload or {},
                created_at=command.created_at,
                expires_at=command.expires_at,
            )
        )
    db.commit()
    return pending


def acknowledge_command(
    db: Session,
    device: Device,
    command_id,
    ack: DeviceCommandAckRequest,
) -> Optional[DeviceCommand]:
    command = (
        db.query(DeviceCommand)
        .filter(
            DeviceCommand.id == command_id,
            DeviceCommand.device_id == device.id,
        )
        .first()
    )
    if not command:
        return None

    command.status = "acknowledged"
    command.result_status = ack.status
    command.result_message = ack.message
    command.result_payload = ack.result_payload
    command.acknowledged_at = utcnow()
    db.commit()
    db.refresh(command)
    return command


def build_sync_response(db: Session, device: Device, payload: DeviceSyncRequest, api_base_url: str) -> DeviceSyncResponse:
    _ensure_runtime_records(db, device)
    update_runtime_status(db, device, payload)

    assigned_content = get_assigned_content(db, device, api_base_url)
    runtime_config = get_runtime_config(device)

    content_changed = payload.known_content_revision != assigned_content.content_revision
    config_changed = payload.known_config_revision != runtime_config.config_revision
    pending_commands = get_pending_commands(db, device) if payload.include_commands else []
    pairing = None
    account_name = None
    if not device.owner_user_id:
        if not device.pairing_code or not device.pairing_expires_at or _ensure_aware(device.pairing_expires_at) < utcnow():
            pairing = create_pairing_request(db, device)
        else:
            pairing = PairingResponse(
                pairing_code=device.pairing_code,
                expires_at=device.pairing_expires_at,
                claim_url=f"{settings.WEB_BASE_URL}/claim?code={device.pairing_code}",
            )
    else:
        owner = db.query(User).filter(User.id == device.owner_user_id).first()
        account_name = owner.email if owner else None

    return DeviceSyncResponse(
        server_time=utcnow(),
        device=DeviceIdentityResponse(
            device_id=device.id,
            device_name=device.name,
            state=get_device_state(device),
            is_claimed=device.owner_user_id is not None,
            last_seen_at=device.last_seen_at,
        ),
        account_name=account_name,
        pairing=pairing,
        has_changes=content_changed or config_changed or len(pending_commands) > 0,
        content_changed=content_changed,
        config_changed=config_changed,
        assigned_content=assigned_content,
        runtime_config=runtime_config,
        pending_commands=pending_commands,
    )


def build_heartbeat_response(db: Session, device: Device, payload: DeviceHeartbeatRequest):
    _ensure_runtime_records(db, device)
    update_runtime_status(db, device, payload)
    return {
        "device_id": device.id,
        "state": get_device_state(device),
        "server_time": utcnow(),
        "poll_interval_seconds": device.runtime_config.poll_interval_seconds,
    }


def can_device_access_media(db: Session, device: Device, media_id) -> bool:
    if not device.owner_user_id:
        return False
    assignment = device.assignment
    if not assignment:
        return False

    playlist_item = (
        db.query(PlaylistItem)
        .join(Media, Media.id == PlaylistItem.media_id)
        .filter(
            PlaylistItem.playlist_id == assignment.playlist_id,
            PlaylistItem.media_id == media_id,
            Media.status == READY,
            Media.playback_storage_key.isnot(None),
        )
        .first()
    )
    return playlist_item is not None


def command_to_status_response(command: DeviceCommand) -> DeviceCommandStatusResponse:
    return DeviceCommandStatusResponse.model_validate(command)

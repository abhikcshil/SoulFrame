from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Time, ForeignKey, Uuid, JSON, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    devices = relationship("Device", back_populates="owner")
    media = relationship("Media", back_populates="owner")
    playlists = relationship("Playlist", back_populates="owner")


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    device_token = Column(String(255), unique=True, nullable=False, index=True)
    pairing_code = Column(String(20), unique=True, nullable=True, index=True)
    pairing_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="devices")
    assignment = relationship("DeviceAssignment", back_populates="device", uselist=False)
    settings = relationship("DeviceSettings", back_populates="device", uselist=False)
    runtime_status = relationship("DeviceRuntimeStatus", back_populates="device", uselist=False, cascade="all, delete-orphan")
    runtime_config = relationship("DeviceRuntimeConfig", back_populates="device", uselist=False, cascade="all, delete-orphan")
    commands = relationship("DeviceCommand", back_populates="device", cascade="all, delete-orphan")


class Media(Base):
    __tablename__ = "media"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    status = Column(String(30), nullable=False, default="uploaded", index=True)
    source_storage_key = Column(String(500), nullable=True)
    playback_storage_key = Column(String(500), nullable=True)
    original_mime_type = Column(String(100), nullable=True)
    playback_mime_type = Column(String(100), nullable=True)
    original_size_bytes = Column(BigInteger, nullable=True)
    playback_size_bytes = Column(BigInteger, nullable=True)
    thumbnail_storage_key = Column(String(500), nullable=True)
    thumbnail_generated_at = Column(DateTime(timezone=True), nullable=True)
    thumbnail_error = Column(Text, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    normalized_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    normalization_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="media")
    playlist_items = relationship("PlaylistItem", back_populates="media")
    direct_assignments = relationship("DeviceAssignment", back_populates="media")

    @property
    def thumbnail_available(self) -> bool:
        return bool(self.thumbnail_storage_key)


class Playlist(Base):
    __tablename__ = "playlists"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="playlists")
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan")
    assignments = relationship("DeviceAssignment", back_populates="playlist")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playlist_id = Column(Uuid(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    
    playlist = relationship("Playlist", back_populates="items")
    media = relationship("Media", back_populates="playlist_items")


class DeviceAssignment(Base):
    __tablename__ = "device_assignments"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    playlist_id = Column(Uuid(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=True, index=True)
    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    device = relationship("Device", back_populates="assignment")
    playlist = relationship("Playlist", back_populates="assignments")
    media = relationship("Media", back_populates="direct_assignments")


class DeviceSettings(Base):
    __tablename__ = "device_settings"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    brightness = Column(Integer, nullable=False, default=50)
    orientation = Column(String(20), nullable=False, default="portrait")
    sleep_enabled = Column(Boolean, nullable=False, default=False)
    sleep_start = Column(Time, nullable=True)
    sleep_end = Column(Time, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    device = relationship("Device", back_populates="settings")


class DeviceRuntimeStatus(Base):
    __tablename__ = "device_runtime_status"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    app_version = Column(String(100), nullable=True)
    local_ip = Column(String(100), nullable=True)
    uptime_seconds = Column(BigInteger, nullable=True)
    storage_free_bytes = Column(BigInteger, nullable=True)
    cache_free_bytes = Column(BigInteger, nullable=True)
    current_media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True)
    current_playlist_id = Column(Uuid(as_uuid=True), ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)
    device_state = Column(String(50), nullable=True)
    temperature_c = Column(Float, nullable=True)
    cpu_frequency_mhz = Column(Float, nullable=True)
    dropped_frames = Column(Integer, nullable=True)
    playback_errors = Column(Integer, nullable=True)
    recent_logs = Column(JSON, nullable=True)
    health_status = Column(String(50), nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    device = relationship("Device", back_populates="runtime_status")


class DeviceRuntimeConfig(Base):
    __tablename__ = "device_runtime_config"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    poll_interval_seconds = Column(Integer, nullable=False, default=15)
    sync_interval_seconds = Column(Integer, nullable=False, default=60)
    cache_max_bytes = Column(BigInteger, nullable=True)
    playback_mode = Column(String(50), nullable=False, default="sequential")
    fallback_behavior = Column(String(50), nullable=False, default="keep_last")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    device = relationship("Device", back_populates="runtime_config")


class DeviceCommand(Base):
    __tablename__ = "device_commands"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    command_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String(30), nullable=False, default="queued", index=True)
    result_status = Column(String(30), nullable=True)
    result_message = Column(Text, nullable=True)
    result_payload = Column(JSON, nullable=True)
    requested_by_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    device = relationship("Device", back_populates="commands")

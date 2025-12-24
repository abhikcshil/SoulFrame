from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    devices = relationship("Device", back_populates="owner")
    media = relationship("Media", back_populates="owner")
    playlists = relationship("Playlist", back_populates="owner")


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    device_token = Column(String(255), unique=True, nullable=False, index=True)
    pairing_code = Column(String(20), unique=True, nullable=True, index=True)
    pairing_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="devices")
    assignment = relationship("DeviceAssignment", back_populates="device", uselist=False)
    settings = relationship("DeviceSettings", back_populates="device", uselist=False)


class Media(Base):
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="media")
    playlist_items = relationship("PlaylistItem", back_populates="media")


class Playlist(Base):
    __tablename__ = "playlists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="playlists")
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan")
    assignments = relationship("DeviceAssignment", back_populates="playlist")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    
    playlist = relationship("Playlist", back_populates="items")
    media = relationship("Media", back_populates="playlist_items")


class DeviceAssignment(Base):
    __tablename__ = "device_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    device = relationship("Device", back_populates="assignment")
    playlist = relationship("Playlist", back_populates="assignments")


class DeviceSettings(Base):
    __tablename__ = "device_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    brightness = Column(Integer, nullable=False, default=50)
    orientation = Column(String(20), nullable=False, default="portrait")
    sleep_enabled = Column(Boolean, nullable=False, default=False)
    sleep_start = Column(Time, nullable=True)
    sleep_end = Column(Time, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    device = relationship("Device", back_populates="settings")
"""initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('owner_user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('device_token', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('pairing_code', sa.String(20), unique=True, nullable=True, index=True),
        sa.Column('pairing_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Media table
    op.create_table(
        'media',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('owner_user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Playlists table
    op.create_table(
        'playlists',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('owner_user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # PlaylistItems table
    op.create_table(
        'playlist_items',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('playlist_id', sa.Uuid(as_uuid=True), sa.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('media_id', sa.Uuid(as_uuid=True), sa.ForeignKey('media.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('position', sa.Integer, nullable=False),
    )
    op.create_index('ix_playlist_items_playlist_position', 'playlist_items', ['playlist_id', 'position'])

    # DeviceAssignments table
    op.create_table(
        'device_assignments',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('playlist_id', sa.Uuid(as_uuid=True), sa.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # DeviceSettings table
    op.create_table(
        'device_settings',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('brightness', sa.Integer, nullable=False, server_default='50'),
        sa.Column('orientation', sa.String(20), nullable=False, server_default='portrait'),
        sa.Column('sleep_enabled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('sleep_start', sa.Time, nullable=True),
        sa.Column('sleep_end', sa.Time, nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('device_settings')
    op.drop_table('device_assignments')
    op.drop_table('playlist_items')
    op.drop_table('playlists')
    op.drop_table('media')
    op.drop_table('devices')
    op.drop_table('users')

"""direct media assignment and runtime telemetry

Revision ID: 003
Revises: 002
Create Date: 2026-04-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    assignment_columns = {column['name'] for column in inspector.get_columns('device_assignments')}
    with op.batch_alter_table('device_assignments') as batch_op:
        batch_op.alter_column('playlist_id', existing_type=sa.Uuid(as_uuid=True), nullable=True)
        if 'media_id' not in assignment_columns:
            batch_op.add_column(sa.Column('media_id', sa.Uuid(as_uuid=True), nullable=True))
            batch_op.create_index('ix_device_assignments_media_id', ['media_id'])
            batch_op.create_foreign_key(
                'fk_device_assignments_media_id_media',
                'media',
                ['media_id'],
                ['id'],
                ondelete='CASCADE',
            )

    if 'device_runtime_status' not in tables:
        op.create_table(
            'device_runtime_status',
            sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
            sa.Column('app_version', sa.String(100), nullable=True),
            sa.Column('local_ip', sa.String(100), nullable=True),
            sa.Column('uptime_seconds', sa.BigInteger(), nullable=True),
            sa.Column('storage_free_bytes', sa.BigInteger(), nullable=True),
            sa.Column('cache_free_bytes', sa.BigInteger(), nullable=True),
            sa.Column('current_media_id', sa.Uuid(as_uuid=True), sa.ForeignKey('media.id', ondelete='SET NULL'), nullable=True),
            sa.Column('current_playlist_id', sa.Uuid(as_uuid=True), sa.ForeignKey('playlists.id', ondelete='SET NULL'), nullable=True),
            sa.Column('health_status', sa.String(50), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        runtime_columns = set()
    else:
        runtime_columns = {column['name'] for column in inspector.get_columns('device_runtime_status')}

    with op.batch_alter_table('device_runtime_status') as batch_op:
        if 'device_state' not in runtime_columns:
            batch_op.add_column(sa.Column('device_state', sa.String(50), nullable=True))
        if 'temperature_c' not in runtime_columns:
            batch_op.add_column(sa.Column('temperature_c', sa.Float(), nullable=True))
        if 'cpu_frequency_mhz' not in runtime_columns:
            batch_op.add_column(sa.Column('cpu_frequency_mhz', sa.Float(), nullable=True))
        if 'dropped_frames' not in runtime_columns:
            batch_op.add_column(sa.Column('dropped_frames', sa.Integer(), nullable=True))
        if 'playback_errors' not in runtime_columns:
            batch_op.add_column(sa.Column('playback_errors', sa.Integer(), nullable=True))
        if 'recent_logs' not in runtime_columns:
            batch_op.add_column(sa.Column('recent_logs', sa.JSON(), nullable=True))

    if 'device_runtime_config' not in tables:
        op.create_table(
            'device_runtime_config',
            sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
            sa.Column('poll_interval_seconds', sa.Integer(), nullable=False, server_default='15'),
            sa.Column('sync_interval_seconds', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('cache_max_bytes', sa.BigInteger(), nullable=True),
            sa.Column('playback_mode', sa.String(50), nullable=False, server_default='sequential'),
            sa.Column('fallback_behavior', sa.String(50), nullable=False, server_default='keep_last'),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if 'device_commands' not in tables:
        op.create_table(
            'device_commands',
            sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('command_type', sa.String(50), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(30), nullable=False, server_default='queued', index=True),
            sa.Column('result_status', sa.String(30), nullable=True),
            sa.Column('result_message', sa.Text(), nullable=True),
            sa.Column('result_payload', sa.JSON(), nullable=True),
            sa.Column('requested_by_user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    with op.batch_alter_table('device_runtime_status') as batch_op:
        batch_op.drop_column('recent_logs')
        batch_op.drop_column('playback_errors')
        batch_op.drop_column('dropped_frames')
        batch_op.drop_column('cpu_frequency_mhz')
        batch_op.drop_column('temperature_c')
        batch_op.drop_column('device_state')

    with op.batch_alter_table('device_assignments') as batch_op:
        batch_op.drop_constraint('fk_device_assignments_media_id_media', type_='foreignkey')
        batch_op.drop_index('ix_device_assignments_media_id')
        batch_op.drop_column('media_id')
        batch_op.alter_column('playlist_id', existing_type=sa.Uuid(as_uuid=True), nullable=False)

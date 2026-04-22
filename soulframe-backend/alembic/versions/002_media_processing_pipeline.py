"""add media processing pipeline fields

Revision ID: 002
Revises: 001
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('media') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(30), nullable=False, server_default='uploaded'))
        batch_op.add_column(sa.Column('source_storage_key', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('playback_storage_key', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('original_mime_type', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('playback_mime_type', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('original_size_bytes', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('playback_size_bytes', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('width', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('height', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('duration_seconds', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('normalized_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('processing_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('normalization_metadata', sa.JSON(), nullable=True))

    op.execute(
        """
        UPDATE media
        SET
            source_storage_key = filename,
            original_mime_type = mime_type,
            original_size_bytes = size_bytes
        WHERE source_storage_key IS NULL
        """
    )
    op.create_index('ix_media_status', 'media', ['status'])


def downgrade() -> None:
    op.drop_index('ix_media_status', table_name='media')
    with op.batch_alter_table('media') as batch_op:
        batch_op.drop_column('normalization_metadata')
        batch_op.drop_column('processing_error')
        batch_op.drop_column('normalized_at')
        batch_op.drop_column('duration_seconds')
        batch_op.drop_column('height')
        batch_op.drop_column('width')
        batch_op.drop_column('playback_size_bytes')
        batch_op.drop_column('original_size_bytes')
        batch_op.drop_column('playback_mime_type')
        batch_op.drop_column('original_mime_type')
        batch_op.drop_column('playback_storage_key')
        batch_op.drop_column('source_storage_key')
        batch_op.drop_column('status')

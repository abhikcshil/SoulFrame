"""add media thumbnail metadata

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media") as batch_op:
        batch_op.add_column(sa.Column("thumbnail_storage_key", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_generated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_error", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("media") as batch_op:
        batch_op.drop_column("thumbnail_error")
        batch_op.drop_column("thumbnail_generated_at")
        batch_op.drop_column("thumbnail_storage_key")

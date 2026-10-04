"""Add privacy-preserving face embeddings for duplicate-account checks."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "e5f300000001"
down_revision = "e4f200000001"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("face_embedding", JSONB, nullable=True))


def downgrade():
    op.drop_column("users", "face_embedding")

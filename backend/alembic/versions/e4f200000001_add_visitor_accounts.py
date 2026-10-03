"""Add self-service participant accounts."""

import sqlalchemy as sa

from alembic import op

revision = "e4f200000001"
down_revision = "d3f100000001"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email", sa.String(254)))
    op.add_column("users", sa.Column("password_hash", sa.String(256)))
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade():
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")

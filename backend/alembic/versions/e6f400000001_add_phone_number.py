"""Add phone_number to users

Revision ID: e6f400000001
Revises: e5f300000001
Create Date: 2026-10-04 08:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f400000001"
down_revision: Union[str, None] = "e5f300000001"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=32), nullable=True))
    op.create_index("uq_users_phone_number", "users", ["phone_number"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_phone_number", table_name="users")
    op.drop_column("users", "phone_number")

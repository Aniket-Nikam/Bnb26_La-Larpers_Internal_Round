"""Bridge P2 identities into the canonical model; old sessions require re-login."""

from alembic import op
import sqlalchemy as sa

revision = "d3f100000001"
down_revision = "c2f4a1230001"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("access_credentials", sa.Column("label", sa.String(120)))
    # Existing M1 databases have no P2 archive. Fresh and P2 databases do.
    if sa.inspect(op.get_bind()).has_table("users", schema="legacy_security"):
        op.execute("""INSERT INTO users (id, public_id, display_name, timezone, role, is_active)
          SELECT id, public_id, display_name, timezone, role, is_active FROM legacy_security.users""")
        op.execute("""INSERT INTO access_credentials (id,user_id,digest,issued_at,expires_at,revoked_at,label)
          SELECT id,user_id,credential_digest,COALESCE(issued_at,clock_timestamp()),expires_at,revoked_at,label
          FROM legacy_security.access_credentials""")
        # P2 sessions had no credential binding. Archive them rather than guessing
        # which credential's revocation should invalidate them. Users sign in again.
        # P2 grants had no Drop FK/domain; retain them in the archive for review.


def downgrade():
    op.drop_column("access_credentials", "label")
    op.drop_column("users", "is_active")

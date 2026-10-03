"""
Alembic migration for security tables — P1 area migration, P2 authored fields.
Creates: users, access_credentials, sessions, eligibility_grants
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0001_security_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('public_id', sa.String(64), nullable=False, unique=True),
        sa.Column('display_name', sa.String(120), nullable=False),
        sa.Column('timezone', sa.String(64), nullable=False, server_default='UTC'),
        sa.Column('role', sa.String(32), nullable=False, server_default='participant'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # access_credentials
    op.create_table(
        'access_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('credential_digest', sa.String(64), nullable=False, unique=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('label', sa.String(120), nullable=True),
    )
    op.create_index('ix_access_credentials_user_id', 'access_credentials', ['user_id'])

    # sessions
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_digest', sa.String(64), nullable=False, unique=True),
        sa.Column('csrf_secret', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_ip', sa.String(64), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_token_digest', 'sessions', ['token_digest'])

    # eligibility_grants
    op.create_table(
        'eligibility_grants',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('drop_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('granted_by_user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('drop_id', 'user_id', name='uq_eligibility_grants_drop_user'),
    )
    op.create_index('ix_eligibility_grants_drop_id', 'eligibility_grants', ['drop_id'])
    op.create_index('ix_eligibility_grants_user_id', 'eligibility_grants', ['user_id'])


def downgrade() -> None:
    op.drop_table('eligibility_grants')
    op.drop_table('sessions')
    op.drop_table('access_credentials')
    op.drop_table('users')

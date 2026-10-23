"""add users table and scan ownership

Revision ID: b1f84cad2d90
Revises: a0ab177a1bb2
Create Date: 2026-10-18 00:00:00.000000

Adds:
- users (authentication identity table)
- scans.owner_user_id (nullable FK -> users.id)

Legacy scans (owner_user_id IS NULL) keep ALL records/reports intact; access
is administrator-only per backend/auth.py policy. No data is modified.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1f84cad2d90'
down_revision: Union[str, Sequence[str], None] = 'a0ab177a1bb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='user'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.add_column('scans', sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_scans_owner_user_id'), 'scans', ['owner_user_id'])
    op.create_foreign_key(
        'fk_scans_owner_user_id_users',
        'scans', 'users',
        ['owner_user_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_scans_owner_user_id_users', 'scans', type_='foreignkey')
    op.drop_index(op.f('ix_scans_owner_user_id'), table_name='scans')
    op.drop_column('scans', 'owner_user_id')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')

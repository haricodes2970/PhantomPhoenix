"""add audit_events table

Revision ID: c3a91ffd8e42
Revises: b1f84cad2d90
Create Date: 2026-10-18 00:00:00.000000

Adds the persistent security-audit trail. No existing records modified.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3a91ffd8e42'
down_revision: Union[str, Sequence[str], None] = 'b1f84cad2d90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('outcome', sa.String(length=16), nullable=False),
        sa.Column('resource_type', sa.String(length=32), nullable=True),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('detail', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL', name='fk_audit_events_actor_user_id_users'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_created_at_desc', 'audit_events', [sa.text('created_at DESC')])
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'])
    op.create_index('ix_audit_events_actor_user_id', 'audit_events', ['actor_user_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_events_actor_user_id', table_name='audit_events')
    op.drop_index('ix_audit_events_event_type', table_name='audit_events')
    op.drop_index('ix_audit_events_created_at_desc', table_name='audit_events')
    op.drop_table('audit_events')

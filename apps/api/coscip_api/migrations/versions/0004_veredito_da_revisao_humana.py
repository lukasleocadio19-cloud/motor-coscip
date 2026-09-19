"""veredito humano na decisão de revisão (REV-01/02)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-19 20:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('review_decisions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('final_status', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('review_decisions', schema=None) as batch_op:
        batch_op.drop_column('final_status')

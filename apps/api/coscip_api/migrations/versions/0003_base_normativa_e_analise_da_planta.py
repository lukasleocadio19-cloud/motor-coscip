"""base normativa ingerida e análise automática da planta

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-19 16:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('normative_sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('text_sha256', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('artifact_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('meta', sa.JSON(), nullable=True))
        batch_op.create_index(batch_op.f('ix_normative_sources_text_sha256'), ['text_sha256'],
                              unique=True)
        batch_op.create_foreign_key('fk_normative_sources_artifact_id', 'file_objects',
                                    ['artifact_id'], ['id'])

    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('drawing_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('execution_id', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_analyses_drawing_id'), ['drawing_id'], unique=False)
        batch_op.create_foreign_key('fk_analyses_drawing_id', 'drawings', ['drawing_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.drop_constraint('fk_analyses_drawing_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_analyses_drawing_id'))
        batch_op.drop_column('execution_id')
        batch_op.drop_column('drawing_id')

    with op.batch_alter_table('normative_sources', schema=None) as batch_op:
        batch_op.drop_constraint('fk_normative_sources_artifact_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_normative_sources_text_sha256'))
        batch_op.drop_column('meta')
        batch_op.drop_column('artifact_id')
        batch_op.drop_column('text_sha256')
        batch_op.drop_column('title')

"""Add pgvector embedding support

Revision ID: f6b6cb8b80a8
Revises: ec410f0fb1b0
Create Date: 2026-10-04 13:12:55.217832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = 'f6b6cb8b80a8'
down_revision: Union[str, Sequence[str], None] = 'ec410f0fb1b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('research_document_chunks', sa.Column('embedding_model', sa.String(), nullable=True))
    op.add_column('research_document_chunks', sa.Column('embedding_dimension', sa.Integer(), nullable=True))
    op.execute('ALTER TABLE research_document_chunks DROP COLUMN IF EXISTS embedding')
    op.add_column('research_document_chunks', sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(), nullable=True))

def downgrade() -> None:
    op.execute('ALTER TABLE research_document_chunks DROP COLUMN IF EXISTS embedding')
    op.add_column('research_document_chunks', sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.drop_column('research_document_chunks', 'embedding_dimension')
    op.drop_column('research_document_chunks', 'embedding_model')

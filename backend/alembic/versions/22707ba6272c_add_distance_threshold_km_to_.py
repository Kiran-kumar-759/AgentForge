"""Add distance_threshold_km to ExposureAnalysis

Revision ID: 22707ba6272c
Revises: f6b6cb8b80a8
Create Date: 2026-10-05 17:48:29.592823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22707ba6272c'
down_revision: Union[str, Sequence[str], None] = 'f6b6cb8b80a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('exposure_analyses', sa.Column('distance_threshold_km', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('exposure_analyses', 'distance_threshold_km')

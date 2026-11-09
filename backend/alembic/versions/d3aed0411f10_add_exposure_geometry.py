"""add_exposure_geometry

Revision ID: d3aed0411f10
Revises: 4fe6dcb5ee15
Create Date: 2026-10-04 11:23:01.116130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'd3aed0411f10'
down_revision: Union[str, Sequence[str], None] = '4fe6dcb5ee15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add geom to infrastructure_data and population_data
    op.add_column('infrastructure_data', sa.Column('geom', geoalchemy2.types.Geometry(srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))
    
    op.add_column('population_data', sa.Column('geom', geoalchemy2.types.Geometry(srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))

def downgrade() -> None:
    op.drop_column('population_data', 'geom')
    op.drop_column('infrastructure_data', 'geom')

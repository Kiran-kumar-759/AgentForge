"""add_spatial_geometry

Revision ID: 4fe6dcb5ee15
Revises: efa9c49070f3
Create Date: 2026-10-04 11:07:14.071182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fe6dcb5ee15'
down_revision: Union[str, Sequence[str], None] = 'efa9c49070f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add geometry columns
    op.execute("ALTER TABLE marine_observations ADD COLUMN geom geometry(Point, 4326)")
    op.execute("ALTER TABLE cyclone_track_points ADD COLUMN geom geometry(Point, 4326)")
    op.execute("ALTER TABLE vessel_positions ADD COLUMN geom geometry(Point, 4326)")

    # 2. Populate geometries
    op.execute("UPDATE marine_observations SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE longitude IS NOT NULL AND latitude IS NOT NULL")
    op.execute("UPDATE cyclone_track_points SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE longitude IS NOT NULL AND latitude IS NOT NULL")
    op.execute("UPDATE vessel_positions SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE longitude IS NOT NULL AND latitude IS NOT NULL")

    # 3. Create GiST indexes
    op.create_index('ix_marine_observations_geom', 'marine_observations', ['geom'], unique=False, postgresql_using='gist')
    op.create_index('ix_cyclone_track_points_geom', 'cyclone_track_points', ['geom'], unique=False, postgresql_using='gist')
    op.create_index('ix_vessel_positions_geom', 'vessel_positions', ['geom'], unique=False, postgresql_using='gist')

def downgrade() -> None:
    op.drop_index('ix_vessel_positions_geom', table_name='vessel_positions', postgresql_using='gist')
    op.drop_index('ix_cyclone_track_points_geom', table_name='cyclone_track_points', postgresql_using='gist')
    op.drop_index('ix_marine_observations_geom', table_name='marine_observations', postgresql_using='gist')
    
    op.drop_column('vessel_positions', 'geom')
    op.drop_column('cyclone_track_points', 'geom')
    op.drop_column('marine_observations', 'geom')

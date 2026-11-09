import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class MarineObservation(Base):
    __tablename__ = "marine_observations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    
    variable_name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    
    observation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    quality_status: Mapped[str] = mapped_column(String, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    
    spatial_resolution: Mapped[str] = mapped_column(String, nullable=True)
    temporal_resolution: Mapped[str] = mapped_column(String, nullable=True)
    
    source_record_id: Mapped[str] = mapped_column(String, nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index('ix_marine_observations_dataset_time', 'dataset_id', 'observation_timestamp'),
        Index('ix_marine_observations_source_time', 'data_source_id', 'observation_timestamp'),
        Index('ix_marine_observations_variable_time', 'variable_name', 'observation_timestamp'),
        Index('ix_marine_observations_location', 'latitude', 'longitude'),
        Index('ix_marine_observations_time', 'observation_timestamp'),
        Index(
            'ix_marine_obs_unique',
            'data_source_id', 'dataset_id', 'variable_name', 'latitude', 'longitude', 'observation_timestamp',
            unique=True
        ),
    )

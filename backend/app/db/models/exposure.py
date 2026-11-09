import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, Float, ForeignKey, Integer, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class PopulationData(Base):
    __tablename__ = "population_data"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    geom = mapped_column(Geometry('GEOMETRY', srid=4326), nullable=True)
    population_value: Mapped[float] = mapped_column(Float, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution: Mapped[str] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset: Mapped[str] = mapped_column(String(100), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    __table_args__ = (
        UniqueConstraint('latitude', 'longitude', 'year', 'source', name='uix_population_data'),
    )

class InfrastructureData(Base):
    __tablename__ = "infrastructure_data"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    osm_type: Mapped[str] = mapped_column(String(20))
    osm_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    criticality: Mapped[str] = mapped_column(String(30), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    geom = mapped_column(Geometry('GEOMETRY', srid=4326), nullable=True)
    tags: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    __table_args__ = (
        UniqueConstraint('osm_type', 'osm_id', name='uix_infrastructure_osm_id'),
    )

class ExposureAnalysis(Base):
    __tablename__ = "exposure_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_type: Mapped[str] = mapped_column(String(50))
    hazard_source_type: Mapped[str] = mapped_column(String(50))
    hazard_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True, index=True)
    hazard_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Store geometry as GeoJSON dict, will use Shapely for processing since PostGIS is not available
    geometry: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    
    analysis_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    distance_threshold_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    population_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    population_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    population_resolution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    population_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    settlement_count: Mapped[int] = mapped_column(Integer, default=0)
    infrastructure_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_infrastructure_count: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(30), index=True) # pending, running, completed, partial, unavailable, failed
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False)
    source_retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    settlements: Mapped[List["ExposedSettlement"]] = relationship("ExposedSettlement", back_populates="analysis", cascade="all, delete-orphan")
    infrastructure: Mapped[List["ExposedInfrastructure"]] = relationship("ExposedInfrastructure", back_populates="analysis", cascade="all, delete-orphan")


class ExposedSettlement(Base):
    __tablename__ = "exposed_settlements"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exposure_analyses.id", ondelete="CASCADE"), index=True)
    
    osm_type: Mapped[str] = mapped_column(String(20))
    osm_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    place_type: Mapped[str] = mapped_column(String(50))
    
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    
    tags: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(100))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    analysis: Mapped["ExposureAnalysis"] = relationship("ExposureAnalysis", back_populates="settlements")
    
    __table_args__ = (
        UniqueConstraint('analysis_id', 'osm_type', 'osm_id', name='uix_analysis_osm_settlement'),
    )


class ExposedInfrastructure(Base):
    __tablename__ = "exposed_infrastructure"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exposure_analyses.id", ondelete="CASCADE"), index=True)
    
    osm_type: Mapped[str] = mapped_column(String(20))
    osm_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    infrastructure_type: Mapped[str] = mapped_column(String(80), index=True)
    criticality: Mapped[str] = mapped_column(String(30))
    
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    
    tags: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(100))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    analysis: Mapped["ExposureAnalysis"] = relationship("ExposureAnalysis", back_populates="infrastructure")
    
    __table_args__ = (
        UniqueConstraint('analysis_id', 'osm_type', 'osm_id', name='uix_analysis_osm_infrastructure'),
    )

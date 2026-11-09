from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import String, Float, DateTime, Boolean, JSON, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from app.db.base import Base
from geoalchemy2 import Geometry

class CycloneStatus(str, Enum):
    TROPICAL_DISTURBANCE = "TROPICAL_DISTURBANCE"
    DEPRESSION = "DEPRESSION"
    TROPICAL_STORM = "TROPICAL_STORM"
    CYCLONIC_STORM = "CYCLONIC_STORM"
    SEVERE_CYCLONIC_STORM = "SEVERE_CYCLONIC_STORM"
    VERY_SEVERE_CYCLONIC_STORM = "VERY_SEVERE_CYCLONIC_STORM"
    EXTREMELY_SEVERE_CYCLONIC_STORM = "EXTREMELY_SEVERE_CYCLONIC_STORM"
    SUPER_CYCLONIC_STORM = "SUPER_CYCLONIC_STORM"
    POST_TROPICAL = "POST_TROPICAL"
    UNKNOWN = "UNKNOWN"

class PointType(str, Enum):
    OBSERVED = "OBSERVED"
    FORECAST = "FORECAST"

class CycloneEvent(Base):
    __tablename__ = "cyclone_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String)
    basin: Mapped[str] = mapped_column(String, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, nullable=True)
    classification: Mapped[CycloneStatus] = mapped_column(SQLEnum(CycloneStatus), index=True)
    formation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    dissipation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    current_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    current_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    max_wind_speed: Mapped[float] = mapped_column(Float, nullable=True)
    max_wind_unit: Mapped[str] = mapped_column(String, nullable=True)
    minimum_pressure: Mapped[float] = mapped_column(Float, nullable=True)
    movement_direction: Mapped[float] = mapped_column(Float, nullable=True)
    movement_speed: Mapped[float] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    source: Mapped["DataSource"] = relationship("DataSource")
    track_points: Mapped[List["CycloneTrackPoint"]] = relationship("CycloneTrackPoint", back_populates="event", cascade="all, delete-orphan")

class CycloneTrackPoint(Base):
    __tablename__ = "cyclone_track_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cyclone_event_id: Mapped[int] = mapped_column(ForeignKey("cyclone_events.id", ondelete="CASCADE"), index=True)
    point_type: Mapped[PointType] = mapped_column(SQLEnum(PointType), index=True)
    forecast_hour: Mapped[int] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geom = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    max_wind_speed: Mapped[float] = mapped_column(Float, nullable=True)
    wind_unit: Mapped[str] = mapped_column(String, nullable=True)
    minimum_pressure: Mapped[float] = mapped_column(Float, nullable=True)
    classification: Mapped[str] = mapped_column(String, nullable=True)
    source_record_id: Mapped[str] = mapped_column(String, nullable=True)
    is_observed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    event: Mapped["CycloneEvent"] = relationship("CycloneEvent", back_populates="track_points")

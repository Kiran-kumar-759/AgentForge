"""Phase 8 — Vessel Intelligence models.

Design:
    data_sources ─┬─< vessels ─< vessel_positions
                  └─────────────< vessel_positions (source_id)
    data_provenance ─< vessel_positions (provenance_id, batch-level provenance)

* A vessel's identity is ``(source_id, external_vessel_id)``. Vessels are never merged
  across providers or by name. MMSI / IMO are stored when the provider supplies them.
* A track is NOT a separate table: it is the ordered set of ``vessel_positions`` for a vessel.
* All descriptive fields are nullable — only values actually supplied by the provider are stored.
* FK strategy: deleting a data source is RESTRICTED while vessel data references it, so
  provider clean-up can never silently wipe observational records. Deleting a vessel
  cascades to its own positions only. Deleting a provenance batch sets the link to NULL.
"""
import uuid
from datetime import datetime, timezone

# pyrefly: ignore [missing-import]
from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean, Integer, BigInteger, Index, UniqueConstraint
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    external_vessel_id: Mapped[str] = mapped_column(String, nullable=False)

    mmsi: Mapped[str | None] = mapped_column(String(9), nullable=True)
    imo: Mapped[str | None] = mapped_column(String(7), nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    call_sign: Mapped[str | None] = mapped_column(String, nullable=True)
    vessel_type: Mapped[str | None] = mapped_column(String, nullable=True)
    ais_ship_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flag: Mapped[str | None] = mapped_column(String, nullable=True)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    width_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    draught_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination: Mapped[str | None] = mapped_column(String, nullable=True)

    metadata_source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    source = relationship("DataSource")
    positions = relationship("VesselPosition", back_populates="vessel", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("source_id", "external_vessel_id", name="uq_vessels_source_external_id"),
        Index("ix_vessels_external_vessel_id", "external_vessel_id"),
        Index("ix_vessels_mmsi", "mmsi"),
        Index("ix_vessels_imo", "imo"),
        Index("ix_vessels_source_id", "source_id"),
        Index("ix_vessels_vessel_type", "vessel_type"),
    )


class VesselPosition(Base):
    __tablename__ = "vessel_positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vessel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    provenance_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("data_provenance.id", ondelete="SET NULL"), nullable=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    speed_knots: Mapped[float | None] = mapped_column(Float, nullable=True)
    course_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    navigation_status: Mapped[str | None] = mapped_column(String, nullable=True)

    source_record_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    vessel = relationship("Vessel", back_populates="positions")

    __table_args__ = (
        # Deterministic de-duplication: one report per vessel, per source, per observation instant.
        UniqueConstraint("source_id", "vessel_id", "timestamp", name="uq_vessel_positions_source_vessel_time"),
        # Track queries: WHERE vessel_id = ? AND timestamp BETWEEN ? ORDER BY timestamp
        Index("ix_vessel_positions_vessel_time", "vessel_id", "timestamp"),
        # Spatial/time window queries (bbox strategy without PostGIS)
        Index("ix_vessel_positions_time_lat_lon", "timestamp", "latitude", "longitude"),
        Index("ix_vessel_positions_lat_lon", "latitude", "longitude"),
        Index("ix_vessel_positions_source_time", "source_id", "timestamp"),
        Index("ix_vessel_positions_timestamp", "timestamp"),
        Index("ix_vessel_positions_provenance_id", "provenance_id"),
    )

import uuid
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column
# pyrefly: ignore [missing-import]
from sqlalchemy import String, DateTime, ForeignKey, Float, Index
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class DataProvenance(Base):
    __tablename__ = "data_provenance"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    source_reference: Mapped[str] = mapped_column(String, nullable=True)
    variable_name: Mapped[str] = mapped_column(String, index=True)
    latitude: Mapped[float] = mapped_column(Float, index=True, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, index=True, nullable=True)
    observation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    value: Mapped[str] = mapped_column(String)  # Can be stringified JSON or float string
    unit: Mapped[str] = mapped_column(String, nullable=True)
    quality_flag: Mapped[str] = mapped_column(String, nullable=True)
    method: Mapped[str] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    dataset_name: Mapped[str] = mapped_column(String)
    dataset_identifier: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    data_type: Mapped[str] = mapped_column(String, nullable=True)
    format: Mapped[str] = mapped_column(String, nullable=True)
    spatial_resolution: Mapped[str] = mapped_column(String, nullable=True)
    temporal_resolution: Mapped[str] = mapped_column(String, nullable=True)
    access_method: Mapped[str] = mapped_column(String, nullable=True)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    data_source = relationship("DataSource", back_populates="datasets")

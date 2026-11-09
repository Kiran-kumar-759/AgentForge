import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ReportPackage(Base):
    __tablename__ = "report_packages"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_plans.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    package_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., INCIDENT_REPORT, RESEARCH_PACKAGE
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # PENDING, GENERATING, COMPLETED, FAILED
    version: Mapped[str] = mapped_column(String(20), default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    
    # relationships
    artifacts = relationship("ReportArtifact", back_populates="package", cascade="all, delete-orphan")


class ReportArtifact(Base):
    __tablename__ = "report_artifacts"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_packages.id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PDF, HTML, JSON
    storage_reference: Mapped[str] = mapped_column(String(500), nullable=False) # e.g., local path or object key
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    package = relationship("ReportPackage", back_populates="artifacts")

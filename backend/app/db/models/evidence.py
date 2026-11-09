import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Float, Text, Integer, ARRAY, Table, Column
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

# Association table for Claim <-> Evidence many-to-many relationship
claim_evidence_association = Table(
    'claim_evidence',
    Base.metadata,
    Column('claim_id', UUID(as_uuid=True), ForeignKey('execution_claims.id', ondelete='CASCADE'), primary_key=True),
    Column('evidence_id', UUID(as_uuid=True), ForeignKey('execution_evidence.id', ondelete='CASCADE'), primary_key=True)
)

class Claim(Base):
    __tablename__ = "execution_claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_plans.id", ondelete="CASCADE"), index=True)
    execution_node_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    claim_text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(50)) # OBSERVATION, MEASUREMENT, SPATIAL_ANALYSIS, EXPOSURE, CYCLONE, WEATHER, OCEAN, VESSEL, RESEARCH, INTERPRETATION
    status: Mapped[str] = mapped_column(String(50), default="pending")
    verification_status: Mapped[str] = mapped_column(String(50), default="UNVERIFIED") # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, UNVERIFIABLE, CONFLICTING
    verification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    evidence = relationship("Evidence", secondary=claim_evidence_association, back_populates="claims")


class Evidence(Base):
    __tablename__ = "execution_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_plans.id", ondelete="CASCADE"), index=True)
    execution_node_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    evidence_type: Mapped[str] = mapped_column(String(50)) # DATABASE_RECORD, SPATIAL_QUERY, AGGREGATION, SCIENTIFIC_DATASET, RESEARCH_DOCUMENT, RESEARCH_CHUNK, MODEL_OUTPUT, EXTERNAL_SOURCE, SYSTEM_LIMITATION
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    spatial_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    query_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    computation: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_reference: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="valid")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    claims = relationship("Claim", secondary=claim_evidence_association, back_populates="evidence")

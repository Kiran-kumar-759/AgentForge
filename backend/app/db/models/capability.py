import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Boolean, Integer, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class CapabilityCategory(str, enum.Enum):
    PLANNING = "PLANNING"
    WEATHER = "WEATHER"
    OCEAN = "OCEAN"
    SATELLITE = "SATELLITE"
    GIS = "GIS"
    VESSEL = "VESSEL"
    RESEARCH = "RESEARCH"
    RISK = "RISK"
    IMPACT = "IMPACT"
    VERIFICATION = "VERIFICATION"
    REPORTING = "REPORTING"

class CapabilityStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    UNAVAILABLE = "UNAVAILABLE"

class Capability(Base):
    __tablename__ = "capabilities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[CapabilityCategory] = mapped_column(SQLEnum(CapabilityCategory, name="capability_category"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    status: Mapped[CapabilityStatus] = mapped_column(SQLEnum(CapabilityStatus, name="capability_status"), default=CapabilityStatus.NOT_IMPLEMENTED, index=True)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    required_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    required_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    agent_mappings = relationship("AgentCapability", back_populates="capability", cascade="all, delete-orphan")
    workspace_mappings = relationship("WorkspaceCapability", back_populates="capability", cascade="all, delete-orphan")

class AgentCapability(Base):
    __tablename__ = "agent_capabilities"

    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    capability_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capabilities.id", ondelete="CASCADE"), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    agent = relationship("Agent", back_populates="capabilities")
    capability = relationship("Capability", back_populates="agent_mappings")

class WorkspaceCapability(Base):
    __tablename__ = "workspace_capabilities"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    capability_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capabilities.id", ondelete="CASCADE"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    capability = relationship("Capability", back_populates="workspace_mappings")

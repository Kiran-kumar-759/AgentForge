import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class AgentStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    DISABLED = "DISABLED"
    EXPERIMENTAL = "EXPERIMENTAL"

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    status: Mapped[AgentStatus] = mapped_column(SQLEnum(AgentStatus, name="agent_status"), default=AgentStatus.REGISTERED, index=True)
    agent_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    configuration: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    capabilities = relationship("AgentCapability", back_populates="agent", cascade="all, delete-orphan")

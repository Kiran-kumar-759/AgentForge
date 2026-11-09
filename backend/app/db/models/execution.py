import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_query: Mapped[str] = mapped_column(Text)
    workspace_code: Mapped[str] = mapped_column(String(50))
    intent_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), index=True) # pending, running, completed, failed
    plan_version: Mapped[int] = mapped_column(Integer, default=1)
    replan_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    nodes = relationship("ExecutionNode", back_populates="plan", cascade="all, delete-orphan")
    edges = relationship("ExecutionEdge", back_populates="plan", cascade="all, delete-orphan")


class ExecutionNode(Base):
    __tablename__ = "execution_nodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_plans.id", ondelete="CASCADE"), index=True)
    
    node_id: Mapped[str] = mapped_column(String(100))
    parent_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    agent_code: Mapped[str] = mapped_column(String(100))
    capability_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    node_type: Mapped[str] = mapped_column(String(50)) # planner, agent, capability, synthesis, response
    status: Mapped[str] = mapped_column(String(30)) # pending, running, completed, failed, skipped, unavailable
    
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    plan = relationship("ExecutionPlan", back_populates="nodes")


class ExecutionEdge(Base):
    __tablename__ = "execution_edges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_plans.id", ondelete="CASCADE"), index=True)
    
    source_node_id: Mapped[str] = mapped_column(String(100))
    target_node_id: Mapped[str] = mapped_column(String(100))
    edge_type: Mapped[str] = mapped_column(String(50)) # dependency, data_flow

    plan = relationship("ExecutionPlan", back_populates="edges")

class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_plans.id", ondelete="CASCADE"), index=True)
    execution_node_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capability_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sequence_number: Mapped[int] = mapped_column(Integer, default=0)

    plan = relationship("ExecutionPlan")
    node = relationship("ExecutionNode")

import uuid
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column
# pyrefly: ignore [missing-import]
from sqlalchemy import String, Boolean, DateTime, Integer
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class LLMRequest(Base):
    __tablename__ = "llm_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    request_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_from_provider: Mapped[str] = mapped_column(String, nullable=True)
    error_type: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True)

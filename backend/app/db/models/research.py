import uuid
import datetime
from typing import Dict, Any, List
from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base

class ResearchRequest(Base):
    __tablename__ = "research_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    workspace_id = Column(String, nullable=False)
    geographic_scope = Column(JSONB, nullable=True) # geojson bbox/polygon
    temporal_scope = Column(JSONB, nullable=True) # start/end
    mode = Column(String, default="quick")
    status = Column(String, default="pending") # pending, planning, researching, synthesizing, completed, failed
    
    findings = Column(JSONB, nullable=True)
    limitations = Column(JSONB, nullable=True)
    executive_summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class ResearchPlan(Base):
    __tablename__ = "research_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("research_requests.id", ondelete="CASCADE"), nullable=False)
    
    objectives = Column(ARRAY(String), nullable=True)
    structured_queries = Column(JSONB, nullable=True)
    document_queries = Column(JSONB, nullable=True)
    verification_requirements = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    
    request = relationship("ResearchRequest", backref="plan")

class ResearchDocument(Base):
    __tablename__ = "research_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    document_type = Column(String, nullable=False) # pdf, txt, etc.
    author = Column(String, nullable=True)
    publication_date = Column(DateTime(timezone=True), nullable=True)
    geographic_scope = Column(JSONB, nullable=True)
    topics = Column(ARRAY(String), nullable=True)
    file_hash = Column(String, nullable=False, unique=True)
    
    ingested_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

class ResearchDocumentChunk(Base):
    __tablename__ = "research_document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("research_documents.id", ondelete="CASCADE"), nullable=False)
    
    text = Column(Text, nullable=False)
    page_section = Column(String, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    
    # pgvector embedding column
    embedding = Column(Vector, nullable=True)
    embedding_model = Column(String, nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    
    # Lexical fallback column for full text search
    search_vector = Column(TSVECTOR, nullable=True)
    
    document = relationship("ResearchDocument", backref="chunks")

class ResearchEvidence(Base):
    __tablename__ = "research_evidence"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("research_requests.id", ondelete="CASCADE"), nullable=False)
    
    evidence_type = Column(String, nullable=False) # "structured" or "document"
    
    # Structured specific
    dataset_id = Column(String, nullable=True)
    source_id = Column(String, nullable=True)
    variable = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    geometry = Column(JSONB, nullable=True)
    observation_time = Column(DateTime(timezone=True), nullable=True)
    quality = Column(String, nullable=True)
    provenance_id = Column(String, nullable=True)
    
    # Document specific
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("research_document_chunks.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("research_documents.id", ondelete="SET NULL"), nullable=True)
    text_snippet = Column(Text, nullable=True)
    
    status = Column(String, nullable=False) # "valid", "partial", "unavailable"
    query_context = Column(String, nullable=True)
    retrieval_time = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    
    retrieval_method = Column(String, nullable=True)
    retrieval_score = Column(Float, nullable=True)
    
    request = relationship("ResearchRequest", backref="evidence")

class ResearchClaim(Base):
    __tablename__ = "research_claims"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("research_requests.id", ondelete="CASCADE"), nullable=False)
    
    text = Column(Text, nullable=False)
    evidence_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    confidence = Column(String, nullable=True)
    verification_status = Column(String, nullable=True) # "verified", "unverified", "unsupported"
    
    request = relationship("ResearchRequest", backref="claims")

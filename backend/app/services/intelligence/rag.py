import hashlib
import json
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel
import numpy as np

class Document(BaseModel):
    id: Optional[str] = None
    title: str
    text: str
    metadata: Dict[str, Any] = {}

class Chunk(BaseModel):
    id: Optional[str] = None
    document_id: str
    text: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None

class DocumentLoader:
    def load(self, file_path: str, mime_type: str, metadata: Dict[str, Any] = None) -> Document:
        raise NotImplementedError

class DocumentChunker:
    def chunk(self, document: Document, chunk_size: int = 1000, overlap: int = 200) -> List[Chunk]:
        """Simple text chunker based on characters."""
        text = document.text
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append(Chunk(
                document_id=document.id or "",
                text=chunk_text,
                metadata=document.metadata.copy()
            ))
            start += chunk_size - overlap
        return chunks

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import httpx
import logging
from app.db.models.research import ResearchDocumentChunk, ResearchDocument
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingProvider:
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        self.base_url = settings.EMBEDDING_BASE_URL.rstrip('/')
        self.model = settings.EMBEDDING_MODEL

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": texts
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                
                if not embeddings:
                    raise ValueError("Empty embedding response from Ollama")
                    
                # Validate dimension
                expected_dim = settings.EMBEDDING_DIMENSIONS
                for i, emb in enumerate(embeddings):
                    if len(emb) != expected_dim:
                        raise ValueError(f"Dimension mismatch in chunk {i}: expected {expected_dim}, got {len(emb)}")
                        
                return embeddings
            except httpx.HTTPError as e:
                logger.error(f"Ollama HTTP error: {e}")
                raise ValueError(f"Ollama HTTP error: {e}")
            except Exception as e:
                logger.error(f"Ollama embedding failed: {e}")
                raise ValueError(f"Ollama embedding failed: {e}")

class DocumentRetriever:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = settings.EMBEDDING_PROVIDER
        if self.provider == "ollama":
            self.embedding_service = OllamaEmbeddingProvider()
        else:
            self.embedding_service = None
        
    async def retrieve(self, query: str, top_k: int = 5) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Returns a tuple of (evidence_list, metadata)."""
        if self.provider == "ollama" and self.embedding_service:
            try:
                # 1. Try vector retrieval
                return await self._retrieve_vector(query, top_k)
            except Exception as e:
                logger.error(f"Vector retrieval failed, falling back to lexical: {e}")
                
        # 2. Lexical Fallback
        return await self._retrieve_lexical(query, top_k)

        
    async def _retrieve_vector(self, query: str, top_k: int) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        embeddings = await self.embedding_service.get_embeddings([query])
        if not embeddings or not embeddings[0]:
            raise ValueError("Failed to get embedding for query")
            
        q_vec = embeddings[0]
        
        # pgvector cosine distance operator is <=>
        # similarity = 1 - distance
        sql = text('''
            SELECT c.id, c.document_id, c.text, c.page_section, d.title, d.source, d.publication_date, d.document_type,
                   (1 - (c.embedding <=> CAST(:q_vec AS vector))) as similarity
            FROM research_document_chunks c
            JOIN research_documents d ON c.document_id = d.id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:q_vec AS vector)
            LIMIT :limit
        ''')
        
        count_sql = text("SELECT count(DISTINCT document_id) as docs, count(id) as chunks FROM research_document_chunks WHERE embedding IS NOT NULL")
        count_res = await self.db.execute(count_sql)
        counts = count_res.fetchone()
        
        # we format the array string for vector cast: '[0.1, 0.2, ...]'
        vec_str = str(q_vec)
        result = await self.db.execute(sql, {"q_vec": vec_str, "limit": top_k})
        rows = result.fetchall()
        
        # if no rows matched (maybe all embeddings are null), fallback
        if not rows:
            return await self._retrieve_lexical(query, top_k)
            
        evidence_list = []
        for row in rows:
            evidence_list.append({
                "chunk_id": row.id,
                "document_id": row.document_id,
                "text_snippet": row.text,
                "retrieval_method": "vector",
                "retrieval_score": float(row.similarity),
                "source": row.source,
                "title": row.title,
                "document_type": row.document_type,
                "publication_date": row.publication_date,
                "page_section": row.page_section
            })
            
        meta = {
            "retrieval_method": "vector",
            "documents_considered": counts.docs if counts else 0,
            "chunks_considered": counts.chunks if counts else 0,
            "chunks_returned": len(evidence_list),
            "embedding_provider": "ollama",
            "embedding_model": self.embedding_service.model
        }
            
        return evidence_list, meta
        
    async def _retrieve_lexical(self, query: str, top_k: int) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        sql = text('''
            SELECT c.id, c.document_id, c.text, c.page_section, d.title, d.source, d.publication_date, d.document_type,
                   ts_rank(to_tsvector('english', c.text), plainto_tsquery('english', :query)) as rank
            FROM research_document_chunks c
            JOIN research_documents d ON c.document_id = d.id
            WHERE to_tsvector('english', c.text) @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        ''')
        
        count_sql = text("SELECT count(DISTINCT document_id) as docs, count(id) as chunks FROM research_document_chunks")
        count_res = await self.db.execute(count_sql)
        counts = count_res.fetchone()
        
        result = await self.db.execute(sql, {"query": query, "limit": top_k})
        rows = result.fetchall()
        
        evidence_list = []
        for row in rows:
            evidence_list.append({
                "chunk_id": row.id,
                "document_id": row.document_id,
                "text_snippet": row.text,
                "retrieval_method": "lexical_fallback",
                "retrieval_score": float(row.rank),
                "source": row.source,
                "title": row.title,
                "document_type": row.document_type,
                "publication_date": row.publication_date,
                "page_section": row.page_section
            })
            
        meta = {
            "retrieval_method": "lexical_fallback",
            "documents_considered": counts.docs if counts else 0,
            "chunks_considered": counts.chunks if counts else 0,
            "chunks_returned": len(evidence_list),
            "embedding_provider": None,
            "embedding_model": None
        }
            
        return evidence_list, meta

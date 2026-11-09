import pytest
import uuid
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.models.research import ResearchRequest, ResearchEvidence, ResearchClaim, ResearchDocument, ResearchDocumentChunk
from app.services.intelligence.research_engine import ResearchEngine
from app.db.session import AsyncSessionLocal

pytestmark = pytest.mark.asyncio

async def create_sample_docs(db: AsyncSession):
    doc1 = ResearchDocument(
        id=uuid.uuid4(),
        title="Gujarat Coastal Vulnerability",
        source="Test Source",
        document_type="pdf",
        file_hash=str(uuid.uuid4())
    )
    doc2 = ResearchDocument(
        id=uuid.uuid4(),
        title="Baltic Sea Ice Analysis",
        source="Test Source 2",
        document_type="pdf",
        file_hash=str(uuid.uuid4())
    )
    db.add_all([doc1, doc2])
    await db.flush()

    chunk1 = ResearchDocumentChunk(
        document_id=doc1.id,
        text="Coastal warming in Gujarat has accelerated over the past decade, posing significant risks to port infrastructure due to increased storm surges.",
        page_section="Page 1"
    )
    chunk2 = ResearchDocumentChunk(
        document_id=doc2.id,
        text="The Baltic Sea experiences ice coverage during winter, affecting vessel routing and maritime operations significantly.",
        page_section="Page 1"
    )
    
    db.add_all([chunk1, chunk2])
    await db.flush()
    await db.commit()

async def embed_and_save_chunks(db: AsyncSession, chunks: list):
    from app.services.intelligence.rag import OllamaEmbeddingProvider
    provider = OllamaEmbeddingProvider()
    
    for chunk in chunks:
        embeddings = await provider.get_embeddings([chunk.text])
        if embeddings and embeddings[0]:
            chunk.embedding = embeddings[0]
            chunk.embedding_model = provider.model
            chunk.embedding_dimension = len(embeddings[0])
            
    await db.commit()

async def test_ollama_pgvector_retrieval():
    async with AsyncSessionLocal() as db:
        from app.db.models.research import ResearchDocumentChunk
        
        # Insert test docs
        docA = ResearchDocument(
            id=uuid.uuid4(),
            title="Gujarat Coast Temp",
            source="A",
            document_type="txt",
            file_hash=str(uuid.uuid4())
        )
        docB = ResearchDocument(
            id=uuid.uuid4(),
            title="Fisheries warming",
            source="B",
            document_type="txt",
            file_hash=str(uuid.uuid4())
        )
        docC = ResearchDocument(
            id=uuid.uuid4(),
            title="Aircraft Systems",
            source="C",
            document_type="txt",
            file_hash=str(uuid.uuid4())
        )
        db.add_all([docA, docB, docC])
        await db.flush()
        
        cA = ResearchDocumentChunk(
            document_id=docA.id,
            text="Sea surface temperatures along the Gujarat coast have increased over the observed period, affecting marine ecosystems and coastal livelihoods."
        )
        cB = ResearchDocumentChunk(
            document_id=docB.id,
            text="Coastal warming can alter fisheries distribution and marine ecosystem productivity."
        )
        cC = ResearchDocumentChunk(
            document_id=docC.id,
            text="Aircraft navigation systems require regular maintenance."
        )
        db.add_all([cA, cB, cC])
        await db.flush()
        
        from unittest.mock import patch
        
        # mock Ollama to return a deterministic vector
        async def mock_get_embeddings(self, texts):
            # 768 dimensions
            vec = [0.0] * 768
            # Make docA and docB similar, docC different
            if "Gujarat" in texts[0] or "warming" in texts[0]:
                vec[0] = 0.9
            else:
                vec[0] = 0.1
            return [vec]
            
        with patch("app.services.intelligence.rag.OllamaEmbeddingProvider.get_embeddings", new=mock_get_embeddings):
            await embed_and_save_chunks(db, [cA, cB, cC])
            
            from app.services.intelligence.rag import DocumentRetriever
            retriever = DocumentRetriever(db)
            
            query = "What evidence exists about warming affecting Gujarat coastal fisheries?"
            
            results, meta = await retriever.retrieve(query, top_k=2)
            # Since mock is active, it should use pgvector and return 2 results
            assert len(results) == 2
            texts = [r["text_snippet"] for r in results]
            
            assert results[0]["retrieval_method"] == "vector"
            
        await db.rollback()
        
        # we can't definitively assert "vector" unless we know Ollama is running, but let's assert it returned something useful.
        
        await db.rollback()

async def test_lexical_fallback_retrieval():
    async with AsyncSessionLocal() as db:
        await create_sample_docs(db)
        from app.services.intelligence.rag import DocumentRetriever
        retriever = DocumentRetriever(db)
        
        # Force fallback
        retriever.provider = "none"
        results, meta = await retriever.retrieve("Gujarat warming", top_k=2)
        assert len(results) >= 1
        assert "Gujarat" in results[0]["text_snippet"]
        assert results[0]["retrieval_method"] == "lexical_fallback"
        assert results[0]["retrieval_score"] > 0
        await db.rollback()

async def test_research_engine_execution():
    async with AsyncSessionLocal() as db:
        await create_sample_docs(db)
        req_id = uuid.uuid4()
        req = ResearchRequest(
            id=req_id,
            question="What evidence exists regarding coastal warming and its potential implications for Gujarat coastal communities?",
            workspace_id="WS_TEST",
            geographic_scope={"type": "bbox", "coordinates": [68.0, 20.0, 74.0, 24.0]}
        )
        db.add(req)
        await db.commit()
        
        engine = ResearchEngine(db)
        final_req = await engine.execute_research(req_id)
        
        assert final_req.status == "completed"
        assert final_req.findings
        assert final_req.executive_summary
        
        stmt = select(ResearchEvidence).where(ResearchEvidence.request_id == req_id)
        res = await db.execute(stmt)
        evidence = res.scalars().all()
        
        stmt = select(ResearchClaim).where(ResearchClaim.request_id == req_id)
        res = await db.execute(stmt)
        claims = res.scalars().all()
        
        assert len(claims) > 0
        has_evidence_ref = any(c.evidence_ids and len(c.evidence_ids) > 0 for c in claims)
        assert has_evidence_ref

        
        await db.rollback()

import asyncio
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import select, update

from app.core.config import settings
from app.db.models.research import ResearchDocumentChunk
from app.services.intelligence.rag import OllamaEmbeddingProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def embed_existing_chunks():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    if settings.EMBEDDING_PROVIDER != "ollama":
        logger.error("Embedding provider is not set to ollama. Exiting.")
        return
        
    provider = OllamaEmbeddingProvider()
    
    async with async_session() as session:
        # Find chunks without embeddings
        stmt = select(ResearchDocumentChunk).where(ResearchDocumentChunk.embedding.is_(None))
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            logger.info("No chunks found requiring embeddings.")
            await engine.dispose()
            return
            
        logger.info(f"Found {len(chunks)} chunks requiring embeddings. Processing in batches...")
        
        batch_size = 5
        success_count = 0
        failure_count = 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.text for c in batch]
            
            try:
                # get_embeddings now validates dimensions and raises on error
                embeddings = await provider.get_embeddings(texts)
                
                for j, chunk in enumerate(batch):
                    if j < len(embeddings) and embeddings[j]:
                        chunk.embedding = embeddings[j]
                        chunk.embedding_model = provider.model
                        chunk.embedding_dimension = len(embeddings[j])
                        success_count += 1
                    else:
                        failure_count += 1
                        logger.warning(f"Chunk {chunk.id} returned no embedding from provider.")
                        
                # Commit after each batch
                await session.commit()
                logger.info(f"Processed batch {i//batch_size + 1}, successes: {success_count}, failures: {failure_count}")
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch starting at index {i}: {e}")
                failure_count += len(batch)
                await session.rollback()
                
        logger.info(f"Embedding generation complete. Success: {success_count}, Failed: {failure_count}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(embed_existing_chunks())

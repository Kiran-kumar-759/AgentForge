import asyncio
import logging
from app.db.base import Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Import the existing functions
from ingest_stage2 import process_infrastructure, process_population

load_dotenv(dotenv_path="/home/ckirankumar/AgentForge/backend/.env")
db_url = os.getenv("DATABASE_URL")
engine = create_async_engine(db_url, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_exposure")

async def main():
    async with AsyncSessionLocal() as session:
        await process_infrastructure(session)
        await process_population(session)
        
    await engine.dispose()
    logger.info("Exposure ingestion completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())

# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Since we might need async, we could use asyncpg, but the instruction asks for psycopg.
# SQLAlchemy 2.x supports psycopg for async with `postgresql+psycopg` and setting AsyncEngine.
# Let's use standard sync for simplicity or async if we want to follow modern FastAPI.
# I'll create an async engine.

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg://"),
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

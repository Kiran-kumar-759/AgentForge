from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from app.schemas.health import HealthResponse, ReadinessResponse
from app.db.session import get_db
from app.core.config import settings

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok")

@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    database_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    redis_status = "ok"
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.aclose()
    except Exception:
        redis_status = "error"

    celery_status = "configured"
    
    status = "ready" if database_status == "ok" and redis_status == "ok" else "not_ready"
    
    return ReadinessResponse(
        status=status,
        database=database_status,
        redis=redis_status,
        celery=celery_status
    )

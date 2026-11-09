import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.data.base import IngestionRequest
from app.services.data.ingestion import IngestionService
from app.core.logging import logger

@celery_app.task(name="ingest_open_meteo_task", bind=True, max_retries=3)
def ingest_open_meteo_task(self, provider: str, dataset: str, variables: List[str],
                           min_lat: float, max_lat: float, min_lon: float, max_lon: float,
                           start_time_iso: str, end_time_iso: str):
    logger.info(f"Starting ingestion task for {provider} dataset {dataset}")
    
    from datetime import datetime
    req = IngestionRequest(
        provider=provider,
        dataset=dataset,
        variables=variables,
        start_time=datetime.fromisoformat(start_time_iso),
        end_time=datetime.fromisoformat(end_time_iso),
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon
    )
    
    async def run_ingest():
        async with AsyncSessionLocal() as session:
            service = IngestionService(session)
            result = await service.ingest(req)
            return result.model_dump()
            
    try:
        # Run async function in a sync Celery context
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(run_ingest())
        
        if res.get("errors"):
            logger.error(f"Ingestion failed with errors: {res['errors']}")
            # Retry if transient... for now we just raise to trigger retry if needed
            if "timeout" in str(res["errors"]).lower():
                raise self.retry(countdown=2 ** self.request.retries)
                
        return res
    except SoftTimeLimitExceeded:
        logger.error("Ingestion task time limit exceeded")
        return {"status": "error", "message": "Time limit exceeded"}
    except Exception as exc:
        logger.error(f"Ingestion task error: {str(exc)}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

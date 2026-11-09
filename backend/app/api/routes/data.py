from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.marine_observation import MarineObservation
from app.db.models.dataset import Dataset
from app.services.data.registry import ProviderRegistry
from app.services.data.base import IngestionRequest, IngestionResult
from app.services.data.ingestion import IngestionService
from app.workers.celery_app import celery_app
from app.core.config import settings

router = APIRouter(prefix="/data", tags=["data"])
registry = ProviderRegistry()

@router.get("/providers")
async def get_providers():
    providers = []
    for p in registry.get_all_providers():
        providers.append({
            "provider": p.name,
            "configured": p.is_configured,
            "available": p.is_configured,
            "authentication_required": p.name in ["MOSDAC", "NASA Earthdata"],
        })
    return {"providers": providers}

@router.get("/datasets")
async def get_datasets(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dataset))
    datasets = res.scalars().all()
    return {"datasets": datasets}

@router.get("/health")
async def get_data_health(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from app.db.models.marine_observation import MarineObservation
    from app.db.models.cyclone import CycloneEvent
    from app.db.models.exposure import InfrastructureData, PopulationData
    
    marine_count = await db.scalar(select(func.count()).select_from(MarineObservation))
    cyclone_count = await db.scalar(select(func.count()).select_from(CycloneEvent))
    infra_count = await db.scalar(select(func.count()).select_from(InfrastructureData))
    pop_count = await db.scalar(select(func.count()).select_from(PopulationData))
    
    res = await db.execute(select(MarineObservation).order_by(MarineObservation.created_at.desc()).limit(1))
    latest_obs = res.scalars().first()
    
    return {
        "status": "available" if marine_count > 0 else "no observations",
        "last_ingestion_at": latest_obs.created_at.isoformat() if latest_obs and latest_obs.created_at else None,
        "database": "ok",
        "counts": {
            "marine_observations": marine_count,
            "cyclones": cyclone_count,
            "infrastructure": infra_count,
            "population": pop_count
        },
        "providers": {p.name: "ok" if p.is_configured else "unconfigured" for p in registry.get_all_providers()}
    }

@router.post("/ingest", response_model=IngestionResult)
async def ingest_data(request: IngestionRequest, db: AsyncSession = Depends(get_db)):
    service = IngestionService(db)
    result = await service.ingest(request)
    return result

@router.get("/marine")
async def query_marine_data(
    provider: Optional[str] = None,
    dataset: Optional[str] = None,
    variable: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = 1000,
    db: AsyncSession = Depends(get_db)
):
    # This queries database real records
    stmt = select(MarineObservation)
    
    if variable:
        stmt = stmt.where(MarineObservation.variable_name == variable)
    if latitude is not None:
        stmt = stmt.where(MarineObservation.latitude == latitude)
    if longitude is not None:
        stmt = stmt.where(MarineObservation.longitude == longitude)
    if start_time:
        stmt = stmt.where(MarineObservation.observation_timestamp >= start_time)
    if end_time:
        stmt = stmt.where(MarineObservation.observation_timestamp <= end_time)
        
    stmt = stmt.order_by(MarineObservation.observation_timestamp.desc()).limit(limit)
    
    res = await db.execute(stmt)
    records = res.scalars().all()
    
    return {
        "data": [
            {
                "id": str(r.id),
                "variable": r.variable_name,
                "value": r.value,
                "unit": r.unit,
                "latitude": float(r.latitude) if r.latitude is not None else None,
                "longitude": float(r.longitude) if r.longitude is not None else None,
                "observed_at": r.observation_timestamp.isoformat() if r.observation_timestamp else None,
                "retrieved_at": r.created_at.isoformat() if r.created_at else None,
                "provider": provider or str(r.data_source_id),
                "dataset": str(r.dataset_id) if not dataset else dataset,
                "quality_status": r.quality_status,
                "is_fallback": r.is_fallback
            } for r in records
        ],
        "metadata": {
            "provider": provider,
            "dataset": dataset,
            "variables": [variable] if variable else [],
            "retrieved_at": datetime.utcnow().isoformat(),
            "quality_summary": {
                "valid": len(records)
            }
        }
    }

@router.get("/pfz")
async def get_pfz_data(db: AsyncSession = Depends(get_db)):
    from app.db.models.fishing import FishingZone
    stmt = select(FishingZone).where(FishingZone.zone_type == "PFZ")
    res = await db.execute(stmt)
    zones = res.scalars().all()
    
    # If no data exists, we safely return empty (safely fails to "PFZ data unavailable" in UI)
    return {
        "status": "SUCCESS" if zones else "UNAVAILABLE",
        "message": "PFZ data retrieved" if zones else "PFZ data unavailable. INCOIS API integration pending.",
        "data": [
            {
                "id": str(z.id),
                "provider": z.provider,
                "valid_from": z.valid_from.isoformat() if z.valid_from else None,
                "valid_to": z.valid_to.isoformat() if z.valid_to else None,
                # Convert geometry to GeoJSON would be nice, but simple stub for now
                "geom": "POLYGON(...)" 
            } for z in zones
        ]
    }

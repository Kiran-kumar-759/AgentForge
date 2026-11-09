import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.services.exposure.exposure import ExposureService

router = APIRouter(prefix="/exposure", tags=["exposure"])

class ExposureAnalysisRequest(BaseModel):
    geometry: Dict[str, Any]
    analysis_type: str = "hazard_polygon"
    distance_km: Optional[float] = None
    hazard_name: Optional[str] = None
    population_year: Optional[int] = None
    population_resolution: str = "100m"
    include_settlements: bool = True
    include_infrastructure: bool = True

class CycloneExposureRequest(BaseModel):
    buffer_km: float = 50.0
    population_year: Optional[int] = None
    population_resolution: str = "100m"

@router.post("/analyze")
async def analyze_exposure(req: ExposureAnalysisRequest, db: AsyncSession = Depends(get_db)):
    svc = ExposureService(db)
    try:
        analysis = await svc.analyze_exposure(
            geometry_geojson=req.geometry,
            analysis_type=req.analysis_type,
            hazard_name=req.hazard_name,
            population_year=req.population_year,
            population_resolution=req.population_resolution,
            include_settlements=req.include_settlements,
            include_infrastructure=req.include_infrastructure,
            distance_km=req.distance_km
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "population": {
            "total": analysis.population_total,
            "year": analysis.population_year,
            "resolution": analysis.population_resolution,
            "source": analysis.population_source
        },
        "settlements": {
            "count": analysis.settlement_count
        },
        "infrastructure": {
            "count": analysis.infrastructure_count,
            "critical_count": analysis.critical_infrastructure_count
        },
        "geometry": analysis.geometry,
        "created_at": analysis.created_at
    }

@router.get("/{analysis_id}")
async def get_analysis(analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = ExposureService(db)
    analysis = await svc.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "hazard_source_type": analysis.hazard_source_type,
        "hazard_name": analysis.hazard_name,
        "population": {
            "total": analysis.population_total,
            "year": analysis.population_year,
            "resolution": analysis.population_resolution,
            "source": analysis.population_source
        },
        "settlements": {
            "count": analysis.settlement_count
        },
        "infrastructure": {
            "count": analysis.infrastructure_count,
            "critical_count": analysis.critical_infrastructure_count
        },
        "geometry": analysis.geometry,
        "created_at": analysis.created_at,
        "analysis_timestamp": analysis.analysis_timestamp
    }

@router.get("/{analysis_id}/settlements")
async def get_settlements(
    analysis_id: uuid.UUID, 
    limit: int = Query(100, le=1000), 
    offset: int = 0, 
    db: AsyncSession = Depends(get_db)
):
    svc = ExposureService(db)
    settlements = await svc.get_settlements(analysis_id, limit, offset)
    return {
        "count": len(settlements),
        "items": [
            {
                "id": str(s.id),
                "osm_type": s.osm_type,
                "osm_id": s.osm_id,
                "name": s.name,
                "place_type": s.place_type,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "tags": s.tags,
                "source": s.source
            }
            for s in settlements
        ]
    }

@router.get("/{analysis_id}/infrastructure")
async def get_infrastructure(
    analysis_id: uuid.UUID, 
    limit: int = Query(100, le=1000), 
    offset: int = 0, 
    db: AsyncSession = Depends(get_db)
):
    svc = ExposureService(db)
    infra = await svc.get_infrastructure(analysis_id, limit, offset)
    return {
        "count": len(infra),
        "items": [
            {
                "id": str(i.id),
                "osm_type": i.osm_type,
                "osm_id": i.osm_id,
                "name": i.name,
                "infrastructure_type": i.infrastructure_type,
                "criticality": i.criticality,
                "latitude": i.latitude,
                "longitude": i.longitude,
                "tags": i.tags,
                "source": i.source
            }
            for i in infra
        ]
    }

@router.get("/{analysis_id}/geojson")
async def get_geojson(analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = ExposureService(db)
    analysis = await svc.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    features = []
    
    # 1. Hazard polygon
    features.append({
        "type": "Feature",
        "geometry": analysis.geometry,
        "properties": {
            "feature_type": "hazard_polygon",
            "name": analysis.hazard_name or "Hazard Area",
            "population_exposure": analysis.population_total
        }
    })
    
    # 2. Settlements
    settlements = await svc.get_settlements(analysis_id, limit=5000)
    for s in settlements:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [s.longitude, s.latitude]
            },
            "properties": {
                "feature_type": "settlement",
                "name": s.name,
                "place_type": s.place_type,
                "osm_id": f"{s.osm_type}/{s.osm_id}"
            }
        })
        
    # 3. Infrastructure
    infra = await svc.get_infrastructure(analysis_id, limit=5000)
    for i in infra:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [i.longitude, i.latitude]
            },
            "properties": {
                "feature_type": "infrastructure",
                "name": i.name,
                "infrastructure_type": i.infrastructure_type,
                "criticality": i.criticality,
                "osm_id": f"{i.osm_type}/{i.osm_id}"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

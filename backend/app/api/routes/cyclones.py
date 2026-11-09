from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.db.session import get_db
from app.db.models.cyclone import CycloneEvent, CycloneTrackPoint

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def get_cyclones(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    stmt = select(CycloneEvent)
    if active_only:
        stmt = stmt.where(CycloneEvent.is_active == True)
    res = await db.execute(stmt)
    events = res.scalars().all()
    
    features = []
    for ev in events:
        if ev.current_longitude is not None and ev.current_latitude is not None:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(ev.current_longitude), float(ev.current_latitude)]
                },
                "properties": {
                    "external_id": ev.external_id,
                    "name": ev.name,
                    "classification": ev.classification.value if hasattr(ev.classification, "value") else ev.classification,
                    "is_active": ev.is_active,
                    "basin": ev.basin,
                    "max_wind_speed": ev.max_wind_speed,
                    "feature_type": "cyclone"
                }
            })
            
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "dataset": "GDACS Cyclones",
            "source": "GDACS",
            "coverage": "Global"
        }
    }

@router.get("/{external_id}", response_model=Dict[str, Any])
async def get_cyclone_details(external_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CycloneEvent).where(CycloneEvent.external_id == external_id)
    res = await db.execute(stmt)
    ev = res.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Cyclone not found")
        
    return {
        "external_id": ev.external_id,
        "name": ev.name,
        "basin": ev.basin,
        "classification": ev.classification.value if hasattr(ev.classification, "value") else ev.classification,
        "current_latitude": ev.current_latitude,
        "current_longitude": ev.current_longitude,
        "max_wind_speed": ev.max_wind_speed,
        "is_active": ev.is_active
    }

@router.get("/{external_id}/track", response_model=Dict[str, Any])
async def get_cyclone_track(external_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CycloneEvent).where(CycloneEvent.external_id == external_id)
    res = await db.execute(stmt)
    ev = res.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Cyclone not found")
        
    tp_stmt = select(CycloneTrackPoint).where(CycloneTrackPoint.cyclone_event_id == ev.id).order_by(CycloneTrackPoint.timestamp)
    tp_res = await db.execute(tp_stmt)
    pts = tp_res.scalars().all()
    
    obs = []
    fct = []
    for pt in pts:
        p = {
            "latitude": pt.latitude,
            "longitude": pt.longitude,
            "timestamp": pt.timestamp.isoformat(),
            "max_wind_speed": pt.max_wind_speed,
            "classification": pt.classification
        }
        if pt.is_observed:
            obs.append(p)
        else:
            fct.append(p)
            
    return {
        "external_id": ev.external_id,
        "observed_track": obs,
        "forecast_track": fct
    }

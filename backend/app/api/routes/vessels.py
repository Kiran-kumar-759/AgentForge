from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid

from app.db.session import get_db
from app.db.models.vessel import Vessel, VesselPosition

router = APIRouter(prefix="/vessels", tags=["vessels"])

@router.get("", response_model=Dict[str, Any])
async def get_vessels(
    limit: int = 1000,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Vessel).limit(limit)
    res = await db.execute(stmt)
    vessels = res.scalars().all()
    
    features = []
    for v in vessels:
        pos_stmt = select(VesselPosition).where(VesselPosition.vessel_id == v.id).order_by(VesselPosition.timestamp.desc()).limit(1)
        pos_res = await db.execute(pos_stmt)
        pos = pos_res.scalars().first()
        
        if pos:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(pos.longitude), float(pos.latitude)]
                },
                "properties": {
                    "id": str(v.id),
                    "mmsi": v.mmsi,
                    "name": v.name,
                    "vessel_type": v.vessel_type,
                    "length": v.length_m,
                    "width": v.width_m,
                    "callsign": v.call_sign,
                    "destination": v.destination,
                    "speed": pos.speed_knots,
                    "course": pos.course_degrees,
                    "heading": pos.heading_degrees,
                    "timestamp": pos.timestamp.isoformat(),
                    "updated_at": v.updated_at.isoformat() if v.updated_at else None,
                    "feature_type": "vessel"
                }
            })
            
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "dataset": "AIS/Vessel Data",
            "source": "Fintraffic-AIS",
            "timestamp": features[0]["properties"]["timestamp"] if features else None,
            "coverage": "Baltic Sea (Fintraffic) / Partial",
            "limitations": ["Indian Ocean coverage unavailable in this dataset"]
        }
    }

@router.get("/{vessel_id}", response_model=Dict[str, Any])
async def get_vessel_details(vessel_id: str, db: AsyncSession = Depends(get_db)):
    try:
        vid = uuid.UUID(vessel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vessel ID")

    stmt = select(Vessel).where(Vessel.id == vid)
    res = await db.execute(stmt)
    v = res.scalars().first()
    if not v:
        raise HTTPException(status_code=404, detail="Vessel not found")
        
    pos_stmt = select(VesselPosition).where(VesselPosition.vessel_id == v.id).order_by(VesselPosition.timestamp.desc()).limit(1)
    pos_res = await db.execute(pos_stmt)
    pos = pos_res.scalars().first()
        
    return {
        "id": str(v.id),
        "mmsi": v.mmsi,
        "name": v.name,
        "vessel_type": v.vessel_type,
        "length": v.length_m,
        "width": v.width_m,
        "callsign": v.call_sign,
        "destination": v.destination,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        "last_position": {
            "latitude": float(pos.latitude),
            "longitude": float(pos.longitude),
            "speed": pos.speed_knots,
            "course": pos.course_degrees,
            "heading": pos.heading_degrees,
            "timestamp": pos.timestamp.isoformat()
        } if pos else None
    }

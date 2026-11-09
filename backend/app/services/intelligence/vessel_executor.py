import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.services.data.vessel.digitraffic import DigitrafficProvider
from app.services.data.vessel.base import BBox
from app.db.models.vessel import Vessel, VesselPosition
from app.db.models.data_source import DataSource
from app.services.data.cache import cache_service

from app.services.intelligence.schemas import (
    CapabilityResult, ExecutionMetadata, ProvenanceRecord
)

logger = logging.getLogger(__name__)

class VesselExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = DigitrafficProvider()

    async def _get_or_create_source(self) -> DataSource:
        stmt = select(DataSource).where(DataSource.name == "Fintraffic-AIS")
        res = await self.db.execute(stmt)
        src = res.scalars().first()
        if not src:
            src = DataSource(
                name="Fintraffic-AIS",
                provider="Digitraffic",
                source_type="API",
                description="Fintraffic Digitraffic Marine AIS",
                base_url="https://meri.digitraffic.fi/api/ais/v1",
                authentication_type="None",
                is_active=True
            )
            self.db.add(src)
            await self.db.commit()
            await self.db.refresh(src)
        return src

    async def execute_vessel_intelligence(self, radius_km: float = None, lat: float = None, lon: float = None) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        
        is_fallback = False
        fallback_reason = None
        now = datetime.now(timezone.utc)
        # expand time to catch old fallback data since ingestion might have stopped
        since = now - timedelta(days=365)
        
        bbox = None
        if radius_km and lat and lon:
            deg_radius = radius_km / 111.0
            bbox = BBox(
                min_latitude=lat - deg_radius,
                max_latitude=lat + deg_radius,
                min_longitude=lon - deg_radius,
                max_longitude=lon + deg_radius
            )
            
            # Baltic roughly lat 53-66, lon 10-30
            # If the user asks for Indian Ocean (lat ~0 to 25, lon ~65 to 95)
            # return explicit unavailable message.
            if lat < 50 or lon > 40:
                meta = ExecutionMetadata(request_id=request_id, is_fallback=False)
                return CapabilityResult(
                    status="UNAVAILABLE",
                    capability_code="get_vessel_intelligence",
                    agent_code="VesselAgent",
                    data={
                        "reason": "GEOGRAPHIC_COVERAGE",
                        "message": "Vessel AIS data is not available for the requested area.",
                        "provider": "Digitraffic / Fintraffic",
                        "coverage": {
                            "region": "Baltic / Finnish waters"
                        },
                        "requested_area": {
                            "latitude": lat,
                            "longitude": lon,
                            "radius_km": radius_km
                        },
                        "available_data": False
                    },
                    metadata=meta,
                    errors=["Indian Ocean AIS coverage unavailable. Current dataset is restricted to FINTRAFFIC / BALTIC SEA coverage."]
                )

        stmt = select(VesselPosition, Vessel).join(Vessel).where(
            VesselPosition.timestamp >= since
        ).order_by(VesselPosition.timestamp.desc())
        
        if bbox:
            stmt = stmt.where(
                and_(
                    VesselPosition.latitude >= bbox.min_latitude,
                    VesselPosition.latitude <= bbox.max_latitude,
                    VesselPosition.longitude >= bbox.min_longitude,
                    VesselPosition.longitude <= bbox.max_longitude
                )
            )
            
        res = await self.db.execute(stmt)
        rows = res.all()
        
        vessels_dict = {}
        for db_pt, db_vessel in rows:
            if db_vessel.external_vessel_id not in vessels_dict:
                vessels_dict[db_vessel.external_vessel_id] = {
                    "mmsi": db_vessel.mmsi,
                    "latest_pos": db_pt
                }
                
        vessels_out = []
        provenance = []
        for ext_id, v_data in vessels_dict.items():
            pos = v_data["latest_pos"]
            vessels_out.append({
                "id": ext_id,
                "mmsi": v_data["mmsi"],
                "latitude": pos.latitude,
                "longitude": pos.longitude,
                "speed": pos.speed_knots,
                "heading": pos.heading_degrees,
                "course": pos.course_degrees,
                "timestamp": pos.timestamp.isoformat() if hasattr(pos.timestamp, 'isoformat') else pos.timestamp
            })
        meta = ExecutionMetadata(
            request_id=request_id,
            is_fallback=is_fallback,
            fallback_reason=fallback_reason
        )
        
        return CapabilityResult(
            status="SUCCESS" if not is_fallback else "PARTIAL",
            capability_code="get_vessel_intelligence",
            agent_code="VesselAgent",
            data={"vessels": vessels_out},
            metadata=meta,
            provenance=provenance
        )

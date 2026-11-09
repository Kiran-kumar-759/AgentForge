import uuid
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.services.data.cyclone.gdacs import GDACSProvider
from app.services.data.cyclone.base import NormalizedCycloneEvent
from app.db.models.cyclone import CycloneEvent, CycloneTrackPoint, PointType
from app.db.models.data_source import DataSource
from app.services.data.cache import cache_service

from app.services.intelligence.schemas import (
    CapabilityResult, ExecutionMetadata, ProvenanceRecord
)

logger = logging.getLogger(__name__)

class CycloneExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = GDACSProvider()

    async def _get_or_create_source(self) -> DataSource:
        stmt = select(DataSource).where(DataSource.name == "GDACS-TC")
        res = await self.db.execute(stmt)
        src = res.scalars().first()
        if not src:
            src = DataSource(
                name="GDACS-TC",
                provider="GDACS",
                source_type="API",
                description="Global Disaster Alert and Coordination System - Tropical Cyclones",
                base_url="https://www.gdacs.org",
                authentication_type="None",
                is_active=True
            )
            self.db.add(src)
            await self.db.commit()
            await self.db.refresh(src)
        return src

    async def _upsert_events(self, source_id: int, events: List[NormalizedCycloneEvent]):
        for ev in events:
            stmt = select(CycloneEvent).where(
                CycloneEvent.external_id == ev.external_id,
                CycloneEvent.source_id == source_id
            )
            res = await self.db.execute(stmt)
            db_event = res.scalars().first()
            
            if not db_event:
                db_event = CycloneEvent(
                    external_id=ev.external_id,
                    source_id=source_id,
                    name=ev.name,
                    basin=ev.basin,
                    status=ev.status,
                    classification=ev.classification,
                    formation_time=ev.formation_time,
                    dissipation_time=ev.dissipation_time,
                    current_latitude=ev.current_latitude,
                    current_longitude=ev.current_longitude,
                    current_timestamp=ev.current_timestamp,
                    max_wind_speed=ev.max_wind_speed,
                    max_wind_unit=ev.max_wind_unit,
                    minimum_pressure=ev.minimum_pressure,
                    movement_direction=ev.movement_direction,
                    movement_speed=ev.movement_speed,
                    source_url=ev.source_url,
                    is_active=ev.is_active,
                    metadata_=ev.metadata
                )
                self.db.add(db_event)
                await self.db.flush()
            else:
                db_event.classification = ev.classification
                db_event.current_latitude = ev.current_latitude
                db_event.current_longitude = ev.current_longitude
                db_event.current_timestamp = ev.current_timestamp
                db_event.max_wind_speed = ev.max_wind_speed
                db_event.max_wind_unit = ev.max_wind_unit
                db_event.is_active = ev.is_active
                db_event.metadata_ = ev.metadata
                
            # Upsert track points
            for tp in ev.track_points:
                pt_stmt = select(CycloneTrackPoint).where(
                    CycloneTrackPoint.cyclone_event_id == db_event.id,
                    CycloneTrackPoint.timestamp == tp.timestamp,
                    CycloneTrackPoint.point_type == (PointType.OBSERVED if tp.point_type == "OBSERVED" else PointType.FORECAST)
                )
                pt_res = await self.db.execute(pt_stmt)
                db_pt = pt_res.scalars().first()
                if not db_pt:
                    db_pt = CycloneTrackPoint(
                        cyclone_event_id=db_event.id,
                        point_type=PointType.OBSERVED if tp.point_type == "OBSERVED" else PointType.FORECAST,
                        timestamp=tp.timestamp,
                        latitude=tp.latitude,
                        longitude=tp.longitude,
                        max_wind_speed=tp.max_wind_speed,
                        wind_unit=tp.wind_unit,
                        classification=tp.classification,
                        is_observed=(tp.point_type == "OBSERVED"),
                        is_forecast=(tp.point_type == "FORECAST"),
                        metadata_=tp.metadata
                    )
                    self.db.add(db_pt)
                    
        await self.db.commit()

    async def _get_fallback(self, max_age_hours: int = 24) -> List[NormalizedCycloneEvent]:
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        min_time = now - timedelta(hours=max_age_hours)
        
        stmt = select(CycloneEvent).where(
            CycloneEvent.is_active == True,
            CycloneEvent.current_timestamp >= min_time
        )
        res = await self.db.execute(stmt)
        db_events = res.scalars().all()
        
        events = []
        for dbe in db_events:
            tp_stmt = select(CycloneTrackPoint).where(CycloneTrackPoint.cyclone_event_id == dbe.id).order_by(CycloneTrackPoint.timestamp)
            tp_res = await self.db.execute(tp_stmt)
            db_pts = tp_res.scalars().all()
            
            events.append(NormalizedCycloneEvent(
                external_id=dbe.external_id, name=dbe.name, basin=dbe.basin, status=dbe.status, classification=dbe.classification,
                formation_time=dbe.formation_time, dissipation_time=dbe.dissipation_time, current_latitude=dbe.current_latitude,
                current_longitude=dbe.current_longitude, current_timestamp=dbe.current_timestamp, max_wind_speed=dbe.max_wind_speed,
                max_wind_unit=dbe.max_wind_unit, minimum_pressure=dbe.minimum_pressure, movement_direction=dbe.movement_direction,
                movement_speed=dbe.movement_speed, source_url=dbe.source_url, is_active=dbe.is_active, metadata=dbe.metadata_,
                track_points=[
                    # simplified for fallback construction
                ]
            ))
            # We don't populate full track points in fallback for brevity unless requested. Let's populate them.
            for pt in db_pts:
                events[-1].track_points.append(
                    type("Point", (), {
                        "point_type": pt.point_type.value, "timestamp": pt.timestamp, "latitude": pt.latitude, "longitude": pt.longitude,
                        "max_wind_speed": pt.max_wind_speed, "wind_unit": pt.wind_unit, "classification": pt.classification, "metadata": pt.metadata_
                    })()
                )
        return events

    async def execute_cyclone_intelligence(self, active_only: bool = True, radius_km: float = None, lat: float = None, lon: float = None) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        cache_key = "orca:cyclones:active"
        
        is_cached, is_fallback, fallback_reason = False, False, None
        
        # We exclusively rely on the DB
        events = await self._get_fallback()
            
        if not events:
            return CapabilityResult(status="SUCCESS", capability_code="get_cyclone_intelligence", agent_code="RiskAgent", data={"storms": []}, metadata=ExecutionMetadata(request_id=request_id), provenance=[])

        # filter by radius
        filtered = events
        if radius_km and lat and lon:
            # simplified distance filter (approx degree = 111km)
            deg_radius = radius_km / 111.0
            filtered = [
                ev for ev in events 
                if ev.current_latitude and ev.current_longitude and 
                (abs(ev.current_latitude - lat) <= deg_radius and abs(ev.current_longitude - lon) <= deg_radius)
            ]
            
        storms_data = []
        provenance = []
        now = datetime.now(timezone.utc)
        
        for ev in filtered:
            obs_track = []
            fct_track = []
            for tp in ev.track_points:
                pt_dict = {
                    "timestamp": tp.timestamp.isoformat() if hasattr(tp.timestamp, "isoformat") else tp.timestamp,
                    "latitude": tp.latitude,
                    "longitude": tp.longitude,
                    "max_wind_speed": tp.max_wind_speed,
                    "classification": tp.classification
                }
                if tp.point_type == "OBSERVED":
                    obs_track.append(pt_dict)
                else:
                    fct_track.append(pt_dict)
                    
            storms_data.append({
                "external_id": ev.external_id,
                "name": ev.name,
                "classification": ev.classification,
                "current_position": {"latitude": ev.current_latitude, "longitude": ev.current_longitude},
                "current_time": ev.current_timestamp.isoformat() if hasattr(ev.current_timestamp, "isoformat") else ev.current_timestamp,
                "max_wind_speed": ev.max_wind_speed,
                "observed_track": obs_track,
                "forecast_track": fct_track,
                "source": "GDACS",
                "retrieved_at": now.isoformat(),
                "is_fallback": is_fallback
            })
            
            provenance.append(ProvenanceRecord(
                provider="GDACS", dataset="GDACS-TC", retrieved_at=now, observation_timestamp=ev.current_timestamp,
                latitude=ev.current_latitude, longitude=ev.current_longitude, variable="cyclone_track", unit=""
            ))

        metadata = ExecutionMetadata(request_id=request_id, is_cached=is_cached, is_fallback=is_fallback, fallback_reason=fallback_reason)
        return CapabilityResult(status="SUCCESS" if not is_fallback else "PARTIAL", capability_code="get_cyclone_intelligence", agent_code="RiskAgent", data={"storms": storms_data}, metadata=metadata, provenance=provenance)

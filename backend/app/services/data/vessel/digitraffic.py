import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.services.data.vessel.base import (
    VesselProvider,
    ProviderDescriptor,
    BBox,
    ProviderFetchResult,
    NormalizedVessel,
    NormalizedVesselPosition,
    VesselProviderError
)

logger = logging.getLogger(__name__)

class DigitrafficProvider(VesselProvider):
    def __init__(self):
        self._descriptor = ProviderDescriptor(
            code="digitraffic",
            name="Fintraffic Digitraffic Marine",
            data_source_name="Fintraffic",
            positions_dataset="Vessel Locations",
            metadata_dataset="Vessel Metadata",
            official_url="https://www.digitraffic.fi/en/marine-traffic/",
            api_url="https://meri.digitraffic.fi/api/ais/v1",
            authentication="None (User-Agent header required)",
            coverage_description="Baltic Sea and inland waterways of Finland",
            coverage_bbox=None,  # We can restrict to Baltic if needed, but None is fine for now
            update_frequency="Continuous",
            historical_support="No",
            license="CC 4.0 BY (Fintraffic / digitraffic.fi)"
        )
        self.headers = {
            "Digitraffic-User": "ORCA-AgentForge/1.0",
            "Accept-Encoding": "gzip"
        }
        self.client_timeout = 15.0

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    @property
    def is_configured(self) -> bool:
        return True

    async def get_vessels(self, bbox: Optional[BBox], since: datetime) -> ProviderFetchResult:
        url = f"{self._descriptor.api_url}/locations"
        
        records_received = 0
        records_rejected = 0
        rejection_reasons = {}
        positions = []
        
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.client_timeout) as client:
                res = await client.get(url)
                res.raise_for_status()
                data = res.json()
        except httpx.HTTPStatusError as e:
            raise VesselProviderError(
                provider=self.code,
                reason="http_error",
                message=f"HTTP {e.response.status_code} fetching locations"
            )
        except Exception as e:
            raise VesselProviderError(
                provider=self.code,
                reason="network_error",
                message=str(e)
            )

        features = data.get("features", [])
        records_received = len(features)
        
        for feature in features:
            props = feature.get("properties", {})
            mmsi = props.get("mmsi")
            if not mmsi:
                records_rejected += 1
                rejection_reasons["missing_mmsi"] = rejection_reasons.get("missing_mmsi", 0) + 1
                continue
                
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates")
            if not coords or len(coords) < 2:
                records_rejected += 1
                rejection_reasons["missing_geometry"] = rejection_reasons.get("missing_geometry", 0) + 1
                continue
                
            lon, lat = coords[0], coords[1]
            
            # Filter by bbox
            if bbox and not bbox.contains(lat, lon):
                records_rejected += 1
                rejection_reasons["outside_bbox"] = rejection_reasons.get("outside_bbox", 0) + 1
                continue
                
            ts_ext = props.get("timestampExternal")
            if ts_ext:
                dt = datetime.fromtimestamp(ts_ext / 1000.0, tz=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)
                
            if dt < since:
                records_rejected += 1
                rejection_reasons["too_old"] = rejection_reasons.get("too_old", 0) + 1
                continue

            nav_stat_raw = props.get("navStat")
            nav_status = str(nav_stat_raw) if nav_stat_raw is not None else None
            
            pos = NormalizedVesselPosition(
                external_id=str(mmsi),
                mmsi=str(mmsi),
                latitude=lat,
                longitude=lon,
                timestamp=dt,
                speed_knots=props.get("sog"),
                course_degrees=props.get("cog"),
                heading_degrees=props.get("heading"),
                navigation_status=nav_status,
                metadata={
                    "rot": props.get("rot"),
                    "posAcc": props.get("posAcc"),
                    "raim": props.get("raim")
                }
            )
            positions.append(pos)
            
        return ProviderFetchResult(
            provider=self.code,
            dataset=self._descriptor.positions_dataset,
            request_reference="locations",
            retrieved_at=datetime.now(timezone.utc),
            positions=positions,
            records_received=records_received,
            records_rejected=records_rejected,
            rejection_reasons=rejection_reasons
        )

    async def get_vessels_metadata(self, since: datetime) -> List[NormalizedVessel]:
        url = f"{self._descriptor.api_url}/vessels"
        
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.client_timeout) as client:
                res = await client.get(url)
                res.raise_for_status()
                data = res.json()
        except Exception as e:
            logger.error(f"Error fetching digitraffic vessel metadata: {e}")
            return []
            
        vessels = []
        for v in data:
            mmsi = v.get("mmsi")
            if not mmsi:
                continue
                
            ts = v.get("timestamp")
            dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc) if ts else None
            
            if dt and dt < since:
                continue
                
            imo = str(v.get("imo")) if v.get("imo") else None
            
            # Ship type from AIS
            ship_type = v.get("shipType")
            
            # Dimensions
            length = None
            width = None
            refA = v.get("referencePointA")
            refB = v.get("referencePointB")
            refC = v.get("referencePointC")
            refD = v.get("referencePointD")
            
            if refA is not None and refB is not None:
                length = float(refA + refB)
            if refC is not None and refD is not None:
                width = float(refC + refD)
                
            draught = v.get("draught")
            draught_m = float(draught) / 10.0 if draught is not None else None
            
            vessel = NormalizedVessel(
                external_id=str(mmsi),
                mmsi=str(mmsi),
                imo=imo,
                name=v.get("name", "").strip() or None,
                call_sign=v.get("callSign", "").strip() or None,
                ais_ship_type=ship_type,
                length_m=length,
                width_m=width,
                draught_m=draught_m,
                destination=v.get("destination", "").strip() or None,
                source_timestamp=dt,
                metadata={
                    "eta": v.get("eta")
                }
            )
            vessels.append(vessel)
            
        return vessels

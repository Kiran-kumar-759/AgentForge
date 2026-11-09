import httpx
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.services.data.cyclone.base import (
    CycloneDataProvider,
    NormalizedCycloneEvent,
    NormalizedCycloneTrackPoint
)

logger = logging.getLogger(__name__)

class GDACSProvider(CycloneDataProvider):
    """
    Global Disaster Alert and Coordination System (GDACS) API
    Official source URL: https://www.gdacs.org
    Data product: GDACS Event API (Tropical Cyclones)
    Access method: REST API (JSON / GeoJSON)
    Authentication: None required
    Update frequency: Typically every 6 hours (synoptic times)
    Coverage: Global (aggregates NOAA, JTWC, etc.)
    """

    def __init__(self):
        self.base_url = "https://www.gdacs.org/gdacsapi/api"

    @property
    def name(self) -> str:
        return "gdacs"

    @property
    def is_configured(self) -> bool:
        return True

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        if not time_str:
            return None
        try:
            # GDACS format: 2026-10-01T21:00:00
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _parse_label_time(self, label: str, year: int) -> Optional[datetime]:
        """Parses label like '29/09 15:00 UTC'."""
        try:
            # Remove UTC
            clean_label = label.replace("UTC", "").strip()
            # 29/09 15:00
            dt = datetime.strptime(f"{clean_label} {year}", "%d/%m %H:%M %Y")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def _normalize_status(self, severity_text: str) -> str:
        if not severity_text:
            return "UNKNOWN"
        text = severity_text.lower()
        if "super cyclonic" in text:
            return "SUPER_CYCLONIC_STORM"
        if "extremely severe" in text:
            return "EXTREMELY_SEVERE_CYCLONIC_STORM"
        if "very severe" in text:
            return "VERY_SEVERE_CYCLONIC_STORM"
        if "severe cyclonic" in text:
            return "SEVERE_CYCLONIC_STORM"
        if "cyclonic storm" in text:
            return "CYCLONIC_STORM"
        if "tropical storm" in text:
            return "TROPICAL_STORM"
        if "hurricane" in text or "typhoon" in text:
            return "VERY_SEVERE_CYCLONIC_STORM"
        if "depression" in text:
            return "DEPRESSION"
        if "disturbance" in text:
            return "TROPICAL_DISTURBANCE"
        return "UNKNOWN"

    async def fetch_active_cyclones(self) -> List[NormalizedCycloneEvent]:
        url = f"{self.base_url}/events/geteventlist/MAP?eventtype=TC"
        events = []
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            
            features = data.get("features", [])
            seen_events = set()
            for feature in features:
                props = feature.get("properties", {})
                if not props:
                    continue
                    
                is_current = str(props.get("iscurrent", "")).lower() == "true"
                if not is_current:
                    continue
                    
                # GDACS returns ALL historical events in geteventlist. Filter by last 7 days.
                todate_str = props.get("todate")
                if not todate_str:
                    continue
                todate_dt = self._parse_time(todate_str)
                if not todate_dt or (datetime.now(timezone.utc) - todate_dt).days > 7:
                    continue
                    
                event_id = str(props.get("eventid"))
                if event_id in seen_events:
                    continue
                seen_events.add(event_id)
                
                episode_id = str(props.get("episodeid"))
                name = props.get("eventname", "Unknown")
                
                # Fetch detailed geometry for tracks
                geom_url = f"{self.base_url}/polygons/getgeometry?eventtype=TC&eventid={event_id}&episodeid={episode_id}"
                geom_res = await client.get(geom_url, timeout=10.0)
                geom_data = geom_res.json()
                
                track_points = []
                geom_features = geom_data.get("features", [])
                
                current_time_str = props.get("todate") or props.get("datemodified")
                current_dt = self._parse_time(current_time_str)
                current_year = current_dt.year if current_dt else datetime.utcnow().year
                
                for gf in geom_features:
                    gf_props = gf.get("properties", {})
                    gf_class = gf_props.get("Class", "")
                    if gf_class.startswith("Point_Polygon_Point"):
                        label = gf_props.get("polygonlabel", "")
                        pt_time = self._parse_label_time(label, current_year)
                        if not pt_time:
                            continue
                            
                        # Centroid of bbox
                        bbox = gf.get("bbox")
                        if not bbox or len(bbox) != 4:
                            continue
                        lon = (bbox[0] + bbox[2]) / 2.0
                        lat = (bbox[1] + bbox[3]) / 2.0
                        
                        severity_data = gf_props.get("severitydata", {})
                        wind_speed = severity_data.get("severity")
                        wind_unit = severity_data.get("severityunit")
                        severity_text = severity_data.get("severitytext", "")
                        
                        is_observed = current_dt and pt_time <= current_dt
                        point_type = "OBSERVED" if is_observed else "FORECAST"
                        
                        tp = NormalizedCycloneTrackPoint(
                            point_type=point_type,
                            timestamp=pt_time,
                            latitude=lat,
                            longitude=lon,
                            max_wind_speed=wind_speed,
                            wind_unit=wind_unit,
                            classification=self._normalize_status(severity_text)
                        )
                        track_points.append(tp)
                
                # Sort track points by time
                track_points.sort(key=lambda x: x.timestamp)
                
                severity_data = props.get("severitydata", {})
                wind_speed = severity_data.get("severity")
                wind_unit = severity_data.get("severityunit")
                severity_text = severity_data.get("severitytext", "")
                
                geom = feature.get("geometry", {})
                coords = geom.get("coordinates", [None, None])
                
                # flatten coordinates just in case it's nested (e.g. MultiPoint)
                while coords and isinstance(coords, list) and isinstance(coords[0], list):
                    coords = coords[0]
                    
                lon = coords[0] if len(coords) > 0 else None
                lat = coords[1] if len(coords) > 1 else None
                
                event = NormalizedCycloneEvent(
                    external_id=event_id,
                    name=name,
                    classification=self._normalize_status(severity_text),
                    current_latitude=lat,
                    current_longitude=lon,
                    current_timestamp=current_dt,
                    max_wind_speed=wind_speed,
                    max_wind_unit=wind_unit,
                    source_url=props.get("url", {}).get("report"),
                    track_points=track_points,
                    metadata={"episodeid": episode_id, "alertlevel": props.get("alertlevel")}
                )
                events.append(event)
                
        return events

    async def fetch_cyclone_details(self, external_id: str) -> Optional[NormalizedCycloneEvent]:
        events = await self.fetch_active_cyclones()
        for ev in events:
            if ev.external_id == external_id:
                return ev
        return None

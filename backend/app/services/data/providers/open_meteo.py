import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.core.config import settings
from app.services.data.base import MarineDataProvider, MarineObservation, IngestionRequest, QualityStatus
from app.services.data.validation import is_valid_coordinate, validate_observation_value
from app.services.data.normalization import normalize_unit

class OpenMeteoProvider(MarineDataProvider):
    @property
    def name(self) -> str:
        return "Open-Meteo"
        
    @property
    def is_configured(self) -> bool:
        return bool(settings.OPEN_METEO_BASE_URL)
        
    async def fetch_observations(self, request: IngestionRequest) -> List[MarineObservation]:
        if not self.is_configured:
            return []
            
        lat = (request.min_lat + request.max_lat) / 2
        lon = (request.min_lon + request.max_lon) / 2
        
        if not is_valid_coordinate(lat, lon):
            raise ValueError(f"Invalid coordinates: {lat}, {lon}")
            
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(request.variables),
            "start_date": request.start_time.strftime("%Y-%m-%d"),
            "end_date": request.end_time.strftime("%Y-%m-%d"),
            "timezone": "UTC"
        }
        
        endpoint = settings.OPEN_METEO_BASE_URL
        if request.dataset == "open-meteo-weather":
            endpoint = settings.OPEN_METEO_WEATHER_URL
            
        async with httpx.AsyncClient(timeout=settings.DATA_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
        return self.normalize(data, request.dataset, lat, lon)

    def normalize(self, raw: Dict[str, Any], dataset: str, req_lat: float, req_lon: float) -> List[MarineObservation]:
        observations = []
        hourly = raw.get("hourly", {})
        hourly_units = raw.get("hourly_units", {})
        
        if not hourly or "time" not in hourly:
            return observations
            
        times = hourly["time"]
        now = datetime.now(timezone.utc)
        
        for i, time_str in enumerate(times):
            obs_time = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            
            for var_name, values in hourly.items():
                if var_name == "time":
                    continue
                    
                val = values[i]
                if val is None or not validate_observation_value(var_name, val):
                    continue
                    
                orig_unit = hourly_units.get(var_name, "")
                norm_val, norm_unit, conv_method = normalize_unit(var_name, val, orig_unit)
                
                meta = {
                    "original_unit": orig_unit,
                    "conversion_method": conv_method,
                    "original_value": val
                }
                
                obs = MarineObservation(
                    source=self.name,
                    dataset=dataset,
                    variable_name=var_name,
                    value=norm_val,
                    unit=norm_unit,
                    latitude=req_lat,
                    longitude=req_lon,
                    observation_timestamp=obs_time,
                    retrieved_at=now,
                    quality_status=QualityStatus.VALID,
                    is_fallback=False,
                    metadata=meta
                )
                observations.append(obs)
                
        return observations

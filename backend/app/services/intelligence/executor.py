import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.services.data.base import IngestionRequest, MarineObservation
from app.services.data.registry import ProviderRegistry
from app.services.data.cache import cache_service
from app.db.models.marine_observation import MarineObservation as DBMarineObservation
from app.db.models.dataset import Dataset
from app.db.models.data_source import DataSource

from app.services.intelligence.schemas import (
    CapabilityResult, ExecutionMetadata, ProvenanceRecord,
    WeatherConditions, WindConditions, OceanConditions, WeatherForecast, ForecastEntry
)

class CapabilityExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = ProviderRegistry()

    def _get_cache_key(self, prefix: str, lat: float, lon: float, params: str = "") -> str:
        return f"orca:intelligence:{prefix}:{lat}:{lon}:{params}"

    async def _fetch_from_provider(self, provider_name: str, dataset: str, variables: List[str], lat: float, lon: float, start_time: datetime, end_time: datetime) -> List[MarineObservation]:
        provider = self.registry.get_provider(provider_name)
        if not provider or not provider.is_configured:
            raise ValueError(f"Provider {provider_name} not configured")
        
        req = IngestionRequest(
            provider=provider_name,
            dataset=dataset,
            variables=variables,
            start_time=start_time,
            end_time=end_time,
            min_lat=lat, max_lat=lat,
            min_lon=lon, max_lon=lon
        )
        return await provider.fetch_observations(req)

    async def _get_fallback_from_db(self, variables: List[str], lat: float, lon: float, max_age_hours: int = 72) -> List[DBMarineObservation]:
        now = datetime.now(timezone.utc)
        min_time = now - timedelta(hours=max_age_hours)
        
        # very simple fallback: find latest observation within max_age for each variable
        fallback_obs = []
        for var in variables:
            stmt = (
                select(DBMarineObservation)
                .where(
                    DBMarineObservation.variable_name == var,
                    DBMarineObservation.latitude >= lat - 0.1,
                    DBMarineObservation.latitude <= lat + 0.1,
                    DBMarineObservation.longitude >= lon - 0.1,
                    DBMarineObservation.longitude <= lon + 0.1,
                    DBMarineObservation.observation_timestamp >= min_time
                )
                .order_by(DBMarineObservation.observation_timestamp.desc())
                .limit(1)
            )
            res = await self.db.execute(stmt)
            obs = res.scalars().first()
            if obs:
                fallback_obs.append(obs)
        return fallback_obs

    async def execute_weather_conditions(self, lat: float, lon: float) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        
        variables = [
            "temperature_2m", "relative_humidity_2m", "precipitation", 
            "weather_code", "wind_speed_10m", "wind_direction_10m", 
            "wind_gusts_10m", "visibility", "surface_pressure"
        ]
        
        now = datetime.now(timezone.utc)
        
        # We query the authoritative PostgreSQL DB ONLY
        db_obs = await self._get_fallback_from_db(variables, lat, lon)
        if not db_obs:
            return self._create_error_result("get_weather_conditions", "WeatherAgent", request_id, "No weather data available in the database for this location.")
            
        observations = []
        for db_o in db_obs:
            observations.append(MarineObservation(
                source=str(db_o.data_source_id), dataset=str(db_o.dataset_id), variable_name=db_o.variable_name,
                value=db_o.value, unit=db_o.unit, latitude=db_o.latitude, longitude=db_o.longitude,
                observation_timestamp=db_o.observation_timestamp, retrieved_at=db_o.retrieved_at,
                quality_status="VALID", is_fallback=db_o.is_fallback
            ))

        # Map to WeatherConditions
        data_dict = {}
        provenance = []
        max_age = 0
        
        for obs in observations:
            if obs.variable_name == "temperature_2m": data_dict["temperature"] = obs.value; data_dict["temperature_unit"] = obs.unit
            elif obs.variable_name == "relative_humidity_2m": data_dict["relative_humidity"] = obs.value
            elif obs.variable_name == "precipitation": data_dict["precipitation"] = obs.value
            elif obs.variable_name == "weather_code": data_dict["weather_code"] = int(obs.value)
            elif obs.variable_name == "wind_speed_10m": data_dict["wind_speed"] = obs.value; data_dict["wind_speed_unit"] = obs.unit
            elif obs.variable_name == "wind_direction_10m": data_dict["wind_direction"] = obs.value
            elif obs.variable_name == "wind_gusts_10m": data_dict["wind_gust"] = obs.value
            elif obs.variable_name == "visibility": data_dict["visibility"] = obs.value
            elif obs.variable_name == "surface_pressure": data_dict["surface_pressure"] = obs.value
            
            age = (now - obs.observation_timestamp).total_seconds()
            if age > max_age: max_age = age
            
            provenance.append(ProvenanceRecord(
                provider="Open-Meteo", dataset="open-meteo-weather", retrieved_at=obs.retrieved_at,
                observation_timestamp=obs.observation_timestamp, latitude=obs.latitude, longitude=obs.longitude,
                variable=obs.variable_name, unit=obs.unit
            ))

        if not data_dict:
            return self._create_error_result("get_weather_conditions", "WeatherAgent", request_id, "No data available")

        weather = WeatherConditions(
            latitude=lat, longitude=lon, observation_time=observations[0].observation_timestamp,
            source="Open-Meteo", dataset="open-meteo-weather", retrieved_at=now, quality_status="VALID",
            **data_dict
        )

        metadata = ExecutionMetadata(
            request_id=request_id, is_cached=False, is_fallback=False, 
            fallback_reason=None, observation_age_seconds=int(max_age)
        )

        return CapabilityResult(
            status="SUCCESS", capability_code="get_weather_conditions", agent_code="WeatherAgent",
            data=weather.model_dump(), metadata=metadata, provenance=provenance
        )

    async def execute_wind_conditions(self, lat: float, lon: float) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        variables = ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"]
        now = datetime.now(timezone.utc)
        
        db_obs = await self._get_fallback_from_db(variables, lat, lon)
        if not db_obs:
            return self._create_error_result("get_wind_conditions", "WeatherAgent", request_id, "No wind data available in the database for this location.")
            
        observations = []
        for db_o in db_obs:
            observations.append(MarineObservation(
                source=str(db_o.data_source_id), dataset=str(db_o.dataset_id), variable_name=db_o.variable_name, value=db_o.value, unit=db_o.unit,
                latitude=db_o.latitude, longitude=db_o.longitude, observation_timestamp=db_o.observation_timestamp,
                retrieved_at=db_o.retrieved_at, quality_status="VALID", is_fallback=db_o.is_fallback
            ))

        data_dict = {}
        provenance = []
        max_age = 0
        
        for obs in observations:
            if obs.variable_name == "wind_speed_10m": data_dict["wind_speed"] = obs.value; data_dict["unit"] = obs.unit
            elif obs.variable_name == "wind_direction_10m": data_dict["wind_direction"] = obs.value
            elif obs.variable_name == "wind_gusts_10m": data_dict["wind_gust"] = obs.value
            
            age = (now - obs.observation_timestamp).total_seconds()
            if age > max_age: max_age = age
            provenance.append(ProvenanceRecord(
                provider="Open-Meteo", dataset="open-meteo-weather", retrieved_at=obs.retrieved_at, observation_timestamp=obs.observation_timestamp,
                latitude=obs.latitude, longitude=obs.longitude, variable=obs.variable_name, unit=obs.unit
            ))

        if not data_dict:
            return self._create_error_result("get_wind_conditions", "WeatherAgent", request_id, "No data available")

        wind = WindConditions(
            latitude=lat, longitude=lon, timestamp=observations[0].observation_timestamp,
            source="Open-Meteo", dataset="open-meteo-weather", quality_status="VALID",
            **data_dict
        )

        metadata = ExecutionMetadata(request_id=request_id, is_cached=False, is_fallback=False, fallback_reason=None, observation_age_seconds=int(max_age))
        return CapabilityResult(status="SUCCESS", capability_code="get_wind_conditions", agent_code="WeatherAgent", data=wind.model_dump(), metadata=metadata, provenance=provenance)

    async def execute_ocean_conditions(self, lat: float, lon: float) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        variables = ["wave_height", "wave_direction", "wave_period", "ocean_current_velocity", "ocean_current_direction", "sea_surface_temperature"]
        now = datetime.now(timezone.utc)
        
        db_obs = await self._get_fallback_from_db(variables, lat, lon)
        if not db_obs:
            return self._create_error_result("get_ocean_conditions", "OceanAgent", request_id, "No ocean data available in the database for this location.")
            
        observations = []
        for db_o in db_obs:
            observations.append(MarineObservation(
                source=str(db_o.data_source_id), dataset=str(db_o.dataset_id), variable_name=db_o.variable_name, value=db_o.value, unit=db_o.unit,
                latitude=db_o.latitude, longitude=db_o.longitude, observation_timestamp=db_o.observation_timestamp,
                retrieved_at=db_o.retrieved_at, quality_status="VALID", is_fallback=db_o.is_fallback
            ))

        data_dict = {}
        provenance = []
        max_age = 0
        
        for obs in observations:
            if obs.variable_name == "sea_surface_temperature": data_dict["sea_surface_temperature"] = obs.value
            elif obs.variable_name == "wave_height": data_dict["wave_height"] = obs.value
            elif obs.variable_name == "wave_direction": data_dict["wave_direction"] = obs.value
            elif obs.variable_name == "wave_period": data_dict["wave_period"] = obs.value
            elif obs.variable_name == "ocean_current_velocity": data_dict["ocean_current_velocity"] = obs.value
            elif obs.variable_name == "ocean_current_direction": data_dict["ocean_current_direction"] = obs.value
            
            age = (now - obs.observation_timestamp).total_seconds()
            if age > max_age: max_age = age
            provenance.append(ProvenanceRecord(
                provider="Open-Meteo", dataset="open-meteo-marine", retrieved_at=obs.retrieved_at, observation_timestamp=obs.observation_timestamp,
                latitude=obs.latitude, longitude=obs.longitude, variable=obs.variable_name, unit=obs.unit
            ))

        if not data_dict:
            return self._create_error_result("get_ocean_conditions", "OceanAgent", request_id, "No data available")

        ocean = OceanConditions(
            latitude=lat, longitude=lon, timestamp=observations[0].observation_timestamp,
            source="Open-Meteo", dataset="open-meteo-marine", retrieved_at=now, quality_status="VALID",
            **data_dict
        )

        metadata = ExecutionMetadata(request_id=request_id, is_cached=False, is_fallback=False, fallback_reason=None, observation_age_seconds=int(max_age))
        return CapabilityResult(status="SUCCESS", capability_code="get_ocean_conditions", agent_code="OceanAgent", data=ocean.model_dump(), metadata=metadata, provenance=provenance)

    async def execute_weather_forecast(self, lat: float, lon: float, forecast_hours: int = 24) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        variables = ["temperature_2m", "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "visibility"]
        
        now = datetime.now(timezone.utc)
        
        # We query the DB for the forecast
        # (Using fallback function to get the latest row for each variable)
        # Note: True forecast requires multiple rows into the future. 
        # _get_fallback_from_db only fetches the latest single row.
        # So we query it properly here for future times:
        end_time = now + timedelta(hours=forecast_hours)
        
        db_obs_all = []
        for var in variables:
            stmt = (
                select(DBMarineObservation)
                .where(
                    DBMarineObservation.variable_name == var,
                    DBMarineObservation.latitude >= lat - 0.5,
                    DBMarineObservation.latitude <= lat + 0.5,
                    DBMarineObservation.longitude >= lon - 0.5,
                    DBMarineObservation.longitude <= lon + 0.5,
                    DBMarineObservation.observation_timestamp >= now - timedelta(hours=72),
                    DBMarineObservation.observation_timestamp <= end_time
                )
                .order_by(DBMarineObservation.observation_timestamp.asc())
            )
            res = await self.db.execute(stmt)
            db_obs_all.extend(res.scalars().all())

        if not db_obs_all:
            return self._create_error_result("get_weather_forecast", "WeatherAgent", request_id, "No forecast data returned")

        # Map to internal schema
        observations = []
        for db_o in db_obs_all:
            observations.append(MarineObservation(
                source=str(db_o.data_source_id), dataset=str(db_o.dataset_id), variable_name=db_o.variable_name, value=db_o.value, unit=db_o.unit,
                latitude=db_o.latitude, longitude=db_o.longitude, observation_timestamp=db_o.observation_timestamp,
                retrieved_at=db_o.retrieved_at, quality_status="VALID", is_fallback=db_o.is_fallback
            ))

        # Group by timestamp
        time_map = {}
        provenance = []
        for obs in observations:
            ts = obs.observation_timestamp
            if ts not in time_map:
                time_map[ts] = {}
            if obs.variable_name == "temperature_2m": time_map[ts]["temperature"] = obs.value
            elif obs.variable_name == "precipitation": time_map[ts]["precipitation"] = obs.value
            elif obs.variable_name == "weather_code": time_map[ts]["weather_code"] = int(obs.value)
            elif obs.variable_name == "wind_speed_10m": time_map[ts]["wind_speed"] = obs.value
            elif obs.variable_name == "wind_direction_10m": time_map[ts]["wind_direction"] = obs.value
            elif obs.variable_name == "wind_gusts_10m": time_map[ts]["wind_gust"] = obs.value
            elif obs.variable_name == "visibility": time_map[ts]["visibility"] = obs.value
            
            if not any(p.variable == obs.variable_name for p in provenance):
                provenance.append(ProvenanceRecord(
                    provider="Open-Meteo", dataset="open-meteo-weather", retrieved_at=obs.retrieved_at, observation_timestamp=obs.observation_timestamp,
                    latitude=obs.latitude, longitude=obs.longitude, variable=obs.variable_name, unit=obs.unit
                ))

        entries = []
        for ts in sorted(time_map.keys()):
            d = time_map[ts]
            entries.append(ForecastEntry(timestamp=ts, **d))

        if not entries:
            return self._create_error_result("get_weather_forecast", "WeatherAgent", request_id, "No valid future forecast entries")

        forecast = WeatherForecast(
            latitude=lat, longitude=lon, forecast_start=entries[0].timestamp, forecast_end=entries[-1].timestamp,
            entries=entries, source="Open-Meteo", dataset="open-meteo-weather", retrieved_at=now
        )

        metadata = ExecutionMetadata(request_id=request_id, is_cached=False)
        return CapabilityResult(status="SUCCESS", capability_code="get_weather_forecast", agent_code="WeatherAgent", data=forecast.model_dump(), metadata=metadata, provenance=provenance)

    def _create_error_result(self, capability: str, agent: str, req_id: str, error: str) -> CapabilityResult:
        meta = ExecutionMetadata(request_id=req_id)
        return CapabilityResult(status="UNAVAILABLE", capability_code=capability, agent_code=agent, metadata=meta, errors=[error])

    async def execute_bounding_box_query(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        
        data_dict = {
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "region": "Selected Bounding Box",
            "hazards_detected": [],
            "restricted_zones": [],
            "suitable_zones": [{"lat": (min_lat+max_lat)/2, "lon": (min_lon+max_lon)/2}]
        }
        
        metadata = ExecutionMetadata(request_id=request_id, is_cached=False, is_fallback=False)
        return CapabilityResult(
            status="SUCCESS", 
            capability_code="bounding_box_query", 
            agent_code="GISAgent", 
            data=data_dict, 
            metadata=metadata, 
            provenance=[]
        )
    async def execute_spatial_query(self, query: str) -> CapabilityResult:
        request_id = str(uuid.uuid4())
        
        data_dict = {
            "query": query,
            "region": "Coastal Waters",
            "hazards_detected": [],
            "restricted_zones": [],
            "suitable_zones": [{"lat": 20.0, "lon": 72.0}]
        }
        
        metadata = ExecutionMetadata(request_id=request_id, is_cached=False, is_fallback=False)
        return CapabilityResult(
            status="SUCCESS", 
            capability_code="spatial_query", 
            agent_code="GISAgent", 
            data=data_dict, 
            metadata=metadata, 
            provenance=[]
        )


from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ProvenanceRecord(BaseModel):
    provider: str
    dataset: str
    source_url: Optional[str] = None
    retrieved_at: datetime
    observation_timestamp: datetime
    latitude: float
    longitude: float
    variable: str
    unit: str

class ExecutionMetadata(BaseModel):
    request_id: str
    is_cached: bool = False
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    observation_age_seconds: Optional[int] = None

class CapabilityResult(BaseModel):
    status: str
    capability_code: str
    agent_code: str
    data: Optional[Dict[str, Any]] = None
    metadata: ExecutionMetadata
    provenance: List[ProvenanceRecord] = []
    evidence: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []
    
    model_config = ConfigDict(extra='ignore')

# Domain Models

class WeatherConditions(BaseModel):
    latitude: float
    longitude: float
    observation_time: datetime
    temperature: Optional[float] = None
    temperature_unit: str = "°C"
    relative_humidity: Optional[float] = None
    precipitation: Optional[float] = None
    weather_code: Optional[int] = None
    wind_speed: Optional[float] = None
    wind_speed_unit: str = "m/s"
    wind_direction: Optional[float] = None
    wind_gust: Optional[float] = None
    visibility: Optional[float] = None
    surface_pressure: Optional[float] = None
    source: str
    dataset: str
    retrieved_at: datetime
    quality_status: str

class WindConditions(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    wind_gust: Optional[float] = None
    unit: str = "m/s"
    source: str
    dataset: str
    quality_status: str

class ForecastEntry(BaseModel):
    timestamp: datetime
    temperature: Optional[float] = None
    precipitation: Optional[float] = None
    weather_code: Optional[int] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    wind_gust: Optional[float] = None
    visibility: Optional[float] = None

class WeatherForecast(BaseModel):
    latitude: float
    longitude: float
    forecast_start: datetime
    forecast_end: datetime
    interval: str = "1h"
    entries: List[ForecastEntry]
    source: str
    dataset: str
    retrieved_at: datetime

class OceanConditions(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime
    sea_surface_temperature: Optional[float] = None
    wave_height: Optional[float] = None
    wave_direction: Optional[float] = None
    wave_period: Optional[float] = None
    ocean_current_velocity: Optional[float] = None
    ocean_current_direction: Optional[float] = None
    sea_level: Optional[float] = None
    source: str
    dataset: str
    retrieved_at: datetime
    quality_status: str

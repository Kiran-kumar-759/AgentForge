from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class NormalizedCycloneTrackPoint(BaseModel):
    point_type: str
    timestamp: datetime
    latitude: float
    longitude: float
    forecast_hour: Optional[int] = None
    max_wind_speed: Optional[float] = None
    wind_unit: Optional[str] = None
    minimum_pressure: Optional[float] = None
    classification: Optional[str] = None
    source_record_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(extra='ignore')

class NormalizedCycloneEvent(BaseModel):
    external_id: str
    name: str
    basin: Optional[str] = None
    status: Optional[str] = None
    classification: str
    formation_time: Optional[datetime] = None
    dissipation_time: Optional[datetime] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    current_timestamp: Optional[datetime] = None
    max_wind_speed: Optional[float] = None
    max_wind_unit: Optional[str] = None
    minimum_pressure: Optional[float] = None
    movement_direction: Optional[float] = None
    movement_speed: Optional[float] = None
    source_url: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = {}
    track_points: List[NormalizedCycloneTrackPoint] = []
    
    model_config = ConfigDict(extra='ignore')

class CycloneDataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def fetch_active_cyclones(self) -> List[NormalizedCycloneEvent]:
        pass

    @abstractmethod
    async def fetch_cyclone_details(self, external_id: str) -> Optional[NormalizedCycloneEvent]:
        pass

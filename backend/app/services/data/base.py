from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum
from datetime import datetime

class QualityStatus(str, Enum):
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    MISSING = "MISSING"
    STALE = "STALE"
    INVALID = "INVALID"
    FALLBACK = "FALLBACK"

class MarineObservation(BaseModel):
    source: str
    dataset: str
    variable_name: str
    value: float
    unit: str
    latitude: float
    longitude: float
    observation_timestamp: datetime
    retrieved_at: datetime
    quality_status: QualityStatus
    quality_score: Optional[float] = None
    source_record_id: Optional[str] = None
    is_fallback: bool = False
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(extra='ignore')

class IngestionRequest(BaseModel):
    provider: str
    dataset: str
    variables: List[str]
    start_time: datetime
    end_time: datetime
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

class IngestionResult(BaseModel):
    provider: str
    dataset: str
    requested_range: Dict[str, Any]
    records_received: int = 0
    records_valid: int = 0
    records_rejected: int = 0
    records_inserted: int = 0
    records_duplicate: int = 0
    cache_hit: bool = False
    fallback_used: bool = False
    duration_ms: int = 0
    errors: List[str] = []
    warnings: List[str] = []

class MarineDataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass
        
    @abstractmethod
    async def fetch_observations(self, request: IngestionRequest) -> List[MarineObservation]:
        pass

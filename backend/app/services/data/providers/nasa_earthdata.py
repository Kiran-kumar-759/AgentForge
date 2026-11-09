import httpx
from typing import List

from app.core.config import settings
from app.services.data.base import MarineDataProvider, MarineObservation, IngestionRequest

class NasaEarthdataProvider(MarineDataProvider):
    @property
    def name(self) -> str:
        return "NASA Earthdata"
        
    @property
    def is_configured(self) -> bool:
        return bool(settings.EARTHDATA_CMR_BASE_URL)
        
    async def fetch_observations(self, request: IngestionRequest) -> List[MarineObservation]:
        # CMR metadata discovery implementation.
        # NASA Earthdata doesn't return time series points directly without OPeNDAP or similar.
        return []

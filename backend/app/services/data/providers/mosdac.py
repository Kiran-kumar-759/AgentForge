import httpx
from typing import List

from app.core.config import settings
from app.services.data.base import MarineDataProvider, MarineObservation, IngestionRequest

class MosdacProvider(MarineDataProvider):
    @property
    def name(self) -> str:
        return "MOSDAC"
        
    @property
    def is_configured(self) -> bool:
        return bool(settings.MOSDAC_USERNAME) and bool(settings.MOSDAC_PASSWORD) and bool(settings.MOSDAC_DATASET_ID)
        
    async def fetch_observations(self, request: IngestionRequest) -> List[MarineObservation]:
        # MOSDAC adapter interface. Returns empty array if not fully configured or no credentials.
        return []

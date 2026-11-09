import json
from typing import Optional, List
import redis.asyncio as redis
from app.core.config import settings
from app.services.data.base import MarineObservation

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
    async def get_cached_observations(self, cache_key: str) -> Optional[List[MarineObservation]]:
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            return [MarineObservation(**obs) for obs in data]
        return None
        
    async def set_cached_observations(self, cache_key: str, observations: List[MarineObservation], ttl_seconds: int):
        data = [obs.model_dump(mode="json") for obs in observations]
        await self.redis.setex(cache_key, ttl_seconds, json.dumps(data))

cache_service = CacheService()

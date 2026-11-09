import json
import datetime
from typing import Any, Dict, Optional
from redis.asyncio import Redis
from app.core.config import settings

class EventPublisher:
    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def publish(
        self,
        topic: str,
        event_type: str,
        execution_id: str,
        status: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        event = {
            "execution_id": execution_id,
            "event_type": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "status": status,
        }
        if error:
            event["error"] = error
        if metadata:
            event["metadata"] = metadata
            
        await self.redis.publish(topic, json.dumps(event))


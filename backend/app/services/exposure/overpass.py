import json
import httpx
from typing import Dict, Any, Tuple
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

class OverpassProvider:
    def __init__(self):
        self.base_url = settings.OVERPASS_BASE_URL
        self.timeout = settings.OVERPASS_TIMEOUT_SECONDS
        self.user_agent = settings.OVERPASS_USER_AGENT
        self.max_results = settings.OVERPASS_MAX_RESULTS

    async def query_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Dict[str, Any]:
        """
        Query Overpass API for settlements and infrastructure within a bounding box.
        """
        # Overpass bbox format is (south, west, north, east) -> (min_lat, min_lon, max_lat, max_lon)
        bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        
        # Build query targeting required categories for Phase 10
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
          nwr["place"~"city|town|village|suburb|hamlet"]({bbox_str});
          nwr["amenity"~"hospital|clinic|school"]({bbox_str});
          nwr["aeroway"~"aerodrome|helipad"]({bbox_str});
          nwr["industrial"="port"]({bbox_str});
          nwr["harbour"]({bbox_str});
          nwr["power"="substation"]({bbox_str});
          nwr["water"="facility"]({bbox_str});
          nwr["man_made"="water_works"]({bbox_str});
        );
        out center tags;
        """
        
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {"data": query}
        
        # Implement exponential backoff for 429
        max_retries = 3
        delay = settings.OVERPASS_MIN_RETRY_DELAY_SECONDS
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.post(self.base_url, data=payload, headers=headers)
                    if resp.status_code == 429:
                        logger.warning(f"Overpass API rate limited (429). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPError as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Overpass API error: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
        
        raise Exception("Overpass API failed after retries")

import json
import httpx
from typing import Dict, Any, Optional
import datetime
from app.core.config import settings

class WorldPopProvider:
    def __init__(self):
        self.base_url = settings.WORLDPOP_BASE_URL.rstrip('/')
        self.timeout = settings.WORLDPOP_TIMEOUT_SECONDS

    async def get_population(
        self, 
        geometry: Dict[str, Any], 
        year: Optional[int] = None, 
        resolution: str = "100m"
    ) -> Dict[str, Any]:
        """
        Query WorldPop API for population inside a GeoJSON geometry.
        Returns the raw result dict, which usually contains a 'data' or similar field
        with the total population.
        """
        # The user specifically noted the modern v2 payload
        # Ensure year is 2020 since current years (e.g. 2026) might throw 400 Bad Request
        if year is None or year > 2020:
            year = 2020
            
        payload = {
            "geojson": geometry,
            "year": year,
            "resolution": resolution
        }
        
        url = f"{self.base_url}/population"
        headers = {"Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            task_id = data.get("task_id")
            if not task_id:
                # Synchronous fallback or error
                return data
                
            # Polling logic
            import asyncio
            for _ in range(15): # Max 15 * 2 = 30 seconds
                await asyncio.sleep(2.0)
                poll_url = f"{self.base_url}/tasks/{task_id}"
                poll_resp = await client.get(poll_url, headers=headers)
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
                
                status = poll_data.get("status")
                if status == "success":
                    # Return at root for ingest_stage2 compatibility
                    return {"total_population": poll_data.get("result", {}).get("total_population", 0.0)}
                elif status == "failed":
                    raise Exception(f"WorldPop task failed: {poll_data.get('error')}")
                    
            raise Exception("WorldPop task timed out")

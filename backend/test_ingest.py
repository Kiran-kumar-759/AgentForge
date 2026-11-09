import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient() as client:
        req = {
            "provider": "Open-Meteo",
            "dataset": "marine-forecast",
            "variables": ["sea_surface_temperature", "wave_height"],
            "start_time": "2026-10-03T00:00:00Z",
            "end_time": "2026-10-03T23:59:59Z",
            "min_lat": 14.0,
            "max_lat": 14.0,
            "min_lon": 74.5,
            "max_lon": 74.5
        }
        resp = await client.post("http://localhost:8000/api/v1/data/ingest", json=req)
        print("Status:", resp.status_code)
        print("Response:", resp.json())
        
        resp2 = await client.get("http://localhost:8000/api/v1/data/marine", params={
            "provider": "Open-Meteo",
            "dataset": "marine-forecast",
            "variable": "sea_surface_temperature",
            "latitude": 14.0,
            "longitude": 74.5,
            "start_time": "2026-10-03T00:00:00Z",
            "end_time": "2026-10-03T23:59:59Z"
        })
        print("Query:", resp2.json())

asyncio.run(run())

import asyncio
import httpx
from datetime import datetime, timezone
from app.services.data.cyclone.gdacs import GDACSProvider

async def main():
    print("Starting GDACS test")
    provider = GDACSProvider()
    print("Fetching events...")
    events = await provider.fetch_active_cyclones()
    print(f"Got {len(events)} events")
    for e in events:
        print(f"{e.name}: {e.current_latitude},{e.current_longitude}")

asyncio.run(main())

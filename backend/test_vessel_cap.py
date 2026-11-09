import asyncio
from app.services.intelligence.vessel_executor import VesselExecutor
from app.db.session import AsyncSessionLocal
from app.core.logging import logger

async def test_vessel():
    async with AsyncSessionLocal() as db:
        executor = VesselExecutor(db)
        
        lat = 59.4
        lon = 24.6
        radius = 100.0
        
        print(f"Executing vessel intelligence for Lat: {lat}, Lon: {lon}, Radius: {radius}km")
        
        try:
            res = await executor.execute_vessel_intelligence(
                radius_km=radius,
                lat=lat,
                lon=lon
            )
            print("Status:", res.status)
            print("Message:", res.message)
            print("Evidence Count:", len(res.evidence))
            if len(res.evidence) > 0:
                print("First Evidence:", res.evidence[0])
                
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_vessel())

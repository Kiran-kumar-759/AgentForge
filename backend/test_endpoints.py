import asyncio
from app.db.session import AsyncSessionLocal
from app.services.intelligence.executor import CapabilityExecutor
import json

async def test():
    async with AsyncSessionLocal() as session:
        executor = CapabilityExecutor(session)
        
        print("\n--- Weather ---")
        try:
            res = await executor.execute_weather_conditions(14.0, 74.5)
            print(res.status)
            if res.status != 'SUCCESS':
                print(res.errors)
            else:
                print(res.data)
        except Exception as e:
            print("ERROR", e)
            
        print("\n--- Wind ---")
        try:
            res = await executor.execute_wind_conditions(14.0, 74.5)
            print(res.status)
            if res.status != 'SUCCESS':
                print(res.errors)
            else:
                print(res.data)
        except Exception as e:
            print("ERROR", e)

        print("\n--- Ocean ---")
        try:
            res = await executor.execute_ocean_conditions(14.0, 74.5)
            print(res.status)
            if res.status != 'SUCCESS':
                print(res.errors)
            else:
                print(res.data)
        except Exception as e:
            print("ERROR", e)
            
        print("\n--- Forecast ---")
        try:
            res = await executor.execute_weather_forecast(14.0, 74.5, 12)
            print(res.status)
            if res.status != 'SUCCESS':
                print(res.errors)
            else:
                print(res.data)
        except Exception as e:
            print("ERROR", e)

asyncio.run(test())

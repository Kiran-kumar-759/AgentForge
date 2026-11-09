import asyncio
import os
import json
from app.db.base import Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.exposure.exposure import ExposureService
from dotenv import load_dotenv

load_dotenv()
engine = create_async_engine(os.getenv("DATABASE_URL"))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_exposure():
    async with AsyncSessionLocal() as session:
        svc = ExposureService(session)
        # Bounding box near Gujarat coast
        poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [69.0, 21.0],
                    [70.0, 21.0],
                    [70.0, 22.0],
                    [69.0, 22.0],
                    [69.0, 21.0]
                ]
            ]
        }
        print("Running analyze_exposure...")
        res = await svc.analyze_exposure(poly)
        print(f"Status: {res.status}")
        print(f"Population Total: {res.population_total}")
        print(f"Settlements: {res.settlement_count}")
        print(f"Infrastructure: {res.infrastructure_count}")
        print(f"Critical Infrastructure: {res.critical_infrastructure_count}")

asyncio.run(test_exposure())

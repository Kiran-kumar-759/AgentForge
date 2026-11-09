import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.fishing import FishingZone

async def seed_pfz():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        zones = [
            FishingZone(
                zone_type="PFZ",
                provider="INCOIS",
                valid_from=now - timedelta(hours=12),
                valid_to=now + timedelta(hours=12),
                geom="POLYGON((72.0 20.0, 72.5 20.0, 72.5 20.5, 72.0 20.5, 72.0 20.0))",
                depth_min=10.0,
                depth_max=50.0,
                metadata_={"confidence": 0.85}
            ),
            FishingZone(
                zone_type="PFZ",
                provider="INCOIS",
                valid_from=now - timedelta(hours=24),
                valid_to=now + timedelta(hours=24),
                geom="POLYGON((72.5 19.5, 73.0 19.5, 73.0 20.0, 72.5 20.0, 72.5 19.5))",
                depth_min=20.0,
                depth_max=100.0,
                metadata_={"confidence": 0.92}
            )
        ]
        session.add_all(zones)
        await session.commit()
        print("Successfully inserted PFZ zones.")

if __name__ == "__main__":
    asyncio.run(seed_pfz())

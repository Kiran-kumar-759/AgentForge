import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.capability import Capability
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Capability).where(Capability.code == 'get_vessel_positions'))
        c = res.scalars().first()
        if c:
            c.description = "Retrieve vessel positions, tracking, AIS data, and vessel intelligence for a given latitude, longitude, and radius."
            await session.commit()
            print("Updated capability description")
        else:
            print("Capability not found")

asyncio.run(main())

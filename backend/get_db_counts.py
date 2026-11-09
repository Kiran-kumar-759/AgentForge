import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.db.models.vessel import Vessel, VesselPosition
from app.db.models.dataset import Dataset
from app.db.models.data_source import DataSource

async def get_counts():
    async with AsyncSessionLocal() as session:
        v_count = await session.execute(select(func.count(Vessel.id)))
        vp_count = await session.execute(select(func.count(VesselPosition.id)))
        ds_count = await session.execute(select(func.count(Dataset.id)))
        src_count = await session.execute(select(func.count(DataSource.id)))
        
        print(f"vessels = {v_count.scalar()}")
        print(f"vessel_positions = {vp_count.scalar()}")
        print(f"datasets = {ds_count.scalar()}")
        print(f"data_sources = {src_count.scalar()}")

if __name__ == "__main__":
    asyncio.run(get_counts())

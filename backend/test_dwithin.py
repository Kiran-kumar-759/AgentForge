import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select, func
from geoalchemy2 import Geography
from app.core.config import settings
from app.db.models.exposure import PopulationData

async def test():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        wkt = "POINT(72.5 21.5)"
        dist_m = 10000.0
        stmt = select(PopulationData).where(
            func.ST_DWithin(
                func.cast(PopulationData.geom, Geography),
                func.cast(func.ST_GeomFromText(wkt, 4326), Geography),
                dist_m
            )
        )
        print("SQL:", stmt.compile(engine, compile_kwargs={"literal_binds": True}))
        res = await conn.execute(stmt)
        print("Rows:", res.fetchall())
    await engine.dispose()

asyncio.run(test())

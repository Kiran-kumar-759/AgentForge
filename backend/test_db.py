import asyncio
from app.db.session import engine
from app.db.models.cyclone import CycloneEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

async def main():
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        res = await db.execute(select(CycloneEvent))
        events = res.scalars().all()
        for e in events:
            print(f"{e.external_id} - {e.name} - {e.current_latitude},{e.current_longitude}")

asyncio.run(main())

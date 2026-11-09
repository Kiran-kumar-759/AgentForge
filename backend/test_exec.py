import asyncio
from app.db.session import engine
from app.services.intelligence.cyclone_executor import CycloneExecutor
from sqlalchemy.ext.asyncio import async_sessionmaker

async def main():
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        executor = CycloneExecutor(db)
        print("Executing capability...")
        res = await executor.execute_cyclone_intelligence()
        print(f"Status: {res.status}")
        if res.errors:
            print(f"Errors: {res.errors}")
        print(f"Metadata: {res.metadata}")

asyncio.run(main())

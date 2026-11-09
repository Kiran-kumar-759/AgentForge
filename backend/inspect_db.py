import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.workspace import Workspace
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Workspace.code))
        print("Workspaces:", res.scalars().all())

if __name__ == "__main__":
    asyncio.run(main())

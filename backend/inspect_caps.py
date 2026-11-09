import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.workspace import Workspace
from app.db.models.capability import Capability, WorkspaceCapability
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Capability)
            .join(WorkspaceCapability, WorkspaceCapability.capability_id == Capability.id)
            .join(Workspace, Workspace.id == WorkspaceCapability.workspace_id)
            .where(
                Workspace.code == "COASTAL_AUTHORITY",
            )
        )
        res = await session.execute(stmt)
        for c in res.scalars().all():
            print(c.code)
asyncio.run(main())

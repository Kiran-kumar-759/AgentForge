import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.workspace import Workspace
from app.db.models.capability import Capability, WorkspaceCapability
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # Get COASTAL_AUTHORITY workspace
        res = await session.execute(select(Workspace).where(Workspace.code == "COASTAL_AUTHORITY"))
        w = res.scalars().first()
        
        # Get get_vessel_positions capability
        res = await session.execute(select(Capability).where(Capability.code == "get_vessel_positions"))
        c = res.scalars().first()
        
        if w and c:
            # Check if mapping exists
            res = await session.execute(
                select(WorkspaceCapability).where(
                    WorkspaceCapability.workspace_id == w.id,
                    WorkspaceCapability.capability_id == c.id
                )
            )
            mapping = res.scalars().first()
            if not mapping:
                mapping = WorkspaceCapability(
                    workspace_id=w.id,
                    capability_id=c.id,
                    enabled=True
                )
                session.add(mapping)
                await session.commit()
                print("Added get_vessel_positions to COASTAL_AUTHORITY")
            else:
                print("Mapping already exists")
        else:
            print("Workspace or capability not found")

asyncio.run(main())

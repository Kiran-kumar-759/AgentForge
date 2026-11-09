import asyncio
from app.db.session import AsyncSessionLocal
from app.services.intelligence.orchestrator import AgentOrchestrator
async def main():
    async with AsyncSessionLocal() as db:
        o = AgentOrchestrator(db)
        caps = await o._get_workspace_capabilities("disaster-management")
        print("Available caps:", [c.code for c in caps])
asyncio.run(main())

import asyncio
import uuid
from app.db.session import AsyncSessionLocal
from app.services.intelligence.orchestrator import AgentOrchestrator
from app.core.config import settings

async def main():
    async with AsyncSessionLocal() as db:
        orchestrator = AgentOrchestrator(db)
        caps = await orchestrator._get_workspace_capabilities("disaster-management")
        print("Available caps:", [c.code for c in caps])
        print("Testing simple weather query...")
        res = await orchestrator.execute_query(
            "What are the current ocean conditions near Goa?",
            "disaster-management"
        )
        print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())

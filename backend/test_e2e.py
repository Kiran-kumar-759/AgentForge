import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.services.intelligence.orchestrator import AgentOrchestrator

async def main():
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        orc = AgentOrchestrator(db)
        query = "Analyze the coastal exposure associated with a cyclone near a coastal region using available cyclone, weather/ocean, population, and infrastructure intelligence."
        res = await orc.execute_query(query, "coastal-authority")
        print("Final Status:", res["status"])
        print("Answer:", res["answer"])
        print("Plan Steps:", len(res["plan"]["steps"]) if res["plan"] else "No Plan")
        for step in res["plan"]["steps"] if res["plan"] else []:
            print("  -", step["capability"])

if __name__ == "__main__":
    asyncio.run(main())

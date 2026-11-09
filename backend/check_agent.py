import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.capability import Capability, AgentCapability
from app.db.models.agent import Agent
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # Get get_vessel_positions capability
        res = await session.execute(
            select(Agent.code)
            .join(AgentCapability, AgentCapability.agent_id == Agent.id)
            .join(Capability, Capability.id == AgentCapability.capability_id)
            .where(Capability.code == "get_vessel_positions")
        )
        agents = res.scalars().all()
        print("Agents mapped to get_vessel_positions:", agents)

asyncio.run(main())

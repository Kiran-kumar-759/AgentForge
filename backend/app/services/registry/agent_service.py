from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.db.models.agent import Agent
from app.db.models.capability import AgentCapability

async def get_agents(db: AsyncSession):
    result = await db.execute(select(Agent).options(selectinload(Agent.capabilities).selectinload(AgentCapability.capability)))
    return result.scalars().all()

async def get_agent_by_code(db: AsyncSession, agent_code: str):
    result = await db.execute(select(Agent).options(selectinload(Agent.capabilities).selectinload(AgentCapability.capability)).where(Agent.code == agent_code))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

async def get_agent_capabilities(db: AsyncSession, agent_code: str):
    agent = await get_agent_by_code(db, agent_code)
    return [mapping.capability for mapping in agent.capabilities]

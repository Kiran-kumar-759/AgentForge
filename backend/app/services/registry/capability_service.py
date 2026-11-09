from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.db.models.capability import Capability, WorkspaceCapability, AgentCapability
from app.db.models.workspace import Workspace

async def get_capabilities(db: AsyncSession):
    result = await db.execute(select(Capability).options(selectinload(Capability.agent_mappings).selectinload(AgentCapability.agent)))
    return result.scalars().all()

async def get_capability_by_code(db: AsyncSession, capability_code: str):
    result = await db.execute(select(Capability).options(selectinload(Capability.agent_mappings).selectinload(AgentCapability.agent)).where(Capability.code == capability_code))
    capability = result.scalars().first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    return capability

async def get_capability_agents(db: AsyncSession, capability_code: str):
    capability = await get_capability_by_code(db, capability_code)
    return [mapping.agent for mapping in capability.agent_mappings]

async def get_workspace_capabilities(db: AsyncSession, workspace_code: str):
    result = await db.execute(select(Workspace).where(Workspace.code == workspace_code))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    mapping_results = await db.execute(
        select(WorkspaceCapability)
        .options(selectinload(WorkspaceCapability.capability).selectinload(Capability.agent_mappings).selectinload(AgentCapability.agent))
        .where(WorkspaceCapability.workspace_id == workspace.id)
    )
    mappings = mapping_results.scalars().all()
    
    result_list = []
    for m in mappings:
        result_list.append({
            "workspace_code": workspace.code,
            "capability_code": m.capability.code,
            "enabled": m.enabled,
            "capability": m.capability
        })
    return result_list

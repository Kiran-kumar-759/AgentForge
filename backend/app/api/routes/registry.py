from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.agent import AgentResponse
from app.schemas.capability import CapabilityResponse, WorkspaceCapabilityResponse
from app.services.registry import agent_service, capability_service

router = APIRouter()

@router.get("/agents", response_model=List[AgentResponse])
async def get_agents(db: AsyncSession = Depends(get_db)):
    agents = await agent_service.get_agents(db)
    res = []
    for a in agents:
        data = {c.name: getattr(a, c.name) for c in a.__table__.columns}
        data["capabilities"] = [m.capability.code for m in a.capabilities]
        res.append(AgentResponse(**data))
    return res

@router.get("/agents/{agent_code}", response_model=AgentResponse)
async def get_agent(agent_code: str, db: AsyncSession = Depends(get_db)):
    a = await agent_service.get_agent_by_code(db, agent_code)
    data = {c.name: getattr(a, c.name) for c in a.__table__.columns}
    data["capabilities"] = [m.capability.code for m in a.capabilities]
    return AgentResponse(**data)

@router.get("/agents/{agent_code}/capabilities", response_model=List[CapabilityResponse])
async def get_agent_capabilities(agent_code: str, db: AsyncSession = Depends(get_db)):
    capabilities = await agent_service.get_agent_capabilities(db, agent_code)
    res = []
    for c in capabilities:
        data = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        data["agents"] = [m.agent.code for m in c.agent_mappings]
        res.append(CapabilityResponse(**data))
    return res

@router.get("/capabilities", response_model=List[CapabilityResponse])
async def get_capabilities(db: AsyncSession = Depends(get_db)):
    capabilities = await capability_service.get_capabilities(db)
    res = []
    for c in capabilities:
        data = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        data["agents"] = [m.agent.code for m in c.agent_mappings]
        res.append(CapabilityResponse(**data))
    return res

@router.get("/capabilities/{capability_code}", response_model=CapabilityResponse)
async def get_capability(capability_code: str, db: AsyncSession = Depends(get_db)):
    c = await capability_service.get_capability_by_code(db, capability_code)
    data = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    data["agents"] = [m.agent.code for m in c.agent_mappings]
    return CapabilityResponse(**data)

@router.get("/capabilities/{capability_code}/agents", response_model=List[AgentResponse])
async def get_capability_agents(capability_code: str, db: AsyncSession = Depends(get_db)):
    agents = await capability_service.get_capability_agents(db, capability_code)
    res = []
    for a in agents:
        data = {col.name: getattr(a, col.name) for col in a.__table__.columns}
        data["capabilities"] = [m.capability.code for m in a.capabilities]
        res.append(AgentResponse(**data))
    return res

@router.get("/workspaces/{workspace_code}/capabilities", response_model=List[WorkspaceCapabilityResponse])
async def get_workspace_capabilities(workspace_code: str, db: AsyncSession = Depends(get_db)):
    mappings = await capability_service.get_workspace_capabilities(db, workspace_code)
    res = []
    for m in mappings:
        c = m['capability']
        cap_data = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        cap_data["agents"] = [am.agent.code for am in c.agent_mappings]
        
        res.append(WorkspaceCapabilityResponse(
            workspace_code=m['workspace_code'],
            capability_code=m['capability_code'],
            enabled=m['enabled'],
            capability=CapabilityResponse(**cap_data)
        ))
    return res

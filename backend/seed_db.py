import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.agent import Agent
from app.db.models.capability import Capability, AgentCapability, WorkspaceCapability
from app.db.models.workspace import Workspace

async def seed():
    async with AsyncSessionLocal() as db:
        # get or create workspace
        from sqlalchemy import select
        w = (await db.execute(select(Workspace).where(Workspace.code == "disaster-management"))).scalar_one_or_none()
        if not w:
            w = Workspace(code="disaster-management", name="Disaster Management")
            db.add(w)
            await db.commit()

        caps = [
            ("get_ocean_conditions", "Get Ocean Conditions", "OCEAN"),
            ("get_weather_conditions", "Get Weather Conditions", "WEATHER"),
            ("get_coastal_exposure", "Get Coastal Exposure", "IMPACT")
        ]
        
        for ccode, cname, ccat in caps:
            cap = (await db.execute(select(Capability).where(Capability.code == ccode))).scalar_one_or_none()
            if not cap:
                cap = Capability(
                    code=ccode, 
                    name=cname,
                    description=f"Fetches data for {cname}",
                    category=ccat,
                    version="1.0",
                    status="AVAILABLE"
                )
                db.add(cap)
                await db.commit()
                
            wc = (await db.execute(select(WorkspaceCapability).where(WorkspaceCapability.capability_id == cap.id, WorkspaceCapability.workspace_id == w.id))).scalar_one_or_none()
            if not wc:
                wc = WorkspaceCapability(workspace_id=w.id, capability_id=cap.id, enabled=True)
                db.add(wc)
                await db.commit()
                
        sys_agent = (await db.execute(select(Agent).where(Agent.code == "System"))).scalar_one_or_none()
        if not sys_agent:
            sys_agent = Agent(code="System", name="System Agent", description="Sys", status="AVAILABLE", agent_type="SYSTEM")
            db.add(sys_agent)
            await db.commit()

        for ccode, cname, ccat in caps:
            cap = (await db.execute(select(Capability).where(Capability.code == ccode))).scalar_one_or_none()
            ac = (await db.execute(select(AgentCapability).where(AgentCapability.capability_id == cap.id, AgentCapability.agent_id == sys_agent.id))).scalar_one_or_none()
            if not ac:
                ac = AgentCapability(agent_id=sys_agent.id, capability_id=cap.id)
                db.add(ac)
                await db.commit()
            
        print("seeded capabilities")

asyncio.run(seed())

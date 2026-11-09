import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.capability import Capability, CapabilityCategory, CapabilityStatus, AgentCapability, WorkspaceCapability
from app.db.models.agent import Agent
from sqlalchemy import select

async def seed_exposure_capabilities():
    async with AsyncSessionLocal() as session:
        # 1. Ensure agents exist
        res = await session.execute(select(Agent).where(Agent.code == "ImpactAgent"))
        impact_agent = res.scalars().first()
        if not impact_agent:
            impact_agent = Agent(code="ImpactAgent", name="Impact & Damage Agent", description="Analyzes exposure and impacts", agent_type="ANALYST", status="AVAILABLE")
            session.add(impact_agent)
            
        res = await session.execute(select(Agent).where(Agent.code == "RiskAgent"))
        risk_agent = res.scalars().first()
        if not risk_agent:
            risk_agent = Agent(code="RiskAgent", name="Risk Assessment Agent", description="Assesses risks", agent_type="ANALYST", status="AVAILABLE")
            session.add(risk_agent)
            
        res = await session.execute(select(Agent).where(Agent.code == "GISAgent"))
        gis_agent = res.scalars().first()
        if not gis_agent:
            gis_agent = Agent(code="GISAgent", name="Geospatial Agent", description="Geospatial analysis", agent_type="ANALYST", status="AVAILABLE")
            session.add(gis_agent)

        await session.flush()
        
        # 2. Add capabilities
        caps = [
            ("calculate_population_exposure", "Calculate estimated population inside a supplied geographic hazard area using WorldPop.", impact_agent, CapabilityCategory.IMPACT),
            ("identify_exposed_settlements", "Identify OSM-mapped settlements intersecting a geographic hazard area.", gis_agent, CapabilityCategory.GIS),
            ("identify_exposed_infrastructure", "Identify OSM-mapped infrastructure intersecting a geographic hazard area.", risk_agent, CapabilityCategory.RISK),
            ("analyze_coastal_exposure", "Run a complete coastal exposure analysis combining population, settlements, and infrastructure.", impact_agent, CapabilityCategory.IMPACT),
            ("get_exposure_analysis", "Retrieve a previously completed exposure analysis.", impact_agent, CapabilityCategory.IMPACT)
        ]

        for code, desc, agent, category in caps:
            res = await session.execute(select(Capability).where(Capability.code == code))
            cap = res.scalars().first()
            if not cap:
                cap = Capability(
                    code=code,
                    name=code.replace("_", " ").title(),
                    description=desc,
                    category=category,
                    status=CapabilityStatus.AVAILABLE
                )
                session.add(cap)
                await session.flush()
            
            # Map to agent
            res = await session.execute(select(AgentCapability).where(AgentCapability.agent_id == agent.id, AgentCapability.capability_id == cap.id))
            if not res.scalars().first():
                session.add(AgentCapability(agent_id=agent.id, capability_id=cap.id, priority=1))
                
            # Map to workspaces
            # Disaster Management, Coastal Authority
            workspaces = ["DISASTER_MANAGEMENT", "COASTAL_AUTHORITY"]
            for w in workspaces:
                # Need to look up workspace UUID
                from app.db.models.workspace import Workspace
                res = await session.execute(select(Workspace).where(Workspace.code == w))
                ws = res.scalars().first()
                if ws:
                    res2 = await session.execute(select(WorkspaceCapability).where(WorkspaceCapability.workspace_id == ws.id, WorkspaceCapability.capability_id == cap.id))
                    if not res2.scalars().first():
                        session.add(WorkspaceCapability(workspace_id=ws.id, capability_id=cap.id, enabled=True))

        await session.commit()
        print("Exposure capabilities seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_exposure_capabilities())

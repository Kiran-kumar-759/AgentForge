import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models.workspace import Workspace
from app.db.models.data_source import DataSource
from app.db.models.dataset import Dataset
from app.db.models.agent import Agent, AgentStatus
from app.db.models.capability import Capability, CapabilityCategory, CapabilityStatus, AgentCapability, WorkspaceCapability

# -----------------
# PHASE 1-4 DATA
# -----------------
WORKSPACES = [
    {"code": "FISHERMAN", "name": "Fisherman", "description": "Workspace for fishermen."},
    {"code": "RESEARCHER", "name": "Researcher", "description": "Workspace for marine researchers."},
    {"code": "COASTAL_AUTHORITY", "name": "Coastal Authority", "description": "Workspace for coastal authorities."},
    {"code": "DISASTER_MANAGEMENT", "name": "Disaster Management", "description": "Workspace for disaster management teams."},
    {"code": "MARITIME_OPERATOR", "name": "Maritime Operator", "description": "Workspace for maritime operators."},
]

DATA_SOURCES = [
    {"name": "Open-Meteo", "provider": "Open-Meteo", "source_type": "API", "base_url": "https://api.open-meteo.com", "authentication_type": "None"},
    {"name": "NASA Earthdata", "provider": "NASA", "source_type": "API", "base_url": "https://earthdata.nasa.gov", "authentication_type": "Token"},
    {"name": "MOSDAC", "provider": "ISRO", "source_type": "API", "base_url": "https://mosdac.gov.in", "authentication_type": "Account"},
    {"name": "NOAA", "provider": "NOAA", "source_type": "API", "base_url": "https://www.noaa.gov", "authentication_type": "None"},
    {"name": "OpenStreetMap", "provider": "OSM", "source_type": "MapTiles", "base_url": "https://www.openstreetmap.org", "authentication_type": "None"},
]

DATASETS = [
    {
        "provider_name": "Open-Meteo",
        "dataset_name": "Marine Forecast",
        "dataset_identifier": "open-meteo-marine",
        "requires_auth": False,
        "is_active": True,
        "description": "Open-Meteo Marine API",
    },
    {
        "provider_name": "Open-Meteo",
        "dataset_name": "Weather Forecast",
        "dataset_identifier": "open-meteo-weather",
        "requires_auth": False,
        "is_active": True,
        "description": "Open-Meteo Weather API",
    },
    {
        "provider_name": "NOAA",
        "dataset_name": "JPL MUR SST",
        "dataset_identifier": "jplMURSST41",
        "requires_auth": False,
        "is_active": True,
        "description": "NOAA CoastWatch JPL MUR SST",
    }
]

# -----------------
# PHASE 5 AGENTS
# -----------------
AGENTS = [
    {"code": "planner_agent", "name": "PlannerAgent", "description": "Understand a user objective and determine capabilities.", "agent_type": "PLANNER", "status": AgentStatus.REGISTERED},
    {"code": "weather_agent", "name": "WeatherAgent", "description": "Marine/coastal weather intelligence.", "agent_type": "DOMAIN", "status": AgentStatus.REGISTERED},
    {"code": "cyclone_agent", "name": "CycloneAgent", "description": "Global cyclone and storm intelligence.", "agent_type": "DOMAIN", "status": AgentStatus.REGISTERED},
    {"code": "ocean_agent", "name": "OceanAgent", "description": "Marine/ocean condition intelligence.", "agent_type": "DOMAIN", "status": AgentStatus.REGISTERED},
    {"code": "satellite_agent", "name": "SatelliteAgent", "description": "Satellite-derived marine/coastal intelligence.", "agent_type": "DOMAIN", "status": AgentStatus.REGISTERED},
    {"code": "gis_agent", "name": "GISAgent", "description": "Geospatial reasoning and spatial operations.", "agent_type": "DOMAIN", "status": AgentStatus.REGISTERED},
    {"code": "vessel_agent", "name": "VesselAgent", "description": "Maritime/vessel intelligence.", "agent_type": "DOMAIN", "status": AgentStatus.REGISTERED},
    {"code": "research_agent", "name": "ResearchAgent", "description": "Scientific marine research.", "agent_type": "ANALYTICS", "status": AgentStatus.REGISTERED},
    {"code": "risk_agent", "name": "RiskAgent", "description": "Marine/coastal risk assessment.", "agent_type": "ANALYTICS", "status": AgentStatus.REGISTERED},
    {"code": "impact_agent", "name": "ImpactAgent", "description": "Assess consequences of marine hazards.", "agent_type": "ANALYTICS", "status": AgentStatus.REGISTERED},
    {"code": "verification_agent", "name": "VerificationAgent", "description": "Validate evidence and analytical outputs.", "agent_type": "VALIDATION", "status": AgentStatus.REGISTERED},
    {"code": "report_agent", "name": "ReportAgent", "description": "Generate structured scientific/operational reports.", "agent_type": "GENERATION", "status": AgentStatus.REGISTERED},
]

AVAILABLE_CAPABILITIES = {
    "spatial_query", "bounding_box_query", "location_filter", 
    "get_sea_surface_temperature", "get_wave_height", "get_wave_direction", 
    "get_wave_period", "get_ocean_currents", "get_sea_level",
    "get_weather_conditions", "get_wind_conditions", "get_weather_forecast",
    "get_cyclone_intelligence", "get_vessel_positions"
}

CAPABILITIES = [
    # PLANNING
    {"code": "objective_understanding", "name": "Objective Understanding", "category": CapabilityCategory.PLANNING, "agent": "planner_agent"},
    {"code": "capability_selection", "name": "Capability Selection", "category": CapabilityCategory.PLANNING, "agent": "planner_agent"},
    {"code": "execution_planning", "name": "Execution Planning", "category": CapabilityCategory.PLANNING, "agent": "planner_agent"},

    # WEATHER
    {"code": "get_weather_conditions", "name": "Get Weather Conditions", "category": CapabilityCategory.WEATHER, "agent": "weather_agent"},
    {"code": "get_wind_conditions", "name": "Get Wind Conditions", "category": CapabilityCategory.WEATHER, "agent": "weather_agent"},
    {"code": "get_weather_forecast", "name": "Get Weather Forecast", "category": CapabilityCategory.WEATHER, "agent": "weather_agent"},
    {"code": "get_cyclone_intelligence", "name": "Get Cyclone Intelligence", "category": CapabilityCategory.WEATHER, "agent": "cyclone_agent"},

    # OCEAN
    {"code": "get_sea_surface_temperature", "name": "Get Sea Surface Temperature", "category": CapabilityCategory.OCEAN, "agent": "ocean_agent"},
    {"code": "get_wave_height", "name": "Get Wave Height", "category": CapabilityCategory.OCEAN, "agent": "ocean_agent"},
    {"code": "get_wave_direction", "name": "Get Wave Direction", "category": CapabilityCategory.OCEAN, "agent": "ocean_agent"},
    {"code": "get_wave_period", "name": "Get Wave Period", "category": CapabilityCategory.OCEAN, "agent": "ocean_agent"},
    {"code": "get_ocean_currents", "name": "Get Ocean Currents", "category": CapabilityCategory.OCEAN, "agent": "ocean_agent"},
    {"code": "get_sea_level", "name": "Get Sea Level", "category": CapabilityCategory.OCEAN, "agent": "ocean_agent"},

    # SATELLITE
    {"code": "discover_satellite_dataset", "name": "Discover Satellite Dataset", "category": CapabilityCategory.SATELLITE, "agent": "satellite_agent"},
    {"code": "retrieve_satellite_data", "name": "Retrieve Satellite Data", "category": CapabilityCategory.SATELLITE, "agent": "satellite_agent"},

    # GIS
    {"code": "spatial_query", "name": "Spatial Query", "category": CapabilityCategory.GIS, "agent": "gis_agent"},
    {"code": "bounding_box_query", "name": "Bounding Box Query", "category": CapabilityCategory.GIS, "agent": "gis_agent"},
    {"code": "geojson_generation", "name": "GeoJSON Generation", "category": CapabilityCategory.GIS, "agent": "gis_agent"},
    {"code": "location_filter", "name": "Location Filter", "category": CapabilityCategory.GIS, "agent": "gis_agent"},
    {"code": "proximity_analysis", "name": "Proximity Analysis", "category": CapabilityCategory.GIS, "agent": "gis_agent"},

    # VESSEL
    {"code": "get_vessel_positions", "name": "Get Vessel Positions", "category": CapabilityCategory.VESSEL, "agent": "vessel_agent"},
    {"code": "get_vessel_tracks", "name": "Get Vessel Tracks", "category": CapabilityCategory.VESSEL, "agent": "vessel_agent"},
    {"code": "calculate_vessel_density", "name": "Calculate Vessel Density", "category": CapabilityCategory.VESSEL, "agent": "vessel_agent"},

    # RESEARCH
    {"code": "historical_analysis", "name": "Historical Analysis", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "temporal_analysis", "name": "Temporal Analysis", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "seasonal_analysis", "name": "Seasonal Analysis", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "trend_analysis", "name": "Trend Analysis", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "anomaly_detection", "name": "Anomaly Detection", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "correlation_analysis", "name": "Correlation Analysis", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "spatial_comparison", "name": "Spatial Comparison", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},
    {"code": "multi_variable_analysis", "name": "Multi-Variable Analysis", "category": CapabilityCategory.RESEARCH, "agent": "research_agent"},

    # RISK
    {"code": "hazard_assessment", "name": "Hazard Assessment", "category": CapabilityCategory.RISK, "agent": "risk_agent"},
    {"code": "risk_assessment", "name": "Risk Assessment", "category": CapabilityCategory.RISK, "agent": "risk_agent"},
    {"code": "scenario_comparison", "name": "Scenario Comparison", "category": CapabilityCategory.RISK, "agent": "risk_agent"},

    # IMPACT
    {"code": "population_exposure", "name": "Population Exposure", "category": CapabilityCategory.IMPACT, "agent": "impact_agent"},
    {"code": "infrastructure_exposure", "name": "Infrastructure Exposure", "category": CapabilityCategory.IMPACT, "agent": "impact_agent"},
    {"code": "vessel_exposure", "name": "Vessel Exposure", "category": CapabilityCategory.IMPACT, "agent": "impact_agent"},
    {"code": "coastal_impact_assessment", "name": "Coastal Impact Assessment", "category": CapabilityCategory.IMPACT, "agent": "impact_agent"},

    # VERIFICATION
    {"code": "verify_source", "name": "Verify Source", "category": CapabilityCategory.VERIFICATION, "agent": "verification_agent"},
    {"code": "validate_data_quality", "name": "Validate Data Quality", "category": CapabilityCategory.VERIFICATION, "agent": "verification_agent"},
    {"code": "detect_stale_data", "name": "Detect Stale Data", "category": CapabilityCategory.VERIFICATION, "agent": "verification_agent"},
    {"code": "detect_conflicting_data", "name": "Detect Conflicting Data", "category": CapabilityCategory.VERIFICATION, "agent": "verification_agent"},
    {"code": "validate_conclusion", "name": "Validate Conclusion", "category": CapabilityCategory.VERIFICATION, "agent": "verification_agent"},

    # REPORTING
    {"code": "generate_scientific_report", "name": "Generate Scientific Report", "category": CapabilityCategory.REPORTING, "agent": "report_agent"},
    {"code": "generate_operational_report", "name": "Generate Operational Report", "category": CapabilityCategory.REPORTING, "agent": "report_agent"},
    {"code": "generate_research_package", "name": "Generate Research Package", "category": CapabilityCategory.REPORTING, "agent": "report_agent"},
]

WORKSPACE_MAPPINGS = {
    "FISHERMAN": [
        "get_wave_height", "get_wave_direction", "get_sea_surface_temperature",
        "spatial_query", "bounding_box_query", "location_filter"
    ],
    "RESEARCHER": [
        "historical_analysis", "anomaly_detection", "spatial_comparison", "temporal_analysis",
        "generate_scientific_report", "generate_research_package"
    ],
    "DISASTER_MANAGEMENT": [
        "hazard_assessment", "population_exposure", "infrastructure_exposure", 
        "coastal_impact_assessment", "scenario_comparison", "get_cyclone_intelligence"
    ],
    "MARITIME_OPERATOR": [
        "get_wave_height", "get_ocean_currents", "risk_assessment", "vessel_exposure",
        "get_vessel_positions", "get_vessel_tracks", "get_cyclone_intelligence"
    ],
    "COASTAL_AUTHORITY": [
        "spatial_query", "proximity_analysis", "coastal_impact_assessment",
        "historical_analysis", "generate_operational_report", "get_cyclone_intelligence"
    ]
}

async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with Session() as session:
        # 1. Workspaces
        for ws_data in WORKSPACES:
            existing = await session.execute(select(Workspace).where(Workspace.code == ws_data["code"]))
            if not existing.scalars().first():
                session.add(Workspace(**ws_data))
                
        # 2. Data Sources
        for ds_data in DATA_SOURCES:
            existing = await session.execute(select(DataSource).where(DataSource.name == ds_data["name"]))
            if not existing.scalars().first():
                session.add(DataSource(**ds_data))
                
        await session.commit()
        
        # 3. Datasets
        for ds in DATASETS:
            provider_q = await session.execute(select(DataSource).where(DataSource.name == ds["provider_name"]))
            provider = provider_q.scalars().first()
            if provider:
                existing_ds = await session.execute(
                    select(Dataset).where(Dataset.dataset_identifier == ds["dataset_identifier"])
                )
                if not existing_ds.scalars().first():
                    session.add(Dataset(
                        data_source_id=provider.id,
                        dataset_name=ds["dataset_name"],
                        dataset_identifier=ds["dataset_identifier"],
                        requires_auth=ds["requires_auth"],
                        is_active=ds["is_active"],
                        description=ds["description"]
                    ))
        await session.commit()

        # 4. Agents
        for agent_data in AGENTS:
            existing_agent = await session.execute(select(Agent).where(Agent.code == agent_data["code"]))
            if not existing_agent.scalars().first():
                session.add(Agent(**agent_data))
        await session.commit()

        # 5. Capabilities and Agent Mappings
        for cap_data in CAPABILITIES:
            agent_code = cap_data.pop("agent")
            existing_cap = await session.execute(select(Capability).where(Capability.code == cap_data["code"]))
            cap_obj = existing_cap.scalars().first()
            
            if not cap_obj:
                status = CapabilityStatus.AVAILABLE if cap_data["code"] in AVAILABLE_CAPABILITIES else CapabilityStatus.NOT_IMPLEMENTED
                cap_obj = Capability(**cap_data, status=status)
                session.add(cap_obj)
                await session.flush()
            
            # map to agent
            agent_obj = await session.execute(select(Agent).where(Agent.code == agent_code))
            agent_obj = agent_obj.scalars().first()
            
            if agent_obj and cap_obj:
                existing_mapping = await session.execute(
                    select(AgentCapability).where(
                        AgentCapability.agent_id == agent_obj.id,
                        AgentCapability.capability_id == cap_obj.id
                    )
                )
                if not existing_mapping.scalars().first():
                    session.add(AgentCapability(agent_id=agent_obj.id, capability_id=cap_obj.id))
        
        await session.commit()

        # 6. Workspace Capabilities
        for ws_code, cap_codes in WORKSPACE_MAPPINGS.items():
            ws_obj = await session.execute(select(Workspace).where(Workspace.code == ws_code))
            ws_obj = ws_obj.scalars().first()
            if not ws_obj: continue

            for cap_code in cap_codes:
                cap_obj = await session.execute(select(Capability).where(Capability.code == cap_code))
                cap_obj = cap_obj.scalars().first()
                if not cap_obj: continue

                existing_ws_map = await session.execute(
                    select(WorkspaceCapability).where(
                        WorkspaceCapability.workspace_id == ws_obj.id,
                        WorkspaceCapability.capability_id == cap_obj.id
                    )
                )
                if not existing_ws_map.scalars().first():
                    session.add(WorkspaceCapability(workspace_id=ws_obj.id, capability_id=cap_obj.id))
        
        await session.commit()

    await engine.dispose()
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())

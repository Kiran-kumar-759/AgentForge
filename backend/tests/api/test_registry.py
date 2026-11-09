import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_agents():
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    # the seed has 11 agents
    assert len(agents) == 11
    planner = next((a for a in agents if a["code"] == "planner_agent"), None)
    assert planner is not None
    assert planner["name"] == "PlannerAgent"
    assert "objective_understanding" in planner["capabilities"]

def test_get_agent_by_code():
    response = client.get("/api/v1/agents/weather_agent")
    assert response.status_code == 200
    agent = response.json()
    assert agent["code"] == "weather_agent"
    assert agent["status"] == "REGISTERED"

def test_get_agent_not_found():
    response = client.get("/api/v1/agents/fake_agent")
    assert response.status_code == 404

def test_get_capabilities():
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    caps = response.json()
    assert isinstance(caps, list)
    assert len(caps) > 10

def test_get_capability_by_code():
    response = client.get("/api/v1/capabilities/get_sea_surface_temperature")
    assert response.status_code == 200
    cap = response.json()
    assert cap["code"] == "get_sea_surface_temperature"
    assert cap["category"] == "OCEAN"
    assert cap["status"] == "AVAILABLE"
    assert "ocean_agent" in cap["agents"]

def test_get_workspace_capabilities():
    response = client.get("/api/v1/workspaces/FISHERMAN/capabilities")
    assert response.status_code == 200
    mappings = response.json()
    assert isinstance(mappings, list)
    assert len(mappings) > 0
    cap_codes = [m["capability_code"] for m in mappings]
    assert "get_wave_height" in cap_codes
    assert "spatial_query" in cap_codes
    assert mappings[0]["workspace_code"] == "FISHERMAN"

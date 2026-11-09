import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def valid_geojson_polygon():
    return {
        "type": "Polygon",
        "coordinates": [[
            [74.0, 14.0],
            [74.1, 14.0],
            [74.1, 14.1],
            [74.0, 14.1],
            [74.0, 14.0]
        ]]
    }

@pytest.mark.asyncio
async def test_analyze_exposure_invalid_geometry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/exposure/analyze", json={
            "geometry": {
                "type": "InvalidType",
                "coordinates": [74.0, 14.0]
            }
        })
        assert response.status_code == 400
        assert "Unsupported geometry type" in response.json()["detail"]

@pytest.mark.asyncio
async def test_analyze_exposure_too_large():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/exposure/analyze", json={
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-180.0, -90.0],
                    [180.0, -90.0],
                    [180.0, 90.0],
                    [-180.0, 90.0],
                    [-180.0, -90.0]
                ]]
            }
        })
        assert response.status_code == 400
        assert "exceeds maximum allowed" in response.json()["detail"]

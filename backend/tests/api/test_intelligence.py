import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.services.data.base import MarineObservation, QualityStatus
from datetime import datetime, timezone

client = TestClient(app)

def get_mock_observations():
    now = datetime.now(timezone.utc)
    return [
        MarineObservation(
            source="Open-Meteo",
            dataset="open-meteo-weather",
            variable_name="temperature_2m",
            value=25.5,
            unit="°C",
            latitude=14.0,
            longitude=74.5,
            observation_timestamp=now,
            retrieved_at=now,
            quality_status=QualityStatus.VALID,
            metadata={"original_unit": "°C", "conversion_method": "", "original_value": 25.5}
        ),
        MarineObservation(
            source="Open-Meteo",
            dataset="open-meteo-weather",
            variable_name="wind_speed_10m",
            value=12.0,
            unit="m/s",
            latitude=14.0,
            longitude=74.5,
            observation_timestamp=now,
            retrieved_at=now,
            quality_status=QualityStatus.VALID,
            metadata={"original_unit": "m/s", "conversion_method": "", "original_value": 12.0}
        )
    ]

@patch("app.services.intelligence.executor.CapabilityExecutor._fetch_from_provider", new_callable=AsyncMock)
def test_execute_weather_conditions(mock_fetch):
    mock_fetch.return_value = get_mock_observations()
    
    response = client.post(
        "/api/v1/capabilities/get_weather_conditions/execute",
        json={"latitude": 14.0, "longitude": 74.5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["capability_code"] == "get_weather_conditions"
    assert data["agent_code"] == "WeatherAgent"
    assert data["data"]["temperature"] == 25.5
    assert data["data"]["wind_speed"] == 12.0
    assert len(data["provenance"]) > 0

def test_execute_invalid_capability():
    response = client.post(
        "/api/v1/capabilities/fake_capability/execute",
        json={"latitude": 14.0, "longitude": 74.5}
    )
    assert response.status_code == 404

def test_execute_not_implemented_capability():
    response = client.post(
        "/api/v1/capabilities/spatial_query/execute",
        json={"latitude": 14.0, "longitude": 74.5}
    )
    assert response.status_code == 409

def test_execute_invalid_coordinates():
    response = client.post(
        "/api/v1/capabilities/get_weather_conditions/execute",
        json={"latitude": 100.0, "longitude": 74.5}
    )
    # Pydantic validation error for latitude > 90
    assert response.status_code == 422

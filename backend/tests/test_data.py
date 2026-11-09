import pytest
from datetime import datetime, timezone
from app.services.data.validation import is_valid_coordinate, is_valid_numeric, validate_observation_value
from app.services.data.normalization import normalize_unit

def test_validation_coordinates():
    assert is_valid_coordinate(14.0, 74.5) is True
    assert is_valid_coordinate(-91.0, 74.5) is False
    assert is_valid_coordinate(14.0, 181.0) is False
    assert is_valid_coordinate(float('nan'), 74.5) is False

def test_validation_numeric():
    assert is_valid_numeric(10.5) is True
    assert is_valid_numeric(float('nan')) is False
    assert is_valid_numeric(float('inf')) is False
    assert is_valid_numeric(None) is False
    assert is_valid_numeric(-9999.0) is False
    assert is_valid_numeric("10.5") is True
    assert is_valid_numeric("invalid") is False

def test_validate_observation_value():
    assert validate_observation_value("sea_surface_temperature", 28.5) is True
    assert validate_observation_value("sea_surface_temperature", 150.0) is False
    assert validate_observation_value("wave_height", -1.0) is False
    assert validate_observation_value("wind_wave_direction", 400.0) is False

def test_normalize_unit():
    val, unit, method = normalize_unit("sea_surface_temperature", 32.0, "Fahrenheit")
    assert val == 0.0
    assert unit == "°C"
    assert method == "fahrenheit_to_celsius"
    
    val, unit, method = normalize_unit("wave_height", 100.0, "cm")
    assert val == 1.0
    assert unit == "m"
    assert method == "cm_to_m"
    
    val, unit, method = normalize_unit("ocean_current_velocity", 36.0, "km/h")
    assert val == 10.0
    assert unit == "m/s"
    assert method == "kmh_to_ms"

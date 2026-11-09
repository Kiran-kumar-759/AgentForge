import math
from typing import Any
from datetime import datetime

def is_valid_coordinate(lat: float, lon: float) -> bool:
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0

def is_valid_numeric(val: Any) -> bool:
    if val is None:
        return False
    if not isinstance(val, (int, float)):
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
    if math.isnan(val) or math.isinf(val):
        return False
    
    # Common missing value sentinels
    if val in [-9999.0, -999.0, -99999.0]:
        return False
        
    return True

def validate_observation_value(variable_name: str, value: Any) -> bool:
    if not is_valid_numeric(value):
        return False
        
    val = float(value)
    
    if "wave_height" in variable_name and val < 0:
        return False
        
    if "direction" in variable_name and (val < 0 or val > 360):
        # direction is usually 0-360
        return False
        
    if "temperature" in variable_name and (val < -100 or val > 100):
        # rough bounds in Celsius
        return False
        
    return True

from typing import Tuple, Any

def normalize_unit(variable_name: str, value: float, original_unit: str) -> Tuple[float, str, str]:
    """
    Returns normalized (value, canonical_unit, conversion_method)
    """
    canonical = original_unit
    val = value
    method = "none"
    
    orig_lower = original_unit.lower().strip() if original_unit else ""
    
    if "temperature" in variable_name:
        canonical = "°C"
        if orig_lower in ["f", "fahrenheit", "°f"]:
            val = (value - 32) * 5.0 / 9.0
            method = "fahrenheit_to_celsius"
        elif orig_lower in ["k", "kelvin"]:
            val = value - 273.15
            method = "kelvin_to_celsius"
            
    elif "height" in variable_name:
        canonical = "m"
        if orig_lower in ["cm"]:
            val = value / 100.0
            method = "cm_to_m"
        elif orig_lower in ["mm"]:
            val = value / 1000.0
            method = "mm_to_m"
        elif orig_lower in ["ft", "feet"]:
            val = value * 0.3048
            method = "ft_to_m"
            
    elif "velocity" in variable_name or "speed" in variable_name:
        canonical = "m/s"
        if orig_lower in ["km/h", "kmh"]:
            val = value / 3.6
            method = "kmh_to_ms"
        elif orig_lower in ["knots", "kt"]:
            val = value * 0.514444
            method = "knots_to_ms"
            
    elif "direction" in variable_name:
        canonical = "°"
        if orig_lower == "rad" or orig_lower == "radians":
            import math
            val = math.degrees(value) % 360
            method = "rad_to_deg"
            
    elif "period" in variable_name:
        canonical = "s"
        
    return val, canonical, method

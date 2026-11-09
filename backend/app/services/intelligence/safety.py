from typing import Dict, Any, List
from datetime import datetime, timezone
import json

from app.services.intelligence.schemas import CapabilityResult
from app.services.intelligence.executor import CapabilityExecutor
from app.services.intelligence.cyclone_executor import CycloneExecutor

class SafetyAnalysisService:
    def __init__(self, db):
        self.db = db
        self.executor = CapabilityExecutor(db)
        self.cyclone_executor = CycloneExecutor(db)

    async def analyze_safety(self, lat: float, lon: float) -> CapabilityResult:
        # Fetch conditions concurrently or sequentially
        ocean = await self.executor.execute_ocean_conditions(lat, lon)
        wind = await self.executor.execute_wind_conditions(lat, lon)
        cyclones = await self.cyclone_executor.execute_cyclone_intelligence(active_only=True, radius_km=1000, lat=lat, lon=lon)
        
        ocean_data = ocean.data if hasattr(ocean, "data") else {}
        wind_data = wind.data if hasattr(wind, "data") else {}
        cyclone_data = cyclones.data if hasattr(cyclones, "data") else {}
        
        # logic
        risk_score = 0
        risk_factors = []
        
        wave_height = ocean_data.get("wave_height", 0)
        if wave_height is None: wave_height = 0
        wind_speed = wind_data.get("wind_speed", 0)
        if wind_speed is None: wind_speed = 0
        
        if wave_height > 2.0:
            risk_score += 3
            risk_factors.append(f"High waves: {wave_height}m")
        elif wave_height > 1.0:
            risk_score += 1
            risk_factors.append(f"Moderate waves: {wave_height}m")
            
        if wind_speed > 30: # km/h
            risk_score += 3
            risk_factors.append(f"High wind speed: {wind_speed}km/h")
        elif wind_speed > 20:
            risk_score += 1
            risk_factors.append(f"Moderate wind speed: {wind_speed}km/h")
            
        active_cyclones = cyclone_data.get("active_cyclones", [])
        if active_cyclones:
            risk_score += 5
            names = ", ".join([c.get("name", "Unknown") for c in active_cyclones])
            risk_factors.append(f"Active cyclone(s) nearby: {names}")
            
        if risk_score >= 5:
            assessment = "Conditions are hazardous. Fishing operations should be suspended."
            status = "CRITICAL_RISK"
        elif risk_score >= 2:
            assessment = "Conditions require caution. Small vessels should avoid open sea."
            status = "MODERATE_RISK"
        else:
            assessment = "Conditions appear safe for normal fishing operations."
            status = "LOW_RISK"
            
        return CapabilityResult(
            status="SUCCESS",
            capability_code="analyze_safety",
            agent_code="SafetyAgent",
            data={
                "assessment": assessment,
                "risk_level": status,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            evidence=ocean.evidence + wind.evidence + cyclones.evidence,
            provenance=ocean.provenance + wind.provenance + cyclones.provenance,
            metadata={"is_cached": False, "request_id": "safety-1", "is_fallback": False, "fallback_reason": None, "observation_age_seconds": 0}
        )

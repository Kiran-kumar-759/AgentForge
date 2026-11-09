import logging
from typing import Dict, Any, List
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.evidence import Claim, Evidence
from app.db.models.execution import ExecutionNode

logger = logging.getLogger(__name__)

class EvidenceAdapter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def extract_and_store(self, node: ExecutionNode) -> None:
        """
        Extracts claims and evidence from a completed ExecutionNode's output_data
        and persists them to the database.
        """
        if not node.output_data:
            return
            
        status = node.output_data.get("status")
        capability = node.capability_code
        if status == "UNAVAILABLE" and "vessel" in capability:
            # We explicitly handle Vessel out-of-bounds as UNVERIFIABLE
            c = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text="Vessel intelligence could not be verified for the requested region.",
                claim_type="VESSEL",
                status="extracted",
                verification_status="UNVERIFIABLE",
                verification_reason="Available vessel intelligence is restricted to Fintraffic/Baltic coverage."
            )
            self.db.add(c)
            await self.db.commit()
            return
            
        if status != "SUCCESS":
            return
            
        data = node.output_data.get("data", {})
        provenance = node.output_data.get("provenance", [])
        capability = node.capability_code
        
        claims_to_add = []
        evidence_to_add = []
        
        if capability == "get_weather_conditions":
            claims_to_add, evidence_to_add = self._extract_weather(node, data, provenance)
        elif capability == "get_wind_conditions":
            claims_to_add, evidence_to_add = self._extract_wind(node, data, provenance)
        elif capability == "get_ocean_conditions":
            claims_to_add, evidence_to_add = self._extract_ocean(node, data, provenance)
        elif capability == "get_cyclone_status":
            claims_to_add, evidence_to_add = self._extract_cyclone(node, data, provenance)
        elif capability == "analyze_coastal_exposure":
            claims_to_add, evidence_to_add = self._extract_exposure(node, data, provenance)
        elif capability == "get_vessel_positions":
            claims_to_add, evidence_to_add = self._extract_vessel(node, data, provenance)
        
        for e in evidence_to_add:
            self.db.add(e)
            
        for c in claims_to_add:
            self.db.add(c)
            
        await self.db.commit()

    def _extract_weather(self, node: ExecutionNode, data: dict, provenance: list):
        claims = []
        evidence = []
        
        # 1. Create Evidence
        # Combine provenance records into a single evidence source or multiple
        e = Evidence(
            execution_id=node.execution_id,
            execution_node_id=node.id,
            evidence_type="SCIENTIFIC_DATASET",
            dataset_id=data.get("dataset", "open-meteo-weather"),
            source_name=data.get("source", "Open-Meteo"),
            retrieved_at=datetime.fromisoformat(data.get("retrieved_at")) if data.get("retrieved_at") else datetime.now(timezone.utc),
            observation_time=datetime.fromisoformat(data.get("observation_time")) if data.get("observation_time") else None,
            spatial_context={"latitude": data.get("latitude"), "longitude": data.get("longitude")},
            computation="Retrieved from existing database fallback",
            status="valid"
        )
        evidence.append(e)
        
        # 2. Create Claims
        temp = data.get("temperature")
        if temp is not None:
            c = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text=f"Current temperature is {temp}°C.",
                claim_type="WEATHER",
                status="extracted",
                verification_status="SUPPORTED",
                verification_reason="Claim matches authoritative weather observation."
            )
            c.evidence.append(e)
            claims.append(c)
            
        return claims, evidence

    def _extract_wind(self, node: ExecutionNode, data: dict, provenance: list):
        claims = []
        evidence = []
        
        e = Evidence(
            execution_id=node.execution_id,
            execution_node_id=node.id,
            evidence_type="SCIENTIFIC_DATASET",
            dataset_id=data.get("dataset", "open-meteo-weather"),
            source_name=data.get("source", "Open-Meteo"),
            retrieved_at=datetime.fromisoformat(data.get("retrieved_at")) if data.get("retrieved_at") else datetime.now(timezone.utc),
            observation_time=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else None,
            spatial_context={"latitude": data.get("latitude"), "longitude": data.get("longitude")},
            computation="Retrieved from existing database fallback",
            status="valid"
        )
        evidence.append(e)
        
        speed = data.get("wind_speed")
        if speed is not None:
            c = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text=f"Wind speed is {speed} km/h.",
                claim_type="WEATHER",
                status="extracted",
                verification_status="SUPPORTED",
                verification_reason="Claim matches authoritative wind observation."
            )
            c.evidence.append(e)
            claims.append(c)
            
        return claims, evidence
        
    def _extract_ocean(self, node: ExecutionNode, data: dict, provenance: list):
        claims = []
        evidence = []
        
        e = Evidence(
            execution_id=node.execution_id,
            execution_node_id=node.id,
            evidence_type="SCIENTIFIC_DATASET",
            dataset_id=data.get("dataset", "open-meteo-marine"),
            source_name=data.get("source", "Open-Meteo"),
            retrieved_at=datetime.fromisoformat(data.get("retrieved_at")) if data.get("retrieved_at") else datetime.now(timezone.utc),
            observation_time=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else None,
            spatial_context={"latitude": data.get("latitude"), "longitude": data.get("longitude")},
            status="valid"
        )
        evidence.append(e)
        
        sst = data.get("sea_surface_temperature")
        if sst is not None:
            c = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text=f"Sea surface temperature is {sst}°C.",
                claim_type="OCEAN",
                status="extracted",
                verification_status="SUPPORTED",
                verification_reason="Claim matches authoritative ocean observation."
            )
            c.evidence.append(e)
            claims.append(c)
            
        return claims, evidence

    def _extract_cyclone(self, node: ExecutionNode, data: dict, provenance: list):
        claims = []
        evidence = []
        
        # Data has events
        events = data.get("events", [])
        for event in events:
            e = Evidence(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                evidence_type="SCIENTIFIC_DATASET",
                dataset_id="GDACS",
                source_name="GDACS Cyclones",
                status="valid",
                summary=f"Cyclone event: {event.get('name')}",
                spatial_context={"polygon": event.get("bbox")}
            )
            evidence.append(e)
            
            c = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text=f"Cyclone '{event.get('name')}' is active in the region.",
                claim_type="CYCLONE",
                status="extracted",
                verification_status="SUPPORTED",
                verification_reason="Claim matches GDACS cyclone data."
            )
            c.evidence.append(e)
            claims.append(c)
            
        return claims, evidence
        
    def _extract_exposure(self, node: ExecutionNode, data: dict, provenance: list):
        claims = []
        evidence = []
        
        # data: {'intent': ..., 'population_exposure': 1234, 'infrastructure_points': 5, 'summary': ...}
        pop = data.get("population_exposure")
        infra = data.get("infrastructure_points")
        
        if pop is not None:
            e_pop = Evidence(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                evidence_type="SPATIAL_QUERY",
                dataset_id="WORLDPOP_POPULATION",
                source_name="WorldPop",
                computation="Population records intersecting analyzed geometry were aggregated using PostGIS.",
                status="valid"
            )
            evidence.append(e_pop)
            
            c_pop = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text=f"Population exposure is {pop}.",
                claim_type="EXPOSURE",
                status="extracted",
                verification_status="SUPPORTED",
                verification_reason="Claim matches the result returned by the ExposureService using WORLDPOP_POPULATION records within the analyzed geometry."
            )
            c_pop.evidence.append(e_pop)
            claims.append(c_pop)
            
        if infra is not None:
            e_infra = Evidence(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                evidence_type="SPATIAL_QUERY",
                dataset_id="OSM_COASTAL_INFRASTRUCTURE",
                source_name="OpenStreetMap Infrastructure",
                computation="Infrastructure records within the specified spatial relationship were counted using PostGIS.",
                status="valid"
            )
            evidence.append(e_infra)
            
            c_infra = Claim(
                execution_id=node.execution_id,
                execution_node_id=node.id,
                claim_text=f"Coastal infrastructure points exposed: {infra}.",
                claim_type="EXPOSURE",
                status="extracted",
                verification_status="SUPPORTED",
                verification_reason="Claim matches the result returned by the ExposureService using OSM_COASTAL_INFRASTRUCTURE records within the analyzed geometry."
            )
            c_infra.evidence.append(e_infra)
            claims.append(c_infra)
            
        return claims, evidence

    def _extract_vessel(self, node: ExecutionNode, data: dict, provenance: list):
        # We need to handle unsupported vessel geography.
        # "Only create evidence when the available dataset legitimately covers the requested area. For unsupported geography: return: status = UNVERIFIABLE"
        # If node failed with UNAVAILABLE due to bounds, the output status wouldn't be SUCCESS, so it's handled in the orchestrator.
        # But if it succeeded but has no vessels, or the node logic marks it UNVERIFIABLE?
        claims = []
        evidence = []
        
        # If data has vessels, it's supported
        vessels = data.get("vessels", [])
        
        e = Evidence(
            execution_id=node.execution_id,
            execution_node_id=node.id,
            evidence_type="SCIENTIFIC_DATASET",
            dataset_id="AIS",
            source_name="Fintraffic-AIS",
            computation="Vessel positions retrieved for specified bounding box",
            status="valid"
        )
        evidence.append(e)
        
        c = Claim(
            execution_id=node.execution_id,
            execution_node_id=node.id,
            claim_text=f"{len(vessels)} vessels detected in the analyzed region.",
            claim_type="VESSEL",
            status="extracted",
            verification_status="SUPPORTED",
            verification_reason="Claim matches Fintraffic-AIS vessel data."
        )
        c.evidence.append(e)
        claims.append(c)
            
        return claims, evidence

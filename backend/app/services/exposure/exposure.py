import uuid
import datetime
import hashlib
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.exposure import ExposureAnalysis, ExposedSettlement, ExposedInfrastructure, PopulationData, InfrastructureData
from app.db.models.provenance import DataProvenance
from app.db.models.data_source import DataSource
from app.services.exposure.worldpop import WorldPopProvider
from app.services.exposure.overpass import OverpassProvider
from app.services.exposure.geometry import GeometryService
from sqlalchemy import select, func
from geoalchemy2 import Geography

class ExposureService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.worldpop = WorldPopProvider()
        self.overpass = OverpassProvider()

    async def _get_or_create_source(self, name: str, provider: str, url: str) -> uuid.UUID:
        stmt = select(DataSource).where(DataSource.name == name)
        res = await self.db.execute(stmt)
        ds = res.scalars().first()
        if ds:
            return ds.id
        ds = DataSource(
            name=name, provider=provider, source_type="api", base_url=url,
            description=f"Automated registration for {name}"
        )
        self.db.add(ds)
        await self.db.flush()
        return ds.id

    def _map_criticality(self, infra_type: str, tags: Dict[str, Any]) -> str:
        high = ["hospital", "aerodrome", "helipad", "port", "substation", "facility", "water_works"]
        medium = ["school", "clinic"]
        for h in high:
            if h in infra_type or any(h in v for v in tags.values() if isinstance(v, str)):
                return "high"
        for m in medium:
            if m in infra_type or any(m in v for v in tags.values() if isinstance(v, str)):
                return "medium"
        return "unknown"

    async def analyze_exposure(
        self,
        geometry_geojson: Dict[str, Any],
        analysis_type: str = "hazard_polygon",
        hazard_name: Optional[str] = None,
        hazard_source_type: str = "manual_area",
        hazard_source_id: Optional[uuid.UUID] = None,
        population_year: Optional[int] = None,
        population_resolution: str = "100m",
        include_settlements: bool = True,
        include_infrastructure: bool = True,
        distance_km: Optional[float] = None
    ) -> ExposureAnalysis:
        
        # 1. Validate Geometry
        shapely_geom, normalized_geojson = GeometryService.validate_and_normalize(geometry_geojson)
        area_km2 = GeometryService.calculate_area_km2(shapely_geom)
        
        if area_km2 > settings.EXPOSURE_MAX_AREA_KM2:
            raise ValueError(f"Geometry area {area_km2:.2f} km^2 exceeds maximum allowed {settings.EXPOSURE_MAX_AREA_KM2} km^2")
        
        min_lon, min_lat, max_lon, max_lat = GeometryService.get_bbox(shapely_geom)
        
        # 2. Create Analysis Record
        now = datetime.datetime.now(datetime.timezone.utc)
        analysis = ExposureAnalysis(
            analysis_type=analysis_type,
            hazard_source_type=hazard_source_type,
            hazard_source_id=hazard_source_id,
            hazard_name=hazard_name,
            geometry=normalized_geojson,
            status="running",
            analysis_timestamp=now,
            distance_threshold_km=distance_km
        )
        self.db.add(analysis)
        await self.db.flush()

        status = "completed"
        
        # 3. Read Population from PostGIS
        try:
            # Query the PopulationData table
            # Since our PopulationData contains regional polygons, we will find the sum of population
            # for regions that intersect the queried polygon.
            # Convert Shapely geom to WKT
            wkt = shapely_geom.wkt
            
            geom_param = func.ST_GeomFromText(wkt, 4326)
            if distance_km and distance_km > 0:
                dist_m = distance_km * 1000.0
                pop_stmt = select(PopulationData).where(
                    func.ST_DWithin(
                        func.cast(PopulationData.geom, Geography),
                        func.cast(geom_param, Geography),
                        dist_m
                    )
                )
            else:
                pop_stmt = select(PopulationData).where(
                    PopulationData.geom.ST_Intersects(geom_param)
                )
                
            pop_res = await self.db.execute(pop_stmt)
            pop_records = pop_res.scalars().all()
            
            pop = sum(record.population_value for record in pop_records)
            
            if not pop_records:
                status = "partial" # No persisted data for this region
                pop = 0.0
                
            analysis.population_total = pop
            analysis.population_year = population_year or settings.WORLDPOP_DEFAULT_YEAR or now.year
            analysis.population_resolution = population_resolution
            analysis.population_source = "PostgreSQL/PostGIS"
            
        except Exception as e:
            print("Population Error:", e)
            status = "unavailable"

        # 4. Read Infrastructure from PostGIS
        if include_settlements or include_infrastructure:
            try:
                wkt = shapely_geom.wkt
                
                geom_param = func.ST_GeomFromText(wkt, 4326)
                if distance_km and distance_km > 0:
                    dist_m = distance_km * 1000.0
                    infra_stmt = select(InfrastructureData).where(
                        func.ST_DWithin(
                            func.cast(InfrastructureData.geom, Geography),
                            func.cast(geom_param, Geography),
                            dist_m
                        )
                    )
                else:
                    infra_stmt = select(InfrastructureData).where(
                        InfrastructureData.geom.ST_Intersects(geom_param)
                    )
                    
                infra_res = await self.db.execute(infra_stmt)
                infra_records = infra_res.scalars().all()
                
                if not infra_records:
                    if status == "completed":
                        status = "partial"
                
                settlement_count = 0
                infra_count = 0
                critical_count = 0
                
                for el in infra_records:
                    lat = el.latitude
                    lon = el.longitude
                    
                    # Is it a settlement?
                    # The tags are in el.tags JSONB
                    if "place" in el.tags and include_settlements:
                        settlement = ExposedSettlement(
                            analysis_id=analysis.id,
                            osm_type=el.osm_type,
                            osm_id=el.osm_id,
                            name=el.name,
                            place_type=el.tags["place"],
                            latitude=lat,
                            longitude=lon,
                            tags=el.tags,
                            source="PostgreSQL/PostGIS",
                            retrieved_at=now
                        )
                        self.db.add(settlement)
                        settlement_count += 1
                        
                    # Is it infrastructure?
                    # Since category is already extracted during ingestion:
                    if el.category != "unknown" and el.category != "settlement" and include_infrastructure:
                        criticality = self._map_criticality(el.category, el.tags)
                        infra = ExposedInfrastructure(
                            analysis_id=analysis.id,
                            osm_type=el.osm_type,
                            osm_id=el.osm_id,
                            name=el.name,
                            infrastructure_type=el.category,
                            criticality=criticality,
                            latitude=lat,
                            longitude=lon,
                            tags=el.tags,
                            source="PostgreSQL/PostGIS",
                            retrieved_at=now
                        )
                        self.db.add(infra)
                        infra_count += 1
                        if criticality == "high":
                            critical_count += 1
                            
                analysis.settlement_count = settlement_count
                analysis.infrastructure_count = infra_count
                analysis.critical_infrastructure_count = critical_count
                
            except Exception as e:
                print("Infrastructure Error:", e)
                if status == "completed":
                    status = "partial"
                # If population also failed, status remains unavailable.

        analysis.status = status
        analysis.source_retrieved_at = now
        await self.db.commit()
        await self.db.refresh(analysis)
        
        return analysis

    async def get_analysis(self, analysis_id: uuid.UUID) -> Optional[ExposureAnalysis]:
        stmt = select(ExposureAnalysis).where(ExposureAnalysis.id == analysis_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_settlements(self, analysis_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[ExposedSettlement]:
        stmt = select(ExposedSettlement).where(ExposedSettlement.analysis_id == analysis_id).limit(limit).offset(offset)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_infrastructure(self, analysis_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[ExposedInfrastructure]:
        stmt = select(ExposedInfrastructure).where(ExposedInfrastructure.analysis_id == analysis_id).limit(limit).offset(offset)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

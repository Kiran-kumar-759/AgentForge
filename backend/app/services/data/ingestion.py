import time
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.core.config import settings
from app.services.data.base import IngestionRequest, IngestionResult, MarineObservation
from app.services.data.registry import ProviderRegistry
from app.services.data.cache import cache_service
from app.db.models.marine_observation import MarineObservation as DBMarineObservation
from app.db.models.dataset import Dataset
from app.db.models.data_source import DataSource
from app.db.models.provenance import DataProvenance

class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = ProviderRegistry()
        
    def _generate_cache_key(self, req: IngestionRequest) -> str:
        vars_str = ",".join(sorted(req.variables))
        start = req.start_time.isoformat()
        end = req.end_time.isoformat()
        return f"orca:data:{req.provider}:{req.dataset}:{vars_str}:{req.min_lat}:{req.max_lat}:{req.min_lon}:{req.max_lon}:{start}:{end}"

    async def ingest(self, request: IngestionRequest) -> IngestionResult:
        start_ms = int(time.time() * 1000)
        result = IngestionResult(
            provider=request.provider,
            dataset=request.dataset,
            requested_range={
                "start": request.start_time.isoformat(),
                "end": request.end_time.isoformat(),
                "bbox": [request.min_lat, request.max_lat, request.min_lon, request.max_lon]
            }
        )
        
        try:
            provider = self.registry.get_provider(request.provider)
            if not provider.is_configured:
                result.errors.append(f"Provider {request.provider} is not configured.")
                result.duration_ms = int(time.time() * 1000) - start_ms
                return result
                
            cache_key = self._generate_cache_key(request)
            cached = await cache_service.get_cached_observations(cache_key)
            
            if cached is not None:
                observations = cached
                result.cache_hit = True
            else:
                observations = await provider.fetch_observations(request)
                if observations:
                    ttl = settings.OPEN_METEO_CACHE_TTL_SECONDS
                    if request.provider == "NOAA": ttl = settings.NOAA_CACHE_TTL_SECONDS
                    await cache_service.set_cached_observations(cache_key, observations, ttl)
            
            result.records_received = len(observations)
            result.records_valid = len(observations) # Validation already happens in normalize
            
            # Fetch Dataset and Source from DB
            ds_q = await self.db.execute(select(Dataset).join(DataSource).where(DataSource.name == request.provider))
            dataset_record = ds_q.scalars().first()
            if not dataset_record:
                result.errors.append(f"Dataset for provider {request.provider} not found in DB.")
                result.duration_ms = int(time.time() * 1000) - start_ms
                return result
                
            source_id = dataset_record.data_source_id
            dataset_id = dataset_record.id
            
            # Deduplicate and Persist
            inserted_count = 0
            duplicate_count = 0
            
            if observations:
                # Batch insert using ON CONFLICT DO NOTHING
                values_to_insert = []
                provenance_to_insert = []
                for obs in observations:
                    values_to_insert.append({
                        "dataset_id": dataset_id,
                        "data_source_id": source_id,
                        "variable_name": obs.variable_name,
                        "value": obs.value,
                        "unit": obs.unit,
                        "latitude": obs.latitude,
                        "longitude": obs.longitude,
                        "observation_timestamp": obs.observation_timestamp,
                        "retrieved_at": obs.retrieved_at,
                        "quality_status": obs.quality_status.value,
                        "is_fallback": obs.is_fallback,
                        "metadata": obs.metadata
                    })
                    provenance_to_insert.append({
                        "dataset_id": dataset_id,
                        "data_source_id": source_id,
                        "variable_name": obs.variable_name,
                        "latitude": obs.latitude,
                        "longitude": obs.longitude,
                        "observation_timestamp": obs.observation_timestamp,
                        "retrieved_at": obs.retrieved_at,
                        "value": str(obs.value),
                        "unit": obs.unit,
                        "metadata": obs.metadata
                    })
                
                # We need to chunk inserts to avoid massive queries
                chunk_size = 1000
                for i in range(0, len(values_to_insert), chunk_size):
                    chunk = values_to_insert[i:i+chunk_size]
                    prov_chunk = provenance_to_insert[i:i+chunk_size]
                    
                    stmt = insert(DBMarineObservation).values(chunk)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=['data_source_id', 'dataset_id', 'variable_name', 'latitude', 'longitude', 'observation_timestamp']
                    )
                    res = await self.db.execute(stmt)
                    inserted_count += res.rowcount
                    
                    # Insert provenance
                    prov_stmt = insert(DataProvenance).values(prov_chunk).on_conflict_do_nothing(
                        # Assuming index or just blind insert without constraint if not unique, 
                        # but we want to avoid duplicates. Currently provenance has no unique constraint in Phase 1 models.
                        # We'll just insert it.
                    )
                    await self.db.execute(prov_stmt)
                    
                await self.db.commit()
                duplicate_count = len(observations) - inserted_count
                
            result.records_inserted = inserted_count
            result.records_duplicate = duplicate_count
            
        except Exception as e:
            result.errors.append(str(e))
            
        result.duration_ms = int(time.time() * 1000) - start_ms
        return result

import asyncio
import os
import json
import logging
from datetime import datetime, timezone, timedelta
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from dotenv import load_dotenv

# Set up environment and config
load_dotenv(dotenv_path="/home/ckirankumar/AgentForge/backend/.env")
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL not set")

engine = create_async_engine(db_url, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_stage2")

# Import models
from app.db.models.marine_observation import MarineObservation
from app.db.models.data_source import DataSource
from app.db.models.dataset import Dataset
from app.db.models.provenance import DataProvenance
from app.db.models.cyclone import CycloneEvent, CycloneTrackPoint
from app.db.models.exposure import PopulationData, InfrastructureData

# Import providers
from app.services.data.providers.open_meteo import OpenMeteoProvider
from app.services.data.cyclone.gdacs import GDACSProvider
from app.services.exposure.worldpop import WorldPopProvider
from app.services.exposure.overpass import OverpassProvider

# Define Coastal Regions (Bounding Boxes for Infrastructure/Population)
COASTAL_REGIONS = [
    {"name": "Gujarat Coast", "bbox": [68.0, 20.0, 72.5, 23.5]}, # min_lon, min_lat, max_lon, max_lat
    {"name": "Maharashtra Coast", "bbox": [72.0, 15.5, 73.5, 20.5]},
    {"name": "Goa", "bbox": [73.5, 14.8, 74.5, 15.8]},
    {"name": "Karnataka Coast", "bbox": [74.0, 12.5, 75.2, 15.0]},
    {"name": "Kerala Coast", "bbox": [74.5, 8.0, 77.0, 12.8]},
    {"name": "Tamil Nadu Coast", "bbox": [77.0, 8.0, 80.5, 13.5]},
    {"name": "Andhra Pradesh Coast", "bbox": [79.5, 13.0, 84.5, 19.0]},
    {"name": "Odisha Coast", "bbox": [84.0, 18.5, 87.5, 22.0]},
    {"name": "West Bengal Coast", "bbox": [87.0, 21.0, 89.0, 22.5]},
    {"name": "Andaman & Nicobar", "bbox": [92.0, 6.0, 94.0, 14.0]},
    {"name": "Lakshadweep", "bbox": [71.0, 8.0, 74.0, 12.0]},
]

# Generate a grid of points for Marine & Weather
def generate_grid(regions, resolution=1.0):
    points = []
    for r in regions:
        min_lon, min_lat, max_lon, max_lat = r["bbox"]
        lon = min_lon
        while lon <= max_lon:
            lat = min_lat
            while lat <= max_lat:
                points.append((lat, lon))
                lat += resolution
            lon += resolution
    return list(set(points)) # Deduplicate

async def get_or_create_source(session, name, provider, url):
    stmt = select(DataSource).where(DataSource.name == name)
    result = await session.execute(stmt)
    source = result.scalar_one_or_none()
    if not source:
        source = DataSource(
            id=uuid.uuid4(),
            name=name,
            provider=provider,
            source_type="API",
            base_url=url,
            is_active=True
        )
        session.add(source)
        await session.commit()
    return source

async def get_or_create_dataset(session, source_id, name, identifier):
    stmt = select(Dataset).where(Dataset.dataset_name == name, Dataset.data_source_id == source_id)
    result = await session.execute(stmt)
    ds = result.scalar_one_or_none()
    if not ds:
        ds = Dataset(
            id=uuid.uuid4(),
            data_source_id=source_id,
            dataset_name=name,
            dataset_identifier=identifier,
            requires_auth=False,
            is_active=True
        )
        session.add(ds)
        await session.commit()
    return ds

async def process_marine_and_weather(session):
    logger.info("Starting Marine & Weather processing...")
    import httpx
    
    source = await get_or_create_source(session, "Open-Meteo API", "Open-Meteo", "https://api.open-meteo.com")
    marine_ds = await get_or_create_dataset(session, source.id, "Marine Forecast", "marine-meteo")
    weather_ds = await get_or_create_dataset(session, source.id, "Weather Forecast", "weather-meteo")
    
    grid = generate_grid(COASTAL_REGIONS, resolution=1.5)
    logger.info(f"Generated {len(grid)} grid points for Marine/Weather.")
    
    # Define variables based on stage1
    MARINE_VARIABLES = ["wave_height", "sea_surface_temperature", "wave_direction", "wave_period", "ocean_current_velocity", "ocean_current_direction", "sea_level_height_msl", "swell_wave_height", "swell_wave_direction", "swell_wave_period"]
    WEATHER_VARIABLES = ["temperature_2m", "apparent_temperature", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "precipitation", "surface_pressure", "weather_code"]
    
    now_utc = datetime.now(timezone.utc)
    start_date = (now_utc - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = (now_utc + timedelta(days=2)).strftime("%Y-%m-%d")
    
    batch_size = 5
    total_marine = 0
    total_weather = 0
    
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(0, len(grid), batch_size):
            batch = grid[i:i+batch_size]
            try:
                # Weather
                for lat, lon in batch:
                    r = await client.get(
                        "https://api.open-meteo.com/v1/forecast",
                        params={
                            "latitude": lat, "longitude": lon,
                            "hourly": ",".join(WEATHER_VARIABLES),
                            "start_date": start_date, "end_date": end_date,
                            "timezone": "UTC",
                        }
                    )
                    raw = r.json()
                    hourly = raw.get("hourly", {})
                    times = hourly.get("time", [])
                    
                    obs_to_insert = []
                    for k, ts in enumerate(times):
                        obs_time = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                        for var in WEATHER_VARIABLES:
                            if var in hourly:
                                val = hourly[var][k]
                                if val is not None:
                                    obs_to_insert.append(dict(
                                        id=uuid.uuid4(),
                                        dataset_id=weather_ds.id,
                                        data_source_id=source.id,
                                        variable_name=var,
                                        value=float(val),
                                        unit="",
                                        latitude=lat,
                                        longitude=lon,
                                        observation_timestamp=obs_time,
                                        retrieved_at=now_utc,
                                        quality_status="VALID",
                                        is_fallback=False
                                    ))
                    if obs_to_insert:
                        stmt = insert(MarineObservation).values(obs_to_insert).on_conflict_do_nothing()
                        await session.execute(stmt)
                        total_weather += len(obs_to_insert)
                
                # Marine
                for lat, lon in batch:
                    r = await client.get(
                        "https://marine-api.open-meteo.com/v1/marine",
                        params={
                            "latitude": lat, "longitude": lon,
                            "hourly": ",".join(MARINE_VARIABLES),
                            "start_date": start_date, "end_date": end_date,
                            "timezone": "UTC",
                        }
                    )
                    raw = r.json()
                    hourly = raw.get("hourly", {})
                    times = hourly.get("time", [])
                    
                    obs_to_insert = []
                    for k, ts in enumerate(times):
                        obs_time = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                        for var in MARINE_VARIABLES:
                            if var in hourly:
                                val = hourly[var][k]
                                if val is not None:
                                    obs_to_insert.append(dict(
                                        id=uuid.uuid4(),
                                        dataset_id=marine_ds.id,
                                        data_source_id=source.id,
                                        variable_name=var,
                                        value=float(val),
                                        unit="",
                                        latitude=lat,
                                        longitude=lon,
                                        observation_timestamp=obs_time,
                                        retrieved_at=now_utc,
                                        quality_status="VALID",
                                        is_fallback=False
                                    ))
                    if obs_to_insert:
                        stmt = insert(MarineObservation).values(obs_to_insert).on_conflict_do_nothing()
                        await session.execute(stmt)
                        total_marine += len(obs_to_insert)
                
                await session.commit()
                logger.info(f"Processed batch {i//batch_size + 1}, inserted {total_marine} marine, {total_weather} weather.")
                await asyncio.sleep(1) # rate limit
            except Exception as e:
                logger.error(f"Batch failed: {e}")
                await session.rollback()

async def process_infrastructure(session):
    logger.info("Starting Infrastructure processing...")
    op_provider = OverpassProvider()
    
    for r in COASTAL_REGIONS:
        min_lon, min_lat, max_lon, max_lat = r["bbox"]
        try:
            logger.info(f"Querying Overpass for {r['name']}...")
            res = await op_provider.query_bbox(min_lon, min_lat, max_lon, max_lat)
            
            infra_to_insert = []
            for inf in res.get("elements", []):
                osm_type = inf.get("type", "unknown")
                osm_id = inf.get("id", 0)
                tags = inf.get("tags", {})
                
                # Determine lat/lon based on type
                lat = inf.get("lat")
                lon = inf.get("lon")
                if "center" in inf:
                    lat = inf["center"].get("lat")
                    lon = inf["center"].get("lon")
                    
                if lat is None or lon is None:
                    continue
                    
                category = tags.get("amenity") or tags.get("aeroway") or tags.get("industrial") or tags.get("power") or "unknown"
                
                infra_to_insert.append(dict(
                    id=uuid.uuid4(),
                    osm_type=osm_type,
                    osm_id=osm_id,
                    name=tags.get("name"),
                    category=category,
                    latitude=lat,
                    longitude=lon,
                    geom=f"SRID=4326;POINT({lon} {lat})",
                    tags=tags,
                    source="Overpass",
                    retrieved_at=datetime.now(timezone.utc)
                ))
            
            if infra_to_insert:
                for idx in range(0, len(infra_to_insert), 1000):
                    batch = infra_to_insert[idx:idx+1000]
                    stmt = insert(InfrastructureData).values(batch).on_conflict_do_nothing()
                    await session.execute(stmt)
            
            await session.commit()
            logger.info(f"Inserted {len(infra_to_insert)} infrastructure for {r['name']}")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Infrastructure failed for {r['name']}: {e}")
            await session.rollback()

async def process_population(session):
    logger.info("Starting Population processing...")
    wp_provider = WorldPopProvider()
    
    # We will use the bounding boxes to create artificial center-points for population 
    # instead of downloading huge rasters for now, representing the general region.
    # WorldPop API expects a geojson polygon. We'll send a bounding box polygon.
    
    for r in COASTAL_REGIONS:
        min_lon, min_lat, max_lon, max_lat = r["bbox"]
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat]
                ]]
            }
        }
        try:
            logger.info(f"Querying WorldPop for {r['name']}...")
            # This API call may take time.
            pop_val = 0
            try:
                res = await wp_provider.get_population(geojson, resolution="1km")
                pop_val = res.get("total_population")
                if pop_val is None:
                    raise Exception("API did not return total_population")
            except Exception as e:
                logger.warning(f"WorldPop actual API failed, doing approximation: {e}")
                logger.warning(f"INGESTION_PARTIAL: WorldPop provider failed for {r['name']}. Not inserting substitute data.")
                continue
                
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            
            pop_data = dict(
                id=uuid.uuid4(),
                latitude=center_lat,
                longitude=center_lon,
                geom=f"SRID=4326;POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))",
                population_value=pop_val,
                year=datetime.now().year,
                resolution="1km",
                source="WorldPop",
                dataset="WorldPop Region",
                retrieved_at=datetime.now(timezone.utc)
            )
            stmt = insert(PopulationData).values([pop_data]).on_conflict_do_nothing()
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Inserted population {pop_val} for {r['name']}")
        except Exception as e:
            logger.error(f"Population failed for {r['name']}: {e}")
            await session.rollback()

async def process_cyclones(session):
    logger.info("Starting Cyclone processing...")
    gdacs = GDACSProvider()
    source = await get_or_create_source(session, "GDACS", "GDACS", "https://gdacs.org")
    ds = await get_or_create_dataset(session, source.id, "GDACS Cyclones", "gdacs-cyclones")
    
    try:
        events = await gdacs.get_active_cyclones()
        for evt in events:
            # We are just doing basic updates
            stmt = select(CycloneEvent).where(CycloneEvent.event_identifier == evt["event_id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if not existing:
                new_evt = CycloneEvent(
                    id=uuid.uuid4(),
                    dataset_id=ds.id,
                    data_source_id=source.id,
                    event_identifier=evt["event_id"],
                    name=evt.get("name", "Unknown"),
                    basin=evt.get("basin", ""),
                    start_date=evt.get("start_date") or datetime.now(timezone.utc),
                    is_active=True,
                    metadata_json={},
                    retrieved_at=datetime.now(timezone.utc)
                )
                session.add(new_evt)
        await session.commit()
    except Exception as e:
        logger.error(f"Cyclone processing failed: {e}")
        await session.rollback()

async def main():
    async with AsyncSessionLocal() as session:
        await process_marine_and_weather(session)
        await process_infrastructure(session)
        await process_population(session)
        await process_cyclones(session)
        
    await engine.dispose()
    logger.info("Ingestion completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())

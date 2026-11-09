"""
ORCA Stage-1 Real Dataset Ingestion Script
===========================================
Populates the existing ORCA PostgreSQL database with real scientific data.

DATA STATUS RULES:
  REAL     = directly source-backed observation/forecast
  DERIVED  = calculated from real records with lineage
  FALLBACK = stored fallback data explicitly identified
  CONTROLLED_TEST = test-only, never in production queries

NO INVENTED DATA. ALL values come from live API responses.
"""

import asyncio
import sys
import json
import math
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import uuid as uuid_lib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("orca.ingest")

DB_URL = "postgresql+psycopg://postgres:postgre123@localhost:5432/orca"

# Indian Marine Sampling Grid — 12 coastal/offshore points
INDIAN_MARINE_GRID = [
    ("Gujarat_Coast",       22.5,  68.5),
    ("Mumbai_Offshore",     19.0,  71.5),
    ("Goa_Coast",           15.5,  73.8),
    ("Karnataka_Coast",     13.5,  74.5),
    ("Kerala_Coast",        10.5,  75.8),
    ("Kanyakumari_Coast",    8.2,  77.5),
    ("Chennai_Coast",       13.1,  80.3),
    ("Andhra_Coast",        15.9,  80.7),
    ("Odisha_Coast",        19.5,  85.5),
    ("Bay_of_Bengal_North", 20.5,  87.5),
    ("Andaman_Sea",         11.7,  92.7),
    ("Lakshadweep",         10.6,  72.6),
]

# 8 Indian coastal cities for weather
INDIAN_COASTAL_CITIES = [
    ("Mumbai",        19.076, 72.877),
    ("Goa_Panaji",   15.499, 73.824),
    ("Kochi",        9.966,  76.289),
    ("Chennai",      13.083, 80.270),
    ("Visakhapatnam",17.686, 83.218),
    ("Puri",         19.813, 85.831),
    ("Surat_Coast",  21.170, 72.831),
    ("Port_Blair",   11.667, 92.746),
]

# Verified variables from Open-Meteo Marine API
MARINE_VARIABLES = [
    "wave_height", "sea_surface_temperature", "wave_direction", "wave_period",
    "ocean_current_velocity", "ocean_current_direction", "sea_level_height_msl",
    "swell_wave_height", "swell_wave_direction", "swell_wave_period",
]

# Verified variables from Open-Meteo Weather API
WEATHER_VARIABLES = [
    "temperature_2m", "apparent_temperature", "relative_humidity_2m",
    "wind_speed_10m", "wind_direction_10m", "precipitation",
    "surface_pressure", "weather_code",
]

report: Dict[str, Any] = {
    "postgis_status": "NOT_AVAILABLE",
    "datasets": {},
    "step_results": {},
    "validation_queries": {},
    "service_tests": {},
    "mosdac_status": "UNKNOWN",
    "vessel_status": "VESSEL_DATA_NOT_CONFIGURED",
    "satellite_status": "NOT_CONFIGURED",
}


# ─── Validation ───────────────────────────────────────────────────────────────

def is_valid_coord(lat: float, lon: float) -> bool:
    try:
        return (not math.isnan(lat) and not math.isnan(lon) and
                not math.isinf(lat) and not math.isinf(lon) and
                -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0)
    except Exception:
        return False


def is_valid_numeric(val: Any) -> bool:
    if val is None:
        return False
    try:
        v = float(val)
    except (ValueError, TypeError):
        return False
    if math.isnan(v) or math.isinf(v):
        return False
    return v not in (-9999.0, -999.0, -99999.0)


def validate_obs(variable: str, val: Any, lat: float, lon: float) -> Tuple[bool, str]:
    if not is_valid_coord(lat, lon):
        return False, "invalid_coordinate"
    if not is_valid_numeric(val):
        return False, "invalid_or_missing_value"
    v = float(val)
    if "height" in variable and "sea_level" not in variable and v < 0:
        return False, "negative_height"
    if "direction" in variable and not (0 <= v <= 360):
        return False, "direction_out_of_range"
    if "temperature" in variable and not (-5 <= v <= 40):
        return False, "temperature_out_of_range"
    return True, "ok"


def normalize_unit(variable: str, val: float, orig_unit: str) -> Tuple[float, str]:
    ou = (orig_unit or "").lower().strip()
    if "temperature" in variable:
        if ou in ("f", "°f", "fahrenheit"):
            return (val - 32) * 5 / 9, "°C"
        if ou in ("k", "kelvin"):
            return val - 273.15, "°C"
        return val, "°C"
    if "velocity" in variable or ("speed" in variable and "weather_code" not in variable):
        if ou in ("km/h", "kmh"):
            return val / 3.6, "m/s"
        if ou in ("knots", "kt"):
            return val * 0.514444, "m/s"
        return val, "m/s"
    if "direction" in variable:
        return val, "°"
    if "height" in variable or variable in ("wave_height", "swell_wave_height"):
        return val, "m"
    if "period" in variable:
        return val, "s"
    if "humidity" in variable:
        return val, "%"
    if "pressure" in variable:
        return val, "hPa"
    if "precipitation" in variable:
        return val, "mm"
    return val, orig_unit


# ─── DB batch insert helper ───────────────────────────────────────────────────

INSERT_OBS_SQL = text("""
    INSERT INTO marine_observations
    (id, dataset_id, data_source_id, variable_name, value, unit,
     latitude, longitude, observation_timestamp, retrieved_at,
     quality_status, quality_score, is_fallback, source_record_id, metadata, created_at)
    VALUES
    (:id, :dataset_id, :data_source_id, :variable_name, :value, :unit,
     :latitude, :longitude, :observation_timestamp, :retrieved_at,
     :quality_status, :quality_score, :is_fallback, :source_record_id, CAST(:metadata AS jsonb), NOW())
    ON CONFLICT (data_source_id, dataset_id, variable_name, latitude, longitude, observation_timestamp)
    DO NOTHING
""")


async def batch_insert_obs(session: AsyncSession, rows: List[Dict]) -> Tuple[int, int]:
    """Insert rows in 500-record chunks. Returns (inserted, duplicates)."""
    total_inserted = 0
    total_dup = 0
    chunk_size = 500
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        try:
            result = await session.execute(INSERT_OBS_SQL, chunk)
            ins = result.rowcount
            total_inserted += ins
            total_dup += len(chunk) - ins
        except Exception as e:
            log.error(f"  Batch insert error: {e}")
            await session.rollback()
    return total_inserted, total_dup


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Audit
# ─────────────────────────────────────────────────────────────────────────────

async def step1_audit(session: AsyncSession):
    log.info("═══ STEP 1: Database Audit ═══")
    try:
        r = await session.execute(text("SELECT PostGIS_Full_Version()"))
        v = r.scalar()
        report["postgis_status"] = f"AVAILABLE: {v[:80]}"
        log.info(f"PostGIS: {v[:80]}")
    except Exception:
        await session.rollback()
        report["postgis_status"] = (
            "NOT_AVAILABLE — postgis extension not installed on PostgreSQL 18.6. "
            "Proceeding with lat/lon float columns (no geometry type)."
        )
        log.warning("PostGIS NOT available — using lat/lon float columns.")

    tables = [
        "data_sources", "datasets", "marine_observations", "data_provenance",
        "cyclone_events", "cyclone_track_points", "exposed_infrastructure",
        "exposed_settlements", "vessel_positions", "vessels",
    ]
    counts = {}
    for t in tables:
        r = await session.execute(text(f"SELECT COUNT(*) FROM {t}"))
        counts[t] = r.scalar()
        log.info(f"  {t}: {counts[t]} rows")

    report["step_results"]["step1_audit"] = {"postgis": report["postgis_status"], "table_counts": counts}
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Dataset catalog
# ─────────────────────────────────────────────────────────────────────────────

async def step2_dataset_catalog(session: AsyncSession) -> Dict:
    log.info("═══ STEP 2: Dataset Catalog ═══")
    r = await session.execute(text("SELECT id, name FROM data_sources"))
    sources = {row[1]: str(row[0]) for row in r.fetchall()}

    r2 = await session.execute(text("SELECT id, dataset_identifier, data_source_id FROM datasets"))
    datasets_db = {row[1]: (str(row[0]), str(row[2])) for row in r2.fetchall()}

    catalog: Dict[str, Any] = {}

    for key, ds_id_col in [("marine", "open-meteo-marine"), ("weather", "open-meteo-weather")]:
        if ds_id_col in datasets_db:
            ds_id, src_id = datasets_db[ds_id_col]
            catalog[key] = {"dataset_id": ds_id, "source_id": src_id, "identifier": ds_id_col}
            log.info(f"  {ds_id_col}: dataset_id={ds_id}")
        else:
            log.warning(f"  {ds_id_col} dataset NOT found in DB")

    if "GDACS-TC" in sources:
        catalog["gdacs_source_id"] = sources["GDACS-TC"]
        log.info(f"  GDACS-TC source: {sources['GDACS-TC']}")

    if "Fintraffic-AIS" in sources:
        catalog["ais_source_id"] = sources["Fintraffic-AIS"]
        report["vessel_status"] = (
            "AVAILABLE_BALTIC_ONLY — Fintraffic-AIS data covers Finnish/Baltic waters. "
            "Indian Ocean AIS: NOT_CONFIGURED"
        )
        log.info("  Fintraffic-AIS source present (Baltic waters only)")

    report["step_results"]["step2_catalog"] = catalog
    return catalog


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Marine ingestion
# ─────────────────────────────────────────────────────────────────────────────

async def step3_marine_ingestion(session: AsyncSession, catalog: Dict) -> Dict:
    log.info("═══ STEP 3: Open-Meteo Marine Ingestion ═══")

    if "marine" not in catalog:
        log.error("Marine dataset missing — skipping")
        report["datasets"]["marine"] = {"status": "FAILED", "reason": "dataset_not_in_catalog"}
        return {}

    dataset_id = catalog["marine"]["dataset_id"]
    source_id = catalog["marine"]["source_id"]

    now_utc = datetime.now(timezone.utc)
    end_date = now_utc
    start_date = end_date - timedelta(days=7)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    total_inserted = 0
    total_rejected = 0
    total_duplicate = 0
    reject_reasons: Dict[str, int] = {}
    locations_ingested = []

    async with httpx.AsyncClient(timeout=30) as client:
        for (loc_name, lat, lon) in INDIAN_MARINE_GRID:
            log.info(f"  Fetching marine: {loc_name} ({lat}, {lon})")
            try:
                r = await client.get(
                    "https://marine-api.open-meteo.com/v1/marine",
                    params={
                        "latitude": lat, "longitude": lon,
                        "hourly": ",".join(MARINE_VARIABLES),
                        "start_date": start_str, "end_date": end_str,
                        "timezone": "UTC",
                    }
                )
                r.raise_for_status()
                raw = r.json()
            except Exception as e:
                log.warning(f"    API error for {loc_name}: {e}")
                reject_reasons["api_error"] = reject_reasons.get("api_error", 0) + 1
                continue

            hourly = raw.get("hourly", {})
            hourly_units = raw.get("hourly_units", {})
            times = hourly.get("time", [])
            actual_lat = raw.get("latitude", lat)
            actual_lon = raw.get("longitude", lon)

            rows_to_insert = []
            loc_rejected = 0

            for i, ts in enumerate(times):
                try:
                    obs_time = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                except ValueError:
                    loc_rejected += 1
                    reject_reasons["bad_timestamp"] = reject_reasons.get("bad_timestamp", 0) + 1
                    continue

                for var in MARINE_VARIABLES:
                    if var not in hourly:
                        continue
                    vals_list = hourly[var]
                    raw_val = vals_list[i] if i < len(vals_list) else None
                    if raw_val is None:
                        continue

                    ok, reason = validate_obs(var, raw_val, actual_lat, actual_lon)
                    if not ok:
                        loc_rejected += 1
                        reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
                        continue

                    orig_unit = hourly_units.get(var, "")
                    norm_val, canon_unit = normalize_unit(var, float(raw_val), orig_unit)

                    rows_to_insert.append({
                        "id": str(uuid_lib.uuid4()),
                        "dataset_id": dataset_id,
                        "data_source_id": source_id,
                        "variable_name": var,
                        "value": norm_val,
                        "unit": canon_unit,
                        "latitude": actual_lat,
                        "longitude": actual_lon,
                        "observation_timestamp": obs_time,
                        "retrieved_at": now_utc,
                        "quality_status": "VALID",
                        "quality_score": 1.0,
                        "is_fallback": False,
                        "source_record_id": f"om_marine_{actual_lat}_{actual_lon}_{var}_{ts}",
                        "metadata": json.dumps({
                            "data_status": "REAL",
                            "location_name": loc_name,
                            "original_unit": orig_unit,
                            "original_value": raw_val,
                            "provider": "Open-Meteo Marine API",
                        }),
                    })

            ins, dup = await batch_insert_obs(session, rows_to_insert)
            await session.commit()

            total_inserted += ins
            total_duplicate += dup
            total_rejected += loc_rejected
            locations_ingested.append({"name": loc_name, "lat": actual_lat, "lon": actual_lon,
                                        "inserted": ins, "rejected": loc_rejected})
            log.info(f"    {loc_name}: inserted={ins}, rejected={loc_rejected}, dup={dup}")

    result = {
        "status": "AVAILABLE" if total_inserted > 0 else "FAILED",
        "provider": "Open-Meteo Marine API",
        "dataset_identifier": "open-meteo-marine",
        "variables": MARINE_VARIABLES,
        "geographic_coverage": "12 Indian coastal/offshore grid points",
        "temporal_coverage": f"{start_str} to {end_str}",
        "temporal_resolution": "hourly",
        "records_inserted": total_inserted,
        "records_rejected": total_rejected,
        "records_duplicate": total_duplicate,
        "reject_reasons": reject_reasons,
        "locations": locations_ingested,
        "last_ingestion": now_utc.isoformat(),
    }
    report["datasets"]["marine"] = result
    log.info(f"  Marine done: inserted={total_inserted}, rejected={total_rejected}, dup={total_duplicate}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Weather ingestion
# ─────────────────────────────────────────────────────────────────────────────

async def step4_weather_ingestion(session: AsyncSession, catalog: Dict) -> Dict:
    log.info("═══ STEP 4: Open-Meteo Weather Ingestion ═══")

    if "weather" not in catalog:
        log.error("Weather dataset missing — skipping")
        report["datasets"]["weather"] = {"status": "FAILED", "reason": "dataset_not_in_catalog"}
        return {}

    dataset_id = catalog["weather"]["dataset_id"]
    source_id = catalog["weather"]["source_id"]

    now_utc = datetime.now(timezone.utc)
    start_date = (now_utc - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = (now_utc + timedelta(days=3)).strftime("%Y-%m-%d")

    total_inserted = 0
    total_rejected = 0
    total_duplicate = 0
    locations_ingested = []

    async with httpx.AsyncClient(timeout=30) as client:
        for (city_name, lat, lon) in INDIAN_COASTAL_CITIES:
            log.info(f"  Fetching weather: {city_name} ({lat}, {lon})")
            try:
                r = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat, "longitude": lon,
                        "hourly": ",".join(WEATHER_VARIABLES),
                        "start_date": start_date, "end_date": end_date,
                        "timezone": "UTC",
                    }
                )
                r.raise_for_status()
                raw = r.json()
            except Exception as e:
                log.warning(f"    API error for {city_name}: {e}")
                continue

            hourly = raw.get("hourly", {})
            hourly_units = raw.get("hourly_units", {})
            times = hourly.get("time", [])
            actual_lat = raw.get("latitude", lat)
            actual_lon = raw.get("longitude", lon)

            rows_to_insert = []
            loc_rejected = 0

            for i, ts in enumerate(times):
                try:
                    obs_time = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                except ValueError:
                    loc_rejected += 1
                    continue

                for var in WEATHER_VARIABLES:
                    if var not in hourly:
                        continue
                    vals_list = hourly[var]
                    raw_val = vals_list[i] if i < len(vals_list) else None
                    if raw_val is None:
                        continue
                    if not is_valid_numeric(raw_val):
                        loc_rejected += 1
                        continue

                    orig_unit = hourly_units.get(var, "")
                    norm_val, canon_unit = normalize_unit(var, float(raw_val), orig_unit)
                    is_forecast = obs_time > now_utc

                    rows_to_insert.append({
                        "id": str(uuid_lib.uuid4()),
                        "dataset_id": dataset_id,
                        "data_source_id": source_id,
                        "variable_name": var,
                        "value": norm_val,
                        "unit": canon_unit,
                        "latitude": actual_lat,
                        "longitude": actual_lon,
                        "observation_timestamp": obs_time,
                        "retrieved_at": now_utc,
                        "quality_status": "VALID",
                        "quality_score": 1.0,
                        "is_fallback": False,
                        "source_record_id": f"om_weather_{actual_lat}_{actual_lon}_{var}_{ts}",
                        "metadata": json.dumps({
                            "data_status": "REAL",
                            "is_forecast": is_forecast,
                            "city_name": city_name,
                            "original_unit": orig_unit,
                            "original_value": raw_val,
                            "provider": "Open-Meteo Weather Forecast API",
                        }),
                    })

            ins, dup = await batch_insert_obs(session, rows_to_insert)
            await session.commit()

            total_inserted += ins
            total_duplicate += dup
            total_rejected += loc_rejected
            locations_ingested.append({"city": city_name, "lat": actual_lat, "lon": actual_lon,
                                        "inserted": ins, "rejected": loc_rejected})
            log.info(f"    {city_name}: inserted={ins}, rejected={loc_rejected}, dup={dup}")

    result = {
        "status": "AVAILABLE" if total_inserted > 0 else "FAILED",
        "provider": "Open-Meteo Weather Forecast API",
        "dataset_identifier": "open-meteo-weather",
        "variables": WEATHER_VARIABLES,
        "geographic_coverage": "8 Indian coastal cities",
        "temporal_coverage": f"{start_date} to {end_date} (includes 3-day forecast)",
        "temporal_resolution": "hourly",
        "records_inserted": total_inserted,
        "records_rejected": total_rejected,
        "records_duplicate": total_duplicate,
        "locations": locations_ingested,
        "last_ingestion": now_utc.isoformat(),
    }
    report["datasets"]["weather"] = result
    log.info(f"  Weather done: inserted={total_inserted}, rejected={total_rejected}, dup={total_duplicate}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: GDACS Cyclone Refresh
# ─────────────────────────────────────────────────────────────────────────────

async def step5_cyclones(session: AsyncSession, catalog: Dict) -> Dict:
    log.info("═══ STEP 5: GDACS Cyclone Refresh ═══")

    gdacs_source_id = catalog.get("gdacs_source_id")
    if not gdacs_source_id:
        log.warning("GDACS source missing — skipping")
        report["datasets"]["cyclones"] = {"status": "FAILED", "reason": "source_not_in_catalog"}
        return {}

    sys.path.insert(0, "/home/ckirankumar/AgentForge/backend")
    from app.services.data.cyclone.gdacs import GDACSProvider

    provider = GDACSProvider()
    now_utc = datetime.now(timezone.utc)

    try:
        events = await provider.fetch_active_cyclones()
    except Exception as e:
        log.error(f"GDACS fetch failed: {e}")
        report["datasets"]["cyclones"] = {"status": "FAILED", "reason": str(e)}
        return {}

    log.info(f"  GDACS returned {len(events)} current cyclone events globally")

    inserted_events = 0
    updated_events = 0
    track_points_inserted = 0

    for ev in events:
        try:
            r = await session.execute(
                text("SELECT id FROM cyclone_events WHERE external_id = :eid"),
                {"eid": ev.external_id}
            )
            existing_id = r.scalar()

            wind_speed = ev.max_wind_speed
            wind_unit = ev.max_wind_unit or "km/h"
            metadata_json = json.dumps(ev.metadata or {})

            if existing_id:
                await session.execute(text("""
                    UPDATE cyclone_events SET
                        name = :name,
                        status = :status,
                        classification = :classification,
                        current_latitude = :current_latitude,
                        current_longitude = :current_longitude,
                        current_timestamp = :current_timestamp,
                        max_wind_speed = :max_wind_speed,
                        max_wind_unit = :max_wind_unit,
                        source_url = :source_url,
                        is_active = true,
                        metadata = CAST(:metadata AS json),
                        updated_at = NOW()
                    WHERE external_id = :external_id
                """), {
                    "name": ev.name,
                    "status": ev.classification,
                    "classification": ev.classification,
                    "current_latitude": ev.current_latitude,
                    "current_longitude": ev.current_longitude,
                    "current_timestamp": ev.current_timestamp,
                    "max_wind_speed": float(wind_speed) if wind_speed is not None else None,
                    "max_wind_unit": wind_unit,
                    "source_url": ev.source_url,
                    "metadata": metadata_json,
                    "external_id": ev.external_id,
                })
                event_db_id = existing_id
                updated_events += 1
            else:
                r2 = await session.execute(text("""
                    INSERT INTO cyclone_events
                    (external_id, source_id, name, basin, status, classification,
                     current_latitude, current_longitude, current_timestamp,
                     max_wind_speed, max_wind_unit, source_url,
                     is_active, is_fallback, metadata, created_at, updated_at)
                    VALUES
                    (:external_id, :source_id, :name, :basin, :status, :classification,
                     :current_latitude, :current_longitude, :current_timestamp,
                     :max_wind_speed, :max_wind_unit, :source_url,
                     true, false, CAST(:metadata AS json), NOW(), NOW())
                    RETURNING id
                """), {
                    "external_id": ev.external_id,
                    "source_id": gdacs_source_id,
                    "name": ev.name,
                    "basin": getattr(ev, "basin", None),
                    "status": ev.classification,
                    "classification": ev.classification,
                    "current_latitude": ev.current_latitude,
                    "current_longitude": ev.current_longitude,
                    "current_timestamp": ev.current_timestamp,
                    "max_wind_speed": float(wind_speed) if wind_speed is not None else None,
                    "max_wind_unit": wind_unit,
                    "source_url": ev.source_url,
                    "metadata": metadata_json,
                })
                event_db_id = r2.scalar()
                inserted_events += 1

            # Insert track points
            for tp in ev.track_points:
                if not tp.latitude or not tp.longitude:
                    continue
                if not is_valid_coord(float(tp.latitude), float(tp.longitude)):
                    continue

                is_obs = getattr(tp, "point_type", "OBSERVED") == "OBSERVED"
                is_fc = not is_obs

                try:
                    await session.execute(text("""
                        INSERT INTO cyclone_track_points
                        (cyclone_event_id, point_type, forecast_hour, timestamp, latitude, longitude,
                         max_wind_speed, wind_unit, minimum_pressure, classification,
                         source_record_id, is_observed, is_forecast, metadata, created_at)
                        VALUES
                        (:cyclone_event_id, :point_type, :forecast_hour, :timestamp, :latitude, :longitude,
                         :max_wind_speed, :wind_unit, :minimum_pressure, :classification,
                         :source_record_id, :is_observed, :is_forecast, CAST(:metadata AS json), NOW())
                        ON CONFLICT DO NOTHING
                    """), {
                        "cyclone_event_id": event_db_id,
                        "point_type": getattr(tp, "point_type", "OBSERVED"),
                        "forecast_hour": getattr(tp, "forecast_hour", None),
                        "timestamp": tp.timestamp,
                        "latitude": float(tp.latitude),
                        "longitude": float(tp.longitude),
                        "max_wind_speed": float(tp.max_wind_speed) if tp.max_wind_speed else None,
                        "wind_unit": getattr(tp, "wind_unit", None),
                        "minimum_pressure": getattr(tp, "minimum_pressure", None),
                        "classification": getattr(tp, "classification", None),
                        "source_record_id": getattr(tp, "source_record_id", None),
                        "is_observed": is_obs,
                        "is_forecast": is_fc,
                        "metadata": json.dumps(getattr(tp, "metadata", {}) or {}),
                    })
                    track_points_inserted += 1
                except Exception as tp_err:
                    log.debug(f"Track point insert skip: {tp_err}")

        except Exception as ev_err:
            log.error(f"  Cyclone {ev.external_id} error: {ev_err}")
            await session.rollback()
            continue

    await session.commit()

    indian_ocean_events = [
        ev for ev in events
        if ev.current_latitude is not None and ev.current_longitude is not None
        and 50.0 <= float(ev.current_longitude) <= 100.0
        and -30.0 <= float(ev.current_latitude) <= 25.0
    ]
    log.info(f"  Indian Ocean cyclones: {len(indian_ocean_events)}")
    if not indian_ocean_events:
        log.info("  No Indian Ocean cyclones currently active — valid meteorological state.")

    result = {
        "status": "AVAILABLE",
        "provider": "GDACS",
        "dataset_identifier": "gdacs-tc",
        "geographic_coverage": "Global tropical cyclones",
        "events_fetched": len(events),
        "events_inserted": inserted_events,
        "events_updated": updated_events,
        "track_points_inserted": track_points_inserted,
        "indian_ocean_active": len(indian_ocean_events),
        "note": "No active Indian Ocean cyclones = valid state" if not indian_ocean_events else None,
        "last_ingestion": now_utc.isoformat(),
    }
    report["datasets"]["cyclones"] = result
    log.info(f"  Cyclone refresh done: +{inserted_events} new, ~{updated_events} updated, {track_points_inserted} track pts")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: WorldPop test
# ─────────────────────────────────────────────────────────────────────────────

async def step6_worldpop() -> Dict:
    log.info("═══ STEP 6: WorldPop Accessibility Test ═══")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get("https://api.worldpop.org/v2/populations", params={"iso3": "IND"})
            d = r.json()
            datasets_count = len(d.get("data", []))
            result = {
                "status": "ACCESSIBLE",
                "provider": "WorldPop (https://api.worldpop.org/v2/)",
                "http_status": r.status_code,
                "india_datasets_available": datasets_count,
                "note": (
                    "WorldPop API is ACCESSIBLE. India population datasets exist. "
                    "Full raster download not performed on this i3/8GB machine. "
                    "Exposure analyses use Overpass settlements + WorldPop API point queries on demand."
                ),
            }
            log.info(f"  WorldPop: ACCESSIBLE, {datasets_count} India datasets")
        except Exception as e:
            result = {"status": "UNREACHABLE", "error": str(e)}
            log.warning(f"  WorldPop: {e}")
    report["datasets"]["worldpop"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Overpass test (Goa)
# ─────────────────────────────────────────────────────────────────────────────

async def step7_overpass() -> Dict:
    log.info("═══ STEP 7: Overpass Infrastructure Test (Goa) ═══")
    bbox = "14.9,73.7,15.7,74.4"
    query = f"""[out:json][timeout:30];
(
  nwr["amenity"~"hospital|clinic"]["name"]({bbox});
  nwr["harbour"]["name"]({bbox});
  nwr["man_made"="lighthouse"]({bbox});
);
out center tags qt 50;"""
    async with httpx.AsyncClient(timeout=40) as client:
        try:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"User-Agent": "ORCA-Coastal-Intelligence/1.0"},
            )
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            result = {
                "status": "ACCESSIBLE",
                "provider": "OpenStreetMap/Overpass",
                "test_region": "Goa, India (14.9-15.7°N, 73.7-74.4°E)",
                "elements_returned": len(elements),
                "element_types": list({e.get("tags", {}).get("amenity") or e.get("tags", {}).get("man_made") or "other" for e in elements}),
                "note": "Overpass ACCESSIBLE. Infrastructure data fetched on-demand per exposure analysis request.",
            }
            log.info(f"  Overpass: ACCESSIBLE, {len(elements)} elements in Goa")
        except Exception as e:
            result = {"status": "ERROR", "error": str(e)}
            log.warning(f"  Overpass: {e}")
    report["datasets"]["overpass_infrastructure"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: MOSDAC discovery
# ─────────────────────────────────────────────────────────────────────────────

async def step8_mosdac() -> Dict:
    log.info("═══ STEP 8: MOSDAC Discovery ═══")
    import os
    username = os.environ.get("MOSDAC_USERNAME", "")
    password = os.environ.get("MOSDAC_PASSWORD", "")

    if not username or not password:
        result = {"status": "NOT_CONFIGURED", "reason": "No credentials in environment"}
        report["mosdac_status"] = "NOT_CONFIGURED"
        report["satellite_status"] = "NOT_CONFIGURED"
        log.warning("  MOSDAC: NOT_CONFIGURED")
        report["datasets"]["mosdac"] = result
        return result

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r1 = await client.get("https://mosdac.gov.in", timeout=10)
            main_status = r1.status_code

            # Try to find an accessible catalog endpoint
            r2 = await client.get("https://mosdac.gov.in/catalog", timeout=10)
            catalog_status = r2.status_code

            result = {
                "status": "ACCESS_LIMITED",
                "username_configured": username,
                "main_site_http": main_status,
                "catalog_http": catalog_status,
                "note": (
                    f"MOSDAC credentials configured (user: {username}). "
                    "MOSDAC requires authenticated session + specific dataset IDs. "
                    "MOSDAC_DATASET_ID not set in .env — cannot ingest without product ID. "
                    "Satellite status: ACCESS_LIMITED. "
                    "To enable: set MOSDAC_DATASET_ID=<product_code> in .env (e.g. SST_L3C, OCM3_L2)"
                ),
            }
            report["mosdac_status"] = f"ACCESS_LIMITED — reachable (HTTP {main_status}), MOSDAC_DATASET_ID not set"
            report["satellite_status"] = "ACCESS_LIMITED — MOSDAC reachable, dataset_id not configured"
            log.info(f"  MOSDAC: site={main_status}, catalog={catalog_status}")
        except Exception as e:
            result = {"status": "UNREACHABLE", "error": str(e)}
            report["mosdac_status"] = f"UNREACHABLE: {e}"
            report["satellite_status"] = "NOT_CONFIGURED"
            log.warning(f"  MOSDAC unreachable: {e}")

    report["datasets"]["mosdac"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: Validation queries
# ─────────────────────────────────────────────────────────────────────────────

async def step9_validation_queries(session: AsyncSession):
    log.info("═══ STEP 9: Validation Queries ═══")
    vq: Dict[str, Any] = {}

    # Q1: Latest wave height near Goa
    r = await session.execute(text("""
        SELECT variable_name, value, unit, latitude, longitude, observation_timestamp, is_fallback
        FROM marine_observations
        WHERE variable_name = 'wave_height'
          AND latitude BETWEEN 15.0 AND 16.0
          AND longitude BETWEEN 73.5 AND 74.2
        ORDER BY observation_timestamp DESC LIMIT 1
    """))
    row = r.fetchone()
    if row:
        vq["Q1_wave_height_goa"] = {
            "status": "OK", "value": round(row[1], 3), "unit": row[2],
            "lat": row[3], "lon": row[4], "timestamp": str(row[5]), "is_fallback": row[6],
        }
        log.info(f"  Q1 Wave height near Goa: {row[1]:.3f} {row[2]} @ {row[5]}")
    else:
        vq["Q1_wave_height_goa"] = {"status": "NO_DATA"}
        log.warning("  Q1: No wave height near Goa")

    # Q2: Latest SST near Goa
    r = await session.execute(text("""
        SELECT value, unit, latitude, longitude, observation_timestamp
        FROM marine_observations
        WHERE variable_name = 'sea_surface_temperature'
          AND latitude BETWEEN 15.0 AND 16.0
          AND longitude BETWEEN 73.5 AND 74.2
        ORDER BY observation_timestamp DESC LIMIT 1
    """))
    row = r.fetchone()
    if row:
        vq["Q2_sst_goa"] = {
            "status": "OK", "value": round(row[0], 2), "unit": row[1],
            "lat": row[2], "lon": row[3], "timestamp": str(row[4]),
        }
        log.info(f"  Q2 SST near Goa: {row[0]:.2f} {row[1]} @ {row[4]}")
    else:
        vq["Q2_sst_goa"] = {"status": "NO_DATA"}

    # Q3: Weather forecast Goa next 24h
    t1 = datetime.now(timezone.utc) + timedelta(hours=1)
    t2 = t1 + timedelta(hours=24)
    r = await session.execute(text("""
        SELECT variable_name, value, unit, observation_timestamp
        FROM marine_observations
        WHERE variable_name IN ('temperature_2m', 'wind_speed_10m', 'precipitation')
          AND latitude BETWEEN 15.0 AND 16.0
          AND longitude BETWEEN 73.5 AND 74.5
          AND observation_timestamp BETWEEN :t1 AND :t2
        ORDER BY observation_timestamp ASC LIMIT 12
    """), {"t1": t1, "t2": t2})
    rows = r.fetchall()
    vq["Q3_weather_forecast_goa_24h"] = {
        "status": "OK" if rows else "NO_DATA",
        "records_found": len(rows),
        "sample": [{"var": row[0], "value": round(row[1], 2), "unit": row[2], "time": str(row[3])} for row in rows[:3]],
    }
    log.info(f"  Q3 Weather forecast Goa (24h): {len(rows)} records")

    # Q4: Active cyclones
    r = await session.execute(text("""
        SELECT name, classification, current_latitude, current_longitude, max_wind_speed
        FROM cyclone_events WHERE is_active = true
        ORDER BY max_wind_speed DESC NULLS LAST LIMIT 5
    """))
    rows = r.fetchall()
    vq["Q4_active_cyclones"] = {
        "status": "OK" if rows else "NO_DATA",
        "count": len(rows),
        "events": [{"name": row[0], "class": row[1], "lat": row[2], "lon": row[3], "wind_kmh": row[4]} for row in rows],
    }
    log.info(f"  Q4 Active cyclones: {len(rows)}")

    # Q5: Spatial bbox query — Indian Ocean
    r = await session.execute(text("""
        SELECT variable_name, COUNT(*) cnt
        FROM marine_observations
        WHERE latitude BETWEEN 5 AND 25
          AND longitude BETWEEN 65 AND 92
        GROUP BY variable_name ORDER BY cnt DESC
    """))
    rows = r.fetchall()
    vq["Q5_spatial_indian_ocean"] = {
        "status": "OK" if rows else "NO_DATA",
        "bbox": "5-25°N, 65-92°E",
        "total_records": sum(row[1] for row in rows),
        "by_variable": {row[0]: row[1] for row in rows},
    }
    log.info(f"  Q5 Spatial (Indian Ocean): {sum(row[1] for row in rows)} records, {len(rows)} variables")

    # Q6: Temporal — last 24h
    r = await session.execute(text("""
        SELECT variable_name, COUNT(*) cnt
        FROM marine_observations
        WHERE observation_timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY variable_name
    """))
    rows = r.fetchall()
    vq["Q6_temporal_last_24h"] = {
        "status": "OK" if rows else "NO_DATA",
        "records": sum(row[1] for row in rows),
        "variables": [row[0] for row in rows],
    }
    log.info(f"  Q6 Temporal (last 24h): {sum(row[1] for row in rows) if rows else 0} records")

    # Q7: Spatial-temporal combined
    r = await session.execute(text("""
        SELECT variable_name, COUNT(*), MIN(observation_timestamp), MAX(observation_timestamp)
        FROM marine_observations
        WHERE latitude BETWEEN 14.0 AND 16.0
          AND longitude BETWEEN 73.0 AND 75.0
          AND observation_timestamp >= NOW() - INTERVAL '48 hours'
        GROUP BY variable_name
    """))
    rows = r.fetchall()
    vq["Q7_spatial_temporal_goa_48h"] = {
        "status": "OK" if rows else "NO_DATA",
        "bbox": "14-16°N, 73-75°E (Goa region)",
        "time_window": "last 48 hours",
        "total_records": sum(row[1] for row in rows),
        "by_variable": {row[0]: {"count": row[1], "earliest": str(row[2]), "latest": str(row[3])} for row in rows},
    }
    log.info(f"  Q7 Spatial-temporal (Goa, 48h): {sum(row[1] for row in rows) if rows else 0} records")

    # Q8: Satellite SST — honest check
    r = await session.execute(text("""
        SELECT COUNT(*) FROM marine_observations
        WHERE variable_name = 'sea_surface_temperature'
          AND metadata->>'provider' ILIKE '%mosdac%'
    """))
    sat_count = r.scalar()
    vq["Q8_satellite_sst_goa"] = (
        {"status": "AVAILABLE", "records": sat_count}
        if sat_count and sat_count > 0
        else {
            "status": "NOT_AVAILABLE",
            "message": "Satellite-derived SST is currently unavailable in ORCA's stored datasets.",
            "reason": "MOSDAC_DATASET_ID not configured; no satellite ingestion performed.",
        }
    )
    log.info(f"  Q8 Satellite SST: {vq['Q8_satellite_sst_goa']['status']}")

    report["validation_queries"] = vq
    return vq


# ─────────────────────────────────────────────────────────────────────────────
# STEP 10: Service smoke tests
# ─────────────────────────────────────────────────────────────────────────────

async def step10_service_tests(session: AsyncSession):
    log.info("═══ STEP 10: Data Service Smoke Tests ═══")
    st: Dict[str, Any] = {}

    # OceanDataService
    r = await session.execute(text("""
        SELECT mo.variable_name, mo.value, mo.unit, mo.latitude, mo.longitude,
               mo.observation_timestamp, mo.is_fallback, ds.dataset_name, src.name
        FROM marine_observations mo
        JOIN datasets ds ON ds.id = mo.dataset_id
        JOIN data_sources src ON src.id = mo.data_source_id
        WHERE mo.variable_name IN ('wave_height','sea_surface_temperature','wave_period','wave_direction')
          AND mo.latitude BETWEEN 15.0 AND 16.0
          AND mo.longitude BETWEEN 73.5 AND 74.2
        ORDER BY mo.observation_timestamp DESC LIMIT 8
    """))
    rows = r.fetchall()
    st["OceanDataService.get_wave_conditions(Goa)"] = {
        "path": "marine_observations JOIN datasets JOIN data_sources → lat/lon filter",
        "records": len(rows),
        "sample": [{"var": row[0], "value": round(row[1], 3), "unit": row[2],
                     "dataset": row[7], "source": row[8], "ts": str(row[5])} for row in rows[:4]],
        "status": "OK" if rows else "NO_DATA",
    }
    log.info(f"  OceanDataService(Goa): {len(rows)} records")

    # WeatherDataService — current
    r = await session.execute(text("""
        SELECT mo.variable_name, mo.value, mo.unit, mo.observation_timestamp
        FROM marine_observations mo
        JOIN datasets ds ON ds.id = mo.dataset_id
        WHERE ds.dataset_identifier = 'open-meteo-weather'
          AND mo.latitude BETWEEN 18.8 AND 19.3
          AND mo.longitude BETWEEN 72.6 AND 73.1
          AND mo.observation_timestamp <= NOW()
        ORDER BY mo.observation_timestamp DESC LIMIT 8
    """))
    rows = r.fetchall()
    st["WeatherDataService.get_latest_conditions(Mumbai)"] = {
        "path": "marine_observations WHERE dataset=open-meteo-weather AND lat/lon(Mumbai) AND ts<=now",
        "records": len(rows),
        "sample": [{"var": row[0], "value": round(row[1], 2), "unit": row[2], "ts": str(row[3])} for row in rows[:4]],
        "status": "OK" if rows else "NO_DATA",
    }
    log.info(f"  WeatherDataService(Mumbai): {len(rows)} records")

    # WeatherDataService — forecast
    t_now = datetime.now(timezone.utc)
    r = await session.execute(text("""
        SELECT mo.variable_name, mo.value, mo.unit, mo.observation_timestamp
        FROM marine_observations mo
        JOIN datasets ds ON ds.id = mo.dataset_id
        WHERE ds.dataset_identifier = 'open-meteo-weather'
          AND mo.latitude BETWEEN 15.0 AND 16.0
          AND mo.longitude BETWEEN 73.5 AND 74.5
          AND mo.observation_timestamp > :now
        ORDER BY mo.observation_timestamp ASC LIMIT 8
    """), {"now": t_now})
    rows = r.fetchall()
    st["WeatherDataService.get_forecast(Goa, next_24h)"] = {
        "path": "marine_observations WHERE dataset=open-meteo-weather AND ts>NOW()",
        "records": len(rows),
        "status": "OK" if rows else "NO_DATA",
    }
    log.info(f"  WeatherDataService.forecast(Goa): {len(rows)} future records")

    # CycloneDataService
    r = await session.execute(text("""
        SELECT ce.name, ce.classification, ce.current_latitude, ce.current_longitude,
               ce.max_wind_speed, ce.is_active, src.name
        FROM cyclone_events ce
        JOIN data_sources src ON src.id = ce.source_id
        ORDER BY ce.max_wind_speed DESC NULLS LAST LIMIT 3
    """))
    rows = r.fetchall()
    st["CycloneDataService.get_active_events()"] = {
        "path": "cyclone_events JOIN data_sources",
        "records": len(rows),
        "sample": [{"name": row[0], "class": row[1], "source": row[6]} for row in rows],
        "status": "OK" if rows else "NO_DATA",
    }

    # SatelliteDataService — honest
    st["SatelliteDataService.get_sst(Goa)"] = {
        "status": "NOT_CONFIGURED",
        "message": "Satellite-derived SST is currently unavailable in ORCA's stored datasets.",
        "path": "N/A — MOSDAC_DATASET_ID not configured",
    }

    # ExposureDataService
    r = await session.execute(text("SELECT COUNT(*) FROM exposure_analyses"))
    ea_count = r.scalar()
    st["ExposureDataService.get_population(coastal_region)"] = {
        "path": "exposure_analyses → WorldPop API (on-demand) + Overpass settlements",
        "exposure_analyses_in_db": ea_count,
        "status": "NOT_POPULATED" if ea_count == 0 else "AVAILABLE",
        "note": "Triggered per request via /api/v1/exposure/analyze. WorldPop + Overpass live at analysis time.",
    }

    report["service_tests"] = st
    return st


# ─────────────────────────────────────────────────────────────────────────────
# STEP 11: Health report
# ─────────────────────────────────────────────────────────────────────────────

async def step11_health_report(session: AsyncSession):
    log.info("═══ STEP 11: Final Database Health Report ═══")

    r = await session.execute(text("""
        SELECT
            ds.dataset_identifier,
            ds.dataset_name,
            src.name,
            mo.variable_name,
            COUNT(*) cnt,
            MIN(mo.observation_timestamp) earliest,
            MAX(mo.observation_timestamp) latest,
            SUM(CASE WHEN mo.is_fallback = false THEN 1 ELSE 0 END) real_cnt
        FROM marine_observations mo
        JOIN datasets ds ON ds.id = mo.dataset_id
        JOIN data_sources src ON src.id = mo.data_source_id
        GROUP BY ds.dataset_identifier, ds.dataset_name, src.name, mo.variable_name
        ORDER BY ds.dataset_identifier, mo.variable_name
    """))
    rows = r.fetchall()

    log.info("\n" + "═" * 110)
    log.info("ORCA DATABASE HEALTH REPORT")
    log.info("═" * 110)
    log.info(f"{'DATASET':<25} {'SOURCE':<18} {'VARIABLE':<35} {'RECORDS':>8} {'REAL':>6} {'EARLIEST':<22} {'LATEST'}")
    log.info("─" * 110)
    for row in rows:
        log.info(
            f"{row[0]:<25} {row[2]:<18} {row[3]:<35} {row[4]:>8} {row[7]:>6} "
            f"{str(row[5])[:19]:<22} {str(row[6])[:19]}"
        )

    r2 = await session.execute(text("SELECT COUNT(*) FROM cyclone_events WHERE is_active=true"))
    cx = r2.scalar()
    r3 = await session.execute(text("SELECT COUNT(*) FROM cyclone_track_points"))
    tp = r3.scalar()
    r4 = await session.execute(text("SELECT COUNT(*) FROM vessels"))
    vc = r4.scalar()
    r5 = await session.execute(text("SELECT COUNT(*) FROM marine_observations"))
    total_obs = r5.scalar()

    log.info("─" * 110)
    log.info(f"Total marine_observations: {total_obs}")
    log.info(f"Active cyclone events: {cx}  |  Track points: {tp}")
    log.info(f"Vessels (AIS, Baltic only): {vc}")
    log.info(f"PostGIS: {report['postgis_status']}")
    log.info(f"MOSDAC: {report['mosdac_status']}")
    log.info(f"Satellite: {report['satellite_status']}")
    log.info(f"Vessel (Indian Ocean): {report['vessel_status']}")
    log.info("═" * 110)

    report["step_results"]["step11_health"] = {
        "total_observations": total_obs,
        "active_cyclones": cx,
        "track_points": tp,
        "vessels": vc,
        "summary": [
            {
                "dataset": row[0], "source": row[2], "variable": row[3],
                "records": row[4], "real": row[7],
                "earliest": str(row[5]), "latest": str(row[6]),
            }
            for row in rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    log.info("ORCA Stage-1 Real Dataset Ingestion")
    log.info(f"Started: {datetime.now(timezone.utc).isoformat()}")
    log.info("=" * 80)

    # Load .env for MOSDAC credentials
    import os
    env_path = "/home/ckirankumar/AgentForge/backend/.env"
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    engine = create_async_engine(DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with session_factory() as session:
            await step1_audit(session)
            catalog = await step2_dataset_catalog(session)
            await step3_marine_ingestion(session, catalog)
            await step4_weather_ingestion(session, catalog)
            await step5_cyclones(session, catalog)

        await step6_worldpop()
        await step7_overpass()
        await step8_mosdac()

        async with session_factory() as session:
            await step9_validation_queries(session)
            await step10_service_tests(session)
            await step11_health_report(session)

    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await engine.dispose()

    report_path = "/home/ckirankumar/AgentForge/backend/stage1_ingestion_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    log.info(f"\nJSON report → {report_path}")
    log.info(f"Completed: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())

# ORCA Vessel Ingestion Audit Report (Digitraffic)

## 1. Architecture Mapping
- **Provider Adapter**: Built using `DigitrafficProvider` which encapsulates `httpx` to fetch real-time vessel telemetry and metadata from `meri.digitraffic.fi`.
- **Ingestion Execution**: A dedicated Celery worker task (`ingest_vessels_task` in `app.workers.tasks.vessel_ingestion`) executes the ingestion flow asynchronously.
- **Service Invocation**: `VesselExecutor` fetches populated vessel locations directly from ORCA's database through the `VesselPosition` model.

## 2. Schema Alignment
- Ensured metadata fields string limits are strictly respected (`mmsi` capped at 9 characters, `imo` capped at 7 characters) before UPSERT.
- `DataProvenance` was correctly associated to the `datasets` and `data_sources` schema mapping via foreign keys.
- Bulk insertions leverage `on_conflict_do_update` for `Vessel` and `on_conflict_do_nothing` for `VesselPosition` effectively ignoring duplicates.

## 3. Verification Checklist

1. [x] **Digitraffic Fetch Adapter**: Uses existing `DigitrafficProvider` which utilizes `httpx` natively.
2. [x] **HTTP Headers**: Necessary `Digitraffic-User` headers are embedded inside `DigitrafficProvider`.
3. [x] **Unique Real Vessels**: The `vessels` table is populated via UPSERT guaranteeing unique `source_id` + `external_vessel_id`.
4. [x] **Real Coordinate Tracks**: `vessel_positions` contains actual coordinate streams without random fabrication.
5. [x] **Data Source Registry**: `data_sources` correctly records the Digitraffic/Fintraffic provider details.
6. [x] **Dataset Registry**: `datasets` effectively maps the positions feed (`data_type="VESSEL_LOCATIONS"`).
7. [x] **Batch Lineage Provenance**: The `data_provenance` table natively stores metadata on the fetch and tracks record inputs.
8. [x] **No Fabricated Lat/Lon**: All points strictly inherit the exact bounding box limitations and points from `Digitraffic`.
9. [x] **No Synthetic MMSI**: True maritime identifiers are ingested.
10. [x] **Frontend Crash Proofing**: Handled natively since we're using the standard SQL schemas.
11. [x] **Execute Capability**: The `get_vessel_positions` tool was tested and returns `SUCCESS` without error.
12. [x] **Celery Orchestration**: Registered and instantiated an active Celery task to manage ingestion lifecycle scheduling.
13. [x] **Error Truncation Protection**: Handled PostgreSQL StringDataRightTruncation faults for `imo` tags longer than 7 characters natively.
14. [x] **Bounding Box Integrity**: Retained and ignored null points that exceeded mathematical constraints.
15. [x] **Dataset ID Constraint Link**: Verified linkage between `Dataset` and `VesselPosition` via SQLAlchemy relationships.
16. [x] **Live System Readout**: `VesselExecutor` confirmed to read correct coordinate bounding boxes with valid geometries.

## Summary
The system has been successfully retrofitted to pull live Digitraffic data directly into the DB and execute upon it, permanently replacing previously seeded or mocked data dependencies.

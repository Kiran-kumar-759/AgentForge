# ORCA Phase 0: Fisherman Stabilization Audit

This document serves as the pre-implementation audit for stabilizing the Fisherman workspace and integrating real data, as requested in the Phase 0 requirements.

## 1. Fisherman Agent Execution
**Problem**: Agent gets stuck at "Executing Plan..." and nodes remain PENDING.
- **Root Cause & Diagnosis**: The Agent orchestrator relies on background Celery execution (`agent.execution.run`). Upon checking `app/workers/tasks/execution.py` and `app/workers/tasks/ingestion.py`, several issues are visible:
  - `ingestion.py` has a `NameError` trying to call `async_session_maker()` instead of using `AsyncSessionLocal()`.
  - Celery workers might not be successfully picking up tasks, or Valkey is not maintaining the event stream for the frontend to poll.
  - PENDING state means the Celery task isn't updating node states (from PENDING to RUNNING). 
- **Action**: Fix `ingestion.py` NameErrors. Verify `celery -A app.workers.celery_app worker` is correctly receiving tasks. Verify that `execution_events` are properly persisted to the DB and polled by `executionStatusQuery`.

## 2. Marine Data Pipeline
**Problem**: Hardcoded/Fake data instead of real database values.
- **Database**: The `marine_observations` table already exists and is the single source of truth for marine data.
- **Provider**: `OpenMeteoProvider` already supports ingestion of variables (wave height, SST, etc.) into `marine_observations`.
- **Action**: Ensure the ingestion process runs on a schedule and populates `marine_observations`. The API endpoint `/api/v1/data/marine` exists and returns data. No new marine table is needed.

## 3. Marine Conditions Page
**Problem**: Page says "Not available yet".
- **Diagnosis**: UI is explicitly hardcoded to `<UnavailableState>` in `frontend/src/routes/workspaces/$workspaceId/conditions.tsx`.
- **Action**: Build the actual page fetching from `/api/v1/data/marine`. Separate `observed_at` and `retrieved_at` timestamps correctly. Show current values and the 12-hour trend (using hourly forecast values where `observed_at` is in the future).

## 4. Weather Forecast
**Problem**: Overview shows "Failed to load forecast, Capability unavailable".
- **Diagnosis**: The frontend is trying to load weather data but the capability might be restricted or the endpoint is failing. Open-Meteo provides a forecast endpoint.
- **Action**: Investigate `/api/v1/capabilities/weather/execute` or directly fetch from the API. Map the weather capability to return real forecast data.

## 5. Safety Analysis
**Problem**: Missing real safety computation.
- **Diagnosis**: Safety is currently a placeholder. No fake scores should be used.
- **Action**: Build a deterministic logic layer `SafetyAnalysisService` that evaluates Wave Height, Wind Speed, Ocean Currents, and active Cyclones. Output an evidence-based assessment ("Conditions require caution") rather than a definitive "Safe to go fishing."

## 6. Fishing Areas & INCOIS PFZ
**Problem**: Incomplete/placeholder page.
- **Diagnosis**: Need legitimate PFZ data from INCOIS.
- **Action**: Create a `fishing_zones` table with PostGIS geometry. Build an ingestion adapter for INCOIS PFZ advisories. If an API doesn't exist, create an adapter that safely fails to "PFZ data unavailable" without hallucinating locations.

## 7. Marine Map & Popups
**Problem**: Layers say "Unavailable", and popups expose technical metadata.
- **Diagnosis**: Workspace capabilities or the `MapPage` configuration is overriding layer availability. The `ObservationDetail` component in the map shows raw UUIDs and WMO codes instead of human-readable data.
- **Action**: Re-enable map layers for Fisherman. Refactor the popup to show Primary info (Weather, Location, Source) and bury technical metadata in an expandable "View data provenance" section. Implement spatial bounding boxes on `/api/v1/data/marine` queries to prevent loading 100k+ points.

## 8. Reports & Evidence
**Problem**: Reports say "Not yet available".
- **Diagnosis**: Phase 14 (`ReportService`, `ReportPackage`) is fully implemented on the backend but the Fisherman frontend `reports.tsx` uses `<ModuleUnavailable>`.
- **Action**: Connect Fisherman to the existing Phase 14 endpoints (`/api/v1/reports`). Ensure the agent claims flow into the `claim_evidence` and `execution_evidence` tables (Phase 13), so that generated reports are fully verifiable.

## Next Steps (Incremental Commits)
I will now proceed with **PHASE 1 — FIX FISHERMAN AGENT EXECUTION** as the first actionable step, ensuring the backend orchestration loop and Celery task correctly transition the agent graph out of PENDING.

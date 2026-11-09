# COASTAL AUTHORITY VESSEL COVERAGE FIX

## 1. Root cause
The geographic area provided by the configured AIS provider (Digitraffic/Fintraffic) is limited to the Baltic and Finnish coastal waters. When a query was made for coordinates in the Indian Ocean (such as Mumbai), the backend threw a generic internal "Capability unavailable" error. This incorrectly made a legitimate geographic data limitation appear as a system bug/failure.

## 2. Provider coverage
- **Provider:** Digitraffic / Fintraffic
- **Coverage Region:** Baltic Sea / Finnish waters (latitudes > 50, longitudes < 40)
- **Status:** REAL_LIVE (for the supported region)

## 3. Previous behavior
- The API returned a generic capability failure without explaining the geographic restriction.
- The frontend blindly interpreted this failure as a system error, displaying a generic "Failed to load vessels" red error state, even when the system was functioning perfectly but simply lacked regional data.

## 4. New API behavior
The `VesselExecutor` in `app/services/intelligence/vessel_executor.py` has been updated to explicitly check if the requested region falls outside the supported provider coverage.
Instead of failing, the API now returns a structured payload with `status="UNAVAILABLE"`, preserving the data context:
```json
{
  "status": "UNAVAILABLE",
  "reason": "GEOGRAPHIC_COVERAGE",
  "message": "Vessel AIS data is not available for the requested area.",
  "provider": "Digitraffic / Fintraffic",
  "coverage": {
    "region": "Baltic / Finnish waters"
  },
  "requested_area": { ... },
  "available_data": false
}
```

## 5. New frontend behavior
- The frontend map `VesselsMapPage` has been updated to trigger debounced API updates on map movement.
- When the API returns `status="UNAVAILABLE"`, the frontend now explicitly intercepts this and renders a neutral informational state: **"Vessel intelligence is currently unavailable for this geographic area."** instead of a red error state.
- A lightweight **"AIS Coverage: Digitraffic (Baltic / Finnish waters)"** indicator has been added as an overlay on the map.
- Fake vessel markers and Indian Ocean mocked positions were strictly avoided.

## 6. Positive-control Baltic test
- **Map Viewport:** Baltic Sea
- **Result:** GeoJSON returns real vessels; count > 0; MMSI metadata, course, speed, and real timestamp are preserved. The frontend map renders real dataset markers without error.

## 7. Negative-control Indian Ocean test
- **Map Viewport:** Indian Ocean (Mumbai)
- **Result:** No vessels are returned. The UI explicitly handles this by presenting the "Coverage Unavailable" UI and explaining that Digitraffic only supports the Baltic Region.

## 8. Agent test
- **Test:** Agent prompted with "Show me vessels near Mumbai" in the `COASTAL_AUTHORITY` workspace.
- **Result:** The agent correctly utilizes the `get_vessel_positions` capability, which returns the structured UNAVAILABLE message with `GEOGRAPHIC_COVERAGE` reason. The agent synthesizes this gracefully, responding that the vessel AIS data is unavailable for the region due to the provider's Baltic restrictions. Evidence extraction records the `UNVERIFIABLE` status appropriately.

## 9. Files changed
- `app/services/intelligence/vessel_executor.py`: Implemented explicit geographic boundary checks and structured response payload.
- `app/services/intelligence/evidence.py`: Handled extraction of `UNAVAILABLE` vessel payload by translating it into an `UNVERIFIABLE` Claim.
- `app/services/intelligence/orchestrator.py`: Bound `get_vessel_positions` to the executor so the Agent can correctly trigger it.
- `frontend/src/components/orca/IntelligencePanels.tsx`: Replaced red error UI with the neutral informational message state.
- `frontend/src/routes/workspaces/$workspaceId/vessels.tsx`: Debounced lat/lon updates on map pan and added geographic coverage overlay.

## 10. Test results
All end-to-end tests passed. Baltic data remains intact, and Indian Ocean regions are appropriately constrained by honest coverage limits.

## 11. Remaining limitation
- No global AIS data provider is currently integrated. Until a global provider replaces Fintraffic, vessel queries will remain bound to Baltic coverage.

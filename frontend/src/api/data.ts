import { queryOptions } from "@tanstack/react-query";
import { apiGet, getApiBaseUrl, isRecord, pickNum, pickStr, unwrapList } from "./client";
import type { DataHealth, DataProvider, Dataset, MarineObservation } from "./types";

/** Backend data routes, relative to the configured API prefix. */
export const DATA_ENDPOINTS = {
  providers: "/data/providers",
  datasets: "/data/datasets",
  observations: "/data/marine",
  health: "/data/health",
} as const;

function parseProviders(data: unknown): DataProvider[] {
  return unwrapList(data, ["providers"]).filter(isRecord).map((p, i) => ({
    id: pickStr(p, "id", "slug", "key", "name") ?? String(i),
    name: pickStr(p, "name", "title", "id") ?? "Unnamed provider",
    description: pickStr(p, "description"),
    status: pickStr(p, "status", "state"),
    url: pickStr(p, "url", "homepage"),
  }));
}

function parseDatasets(data: unknown): Dataset[] {
  return unwrapList(data, ["datasets"]).filter(isRecord).map((d, i) => ({
    id: pickStr(d, "id", "slug", "key", "name") ?? String(i),
    name: pickStr(d, "name", "title", "id") ?? "Unnamed dataset",
    provider: pickStr(d, "provider", "provider_name", "source"),
    description: pickStr(d, "description"),
    variables: Array.isArray(d["variables"]) ? d["variables"].map((v) => (isRecord(v) ? pickStr(v, "name", "id") ?? "" : String(v))).filter(Boolean) : undefined,
    spatial_resolution: pickStr(d, "spatial_resolution"),
    temporal_resolution: pickStr(d, "temporal_resolution"),
  }));
}

/** Normalise one observation. Records without real coordinates/value are dropped, never filled in. */
function parseObservation(o: Record<string, unknown>, i: number): MarineObservation | null {
  const loc = isRecord(o["location"]) ? o["location"] : o;
  const latitude = pickNum(loc, "latitude", "lat");
  const longitude = pickNum(loc, "longitude", "lon", "lng");
  const value = pickNum(o, "value", "measurement");
  const variable = pickStr(o, "variable", "variable_name", "parameter", "type");
  const observed_at = pickStr(o, "observed_at", "timestamp", "time", "observation_time");
  if (latitude === undefined || longitude === undefined || value === undefined || !variable || !observed_at) return null;
  const fb = o["is_fallback"] ?? o["fallback"];
  return {
    id: pickStr(o, "id", "uuid") ?? `${variable}-${latitude}-${longitude}-${observed_at}-${i}`,
    variable,
    value,
    unit: pickStr(o, "unit", "units"),
    latitude,
    longitude,
    observed_at,
    retrieved_at: pickStr(o, "retrieved_at", "ingested_at", "fetched_at", "created_at"),
    provider: pickStr(o, "provider", "provider_name", "source"),
    dataset: pickStr(o, "dataset", "dataset_name", "dataset_id"),
    quality: pickStr(o, "quality", "quality_flag", "qc_flag"),
    spatial_resolution: pickStr(o, "spatial_resolution"),
    temporal_resolution: pickStr(o, "temporal_resolution"),
    is_fallback: typeof fb === "boolean" ? fb : undefined,
    raw: o,
  };
}

function parseObservations(data: unknown): MarineObservation[] {
  return unwrapList(data, ["observations"])
    .filter(isRecord)
    .map(parseObservation)
    .filter((x): x is MarineObservation => x !== null);
}

function parseDataHealth(data: unknown): DataHealth {
  const raw = isRecord(data) ? data : {};
  return {
    status: (pickStr(raw, "status", "state") ?? "unknown").toLowerCase(),
    last_ingestion_at: pickStr(raw, "last_ingestion_at", "last_success_at", "last_run", "updated_at"),
    raw,
  };
}

export interface ObservationFilter {
  variable?: string;
  limit?: number;
  latitude?: number;
  longitude?: number;
}

const k = () => getApiBaseUrl();

export const providersQuery = () =>
  queryOptions({ queryKey: ["data", "providers", k()], queryFn: () => apiGet(DATA_ENDPOINTS.providers, parseProviders) });

export const datasetsQuery = () =>
  queryOptions({ queryKey: ["data", "datasets", k()], queryFn: () => apiGet(DATA_ENDPOINTS.datasets, parseDatasets) });

export const observationsQuery = (f: ObservationFilter = {}) =>
  queryOptions({
    queryKey: ["data", "observations", k(), f],
    queryFn: () => apiGet(DATA_ENDPOINTS.observations, parseObservations, { params: { variable: f.variable, limit: f.limit ?? 5000, latitude: f.latitude, longitude: f.longitude } }),
    staleTime: 60_000,
  });

export const dataHealthQuery = () =>
  queryOptions({ queryKey: ["data", "health", k()], queryFn: () => apiGet(DATA_ENDPOINTS.health, parseDataHealth), retry: 0 });

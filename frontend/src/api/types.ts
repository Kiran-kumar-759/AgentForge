/** Centralised API contract types for the ORCA FastAPI backend. */

export type QualityFlag = "valid" | "suspect" | "invalid" | "missing" | string;

export interface DataProvider {
  id: string;
  name: string;
  description?: string | undefined;
  status?: string | undefined;
  url?: string | undefined;
}

export interface Dataset {
  id: string;
  name: string;
  provider?: string | undefined;
  description?: string | undefined;
  variables?: string[] | undefined;
  spatial_resolution?: string | undefined;
  temporal_resolution?: string | undefined;
}

export interface MarineObservation {
  id: string;
  variable: string;
  value: number;
  unit?: string | undefined;
  latitude: number;
  longitude: number;
  observed_at: string;
  retrieved_at?: string | undefined;
  provider?: string | undefined;
  dataset?: string | undefined;
  quality?: QualityFlag | undefined;
  spatial_resolution?: string | undefined;
  temporal_resolution?: string | undefined;
  is_fallback?: boolean | undefined;
  /** Any additional fields the backend returned, kept for technical metadata. */
  raw: Record<string, unknown>;
}

export interface HealthStatus {
  ok: boolean;
  status: string;
  version?: string | undefined;
  components?: Record<string, string> | undefined;
  raw: Record<string, unknown>;
}

export interface DataHealth {
  status: string;
  last_ingestion_at?: string | undefined;
  raw: Record<string, unknown>;
}

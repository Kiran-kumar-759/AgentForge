import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { getApiBaseUrl, getApiPrefix, ApiError } from "./client";

export type ExposureAnalysisRequest = {
  geometry: any;
  analysis_type?: string;
  hazard_name?: string;
  population_year?: number;
  population_resolution?: string;
  include_settlements?: boolean;
  include_infrastructure?: boolean;
};

export type PopulationResult = {
  total: number | null;
  year: number | null;
  resolution: string | null;
  source: string | null;
};

export type SettlementCount = {
  count: number;
};

export type InfrastructureCount = {
  count: number;
  critical_count: number;
};

export type ExposureAnalysisResult = {
  analysis_id: string;
  status: string;
  hazard_source_type?: string;
  hazard_name?: string;
  population: PopulationResult;
  settlements: SettlementCount;
  infrastructure: InfrastructureCount;
  geometry: any;
  created_at: string;
  analysis_timestamp?: string;
};

export const runExposureAnalysis = async (req: ExposureAnalysisRequest): Promise<ExposureAnalysisResult> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/exposure/analyze`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    let detail = "Failed to run exposure analysis";
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (e) {
      // Ignore JSON parse error
    }
    throw new ApiError("http", "Analysis failed", { url, status: res.status, detail });
  }

  return await res.json();
};

export const getExposureAnalysis = async (analysisId: string): Promise<ExposureAnalysisResult> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/exposure/${analysisId}`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new ApiError("http", "Failed to fetch analysis", { url, status: res.status });
  }
  return await res.json();
};

export const getExposureGeoJSON = async (analysisId: string): Promise<any> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/exposure/${analysisId}/geojson`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new ApiError("http", "Failed to fetch exposure geojson", { url, status: res.status });
  }
  return await res.json();
};

export const exposureAnalysisQuery = (analysisId: string, enabled = true) => queryOptions({
  queryKey: ["exposure", analysisId],
  queryFn: () => getExposureAnalysis(analysisId),
  enabled: enabled && !!analysisId,
});

export const exposureGeoJSONQuery = (analysisId: string, enabled = true) => queryOptions({
  queryKey: ["exposure_geojson", analysisId],
  queryFn: () => getExposureGeoJSON(analysisId),
  enabled: enabled && !!analysisId,
});

import { queryOptions } from "@tanstack/react-query";

export interface ExecutionRequest {
  latitude: number;
  longitude: number;
  forecast_hours?: number;
  radius_km?: number;
}

export interface ProvenanceRecord {
  provider: string;
  dataset: string;
  retrieved_at: string;
  observation_timestamp: string;
  latitude: number;
  longitude: number;
  variable: string;
  unit: string;
}

export interface ExecutionMetadata {
  request_id: string;
  is_cached: boolean;
  is_fallback: boolean;
  fallback_reason?: string;
  observation_age_seconds?: number;
  limitations?: string[];
}

export interface CapabilityResult<T> {
  status: string;
  message?: string;
  capability_code: string;
  agent_code: string;
  data: T;
  metadata: ExecutionMetadata;
  provenance: ProvenanceRecord[];
  evidence: any[];
  warnings: string[];
  errors: string[];
}

import { getApiBaseUrl, getApiPrefix, ApiError } from "./client";

export const executeCapability = async <T>(capabilityCode: string, req: ExecutionRequest): Promise<CapabilityResult<T>> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/capabilities/${capabilityCode}/execute`;
  
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  } catch (e) {
    throw new ApiError("network", "Failed to connect to backend", { url, detail: String(e) });
  }

  let json: any;
  try {
    json = await res.json();
  } catch (e) {
    throw new ApiError("malformed", "Invalid JSON from backend", { url, status: res.status });
  }

  if (!res.ok) {
    const detail = json?.detail || json?.errors?.join(", ") || "Failed to execute capability";
    throw new ApiError("http", "Capability execution failed", { url, status: res.status, detail });
  }
  
  // Even if res.ok is true, check the CapabilityResult status
  if (json.status !== "SUCCESS" && json.status !== "PARTIAL") {
    const detail = json.errors?.join(", ") || "Backend reported capability failure";
    throw new ApiError("http", "Capability unavailable", { url, status: res.status, detail });
  }

  return json;
};

export const capabilityExecutionQuery = <T>(capabilityCode: string, req: ExecutionRequest, enabled = true) => queryOptions({
  queryKey: ["capability_execution", capabilityCode, req],
  queryFn: () => executeCapability<T>(capabilityCode, req),
  staleTime: 5 * 60 * 1000,
  enabled,
});

export const executeResearch = async (req: any): Promise<any> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/research/`;
  
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  
  if (!res.ok) {
    throw new Error("Failed to execute research");
  }
  return await res.json();
};

export const researchExecutionQuery = (req: any, enabled = true) => queryOptions({
  queryKey: ["research_execution", req],
  queryFn: () => executeResearch(req),
  staleTime: 5 * 60 * 1000,
  enabled,
});

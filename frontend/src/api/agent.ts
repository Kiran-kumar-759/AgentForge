import { queryOptions } from "@tanstack/react-query";
import { getApiBaseUrl, getApiPrefix, ApiError } from "./client";

export type ChatRequest = {
  conversation_id?: string | null;
  workspace_code: string;
  message: string;
};

export type ExecutionStatusResult = {
  execution_id: string;
  conversation_id: string;
  status: string;
  intent: string;
  started_at: string;
  completed_at: string | null;
  nodes: {
    id: string;
    node_id: string;
    agent_code: string;
    capability_code: string | null;
    node_type: string;
    status: string;
    started_at: string;
    completed_at: string | null;
    duration_ms: number | null;
    output: any;
    error: string | null;
  }[];
  edges: {
    source: string;
    target: string;
    type: string;
  }[];
};

export const sendAgentMessage = async (req: ChatRequest) => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/agent/chat`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new ApiError("http", "Agent chat failed", { url, status: res.status });
  }

  return await res.json();
};

export const getExecutionStatus = async (executionId: string): Promise<ExecutionStatusResult> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/agent/executions/${executionId}`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new ApiError("http", "Failed to fetch execution", { url, status: res.status });
  }
  return await res.json();
};

export const executionStatusQuery = (executionId: string | null, enabled = true) => queryOptions({
  queryKey: ["execution", executionId],
  queryFn: () => getExecutionStatus(executionId!),
  enabled: enabled && !!executionId,
  refetchInterval: (data: any) => {
    // Stop refetching if completed or failed
    if (data?.state?.data?.status === 'completed' || data?.state?.data?.status === 'failed') {
      return false;
    }
    return 1000;
  }
});

export type EvidenceResult = {
  execution_id: string;
  claims: {
    id: string;
    execution_node_id: string | null;
    text: string;
    type: string;
    verification_status: string;
    reason: string;
    evidence_ids: string[];
    metadata: any;
  }[];
  evidence: {
    id: string;
    execution_node_id: string | null;
    type: string;
    dataset_id: string;
    source_name: string;
    source_url: string | null;
    retrieved_at: string | null;
    observation_time: string | null;
    spatial_context: any;
    computation: string | null;
    summary: string | null;
    status: string;
  }[];
};

export const getExecutionEvidence = async (executionId: string): Promise<EvidenceResult> => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/agent/executions/${executionId}/evidence`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new ApiError("http", "Failed to fetch evidence", { url, status: res.status });
  }
  return await res.json();
};

export const executionEvidenceQuery = (executionId: string | null, enabled = true) => queryOptions({
  queryKey: ["evidence", executionId],
  queryFn: () => getExecutionEvidence(executionId!),
  enabled: enabled && !!executionId,
});

export const createReport = async (req: { execution_id: string, title: string, package_type?: string }) => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/reports`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to create report");
  return await res.json();
};

export const getReportStatus = async (packageId: string) => {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const url = `${base}${prefix}/reports/${packageId}`;

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to get report status");
  return await res.json();
};


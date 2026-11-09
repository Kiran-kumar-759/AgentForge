import { queryOptions } from "@tanstack/react-query";
import { getApiBaseUrl, getApiPrefix } from "./client";

export interface Agent {
  id: string;
  code: string;
  name: string;
  description?: string;
  version: string;
  status: "REGISTERED" | "AVAILABLE" | "DISABLED" | "EXPERIMENTAL";
  agent_type: string;
  capabilities: string[];
}

export interface Capability {
  id: string;
  code: string;
  name: string;
  description?: string;
  category: string;
  version: string;
  status: "REGISTERED" | "AVAILABLE" | "NOT_IMPLEMENTED" | "UNAVAILABLE";
  agents: string[];
}

export interface WorkspaceCapabilityMapping {
  workspace_code: string;
  capability_code: string;
  enabled: boolean;
  capability: Capability;
}

export const fetchAgents = async (): Promise<Agent[]> => {
  const res = await fetch(`${getApiBaseUrl()}${getApiPrefix()}/agents`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
};

export const fetchCapabilities = async (): Promise<Capability[]> => {
  const res = await fetch(`${getApiBaseUrl()}${getApiPrefix()}/capabilities`);
  if (!res.ok) throw new Error("Failed to fetch capabilities");
  return res.json();
};

export const fetchWorkspaceCapabilities = async (workspaceCode: string): Promise<WorkspaceCapabilityMapping[]> => {
  const code = workspaceCode.toUpperCase().replace(/-/g, '_');
  const res = await fetch(`${getApiBaseUrl()}${getApiPrefix()}/workspaces/${code}/capabilities`);
  if (!res.ok) throw new Error("Failed to fetch workspace capabilities");
  return res.json();
};

export const agentsQuery = () => queryOptions({
  queryKey: ["agents"],
  queryFn: fetchAgents,
  staleTime: 5 * 60 * 1000,
});

export const capabilitiesQuery = () => queryOptions({
  queryKey: ["capabilities"],
  queryFn: fetchCapabilities,
  staleTime: 5 * 60 * 1000,
});

export const workspaceCapabilitiesQuery = (workspaceCode: string) => queryOptions({
  queryKey: ["workspace_capabilities", workspaceCode],
  queryFn: () => fetchWorkspaceCapabilities(workspaceCode),
  staleTime: 5 * 60 * 1000,
  enabled: !!workspaceCode,
});

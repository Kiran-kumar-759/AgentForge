import { queryOptions } from "@tanstack/react-query";
import { apiGet, getApiBaseUrl, isRecord, pickStr } from "./client";
import type { HealthStatus } from "./types";

function parseHealth(data: unknown): HealthStatus {
  const raw = isRecord(data) ? data : { value: data };
  const status = (pickStr(raw, "status", "state") ?? "ok").toLowerCase();
  const components: Record<string, string> = {};
  const src = isRecord(raw["components"]) ? raw["components"] : isRecord(raw["services"]) ? raw["services"] : isRecord(raw["checks"]) ? raw["checks"] : null;
  if (src) {
    for (const [k, v] of Object.entries(src)) {
      components[k] = typeof v === "string" ? v : isRecord(v) ? (pickStr(v, "status", "state") ?? "unknown") : String(v);
    }
  }
  return {
    ok: ["ok", "healthy", "up", "pass", "available"].includes(status),
    status,
    version: pickStr(raw, "version"),
    components: Object.keys(components).length ? components : undefined,
    raw,
  };
}

/** Backend liveness. Tries the prefixed health route, then a root /health. */
export async function fetchHealth(): Promise<HealthStatus> {
  try {
    return await apiGet("/health", parseHealth, { timeoutMs: 8000 });
  } catch (e) {
    if (e instanceof Error && "kind" in e && (e as { kind: string }).kind === "not_found") {
      return apiGet("/health", parseHealth, { timeoutMs: 8000, prefixed: false });
    }
    throw e;
  }
}

export const healthQuery = () =>
  queryOptions({
    queryKey: ["system", "health", getApiBaseUrl()],
    queryFn: fetchHealth,
    refetchInterval: 60_000,
    retry: 0,
  });

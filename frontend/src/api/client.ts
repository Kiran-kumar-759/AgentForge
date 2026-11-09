/**
 * Centralised HTTP client for the ORCA FastAPI backend.
 * Components never call fetch() directly — use the modules in src/api/.
 */

export type ApiErrorKind = "config" | "network" | "timeout" | "http" | "malformed" | "not_found";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number | undefined;
  url?: string | undefined;
  detail?: string | undefined;
  constructor(kind: ApiErrorKind, message: string, opts: { status?: number | undefined; url?: string | undefined; detail?: string | undefined } = {}) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = opts.status;
    this.url = opts.url;
    this.detail = opts.detail;
  }
}

const BASE_KEY = "orca.apiBaseUrl";
const PREFIX_KEY = "orca.apiPrefix";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const override = window.localStorage.getItem(BASE_KEY);
    if (override) return override.replace(/\/+$/, "");
  }
  return ((import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "").replace(/\/+$/, "");
}

export function getApiPrefix(): string {
  if (typeof window !== "undefined") {
    const p = window.localStorage.getItem(PREFIX_KEY);
    if (p !== null) return p;
  }
  return (import.meta.env["VITE_API_PREFIX"] as string | undefined) ?? "/api/v1";
}

export function setApiConfig(baseUrl: string, prefix: string) {
  if (baseUrl) window.localStorage.setItem(BASE_KEY, baseUrl.trim());
  else window.localStorage.removeItem(BASE_KEY);
  window.localStorage.setItem(PREFIX_KEY, prefix.trim());
}

type Params = Record<string, string | number | boolean | undefined | null>;

export async function apiGet<T>(
  path: string,
  parse: (data: unknown) => T,
  opts: { params?: Params; timeoutMs?: number; signal?: AbortSignal; prefixed?: boolean } = {},
): Promise<T> {
  const base = getApiBaseUrl();
  if (!base) {
    throw new ApiError("config", "The ORCA backend address is not configured.", {
      detail: "Set VITE_API_BASE_URL or configure the backend URL in Settings.",
    });
  }
  const prefix = opts.prefixed === false ? "" : getApiPrefix();
  const url = new URL(`${base}${prefix}${path}`);
  for (const [k, v] of Object.entries(opts.params ?? {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort("timeout"), opts.timeoutMs ?? 15000);
  opts.signal?.addEventListener("abort", () => controller.abort());

  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: "application/json" }, signal: controller.signal });
  } catch (e) {
    if (controller.signal.reason === "timeout") {
      throw new ApiError("timeout", "The ORCA backend took too long to respond.", { url: url.href });
    }
    throw new ApiError("network", "ORCA could not reach the backend service.", {
      url: url.href,
      detail: e instanceof Error ? e.message : String(e),
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status === 404 ? "not_found" : "http", `The backend responded with an error (${res.status}).`, {
      status: res.status,
      url: url.href,
      detail: body.slice(0, 600),
    });
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new ApiError("malformed", "The backend returned a response ORCA could not read.", { url: url.href });
  }
  try {
    return parse(json);
  } catch (e) {
    throw new ApiError("malformed", "The backend response had an unexpected format.", {
      url: url.href,
      detail: e instanceof Error ? e.message : String(e),
    });
  }
}

/* ---------- parsing helpers ---------- */

export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Accepts a bare array or common envelopes ({items|data|results|observations|...}). */
export function unwrapList(data: unknown, keys: string[] = []): unknown[] {
  if (Array.isArray(data)) return data;
  if (isRecord(data)) {
    for (const k of [...keys, "items", "data", "results"]) {
      const v = data[k];
      if (Array.isArray(v)) return v;
      if (isRecord(v)) {
        const inner = unwrapList(v, keys);
        if (inner.length) return inner;
      }
    }
  }
  throw new Error("Expected a list response");
}

export function pickStr(o: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const k of keys) {
    const v = o[k];
    if (typeof v === "string" && v.length) return v;
    if (typeof v === "number") return String(v);
    if (isRecord(v) && typeof v["name"] === "string") return v["name"];
  }
  return undefined;
}

export function pickNum(o: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const k of keys) {
    const v = o[k];
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
  }
  return undefined;
}

export const apiClient = {
  get: async (path: string, params?: Params) => {
    // Wrap the response in an object with a `data` property to match Axios-like expectations
    return { data: await apiGet(path, (data: any) => data, params ? { params } : {}) };
  }
};

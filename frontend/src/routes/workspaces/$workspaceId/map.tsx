import { createFileRoute, useParams } from "@tanstack/react-router";
import { WORKSPACES } from "@/config/workspaces";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { Crosshair, Layers, Maximize2, Search, X } from "lucide-react";
import { observationsQuery } from "@/api/data";
import { vesselsQuery } from "@/api/vessels";
import { cyclonesQuery } from "@/api/cyclones";
import { MarineMap, type MapApi } from "@/components/orca/MarineMap";
import { ObservationDetail } from "@/components/orca/ProvenancePanel";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/orca/StateView";
import { Button } from "@/components/ui/button";
import { GROUP_LABEL, LAYERS, formatCoord, formatDateTime, layerKeyFor, parseCoordinates, variableLabel, type LayerGroup } from "@/lib/marine";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/workspaces/$workspaceId/map")({
  head: () => ({
    meta: [
      { title: "Marine Map — ORCA" },
      { name: "description", content: "Interactive GIS workspace for inspecting marine observations and their provenance." },
      { property: "og:title", content: "Marine Map — ORCA" },
      { property: "og:description", content: "Interactive GIS workspace for inspecting marine observations and their provenance." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: MapPage,
});

export function MapPage({ workspaceIdProp }: { workspaceIdProp?: string } = {}) {
  const params = useParams({ strict: false });
  const workspaceId = workspaceIdProp || (params as any)?.workspaceId || "command-center";
  const workspace = WORKSPACES[workspaceId] || WORKSPACES["fisherman"];
  
  const q = useQuery(observationsQuery());
  const apiRef = useRef<MapApi | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cursor, setCursor] = useState<{ lat: number; lng: number } | null>(null);
  
  // By default, hide all layers that are NOT in the workspace.mapDefaults.layers
  const [hidden, setHidden] = useState<Set<string>>(() => {
    const s = new Set<string>();
    const defaultLayers = workspace?.mapDefaults?.layers || [];
    for (const l of LAYERS) {
      if (!defaultLayers.includes(l.key)) {
        s.add(l.key);
      }
    }
    return s;
  });
  
  const vesselsQ = useQuery(vesselsQuery(1000));
  const cyclonesQ = useQuery(cyclonesQuery(true));
  
  const [timestamp, setTimestamp] = useState<string>("all");
  const [layersOpen, setLayersOpen] = useState(false);

  const all = q.data ?? [];

  // Layer availability derives entirely from what the backend returned.
  const counts = useMemo(() => {
    const m = new Map<string, number>();
    for (const o of all) {
      const k = layerKeyFor(o.variable) ?? o.variable;
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  }, [all]);

  const timestamps = useMemo(() => [...new Set(all.map((o) => o.observed_at))].sort(), [all]);
  const filtered = useMemo(() => (timestamp === "all" ? all : all.filter((o) => o.observed_at === timestamp)), [all, timestamp]);
  const visibleLayers = useMemo(() => new Set([...counts.keys()].filter((k) => !hidden.has(k))), [counts, hidden]);
  
  // Combine vessels and cyclones into a single GeoJSON FeatureCollection if their layers are enabled
  const mapGeojson = useMemo(() => {
    const features: any[] = [];
    if (!hidden.has("vessel_locations") && vesselsQ.data?.features) {
      features.push(...vesselsQ.data.features);
    }
    if (!hidden.has("cyclone_tracks") && cyclonesQ.data?.features) {
      features.push(...cyclonesQ.data.features);
    }
    return features.length > 0 ? { type: "FeatureCollection", features } : undefined;
  }, [vesselsQ.data, cyclonesQ.data, hidden]);

  const selected = all.find((o) => o.id === selectedId) ?? null;
  const unknownVars = [...counts.keys()].filter((k) => !LAYERS.some((l) => l.key === k));
  const sources = [...new Set(all.map((o) => o.provider).filter(Boolean))];
  const latest = timestamps[timestamps.length - 1];

  const toggle = (k: string) =>
    setHidden((h) => {
      const n = new Set(h);
      n.has(k) ? n.delete(k) : n.add(k);
      return n;
    });

  const layerPanel = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 pb-2 pt-4">
        <p className="text-[13px] font-semibold">Layers</p>
        <button className="lg:hidden" onClick={() => setLayersOpen(false)} aria-label="Close layers">
          <X className="size-4 text-muted-foreground" />
        </button>
      </div>
      <div className="flex-1 overflow-auto px-2 pb-4">
        {(Object.keys(GROUP_LABEL) as LayerGroup[]).map((g) => (
          <fieldset key={g} className="mt-3">
            <legend className="eyebrow px-2 pb-1.5">{GROUP_LABEL[g]}</legend>
            {LAYERS.filter((l) => l.group === g).map((l) => (
              <LayerRow key={l.key} k={l.key} label={l.label} count={counts.get(l.key)} on={visibleLayers.has(l.key)} loading={q.isLoading} onToggle={toggle} />
            ))}
            {g === "marine" &&
              unknownVars.map((k) => (
                <LayerRow key={k} k={k} label={variableLabel(k)} count={counts.get(k)} on={visibleLayers.has(k)} loading={false} onToggle={toggle} />
              ))}
          </fieldset>
        ))}
      </div>
    </div>
  );

  return (
    <div className="flex h-full flex-col">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface px-3 py-2">
        <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setLayersOpen(true)} aria-label="Open layers">
          <Layers /> Layers
        </Button>
        <LocationSearch onCoords={(lat, lon) => apiRef.current?.flyTo(lat, lon)} />
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="hidden sm:inline">Observation time</span>
          <select
            value={timestamp}
            onChange={(e) => setTimestamp(e.target.value)}
            disabled={!timestamps.length}
            className="num h-8 rounded-md border border-input bg-surface px-2 text-xs text-foreground disabled:opacity-50"
          >
            <option value="all">{timestamps.length ? `All (${timestamps.length})` : "No timestamps"}</option>
            {timestamps.map((t) => (
              <option key={t} value={t}>{formatDateTime(t)}</option>
            ))}
          </select>
        </label>
        <div className="ml-auto flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => apiRef.current?.resetView()}>
            <Crosshair /> <span className="hidden sm:inline">Reset view</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={() => apiRef.current?.fitToData()} disabled={!filtered.length}>
            <Maximize2 /> <span className="hidden sm:inline">Fit to data</span>
          </Button>
        </div>
      </div>

      <div className="relative flex min-h-0 flex-1">
        {/* Layer control */}
        <aside className="hidden w-64 shrink-0 border-r border-border bg-surface lg:block" aria-label="Map layers">
          {layerPanel}
        </aside>
        {layersOpen && (
          <div className="panel-float absolute left-3 top-3 z-[1000] h-[min(70%,520px)] w-64 lg:hidden">{layerPanel}</div>
        )}

        {/* Map */}
        <div className="relative min-w-0 flex-1">
          <MarineMap
            observations={filtered}
            visibleLayers={visibleLayers}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onCursor={setCursor}
            apiRef={apiRef}
            geojson={mapGeojson}
          />
          {(q.isLoading || vesselsQ.isLoading || cyclonesQ.isLoading || q.isError || (q.isSuccess && all.length === 0 && !mapGeojson)) && (
            <div className="pointer-events-none absolute inset-x-0 top-4 z-[900] flex justify-center px-4">
              <div className="panel-float pointer-events-auto w-full max-w-sm px-5">
                {q.isLoading && (
                  <div className="py-4">
                    <p className="mb-3 text-xs text-muted-foreground">Loading marine observations…</p>
                    <SkeletonRows rows={2} />
                  </div>
                )}
                {q.isError && <ErrorState compact title="Marine data unavailable" error={q.error} onRetry={() => q.refetch()} />}
                {q.isSuccess && all.length === 0 && (
                  <EmptyState title="No marine observations" body="No marine observations are available for this area and time range." />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Detail panel: sidebar on desktop, drawer on smaller screens */}
        {selected && (
          <aside
            aria-label="Observation detail"
            className={cn(
              "z-[1000] overflow-auto bg-surface animate-in fade-in slide-in-from-right-2 duration-200",
              "absolute inset-x-0 bottom-0 max-h-[60%] rounded-t-xl border-t border-border shadow-float",
              "lg:static lg:max-h-none lg:w-80 lg:shrink-0 lg:rounded-none lg:border-l lg:border-t-0 lg:shadow-none",
            )}
          >
            <div className="flex items-center justify-between px-5 pt-4">
              <p className="text-[13px] font-semibold">Observation</p>
              <button onClick={() => setSelectedId(null)} aria-label="Clear selection" className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground">
                <X className="size-4" />
              </button>
            </div>
            <div className="px-5 pb-6 pt-4">
              <ObservationDetail obs={selected} />
            </div>
          </aside>
        )}
      </div>

      {/* Status bar */}
      <footer className="num flex h-7 shrink-0 items-center gap-4 overflow-hidden border-t border-border bg-surface px-3 text-[11px] text-muted-foreground">
        <span className="w-44 shrink-0">{cursor ? `${formatCoord(cursor.lat, "lat")}  ${formatCoord(cursor.lng, "lon")}` : "—"}</span>
        <span className="truncate">{q.isSuccess ? `${filtered.length} observations` : "No data"}</span>
        {latest && <span className="hidden truncate sm:inline">Latest {formatDateTime(latest)}</span>}
        {sources.length > 0 && <span className="hidden truncate md:inline">Source {sources.join(", ")}</span>}
      </footer>
    </div>
  );
}

function LayerRow({ k, label, count, on, loading, onToggle }: { k: string; label: string; count?: number | undefined; on: boolean; loading: boolean; onToggle: (k: string) => void }) {
  const available = !!count;
  return (
    <label
      className={cn(
        "flex h-8 items-center gap-2.5 rounded-md px-2 text-[13px]",
        available ? "cursor-pointer hover:bg-accent" : "cursor-not-allowed text-subtle-foreground",
      )}
    >
      <input type="checkbox" className="size-3.5 accent-primary" checked={available && on} disabled={!available} onChange={() => onToggle(k)} />
      <span className="size-2 shrink-0 rounded-full" style={{ background: available ? `var(--layer-${LAYERS.some((l) => l.key === k) ? k : "other"})` : "var(--border-strong)" }} aria-hidden />
      <span className="flex-1 truncate">{label}</span>
      <span className="num shrink-0 text-[10.5px] text-subtle-foreground" title={available ? undefined : "Data unavailable from backend"}>{loading ? "…" : available ? count : "Unavailable"}</span>
    </label>
  );
}

function LocationSearch({ onCoords }: { onCoords: (lat: number, lon: number) => void }) {
  const [value, setValue] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <form
      className="relative"
      onSubmit={(e) => {
        e.preventDefault();
        const c = parseCoordinates(value);
        if (c) {
          setMsg(null);
          onCoords(c[0], c[1]);
        } else if (value.trim()) {
          setMsg("Named-place search is not yet available from the ORCA backend. Enter coordinates, e.g. 14.5, 74.2");
        }
      }}
    >
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-subtle-foreground" />
      <input
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setMsg(null);
        }}
        placeholder="Search marine location or lat, lon"
        aria-label="Search marine location"
        className="h-8 w-56 rounded-md border border-input bg-surface pl-8 pr-3 text-xs placeholder:text-subtle-foreground sm:w-72"
      />
      {msg && (
        <p role="status" className="panel-float absolute left-0 top-10 z-[1100] w-72 p-3 text-xs text-muted-foreground">
          {msg}
        </p>
      )}
    </form>
  );
}

import { createFileRoute, Link, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Waves, FileText, Anchor, Bot, Map as MapIcon, ShieldAlert } from "lucide-react";
import { datasetsQuery, dataHealthQuery, observationsQuery, providersQuery } from "@/api/data";
import { healthQuery } from "@/api/system";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/orca/StateView";
import { StatusLine } from "@/components/orca/StatusIndicator";
import { Button } from "@/components/ui/button";
import { formatCoord, formatDateTime, formatValue, layerKeyFor, variableLabel } from "@/lib/marine";
import type { MarineObservation } from "@/api/types";
import { cn } from "@/lib/utils";
import { WORKSPACES } from "@/config/workspaces";

import { MapPage } from "./map";
import { AgentConsole } from "./agent";

export const Route = createFileRoute("/workspaces/$workspaceId/")({
  head: () => ({
    meta: [{ title: "ORCA — Marine Intelligence" }],
  }),
  component: Overview,
});

function useGreeting() {
  const [g, setG] = useState("Welcome.");
  useEffect(() => {
    const h = new Date().getHours();
    setG(h < 12 ? "Good morning." : h < 18 ? "Good afternoon." : "Good evening.");
  }, []);
  return g;
}

function Overview() {
  const { workspaceId } = Route.useParams();
  const workspace = (WORKSPACES[workspaceId] || WORKSPACES["command-center"])!;
  const greeting = useGreeting();

  return (
    <div className={cn("mx-auto px-6 py-8 lg:px-10", workspaceId === "command-center" ? "max-w-[1600px]" : "max-w-5xl")}>
      <p className="eyebrow">ORCA · {workspace.name}</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">{greeting}</h1>
      <p className="mt-2 max-w-lg text-[15px] leading-relaxed text-muted-foreground">
        {workspace.description}
      </p>

      {/* Quick Actions */}
      <div className="mt-8 flex flex-wrap gap-3">
        {workspace.quickActions.map((action, i) => (
          <Button key={i} asChild variant={i === 0 ? "default" : "secondary"}>
            <Link to={`/workspaces/${workspaceId}/${action.to}` as any}>
              {action.label} <ArrowRight className="ml-1.5 size-4" />
            </Link>
          </Button>
        ))}
      </div>

      <div className="mt-12">
        {workspaceId === "command-center" && <CommandCenterDashboard workspaceId={workspaceId} />}
        {workspaceId === "fisherman" && <FishermanDashboard />}
        {workspaceId === "researcher" && <ResearcherDashboard />}
        {workspaceId === "coastal-authority" && <CoastalDashboard />}
        {workspaceId === "disaster-management" && <DisasterDashboard />}
        {workspaceId === "maritime-operator" && <MaritimeDashboard />}
      </div>
    </div>
  );
}

import {
  WeatherConditionsCard,
  WindConditionsCard,
  OceanConditionsPanel,
  ForecastTimeline,
  VesselIntelligencePanel,
} from "@/components/orca/IntelligencePanels";

// hardcoded for demo, normally would come from a selected area/vessel
const DEFAULT_LAT = 20.0;
const DEFAULT_LON = 72.0;

function OrcaSearchForm() {
  const { workspaceId } = Route.useParams();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const q = new FormData(e.currentTarget).get("q");
        if (q) {
          window.location.href = `/workspaces/${workspaceId}/agent?q=${encodeURIComponent(q.toString())}`;
        }
      }}
      className="flex w-full items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3 shadow-sm focus-within:ring-1 focus-within:ring-primary"
    >
      <Bot className="size-4 shrink-0 text-muted-foreground" />
      <input
        type="text"
        name="q"
        placeholder="Ask ORCA..."
        className="flex-1 min-w-0 bg-transparent text-[14px] outline-none placeholder:text-muted-foreground"
        autoComplete="off"
      />
      <Button type="submit" size="sm" className="shrink-0">
        Ask
      </Button>
    </form>
  );
}

function CommandCenterDashboard({ workspaceId }: { workspaceId: string }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1fr_1.3fr]">
        <div className="flex flex-col border border-border rounded-xl bg-surface overflow-hidden min-h-[700px]">
          <MapPage workspaceIdProp={workspaceId} />
        </div>
        
        <div className="flex flex-col border border-border rounded-xl bg-surface overflow-hidden min-h-[700px]">
          <AgentConsole workspaceIdProp={workspaceId} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1fr]">
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-surface p-5 shadow-sm">
            <h3 className="text-[13px] font-semibold flex items-center gap-2">
              <ShieldAlert className="size-4 text-emerald-500" /> Active Hazards
            </h3>
            <p className="mt-3 text-sm text-muted-foreground">No active hazards currently reported.</p>
          </div>
          <CapabilitiesPanel />
        </div>
        <div className="space-y-4">
          <OceanConditionsPanel lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <VesselIntelligencePanel lat={DEFAULT_LAT} lon={DEFAULT_LON} radius_km={100} />
        </div>
        <div className="space-y-4">
          <WeatherConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <WindConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <SystemPanel />
        </div>
      </div>
    </div>
  );
}

function FishermanDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4 min-w-0">
          <OceanConditionsPanel lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <ForecastTimeline lat={DEFAULT_LAT} lon={DEFAULT_LON} />
        </div>
        <div className="space-y-4 min-w-0">
          <WeatherConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <WindConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <SystemPanel />
          <CapabilitiesPanel />
        </div>
      </div>
    </div>
  );
}

function ResearcherDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4 min-w-0">
          <SystemPanel />
          <CapabilitiesPanel />
        </div>
        <div className="space-y-4 min-w-0">
          <OceanConditionsPanel lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <DatasetsPanel />
        </div>
      </div>
      <ForecastTimeline lat={DEFAULT_LAT} lon={DEFAULT_LON} />
      <RecentData title="Recent Database Observations" />
    </div>
  );
}

function CoastalDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4 min-w-0">
          <WeatherConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <RecentData title="Coastal Data" />
        </div>
        <div className="space-y-4 min-w-0">
          <SystemPanel />
          <CapabilitiesPanel />
        </div>
      </div>
    </div>
  );
}

function DisasterDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4 min-w-0">
          <SystemPanel />
          <CapabilitiesPanel />
        </div>
        <div className="space-y-4 min-w-0">
          <WeatherConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <ForecastTimeline lat={DEFAULT_LAT} lon={DEFAULT_LON} />
        </div>
      </div>
    </div>
  );
}

function MaritimeDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4 min-w-0">
          <OceanConditionsPanel lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <WindConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <VesselIntelligencePanel lat={DEFAULT_LAT} lon={DEFAULT_LON} radius_km={100} />
        </div>
        <div className="space-y-4 min-w-0">
          <SystemPanel />
          <CapabilitiesPanel />
        </div>
      </div>
    </div>
  );
}

// Below are the shared components modified slightly to be generic
function SystemPanel() {
  const health = useQuery(healthQuery());
  const data = useQuery(dataHealthQuery());
  const providers = useQuery(providersQuery());
  return (
    <section className="panel p-5" aria-labelledby="sys">
      <h2 id="sys" className="text-[13px] font-semibold">
        Monitoring Status
      </h2>
      <ul className="mt-4 space-y-3">
        <li>
          {health.isLoading ? (
            <SkeletonRows rows={1} />
          ) : health.isSuccess ? (
            <StatusLine
              tone={health.data.ok ? "success" : "warning"}
              label={health.data.ok ? "Backend connected" : `Backend ${health.data.status}`}
            />
          ) : (
            <StatusLine tone="danger" label="Backend unreachable" />
          )}
        </li>
        <li>
          {data.isLoading ? (
            <SkeletonRows rows={1} />
          ) : data.isSuccess ? (
            <StatusLine
              tone={
                ["ok", "healthy", "available"].includes(data.data.status) ? "success" : "warning"
              }
              label={`Marine data ${data.data.status}`}
            />
          ) : (
            <StatusLine tone="muted" label="Marine data status unavailable" />
          )}
        </li>
        <li>
          {providers.isSuccess ? (
            <StatusLine
              tone={providers.data.length ? "success" : "muted"}
              label={`${providers.data.length} active data provider${providers.data.length === 1 ? "" : "s"}`}
            />
          ) : (
            <StatusLine tone="muted" label="Providers unavailable" />
          )}
        </li>
      </ul>
      {data.isSuccess && data.data.last_ingestion_at && (
        <p className="num mt-4 text-[11px] text-subtle-foreground">
          Last ingestion {formatDateTime(data.data.last_ingestion_at)}
        </p>
      )}
    </section>
  );
}

import { capabilitiesQuery, workspaceCapabilitiesQuery } from "@/api/registry";

function CapabilitiesPanel() {
  const { workspaceId } = Route.useParams();
  const code = workspaceId.toUpperCase().replace("-", "_");
  const q = useQuery(workspaceCapabilitiesQuery(code));

  return (
    <section className="panel p-5" aria-labelledby="caps">
      <h2 id="caps" className="text-[13px] font-semibold">
        Workspace Capabilities
      </h2>
      {q.isLoading && <SkeletonRows rows={3} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Could not load capabilities"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.length === 0 && <EmptyState title="No capabilities mapped" />}
      {q.isSuccess && q.data.length > 0 && (
        <ul className="mt-4 space-y-3">
          {q.data.map((c) => (
            <li key={c.capability_code} className="flex justify-between items-center text-[13px]">
              <span className="text-muted-foreground">{c.capability.name}</span>
              {c.capability.status === "AVAILABLE" ? (
                <span className="flex items-center gap-1.5 text-emerald-500 font-medium text-xs">
                  <span className="size-1.5 rounded-full bg-emerald-500"></span> Available
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-muted-foreground text-xs">
                  <span className="size-1 rounded-full border border-muted-foreground"></span> Not
                  available yet
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RecentData({ title = "Recent data" }: { title?: string }) {
  const q = useQuery(observationsQuery({ latitude: DEFAULT_LAT, longitude: DEFAULT_LON }));
  const latest = useMemo(() => {
    const m = new Map<string, MarineObservation>();
    for (const o of q.data ?? []) {
      const k = layerKeyFor(o.variable) ?? o.variable;
      const cur = m.get(k);
      if (!cur || o.observed_at > cur.observed_at) m.set(k, o);
    }
    return [...m.values()].slice(0, 6);
  }, [q.data]);

  return (
    <section className="panel p-5" aria-labelledby="recent">
      <h2 id="recent" className="text-[13px] font-semibold">
        {title}
      </h2>
      {q.isLoading && <SkeletonRows rows={4} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Marine data could not be loaded"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && latest.length === 0 && (
        <EmptyState
          title="No observations yet"
          body="The backend returned no marine observations."
        />
      )}
      {latest.length > 0 && (
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-5">
          {latest.map((o) => (
            <div key={o.id}>
              <dt className="eyebrow">{variableLabel(o.variable)}</dt>
              <dd className="num mt-1 text-xl font-medium">{formatValue(o.value, o.unit)}</dd>
              <dd className="num mt-0.5 text-[11px] text-subtle-foreground">
                {formatCoord(o.latitude, "lat")} {formatCoord(o.longitude, "lon")} ·{" "}
                {formatDateTime(o.observed_at)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function DatasetsPanel() {
  const q = useQuery(datasetsQuery());
  return (
    <section className="panel p-5" aria-labelledby="ds">
      <h2 id="ds" className="text-[13px] font-semibold">
        Available Datasets
      </h2>
      {q.isLoading && <SkeletonRows rows={3} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Datasets could not be loaded"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.length === 0 && <EmptyState title="No datasets registered" />}
      {q.isSuccess && q.data.length > 0 && (
        <table className="mt-3 w-full text-left text-[13px]">
          <thead>
            <tr className="eyebrow border-b border-border">
              <th className="py-2 font-medium">Dataset</th>
              <th className="py-2 font-medium">Provider</th>
              <th className="hidden py-2 font-medium sm:table-cell">Resolution</th>
            </tr>
          </thead>
          <tbody>
            {q.data.map((d) => (
              <tr key={d.id} className="border-b border-border last:border-0">
                <td className="py-2.5">{d.name}</td>
                <td className="py-2.5 text-muted-foreground">{d.provider ?? "—"}</td>
                <td className="num hidden py-2.5 text-xs text-muted-foreground sm:table-cell">
                  {[d.spatial_resolution, d.temporal_resolution].filter(Boolean).join(" · ") || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

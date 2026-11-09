import React from "react";
import { capabilityExecutionQuery, CapabilityResult, researchExecutionQuery } from "@/api/intelligence";
import { useQuery } from "@tanstack/react-query";
import { SkeletonRows, ErrorState } from "@/components/orca/StateView";
import {
  Thermometer,
  Wind,
  Waves,
  Clock,
  Info,
  ShieldAlert,
  CheckCircle2,
  Navigation,
  Search,
} from "lucide-react";
import { formatDateTime, formatValue } from "@/lib/marine";

export function DataFreshnessIndicator({
  metadata,
  timestamp,
}: {
  metadata: any;
  timestamp?: string;
}) {
  if (metadata.is_fallback) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-500 mt-2 font-medium">
        <span className="flex size-2 rounded-full bg-amber-500" />
        <span>Fallback data · Provider unavailable</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 text-xs text-emerald-500 mt-2 font-medium">
      <span className="flex size-2 rounded-full bg-emerald-500" />
      <span>Live {timestamp && `· Updated ${formatDateTime(timestamp)}`}</span>
    </div>
  );
}

export function ScientificProvenancePanel({ provenance }: { provenance: any[] }) {
  if (!provenance || provenance.length === 0) return null;

  // Group by provider
  const providers = Array.from(new Set(provenance.map((p) => p.provider)));

  return (
    <div className="mt-4 pt-3 border-t border-border">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
        <Info className="size-3" />
        <span>Scientific Provenance</span>
      </div>
      <ul className="space-y-1">
        {providers.map((prov) => (
          <li key={prov} className="text-xs text-subtle-foreground flex justify-between">
            <span>Source: {prov}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function WeatherConditionsCard({ lat, lon }: { lat: number; lon: number }) {
  const q = useQuery(
    capabilityExecutionQuery<any>("get_weather_conditions", { latitude: lat, longitude: lon }),
  );

  return (
    <section className="panel p-5">
      <div className="flex items-center gap-2">
        <Thermometer className="size-4 text-blue-400" />
        <h2 className="text-[13px] font-semibold">Weather Conditions</h2>
      </div>

      {q.isLoading && <SkeletonRows rows={3} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Failed to load weather"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.data && (
        <div className="mt-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="eyebrow">Temperature</p>
              <p className="text-xl font-medium mt-1">
                {formatValue(q.data.data.temperature, q.data.data.temperature_unit)}
              </p>
            </div>
            <div>
              <p className="eyebrow">Humidity</p>
              <p className="text-xl font-medium mt-1">
                {formatValue(q.data.data.relative_humidity, "%")}
              </p>
            </div>
          </div>
          <DataFreshnessIndicator
            metadata={q.data.metadata}
            timestamp={q.data.data.observation_time}
          />
          <ScientificProvenancePanel provenance={q.data.provenance} />
        </div>
      )}
    </section>
  );
}

export function WindConditionsCard({ lat, lon }: { lat: number; lon: number }) {
  const q = useQuery(
    capabilityExecutionQuery<any>("get_wind_conditions", { latitude: lat, longitude: lon }),
  );

  return (
    <section className="panel p-5">
      <div className="flex items-center gap-2">
        <Wind className="size-4 text-emerald-400" />
        <h2 className="text-[13px] font-semibold">Wind Conditions</h2>
      </div>

      {q.isLoading && <SkeletonRows rows={3} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Failed to load wind"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.data && (
        <div className="mt-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="eyebrow">Speed</p>
              <p className="text-xl font-medium mt-1">
                {formatValue(q.data.data.wind_speed, q.data.data.unit)}
              </p>
            </div>
            <div>
              <p className="eyebrow">Direction</p>
              <p className="text-xl font-medium mt-1">
                {formatValue(q.data.data.wind_direction, "°")}
              </p>
            </div>
          </div>
          <DataFreshnessIndicator metadata={q.data.metadata} timestamp={q.data.data.timestamp} />
          <ScientificProvenancePanel provenance={q.data.provenance} />
        </div>
      )}
    </section>
  );
}

export function OceanConditionsPanel({ lat, lon }: { lat: number; lon: number }) {
  const q = useQuery(
    capabilityExecutionQuery<any>("get_ocean_conditions", { latitude: lat, longitude: lon }),
  );

  return (
    <section className="panel p-5">
      <div className="flex items-center gap-2">
        <Waves className="size-4 text-blue-500" />
        <h2 className="text-[13px] font-semibold">Ocean Intelligence</h2>
      </div>

      {q.isLoading && <SkeletonRows rows={4} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Failed to load ocean data"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.data && (
        <div className="mt-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-5 gap-x-4">
            <div>
              <p className="eyebrow">Wave Height</p>
              <p className="text-lg font-medium mt-1">
                {formatValue(q.data.data.wave_height, "m")}
              </p>
            </div>
            <div>
              <p className="eyebrow">Wave Period</p>
              <p className="text-lg font-medium mt-1">
                {formatValue(q.data.data.wave_period, "s")}
              </p>
            </div>
            <div>
              <p className="eyebrow">SST</p>
              <p className="text-lg font-medium mt-1">
                {formatValue(q.data.data.sea_surface_temperature, "°C")}
              </p>
            </div>
            {q.data.data.ocean_current_velocity !== undefined && (
              <div>
                <p className="eyebrow">Current Velocity</p>
                <p className="text-lg font-medium mt-1">
                  {formatValue(q.data.data.ocean_current_velocity, "m/s")}
                </p>
              </div>
            )}
          </div>
          <DataFreshnessIndicator metadata={q.data.metadata} timestamp={q.data.data.timestamp} />
          <ScientificProvenancePanel provenance={q.data.provenance} />
        </div>
      )}
    </section>
  );
}

export function ForecastTimeline({ lat, lon }: { lat: number; lon: number }) {
  const q = useQuery(
    capabilityExecutionQuery<any>("get_weather_forecast", {
      latitude: lat,
      longitude: lon,
      forecast_hours: 12,
    }),
  );

  return (
    <section className="panel p-5 min-w-0">
      <h2 className="text-[13px] font-semibold">Weather Forecast (12h)</h2>
      {q.isLoading && <SkeletonRows rows={4} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Failed to load forecast"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.data?.entries && (
        <div className="mt-5 flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
          {q.data.data.entries.slice(0, 12).map((entry: any) => {
            const date = new Date(entry.timestamp);
            return (
              <div
                key={entry.timestamp}
                className="flex flex-col items-center min-w-16 border-r border-border last:border-0 pr-4 last:pr-0 shrink-0"
              >
                <span className="text-xs text-muted-foreground">
                  {date.getHours().toString().padStart(2, "0")}:00
                </span>
                <span className="font-medium text-sm mt-1.5">
                  {entry.temperature !== null && entry.temperature !== undefined
                    ? Math.round(entry.temperature)
                    : "--"}
                  °C
                </span>
                <span className="text-[10px] text-blue-400 mt-1 flex items-center gap-1">
                  <Wind className="size-2.5" /> {formatValue(entry.wind_speed, "m/s")}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export function VesselIntelligencePanel({
  lat,
  lon,
  radius_km = 50,
}: {
  lat: number;
  lon: number;
  radius_km?: number;
}) {
  const q = useQuery(
    capabilityExecutionQuery<any>("get_vessel_positions", {
      latitude: lat,
      longitude: lon,
      radius_km,
    }),
  );

  return (
    <section className="panel p-5">
      <div className="flex items-center gap-2">
        <Navigation className="size-4 text-purple-400" />
        <h2 className="text-[13px] font-semibold">Vessel Intelligence</h2>
      </div>

      {q.isLoading && <SkeletonRows rows={4} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Failed to load vessels"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data.data && (
        <div className="mt-4">
          {q.data.status === "UNAVAILABLE" ? (
             <div className="p-4 rounded border border-dashed border-border bg-muted/50 text-center">
               <p className="text-sm font-medium text-foreground mb-2">Unavailable for requested area</p>
               <p className="text-xs text-muted-foreground mb-3">
                 The currently configured AIS data source provides vessel tracking for Finnish and Baltic Sea waters. Indian Ocean vessel tracking is not currently available through this provider.
               </p>
               <div className="text-left text-[11px] bg-background p-2 rounded border border-border mt-2 space-y-1">
                 <div className="flex justify-between"><span className="font-medium text-muted-foreground">Provider</span> <span>{q.data.data?.provider || "Digitraffic / Fintraffic"}</span></div>
                 <div className="flex justify-between"><span className="font-medium text-muted-foreground">Coverage</span> <span>{q.data.data?.coverage?.region || "Baltic / Finnish waters"}</span></div>
                 <div className="flex justify-between"><span className="font-medium text-muted-foreground">Requested area</span> <span>Lat {lat.toFixed(2)}, Lon {lon.toFixed(2)}</span></div>
               </div>
             </div>
          ) : (
            <div className="flex flex-col gap-3">
              <p className="text-sm font-medium">
                {q.data.data.vessels?.length || 0} vessels detected within {radius_km}km
              </p>
              {q.data.data.vessels?.slice(0, 3).map((v: any) => (
                <div
                  key={v.id}
                  className="text-xs text-subtle-foreground flex justify-between bg-black/20 p-2 rounded"
                >
                  <span className="font-medium text-foreground">MMSI: {v.mmsi || "Unknown"}</span>
                  <span>{v.speed ? `${v.speed} kn` : "Moored"}</span>
                </div>
              ))}
              {q.data.data.vessels?.length > 3 && (
                <p className="text-xs text-muted-foreground italic text-center">
                  +{q.data.data.vessels.length - 3} more
                </p>
              )}
            </div>
          )}
          <DataFreshnessIndicator
            metadata={q.data.metadata}
            timestamp={q.data.data.vessels?.[0]?.timestamp}
          />
          <ScientificProvenancePanel provenance={q.data.provenance} />
        </div>
      )}
    </section>
  );
}

export function ResearchResultsPanel({ requestPayload }: { requestPayload: any }) {
  const q = useQuery(researchExecutionQuery(requestPayload, !!requestPayload));

  if (!requestPayload) return null;

  return (
    <section className="panel p-5">
      <div className="flex items-center gap-2">
        <Search className="size-4 text-orange-400" />
        <h2 className="text-[13px] font-semibold">Phase 9 Research Results</h2>
      </div>

      {q.isLoading && <SkeletonRows rows={4} className="mt-4" />}
      {q.isError && (
        <ErrorState
          compact
          title="Failed to load research"
          error={q.error}
          onRetry={() => q.refetch()}
        />
      )}
      {q.isSuccess && q.data && (
        <div className="mt-4 space-y-4">
          <div>
            <p className="eyebrow">Executive Summary</p>
            <p className="text-sm mt-1">{q.data.executive_summary}</p>
          </div>
          <div>
            <p className="eyebrow">Findings</p>
            <ul className="list-disc pl-4 text-sm mt-1 space-y-1">
              {q.data.findings?.map((f: string, i: number) => <li key={i}>{f}</li>)}
            </ul>
          </div>
          {q.data.limitations?.length > 0 && (
            <div>
              <p className="eyebrow text-amber-500">Limitations</p>
              <ul className="list-disc pl-4 text-sm mt-1 space-y-1 text-amber-400/80">
                {q.data.limitations?.map((l: string, i: number) => <li key={i}>{l}</li>)}
              </ul>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-4 font-medium border-t border-border pt-3">
            <span className="flex size-2 rounded-full bg-emerald-500" />
            <span>Completed at {formatDateTime(q.data.completed_at)} · {q.data.status}</span>
          </div>
        </div>
      )}
    </section>
  );
}

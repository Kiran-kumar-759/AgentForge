import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { MarineObservation } from "@/api/types";
import { formatCoord, formatDate, formatDateTime, formatTime, formatValue, variableLabel } from "@/lib/marine";
import { cn } from "@/lib/utils";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[96px_1fr] gap-3 py-1.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-xs text-foreground">{children}</dd>
    </div>
  );
}

function qualityTone(q?: string) {
  const v = q?.toLowerCase();
  if (!v) return "text-muted-foreground";
  if (["valid", "good", "pass", "ok"].includes(v)) return "text-success";
  if (["suspect", "questionable", "warn"].includes(v)) return "text-warning";
  return "text-danger";
}

/** Observation headline value plus provenance. All fields come from the backend record. */
export function ObservationDetail({ obs }: { obs: MarineObservation }) {
  return (
    <div>
      <p className="eyebrow">{variableLabel(obs.variable)}</p>
      <p className="num mt-1 text-3xl font-medium tracking-tight text-foreground">{formatValue(obs.value, obs.unit, obs.variable)}</p>
      <div className="mt-5 grid grid-cols-2 gap-4">
        <div>
          <p className="eyebrow">Location</p>
          <p className="num mt-1 text-sm">{formatCoord(obs.latitude, "lat")}</p>
          <p className="num text-sm">{formatCoord(obs.longitude, "lon")}</p>
        </div>
        <div>
          <p className="eyebrow">Observed</p>
          <p className="num mt-1 text-sm">{formatDate(obs.observed_at)}</p>
          <p className="num text-sm text-muted-foreground">{formatTime(obs.observed_at)}</p>
        </div>
      </div>
      <div className="my-5 h-px bg-border" />
      <ProvenancePanel obs={obs} />
    </div>
  );
}

export function ProvenancePanel({ obs }: { obs: MarineObservation }) {
  const [open, setOpen] = useState(false);
  const known = new Set([
    "id", "variable", "value", "unit", "latitude", "longitude", "lat", "lon", "lng", "observed_at", "timestamp",
    "retrieved_at", "provider", "dataset", "quality", "spatial_resolution", "temporal_resolution", "is_fallback", "fallback",
  ]);
  const extras = Object.entries(obs.raw).filter(([k]) => !known.has(k));
  return (
    <section aria-label="Data provenance">
      <p className="eyebrow mb-1">Data provenance</p>
      <dl className="divide-y divide-border">
        <Row label="Source">{obs.provider ?? <span className="text-muted-foreground">Not provided</span>}</Row>
        <Row label="Dataset">{obs.dataset ?? <span className="text-muted-foreground">Not provided</span>}</Row>
        <Row label="Variable">{variableLabel(obs.variable)}</Row>
        <Row label="Quality">
          <span className={cn("capitalize", qualityTone(obs.quality))}>{obs.quality ?? "Not provided"}</span>
        </Row>
        <Row label="Retrieved"><span className="num">{formatDateTime(obs.retrieved_at)}</span></Row>
      </dl>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="mt-3 inline-flex items-center gap-1 rounded text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        Technical metadata
        <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <dl className="mt-2 divide-y divide-border">
          <Row label="Record ID"><span className="num break-all">{obs.id}</span></Row>
          <Row label="Raw variable"><span className="num">{obs.variable}</span></Row>
          <Row label="Unit"><span className="num">{obs.unit ?? "—"}</span></Row>
          <Row label="Latitude"><span className="num">{obs.latitude}</span></Row>
          <Row label="Longitude"><span className="num">{obs.longitude}</span></Row>
          <Row label="Timestamp"><span className="num break-all">{obs.observed_at}</span></Row>
          <Row label="Spatial res.">{obs.spatial_resolution ?? "—"}</Row>
          <Row label="Temporal res.">{obs.temporal_resolution ?? "—"}</Row>
          <Row label="Fallback">{obs.is_fallback === undefined ? "—" : obs.is_fallback ? "Yes" : "No"}</Row>
          {extras.map(([k, v]) => (
            <Row key={k} label={k}>
              <span className="num break-all">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
            </Row>
          ))}
        </dl>
      )}
    </section>
  );
}

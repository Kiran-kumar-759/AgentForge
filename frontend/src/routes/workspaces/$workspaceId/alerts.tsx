import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Info, BellRing, Wind, Tornado, Waves, Activity } from "lucide-react";

export const Route = createFileRoute("/workspaces/$workspaceId/alerts")({
  head: () => ({
    meta: [
      { title: "Alert Center — ORCA" },
    ],
  }),
  component: AlertsPage,
});

function AlertsPage() {
  const { workspaceId } = Route.useParams();

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <p className="eyebrow">ORCA · {workspaceId.toUpperCase().replace("-", " ")}</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Alert Center</h1>
      <p className="mt-2 max-w-lg text-[15px] leading-relaxed text-muted-foreground">
        Active marine, weather, and operational alerts across the monitored regions based on current capability evaluation.
      </p>

      <div className="mt-10 space-y-4">
        {/* We do not fabricate alerts. If there is no real backend alert endpoint, we show no alerts / unavailable state */}
        <div className="rounded-xl border border-border bg-surface p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <BellRing className="size-6" />
          </div>
          <h3 className="mt-4 text-[15px] font-semibold text-foreground">No active alerts</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            There are currently no active hazards or alerts in the selected workspace region.
          </p>
        </div>

        {/* System Capability Availability Note */}
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-5 shadow-sm">
          <div className="flex items-start gap-4">
            <Info className="mt-0.5 size-5 text-orange-600" />
            <div>
              <h4 className="text-sm font-semibold text-orange-800">Capability Limitation</h4>
              <p className="mt-1 text-sm text-orange-700 leading-relaxed">
                Some alerting endpoints (e.g., live cyclone warnings, extreme wave event detection) are not currently producing active telemetry from upstream providers. Alerts will dynamically appear here when valid data is ingested.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import {
  WeatherConditionsCard,
  WindConditionsCard,
  OceanConditionsPanel,
  ForecastTimeline,
} from "@/components/orca/IntelligencePanels";

export const Route = createFileRoute("/workspaces/$workspaceId/conditions")({
  component: RouteComponent,
});

const DEFAULT_LAT = 20.0;
const DEFAULT_LON = 72.0;

function RouteComponent() {
  const { workspaceId } = Route.useParams();
  
  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Marine Conditions</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Real-time weather and oceanographic conditions for your operating area.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-6 min-w-0">
          <OceanConditionsPanel lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <ForecastTimeline lat={DEFAULT_LAT} lon={DEFAULT_LON} />
        </div>
        <div className="space-y-6 min-w-0">
          <WeatherConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
          <WindConditionsCard lat={DEFAULT_LAT} lon={DEFAULT_LON} />
        </div>
      </div>
    </div>
  );
}

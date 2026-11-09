import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { MarineMap, type MapApi } from "@/components/orca/MarineMap";
import { VesselIntelligencePanel } from "@/components/orca/IntelligencePanels";
import { useQuery } from "@tanstack/react-query";
import { capabilityExecutionQuery } from "@/api/intelligence";
import { formatDateTime } from "@/lib/marine";
import { Button } from "@/components/ui/button";
import { Crosshair } from "lucide-react";

export const Route = createFileRoute("/workspaces/$workspaceId/vessels")({
  component: VesselsMapPage,
});

function VesselsMapPage() {
  const [lat, setLat] = useState(14.0);
  const [lon, setLon] = useState(74.5);
  const apiRef = useRef<MapApi | null>(null);
  
  const q = useQuery(capabilityExecutionQuery<any>("get_vessel_positions", { latitude: lat, longitude: lon, radius_km: 200 }));
  
  const observations = (q.data?.data?.vessels || []).map((v: any) => ({
    id: v.id,
    variable: "vessel_locations",
    value: v.speed,
    unit: "knots",
    latitude: v.latitude,
    longitude: v.longitude,
    observed_at: v.timestamp,
    provider: "Digitraffic",
  }));

  const visibleLayers = new Set(["vessel_locations"]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface px-3 py-2">
        <span className="text-[13px] font-medium">Vessel Tracking Workspace</span>
        <div className="ml-auto flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => apiRef.current?.resetView()}>
            <Crosshair /> Reset view
          </Button>
        </div>
      </div>
      
      <div className="relative flex min-h-0 flex-1">
        <aside className="hidden w-80 shrink-0 border-r border-border bg-surface lg:block overflow-auto">
          <div className="p-4 space-y-4">
            <VesselIntelligencePanel lat={lat} lon={lon} radius_km={200} />
            <p className="text-xs text-muted-foreground p-2 bg-muted/50 rounded">
              Move the map or click reset view to update coordinates.
            </p>
          </div>
        </aside>
        
        <div className="relative min-w-0 flex-1">
          <MarineMap
            observations={observations}
            visibleLayers={visibleLayers}
            selectedId={null}
            onSelect={() => {}}
            onCursor={(c) => {
                if (c && c.lat !== undefined && c.lon !== undefined) {
                  // Only update if moved significantly
                  if (Math.abs(c.lat - lat) > 1 || Math.abs(c.lon - lon) > 1) {
                    setLat(c.lat);
                    setLon(c.lon);
                  }
                }
            }}
            apiRef={apiRef}
          />
          {q.data?.status === "UNAVAILABLE" && (
            <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-background/90 backdrop-blur-md border border-border px-4 py-2 rounded-lg shadow-lg text-center pointer-events-none z-[1000]">
               <div className="font-medium text-[13px] text-foreground">Vessel data unavailable in this area</div>
            </div>
          )}
          <div className="absolute bottom-6 right-6 bg-background/90 backdrop-blur-md border border-border p-3 rounded-lg shadow-lg z-[1000] text-[11px] min-w-[140px]">
            <div className="font-medium text-foreground mb-1">AIS Coverage</div>
            <div className="text-muted-foreground">{q.data?.data?.provider || "Digitraffic"}</div>
            <div className="text-muted-foreground">{q.data?.data?.coverage?.region || "Baltic / Finnish waters"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

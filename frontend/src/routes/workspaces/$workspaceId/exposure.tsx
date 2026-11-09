import { useState, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Users, Building2, Map as MapIcon, Navigation, Loader2 } from "lucide-react";

import { runExposureAnalysis, exposureAnalysisQuery, exposureGeoJSONQuery, ExposureAnalysisResult } from "@/api/exposure";
import { MarineMap } from "@/components/orca/MarineMap";
import { formatValue, formatDate } from "@/lib/marine";
import { ErrorState } from "@/components/orca/StateView";

export const Route = createFileRoute("/workspaces/$workspaceId/exposure")({
  component: ExposureRoute,
});

function ExposureRoute() {
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);
  
  // A simple static test polygon (a bay or coastal area)
  // Since drawing tools aren't built in this phase, we use a fixed coastal hazard area
  // for the user to trigger the analysis as per requirements.
  const DEFAULT_HAZARD_POLYGON = {
    type: "Polygon",
    coordinates: [[
      [74.0, 14.0],
      [74.2, 14.0],
      [74.2, 14.2],
      [74.0, 14.2],
      [74.0, 14.0]
    ]]
  };

  const mutation = useMutation({
    mutationFn: runExposureAnalysis,
    onSuccess: (data) => {
      setActiveAnalysisId(data.analysis_id);
    }
  });

  const handleRunAnalysis = () => {
    mutation.mutate({
      geometry: DEFAULT_HAZARD_POLYGON,
      analysis_type: "hazard_polygon",
      hazard_name: "Test Coastal Hazard Area",
      population_resolution: "100m"
    });
  };

  const analysisQuery = useQuery(exposureAnalysisQuery(activeAnalysisId || ""));
  const geojsonQuery = useQuery(exposureGeoJSONQuery(activeAnalysisId || ""));

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Coastal Exposure Intelligence</h1>
        <p className="mt-1 text-sm text-subtle-foreground">
          Estimate population and critical infrastructure within a selected coastal hazard area.
        </p>
      </header>

      {/* Control Panel */}
      <section className="rounded-lg border border-border bg-card p-4 flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium">Hazard Source: Custom Area</p>
          <p className="text-xs text-subtle-foreground">Using default test coastal polygon (74.0°E, 14.0°N to 74.2°E, 14.2°N)</p>
        </div>
        <button
          onClick={handleRunAnalysis}
          disabled={mutation.isPending}
          className="inline-flex items-center justify-center rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          {mutation.isPending ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running...</>
          ) : (
            "Run Exposure Analysis"
          )}
        </button>
      </section>

      {mutation.isError && (
        <ErrorState title="Failed to run exposure analysis" error={mutation.error} />
      )}

      {/* Summary Cards */}
      {analysisQuery.isSuccess && analysisQuery.data && (
        <section className="grid gap-4 md:grid-cols-4">
          <SummaryCard 
            title="Estimated Population Exposure" 
            value={analysisQuery.data.population.total !== null ? Math.round(analysisQuery.data.population.total).toLocaleString() : "—"} 
            source={analysisQuery.data.population.source || "WorldPop (Unavailable)"}
            icon={Users}
          />
          <SummaryCard 
            title="Exposed Settlements" 
            value={analysisQuery.data.settlements.count.toString()} 
            source="OpenStreetMap"
            icon={MapIcon}
          />
          <SummaryCard 
            title="Critical Infrastructure" 
            value={analysisQuery.data.infrastructure.critical_count.toString()} 
            source="OpenStreetMap"
            icon={Building2}
          />
          <SummaryCard 
            title="Total Infrastructure" 
            value={analysisQuery.data.infrastructure.count.toString()} 
            source="OpenStreetMap"
            icon={Navigation}
          />
        </section>
      )}

      {/* Map and Detail Panel */}
      <section className="grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2 h-[500px] rounded-lg overflow-hidden border border-border relative">
          <MarineMap 
            center={[14.1, 74.1]} 
            zoom={10} 
            activeLayers={["coastline", "ports"]}
            geojson={geojsonQuery.data}
          />
        </div>
        
        <div className="h-[500px] overflow-y-auto rounded-lg border border-border bg-card p-4">
          <h3 className="font-semibold mb-4">Exposure Detail Panel</h3>
          
          {analysisQuery.isSuccess && analysisQuery.data ? (
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-xs text-subtle-foreground uppercase tracking-wider">Analysis ID</p>
                <p className="font-mono text-xs mt-1 truncate" title={analysisQuery.data.analysis_id}>
                  {analysisQuery.data.analysis_id}
                </p>
              </div>
              
              <div>
                <p className="text-xs text-subtle-foreground uppercase tracking-wider">Status</p>
                <p className="mt-1 flex items-center gap-2">
                  <span className={`inline-block h-2 w-2 rounded-full ${
                    analysisQuery.data.status === 'completed' ? 'bg-green-500' :
                    analysisQuery.data.status === 'partial' ? 'bg-amber-500' : 'bg-red-500'
                  }`} />
                  <span className="capitalize">{analysisQuery.data.status}</span>
                </p>
              </div>
              
              <div>
                <p className="text-xs text-subtle-foreground uppercase tracking-wider">Methodology</p>
                <p className="mt-1 text-muted-foreground text-xs leading-relaxed">
                  Population exposure is estimated from WorldPop within the supplied analysis geometry. 
                  Infrastructure and settlement exposure are based on OpenStreetMap objects intersecting the analysis geometry.
                </p>
              </div>

              <div className="pt-4 border-t border-border">
                <p className="font-medium mb-2">Population</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <span className="text-subtle-foreground">Total:</span>
                  <span className="font-medium">{analysisQuery.data.population.total !== null ? Math.round(analysisQuery.data.population.total).toLocaleString() : "—"}</span>
                  <span className="text-subtle-foreground">Year:</span>
                  <span>{analysisQuery.data.population.year || "—"}</span>
                  <span className="text-subtle-foreground">Resolution:</span>
                  <span>{analysisQuery.data.population.resolution}</span>
                  <span className="text-subtle-foreground">Source:</span>
                  <span>{analysisQuery.data.population.source}</span>
                </div>
              </div>

              <div className="pt-4 border-t border-border">
                <p className="font-medium mb-2">Settlements</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <span className="text-subtle-foreground">Count:</span>
                  <span className="font-medium">{analysisQuery.data.settlements.count}</span>
                  <span className="text-subtle-foreground">Source:</span>
                  <span>OpenStreetMap</span>
                </div>
              </div>

              <div className="pt-4 border-t border-border">
                <p className="font-medium mb-2">Infrastructure</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <span className="text-subtle-foreground">Total:</span>
                  <span className="font-medium">{analysisQuery.data.infrastructure.count}</span>
                  <span className="text-subtle-foreground">Critical:</span>
                  <span className="font-medium text-destructive">{analysisQuery.data.infrastructure.critical_count}</span>
                  <span className="text-subtle-foreground">Source:</span>
                  <span>OpenStreetMap</span>
                </div>
              </div>

            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-center text-sm text-subtle-foreground">
              Run an exposure analysis to view detailed results.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ title, value, source, icon: Icon }: { title: string, value: string, source: string, icon: any }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-subtle-foreground mb-2">
        <Icon className="h-4 w-4" />
        {title}
      </div>
      <p className="text-2xl font-semibold text-foreground">{value}</p>
      <p className="text-xs text-subtle-foreground mt-1">Source: {source}</p>
    </div>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SkeletonRows } from "@/components/orca/StateView";
import { MapIcon, Fish, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/api/client";

export const Route = createFileRoute("/workspaces/$workspaceId/fishing-areas")({
  component: RouteComponent,
});

function RouteComponent() {
  const { workspaceId } = Route.useParams();
  
  const q = useQuery({
    queryKey: ["pfz_data"],
    queryFn: async () => {
      const res = await apiClient.get("/data/pfz");
      return res.data;
    }
  });
  
  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Fishing Areas (PFZ)</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Potential Fishing Zone advisories based on sea surface temperature and chlorophyll data.
        </p>
      </div>

      <section className="panel p-6">
        <div className="flex items-center gap-2 mb-6">
          <Fish className="size-5 text-blue-400" />
          <h2 className="text-lg font-semibold">Demo / Seeded Data</h2>
        </div>

        {q.isLoading && <SkeletonRows rows={3} />}
        {q.isSuccess && (
          <div className="space-y-4">
            {q.data.status === "UNAVAILABLE" ? (
              <div className="p-6 rounded-lg border border-dashed text-center flex flex-col items-center">
                <MapIcon className="size-8 text-muted-foreground mb-3 opacity-50" />
                <p className="text-sm font-medium">{q.data.message}</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-md">
                  Currently, we are unable to retrieve active PFZ geometries from the INCOIS provider. 
                  Please check back later or rely on local knowledge and safety conditions.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {q.data.data.map((zone: any) => (
                  <div key={zone.id} className="p-4 rounded-lg border bg-surface flex justify-between items-center">
                    <div>
                      <p className="font-medium text-sm">Provider: {zone.provider} (MOCK_SEEDED)</p>
                      <p className="text-xs text-muted-foreground mt-1">Advisory date: {zone.valid_from}</p>
                      <p className="text-xs text-muted-foreground mt-1">Valid until: {zone.valid_to}</p>
                      <p className="text-xs text-muted-foreground mt-1">Geometry: {zone.geom}</p>
                    </div>
                    <div className="px-3 py-1 bg-amber-500/10 text-amber-500 text-xs rounded-full">
                      Demo Data
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="mt-6 pt-4 border-t border-border flex items-start gap-2 text-xs text-muted-foreground">
              <Info className="size-4 shrink-0 mt-0.5" />
              <p>
                PFZ (Potential Fishing Zone) advisories are issued by INCOIS (Indian National Centre for Ocean Information Services) 
                to guide fishermen to areas with higher probability of fish aggregation.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

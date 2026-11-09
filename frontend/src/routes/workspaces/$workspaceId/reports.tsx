import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SkeletonRows, ErrorState } from "@/components/orca/StateView";
import { FileText, Download, CheckCircle2, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/api/client";
import { formatDateTime } from "@/lib/marine";

export const Route = createFileRoute("/workspaces/$workspaceId/reports")({
  component: RouteComponent,
});

function RouteComponent() {
  const { workspaceId } = Route.useParams();
  
  const q = useQuery({
    queryKey: ["reports_list", workspaceId],
    queryFn: async () => {
      const res = await apiClient.get(`/reports?workspace=${workspaceId}`);
      return res.data;
    }
  });

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Intelligence Reports</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Shareable situation reports with complete scientific provenance and verification.
          </p>
        </div>
        <Button variant="default">
          Generate New Report
        </Button>
      </div>

      <section className="panel p-0 overflow-hidden">
        {q.isLoading && <div className="p-6"><SkeletonRows rows={4} /></div>}
        {q.isError && (
          <div className="p-6">
            <ErrorState title="Failed to load reports" error={q.error} onRetry={() => q.refetch()} />
          </div>
        )}
        
        {q.isSuccess && q.data.reports && q.data.reports.length === 0 && (
          <div className="p-12 text-center flex flex-col items-center">
            <FileText className="size-10 text-muted-foreground mb-4 opacity-50" />
            <p className="font-medium">No reports generated yet</p>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
              Run an agent analysis from the overview page, and then generate a report to see it here.
            </p>
          </div>
        )}

        {q.isSuccess && q.data.reports && q.data.reports.length > 0 && (
          <div className="divide-y divide-border">
            {q.data.reports.map((r: any) => (
              <div key={r.id} className="p-5 flex items-center justify-between hover:bg-muted/30 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-surface border rounded-md">
                    <FileText className="size-5 text-blue-500" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{r.title}</h3>
                      {r.title.includes("Coastal Weather & Safety Analysis") || r.title.includes("PFZ & Vessel Density") ? (
                         <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 text-[10px] uppercase font-bold rounded-full">Demo Data</span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-4 mt-1.5 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Clock className="size-3.5" />
                        {r.created_at ? formatDateTime(r.created_at) : "Unknown date"}
                      </span>
                      <span className="flex items-center gap-1.5">
                        {r.status === "COMPLETED" ? (
                          <span className="text-emerald-500 flex items-center gap-1"><CheckCircle2 className="size-3.5" /> Generated</span>
                        ) : (
                          <span className="text-amber-500">Processing...</span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" asChild disabled={r.status !== "COMPLETED"}>
                    <a href={`/api/v1/reports/${r.id}/html`} target="_blank" rel="noreferrer">
                      View HTML
                    </a>
                  </Button>
                  <Button variant="secondary" size="sm" asChild disabled={r.status !== "COMPLETED"}>
                    <a href={`/api/v1/reports/${r.id}/pdf`} target="_blank" rel="noreferrer">
                      <Download className="size-4 mr-1.5" /> PDF
                    </a>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

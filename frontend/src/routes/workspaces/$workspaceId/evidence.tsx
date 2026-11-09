import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SkeletonRows, ErrorState } from "@/components/orca/StateView";
import { Database, Link2, CheckCircle2, XCircle, Search } from "lucide-react";
import { apiClient } from "@/api/client";

export const Route = createFileRoute("/workspaces/$workspaceId/evidence")({
  component: RouteComponent,
});

function RouteComponent() {
  const { workspaceId } = Route.useParams();
  
  const q = useQuery({
    queryKey: ["evidence_list", workspaceId],
    queryFn: async () => {
      const res = await apiClient.get(`/agent/evidence?workspace=${workspaceId}`);
      return res.data;
    }
  });

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Evidence & Provenance</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Source documents, scientific data citations, and verified claims that support ORCA findings.
          </p>
        </div>
      </div>

      <section className="panel p-0 overflow-hidden">
        {q.isLoading && <div className="p-6"><SkeletonRows rows={4} /></div>}
        {q.isError && (
          <div className="p-6">
            <ErrorState title="Failed to load evidence" error={q.error} onRetry={() => q.refetch()} />
          </div>
        )}
        
        {q.isSuccess && q.data.claims && q.data.claims.length === 0 && (
          <div className="p-12 text-center flex flex-col items-center">
            <Database className="size-10 text-muted-foreground mb-4 opacity-50" />
            <p className="font-medium">No verified evidence yet</p>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
              Run an agent analysis to generate claims and track their scientific evidence sources.
            </p>
          </div>
        )}

        {q.isSuccess && q.data.claims && q.data.claims.length > 0 && (
          <div className="divide-y divide-border">
            {q.data.claims.map((c: any) => (
              <div key={c.id} className="p-5 flex flex-col hover:bg-muted/30 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-surface border rounded-md shrink-0 mt-0.5">
                    {c.verification_status === "VERIFIED" ? (
                      <CheckCircle2 className="size-5 text-emerald-500" />
                    ) : c.verification_status === "FALSIFIED" ? (
                      <XCircle className="size-5 text-red-500" />
                    ) : (
                      <Search className="size-5 text-amber-500" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-medium text-[15px]">{c.text}</h3>
                    <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <span className="font-medium">Status:</span> {c.verification_status}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="font-medium">Type:</span> {c.type}
                      </span>
                    </div>
                    
                    {c.evidence_ids && c.evidence_ids.length > 0 && (
                      <div className="mt-3 pl-3 border-l-2 border-border/50">
                        <p className="text-xs font-medium mb-1.5 text-muted-foreground flex items-center gap-1">
                          <Link2 className="size-3" /> Supporting Evidence ({c.evidence_ids.length})
                        </p>
                        <div className="flex flex-col gap-1">
                          {c.evidence_ids.map((eid: string) => {
                            const e = q.data.evidence.find((ev: any) => ev.id === eid);
                            return e ? (
                              <div key={eid} className="text-xs flex items-center justify-between p-1.5 bg-surface rounded border">
                                <span className="truncate">{e.provider}</span>
                                <span className="opacity-70">{e.type}</span>
                              </div>
                            ) : null;
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

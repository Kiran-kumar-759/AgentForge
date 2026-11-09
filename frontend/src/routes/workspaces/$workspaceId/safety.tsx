import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { capabilityExecutionQuery } from "@/api/intelligence";
import { SkeletonRows, ErrorState } from "@/components/orca/StateView";
import { ShieldAlert, Info, AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/workspaces/$workspaceId/safety")({
  component: RouteComponent,
});

const DEFAULT_LAT = 20.0;
const DEFAULT_LON = 72.0;

function RouteComponent() {
  const { workspaceId } = Route.useParams();
  
  const q = useQuery(
    capabilityExecutionQuery<any>("analyze_safety", { latitude: DEFAULT_LAT, longitude: DEFAULT_LON }),
  );
  
  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Safety Analysis</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Evidence-based safety assessment for your operating area.
        </p>
      </div>
      
      <section className="panel p-6">
        <div className="flex items-center gap-2 mb-6">
          <ShieldAlert className="size-5 text-indigo-400" />
          <h2 className="text-lg font-semibold">Current Risk Assessment</h2>
        </div>

        {q.isLoading && <SkeletonRows rows={4} />}
        {q.isError && (
          <ErrorState
            title="Failed to load safety analysis"
            error={q.error}
            onRetry={() => q.refetch()}
          />
        )}
        {q.isSuccess && q.data.data && (
          <div className="space-y-6">
            <div className={cn("p-4 rounded-lg border flex gap-4", 
              q.data.data.risk_level === 'CRITICAL_RISK' ? 'bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400' :
              q.data.data.risk_level === 'MODERATE_RISK' ? 'bg-amber-500/10 border-amber-500/20 text-amber-700 dark:text-amber-400' :
              'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
            )}>
              <div className="mt-0.5">
                {q.data.data.risk_level === 'CRITICAL_RISK' ? <AlertTriangle className="size-5" /> : 
                 q.data.data.risk_level === 'MODERATE_RISK' ? <Info className="size-5" /> :
                 <CheckCircle2 className="size-5" />}
              </div>
              <div>
                <p className="font-semibold text-[15px]">{q.data.data.assessment}</p>
                <p className="mt-1 text-sm opacity-90">Risk Score: {q.data.data.risk_score} / 10</p>
              </div>
            </div>

            {q.data.data.risk_factors && q.data.data.risk_factors.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-3">Identified Risk Factors</h3>
                <ul className="space-y-2">
                  {q.data.data.risk_factors.map((factor: string, i: number) => (
                    <li key={i} className="text-sm flex items-center gap-2">
                      <span className="size-1.5 rounded-full bg-muted-foreground" />
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {q.data.provenance && q.data.provenance.length > 0 && (
              <div className="mt-8 pt-4 border-t border-border">
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-3">
                  <Info className="size-3.5" />
                  <span>Evidence & Provenance</span>
                </div>
                <div className="flex flex-wrap gap-2">
                   {Array.from(new Set(q.data.provenance.map((p: any) => p.provider))).map((prov: any, i: number) => (
                      <span key={i} className="px-2 py-1 bg-surface border rounded text-xs text-muted-foreground">
                        {prov}
                      </span>
                   ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

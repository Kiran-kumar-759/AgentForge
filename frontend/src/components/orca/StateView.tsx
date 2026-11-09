import { useState } from "react";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SkeletonRows({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-2.5", className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton-line h-3.5" style={{ width: `${88 - i * 14}%` }} />
      ))}
    </div>
  );
}

export function EmptyState({ title, body, className }: { title: string; body?: string; className?: string }) {
  return (
    <div className={cn("py-6 text-center", className)}>
      <p className="text-sm font-medium text-foreground">{title}</p>
      {body && <p className="mx-auto mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">{body}</p>}
    </div>
  );
}

export function ErrorState({
  title,
  error,
  onRetry,
  className,
  compact,
}: {
  title: string;
  error: unknown;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const message = error instanceof ApiError ? error.message : "Something unexpected went wrong.";
  const tech =
    error instanceof ApiError
      ? [`kind: ${error.kind}`, error.status && `status: ${error.status}`, error.url && `url: ${error.url}`, error.detail && `detail: ${error.detail}`]
          .filter(Boolean)
          .join("\n")
      : String(error);
  return (
    <div className={cn(compact ? "py-3" : "py-6", "text-center", className)} role="alert">
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mx-auto mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">{message}</p>
      <div className="mt-3 flex items-center justify-center gap-2">
        {onRetry && (
          <Button size="sm" variant="outline" onClick={onRetry}>
            Retry
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          Technical details
        </Button>
      </div>
      {open && (
        <pre className="num mx-auto mt-3 max-w-md overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-left text-[11px] text-muted-foreground">
          {tech}
        </pre>
      )}
    </div>
  );
}

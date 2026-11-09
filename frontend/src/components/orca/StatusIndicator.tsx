import { useQuery } from "@tanstack/react-query";
import { healthQuery } from "@/api/system";
import { cn } from "@/lib/utils";

type Tone = "success" | "warning" | "danger" | "muted";

export function Dot({ tone }: { tone: Tone }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block size-1.5 shrink-0 rounded-full",
        tone === "success" && "bg-success",
        tone === "warning" && "bg-warning",
        tone === "danger" && "bg-danger",
        tone === "muted" && "bg-subtle-foreground",
      )}
    />
  );
}

export function StatusLine({ tone, label, className }: { tone: Tone; label: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}>
      <Dot tone={tone} />
      {label}
    </span>
  );
}

/** Reflects the actual backend health response — never a decorative "Live" badge. */
export function ConnectionStatus() {
  const q = useQuery(healthQuery());
  let tone: Tone = "muted";
  let label = "Checking connection";
  if (q.isSuccess) {
    tone = q.data.ok ? "success" : "warning";
    label = q.data.ok ? "Connected" : `Backend ${q.data.status}`;
  } else if (q.isError) {
    tone = "danger";
    label = "Backend unavailable";
  }
  return (
    <span role="status" aria-live="polite">
      <StatusLine tone={tone} label={label} />
    </span>
  );
}

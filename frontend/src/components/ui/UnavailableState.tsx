import { AlertCircle } from "lucide-react";
import { Link } from "@tanstack/react-router";

export function UnavailableState({
  title,
  description,
  workspaceId
}: {
  title: string;
  description: string;
  workspaceId: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center animate-in fade-in zoom-in-95 duration-300">
      <div className="flex size-16 items-center justify-center rounded-full bg-sidebar border border-border shadow-sm mb-6 text-muted-foreground">
        <AlertCircle className="size-8" strokeWidth={1.5} />
      </div>
      <h2 className="text-xl font-medium tracking-tight text-foreground">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground leading-relaxed">
        {description}
      </p>
      <div className="mt-8">
        <Link
          to={`/workspaces/${workspaceId}` as any}
          className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          Return to Overview
        </Link>
      </div>
    </div>
  );
}

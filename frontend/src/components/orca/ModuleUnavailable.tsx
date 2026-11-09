import { useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

/** Honest placeholder for modules whose backend capability does not exist yet. */
export function ModuleUnavailable({ title, description, capabilities }: { title: string; description: string; capabilities: string[] }) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-10">
      <p className="eyebrow">Module</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">{description}</p>

      <div className="panel mt-8 p-6">
        <div className="flex items-center gap-2">
          <span className="inline-block size-1.5 rounded-full bg-subtle-foreground" aria-hidden />
          <p className="text-sm font-medium">Not yet available</p>
        </div>
        <p className="mt-1.5 text-sm text-muted-foreground">
          The ORCA backend does not expose this capability yet. This workspace will connect automatically once it does —
          nothing here is simulated.
        </p>
        <p className="eyebrow mt-6">Planned capabilities</p>
        <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
          {capabilities.map((c) => (
            <li key={c} className="text-sm text-foreground before:mr-2 before:text-subtle-foreground before:content-['—']">
              {c}
            </li>
          ))}
        </ul>
      </div>

      <Button variant="outline" className="mt-6" onClick={() => window.history.back()}>
        Return to Overview
      </Button>
    </div>
  );
}

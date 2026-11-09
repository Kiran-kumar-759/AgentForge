import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { ResearchResultsPanel } from "@/components/orca/IntelligencePanels";

const TITLE = "Research";
const DESC = "Analytical workspace for marine researchers to query, compare and annotate observations.";

export const Route = createFileRoute("/workspaces/$workspaceId/research")({
  head: () => ({
    meta: [
      { title: `${TITLE} — ORCA` },
      { name: "description", content: DESC },
      { property: "og:title", content: `${TITLE} — ORCA` },
      { property: "og:description", content: DESC },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: ResearchPage,
});

function ResearchPage() {
  const [query, setQuery] = useState("");
  const [activePayload, setActivePayload] = useState<any>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setActivePayload({
      query: query,
      enable_web_search: false,
      context_time_range_days: 30
    });
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <p className="eyebrow">ORCA · Research Engine</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Marine Research</h1>
      <p className="mt-2 max-w-lg text-[15px] leading-relaxed text-muted-foreground">
        Semantic query interface connected to the ORCA document RAG engine and evidence repository.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 flex w-full items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3 shadow-sm focus-within:ring-1 focus-within:ring-primary max-w-2xl">
        <Search className="size-4 shrink-0 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a research question..."
          className="flex-1 min-w-0 bg-transparent text-[14px] outline-none placeholder:text-muted-foreground"
          autoComplete="off"
        />
        <button type="submit" disabled={!query.trim()} className="shrink-0 rounded bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50">
          Analyze
        </button>
      </form>

      <div className="mt-8">
        {activePayload ? (
          <ResearchResultsPanel requestPayload={activePayload} />
        ) : (
          <div className="flex h-48 items-center justify-center rounded-lg border border-border bg-surface text-sm text-subtle-foreground">
            Enter a research query above to begin semantic extraction.
          </div>
        )}
      </div>
    </div>
  );
}

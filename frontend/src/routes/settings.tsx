import { createFileRoute } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getApiBaseUrl, getApiPrefix, setApiConfig } from "@/api/client";
import { ConnectionStatus } from "@/components/orca/StatusIndicator";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — ORCA" },
      { name: "description", content: "Configure the ORCA backend connection." },
      { property: "og:title", content: "Settings — ORCA" },
      { property: "og:description", content: "Configure the ORCA backend connection." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const qc = useQueryClient();
  const [base, setBase] = useState("");
  const [prefix, setPrefix] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setBase(getApiBaseUrl());
    setPrefix(getApiPrefix());
  }, []);

  return (
    <div className="mx-auto max-w-2xl px-6 py-8 lg:px-10">
      <p className="eyebrow">Settings</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Backend connection</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        ORCA reads all marine data from its FastAPI service. The default comes from <span className="num">VITE_API_BASE_URL</span>; you can override it for this browser.
      </p>
      <form
        className="panel mt-8 space-y-5 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          setApiConfig(base, prefix);
          qc.invalidateQueries();
          setSaved(true);
        }}
      >
        <label className="block">
          <span className="text-xs font-medium">Backend URL</span>
          <input value={base} onChange={(e) => { setBase(e.target.value); setSaved(false); }} placeholder="https://orca-api.example.org"
            className="num mt-1.5 h-9 w-full rounded-md border border-input bg-surface px-3 text-sm" />
        </label>
        <label className="block">
          <span className="text-xs font-medium">API prefix</span>
          <input value={prefix} onChange={(e) => { setPrefix(e.target.value); setSaved(false); }} placeholder="/api/v1"
            className="num mt-1.5 h-9 w-full rounded-md border border-input bg-surface px-3 text-sm" />
        </label>
        <div className="flex items-center justify-between">
          <ConnectionStatus />
          <div className="flex items-center gap-3">
            {saved && <span className="text-xs text-muted-foreground">Saved</span>}
            <Button type="submit" size="sm">Save and reconnect</Button>
          </div>
        </div>
      </form>
      <p className="mt-4 text-xs text-subtle-foreground">
        The backend must allow requests from this site (CORS). No credentials or keys are stored in the browser.
      </p>
    </div>
  );
}

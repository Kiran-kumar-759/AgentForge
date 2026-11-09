import { createFileRoute } from "@tanstack/react-router";
import { ModuleUnavailable } from "@/components/orca/ModuleUnavailable";

const TITLE = "Cyclones";
const DESC = "Tropical cyclone tracking and impact assessment for the Indian Ocean basin.";

export const Route = createFileRoute("/workspaces/$workspaceId/cyclones")({
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
  component: () => <ModuleUnavailable title={TITLE} description={DESC} capabilities={["Active cyclone tracks", "Forecast cones", "Coastal impact zones", "Advisory history"]} />,
});

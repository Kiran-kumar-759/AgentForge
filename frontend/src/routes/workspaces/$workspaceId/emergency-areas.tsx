import { createFileRoute } from "@tanstack/react-router";
import { UnavailableState } from "@/components/ui/UnavailableState";

export const Route = createFileRoute("/workspaces/$workspaceId/emergency-areas")({
  component: RouteComponent,
});

function RouteComponent() {
  const { workspaceId } = Route.useParams();
  
  return (
    <UnavailableState 
      title="Not available yet" 
      description="This module will be connected in a later phase of ORCA."
      workspaceId={workspaceId}
    />
  );
}

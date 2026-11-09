import { useNavigate, useRouterState } from "@tanstack/react-router";
import { WORKSPACES } from "@/config/workspaces";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export function WorkspaceSwitcher({ collapsed }: { collapsed?: boolean }) {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const segments = pathname.split('/').filter(Boolean);
  const workspaceId = (segments[0] === 'workspaces' && segments[1]) ? segments[1] : "command-center";
  
  const currentWorkspace = (WORKSPACES[workspaceId] || WORKSPACES["command-center"])!;

  return (
    <div className={cn("px-2 py-2", collapsed && "flex justify-center")}>
      {collapsed ? (
        <div 
          className="flex size-8 items-center justify-center rounded-md border border-sidebar-border bg-sidebar-accent text-xs font-bold text-foreground"
          title={currentWorkspace.name}
        >
          {currentWorkspace.name.charAt(0)}
        </div>
      ) : (
        <Select
          value={workspaceId}
          onValueChange={(val) => {
            navigate({ to: "/workspaces/$workspaceId", params: { workspaceId: val } });
          }}
        >
          <SelectTrigger className="h-8 w-full bg-sidebar-accent text-xs font-medium border-sidebar-border focus:ring-0 focus:ring-offset-0">
            <SelectValue placeholder="Select workspace" />
          </SelectTrigger>
          <SelectContent>
            {Object.values(WORKSPACES).map((ws) => (
              <SelectItem key={ws.id} value={ws.id} className="text-xs">
                {ws.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}

import { useEffect, useState, type ReactNode } from "react";
import { Link, useRouterState, useParams } from "@tanstack/react-router";
import {
  Activity, PanelLeftClose, PanelLeftOpen, Settings
} from "lucide-react";
import { OrcaMark } from "./OrcaMark";
import { ConnectionStatus } from "./StatusIndicator";
import { cn } from "@/lib/utils";
import { WORKSPACES } from "@/config/workspaces";
import { WorkspaceSwitcher } from "@/components/workspace/WorkspaceSwitcher";
import type { LucideIcon } from "lucide-react";

const SECONDARY = [
  { to: "/settings", label: "Settings", icon: Settings },
];

function NavItem({ 
  to, 
  label, 
  icon: Icon, 
  collapsed,
  workspaceId
}: { 
  to: string; 
  label: string; 
  icon: LucideIcon; 
  collapsed: boolean;
  workspaceId: string;
}) {
  const finalTo = to ? `/workspaces/${workspaceId}/${to}` : `/workspaces/${workspaceId}/`;
  return (
    <Link
      to={finalTo}
      activeOptions={{ exact: true }}
      title={collapsed ? label : undefined}
      aria-label={collapsed ? label : undefined}
      className={cn(
        "group flex h-8 items-center gap-2.5 rounded-md px-2 text-[13px] text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground",
        collapsed && "justify-center px-0",
      )}
      activeProps={{ className: "bg-sidebar-accent !text-foreground font-medium" }}
    >
      <Icon className="size-4 shrink-0" strokeWidth={1.75} />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  // The route is /workspaces/:workspaceId/...
  const segments = pathname.split('/').filter(Boolean);
  const workspaceId = (segments[0] === 'workspaces' && segments[1]) ? segments[1] : "command-center";
  
  const workspace = (WORKSPACES[workspaceId] || WORKSPACES["command-center"])!;

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const apply = () => setCollapsed(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <aside
        className={cn(
          "flex shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200",
          collapsed ? "w-14" : "w-56",
        )}
        aria-label="Primary"
      >
        <div className={cn("flex h-12 items-center gap-2.5 px-3.5", collapsed && "justify-center px-0")}>
          <OrcaMark className="size-6 shrink-0" />
          {!collapsed && (
            <div className="leading-tight">
              <p className="text-[13px] font-semibold tracking-[0.08em]">ORCA</p>
              <p className="text-[10.5px] text-muted-foreground">Marine Intelligence</p>
            </div>
          )}
        </div>
        
        <WorkspaceSwitcher collapsed={collapsed} />

        <nav className="flex flex-1 flex-col gap-0.5 px-2 pt-2">
          {workspace.nav.map((n) => (
            <NavItem key={n.to} {...n} collapsed={collapsed} workspaceId={workspaceId} />
          ))}
          <div className="my-3 h-px bg-sidebar-border" />
          {SECONDARY.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              activeOptions={{ exact: true }}
              title={collapsed ? n.label : undefined}
              className={cn(
                "group flex h-8 items-center gap-2.5 rounded-md px-2 text-[13px] text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground",
                collapsed && "justify-center px-0"
              )}
              activeProps={{ className: "bg-sidebar-accent !text-foreground font-medium" }}
            >
              <n.icon className="size-4 shrink-0" strokeWidth={1.75} />
              {!collapsed && <span className="truncate">{n.label}</span>}
            </Link>
          ))}
        </nav>
        <div className={cn("p-2", collapsed && "flex justify-center")}>
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex h-8 items-center gap-2 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
          >
            {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
            {!collapsed && "Collapse"}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface px-4">
          <div className="flex min-w-0 items-center gap-2 text-[13px]">
            <span className="text-muted-foreground">ORCA</span>
            <span className="text-subtle-foreground">/</span>
            <span className="text-muted-foreground">{workspace.name}</span>
          </div>
          <div className="flex items-center gap-4">
            <ConnectionStatus />
            <div className="h-4 w-px bg-border" />
            <span
              className="flex size-7 items-center justify-center rounded-full border border-border bg-surface-raised text-[11px] text-muted-foreground"
              title="Not signed in — authentication is not available yet"
              aria-label="Guest user"
            >
              —
            </span>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}

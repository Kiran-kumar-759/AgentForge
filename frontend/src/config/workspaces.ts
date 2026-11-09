import {
  Activity, BookOpen, FileText, LayoutGrid, Map, Ship, Tornado, FlaskConical,
  LifeBuoy, Anchor, Route, ShieldAlert, Navigation, Search, RadioTower, Droplets, Bot, Zap, CloudLightning
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItemConfig = {
  to: string;
  label: string;
  icon: LucideIcon;
};

export type QuickActionConfig = {
  label: string;
  to: string;
};

export type WorkspaceConfig = {
  id: string;
  name: string;
  description: string;
  nav: NavItemConfig[];
  mapDefaults: {
    layers: string[];
  };
  quickActions: QuickActionConfig[];
};

export const WORKSPACES: Record<string, WorkspaceConfig> = {
  "command-center": {
    id: "command-center",
    name: "Command Center",
    description: "Unified Marine Intelligence Command Center",
    nav: [
      { to: "", label: "Overview", icon: LayoutGrid },
      { to: "agent", label: "Agent Console", icon: Bot },
      { to: "map", label: "Marine Map", icon: Map },
      { to: "alerts", label: "Alerts", icon: ShieldAlert },
    ],
    mapDefaults: {
      layers: ["sst", "wave_height", "cyclone_tracks", "marine_observations"],
    },
    quickActions: [
      { label: "Ask Agent", to: "agent" },
      { label: "Marine Map", to: "map" },
      { label: "Active Alerts", to: "alerts" },
    ],
  },
  fisherman: {
    id: "fisherman",
    name: "Fisherman",
    description: "Marine conditions for your selected area",
    nav: [
      { to: "", label: "Overview", icon: LayoutGrid },
      { to: "agent", label: "Agent Console", icon: Bot },
      { to: "map", label: "Marine Map", icon: Map },
      { to: "conditions", label: "Marine Conditions", icon: Droplets },
      { to: "safety", label: "Safety", icon: LifeBuoy },
      { to: "fishing-areas", label: "Fishing Areas", icon: Anchor },
      { to: "evidence", label: "Evidence", icon: BookOpen },
      { to: "reports", label: "Reports", icon: FileText },
    ],
    mapDefaults: {
      layers: ["sea_surface_temperature", "wave_height", "wave_direction", "ocean_current", "coastline"],
    },
    quickActions: [
      { label: "View Marine Conditions", to: "conditions" },
      { label: "Open Marine Map", to: "map" },
      { label: "Check Safety Data", to: "safety" },
    ],
  },
  researcher: {
    id: "researcher",
    name: "Researcher",
    description: "Explore marine observations and scientific datasets",
    nav: [
      { to: "", label: "Overview", icon: LayoutGrid },
      { to: "map", label: "Marine Map", icon: Map },
      { to: "research", label: "Research", icon: FlaskConical },
      { to: "datasets", label: "Datasets", icon: Search },
      { to: "evidence", label: "Evidence", icon: BookOpen },
      { to: "reports", label: "Reports", icon: FileText },
    ],
    mapDefaults: {
      layers: ["sst", "wave_height", "observation_points", "dataset_context"],
    },
    quickActions: [
      { label: "Explore Observations", to: "map" },
      { label: "Inspect Dataset", to: "datasets" },
      { label: "View Provenance", to: "evidence" },
      { label: "Open Research", to: "research" },
    ],
  },
  "coastal-authority": {
    id: "coastal-authority",
    name: "Coastal Authority",
    description: "Coastal and marine situational awareness",
    nav: [
      { to: "", label: "Overview", icon: LayoutGrid },
      { to: "map", label: "Marine Map", icon: Map },
      { to: "monitoring", label: "Coastal Monitoring", icon: RadioTower },
      { to: "vessels", label: "Vessels", icon: Ship },
      { to: "protected-areas", label: "Protected Areas", icon: ShieldAlert },
      { to: "evidence", label: "Evidence", icon: BookOpen },
      { to: "reports", label: "Reports", icon: FileText },
    ],
    mapDefaults: {
      layers: ["coastline", "ports", "protected_areas", "marine_observations"],
    },
    quickActions: [
      { label: "Open Coastal Map", to: "map" },
      { label: "Inspect Monitoring Data", to: "monitoring" },
      { label: "View Evidence", to: "evidence" },
    ],
  },
  "disaster-management": {
    id: "disaster-management",
    name: "Disaster Management",
    description: "Marine and coastal emergency intelligence",
    nav: [
      { to: "", label: "Overview", icon: LayoutGrid },
      { to: "agent", label: "Agent Console", icon: Bot },
      { to: "map", label: "Marine Map", icon: Map },
      { to: "cyclones", label: "Cyclones", icon: Tornado },
      { to: "exposure", label: "Exposure", icon: Activity },
      { to: "risk", label: "Risk", icon: ShieldAlert },
      { to: "emergency-areas", label: "Emergency Areas", icon: Navigation },
      { to: "reports", label: "Reports", icon: FileText },
    ],
    mapDefaults: {
      layers: ["coastline", "marine_conditions", "settlements", "cyclone_tracks", "risk_zones"],
    },
    quickActions: [
      { label: "Open Marine Map", to: "map" },
      { label: "View Monitoring Status", to: "cyclones" },
      { label: "Open Risk Workspace", to: "risk" },
    ],
  },
  "maritime-operator": {
    id: "maritime-operator",
    name: "Maritime Operator",
    description: "Marine conditions and operational awareness",
    nav: [
      { to: "", label: "Overview", icon: LayoutGrid },
      { to: "map", label: "Marine Map", icon: Map },
      { to: "routes", label: "Route Planning", icon: Route },
      { to: "vessels", label: "Vessels", icon: Ship },
      { to: "conditions", label: "Marine Conditions", icon: Droplets },
      { to: "risk", label: "Risk", icon: ShieldAlert },
      { to: "reports", label: "Reports", icon: FileText },
    ],
    mapDefaults: {
      layers: ["wave_height", "currents", "coastline", "restricted_areas"],
    },
    quickActions: [
      { label: "Open Marine Map", to: "map" },
      { label: "Check Marine Conditions", to: "conditions" },
      { label: "Open Route Planning", to: "routes" },
    ],
  },
};

/** Display helpers and variable registry. Never produces values — only formats backend data. */

export type LayerGroup = "marine" | "geographic" | "intelligence";

export interface LayerDef {
  key: string;
  label: string;
  group: LayerGroup;
  aliases: string[];
}

export const LAYERS: LayerDef[] = [
  { key: "sea_surface_temperature", label: "Sea Surface Temperature", group: "marine", aliases: ["sst", "sea_surface_temperature", "water_temperature"] },
  { key: "wave_height", label: "Wave Height", group: "marine", aliases: ["wave_height", "significant_wave_height", "swh"] },
  { key: "wave_direction", label: "Wave Direction", group: "marine", aliases: ["wave_direction", "mean_wave_direction"] },
  { key: "wave_period", label: "Wave Period", group: "marine", aliases: ["wave_period", "mean_wave_period", "peak_wave_period"] },
  { key: "ocean_current", label: "Ocean Current", group: "marine", aliases: ["ocean_current", "ocean_current_velocity", "current_speed", "ocean_current_speed"] },
  { key: "sea_level", label: "Sea Level", group: "marine", aliases: ["sea_level", "sea_level_height", "sea_level_height_msl", "ssh"] },
  { key: "coastline", label: "Coastline", group: "geographic", aliases: [] },
  { key: "ports", label: "Ports", group: "geographic", aliases: [] },
  { key: "settlements", label: "Settlements", group: "geographic", aliases: [] },
  { key: "protected_areas", label: "Protected Areas", group: "geographic", aliases: [] },
  { key: "restricted_areas", label: "Restricted Areas", group: "geographic", aliases: [] },
  { key: "risk_zones", label: "Risk Zones", group: "intelligence", aliases: [] },
  { key: "cyclone_tracks", label: "Cyclone Tracks", group: "intelligence", aliases: [] },
  { key: "vessel_locations", label: "Vessel Locations", group: "intelligence", aliases: [] },
  { key: "vessel_density", label: "Vessel Density", group: "intelligence", aliases: [] },
];

export const GROUP_LABEL: Record<LayerGroup, string> = {
  marine: "Marine conditions",
  geographic: "Geographic",
  intelligence: "Intelligence",
};

/** Map a backend variable name to a known layer key, or null if unrecognised. */
export function layerKeyFor(variable: string): string | null {
  const v = variable.toLowerCase().replace(/[\s-]+/g, "_");
  const hit = LAYERS.find((l) => l.key === v || l.aliases.includes(v));
  return hit ? hit.key : null;
}

export function variableLabel(variable: string): string {
  const key = layerKeyFor(variable);
  if (key) return LAYERS.find((l) => l.key === key)!.label;
  return variable.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function layerColorVar(variable: string): string {
  return `--layer-${layerKeyFor(variable) ?? "other"}`;
}

export function formatCoord(value: number | null | undefined, axis: "lat" | "lon"): string {
  if (value === null || value === undefined) return "—";
  const dir = axis === "lat" ? (value >= 0 ? "N" : "S") : value >= 0 ? "E" : "W";
  return `${Math.abs(value).toFixed(4)}° ${dir}`;
}

export function formatValue(value: number | null | undefined, unit?: string, variable?: string): string {
  if (value === null || value === undefined) return "—";
  
  if (variable === "weather_code") {
    const codes: Record<number, string> = {
      0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
      45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
      55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
      71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
      80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
      95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    };
    return codes[value] || `Code ${value}`;
  }

  if (variable && variable.includes("direction") && (!unit || unit === "°" || unit === "deg")) {
    const val = (value % 360 + 360) % 360;
    const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    const dir = dirs[Math.round(val / 22.5) % 16];
    return `${val.toFixed(0)}° (${dir})`;
  }

  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : abs >= 10 ? 1 : 2;
  const n = value.toFixed(digits);
  if (!unit || unit === "wmo code") return n;
  const u = unit === "C" || unit === "degC" || unit === "°C" ? "°C" : unit;
  return u.startsWith("°") ? `${n}${u}` : `${n} ${u}`;
}

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
const timeFmt = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" });

export function formatDate(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return Number.isNaN(d.getTime()) ? iso : dateFmt.format(d);
}

export function formatTime(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return Number.isNaN(d.getTime()) ? "" : `${timeFmt.format(d)} UTC`;
}

export function formatDateTime(iso?: string): string {
  if (!iso) return "—";
  const t = formatTime(iso);
  return t ? `${formatDate(iso)}, ${t}` : formatDate(iso);
}

/** Parses "14.5, 74.2" or "14.5N 74.2E" into a coordinate pair. */
export function parseCoordinates(input: string): [number, number] | null {
  const m = input.trim().match(/^(-?\d+(?:\.\d+)?)\s*°?\s*([NS])?[\s,;]+(-?\d+(?:\.\d+)?)\s*°?\s*([EW])?$/i);
  if (!m) return null;
  let lat = Number(m[1]);
  let lon = Number(m[3]);
  if (m[2]?.toUpperCase() === "S") lat = -Math.abs(lat);
  if (m[4]?.toUpperCase() === "W") lon = -Math.abs(lon);
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return [lat, lon];
}

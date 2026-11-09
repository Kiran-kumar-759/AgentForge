import { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import type { MarineObservation } from "@/api/types";
import { layerColorVar, layerKeyFor } from "@/lib/marine";

export const DEFAULT_CENTER: [number, number] = [14, 74];
export const DEFAULT_ZOOM = 4;

export interface MapApi {
  resetView: () => void;
  fitToData: () => void;
  flyTo: (lat: number, lon: number, zoom?: number) => void;
}

interface Props {
  observations?: MarineObservation[];
  visibleLayers?: Set<string>;
  selectedId?: string | null;
  onSelect?: (id: string | null) => void;
  onCursor?: (pos: { lat: number; lng: number } | null) => void;
  apiRef?: React.MutableRefObject<MapApi | null>;
  geojson?: any;
  center?: [number, number];
  zoom?: number;
  activeLayers?: string[]; // for simpler usage where full observations aren't used
}

/** Leaflet map. Leaflet is imported dynamically so SSR never evaluates it. */
export function MarineMap({ 
  observations = [], 
  visibleLayers = new Set(), 
  selectedId = null, 
  onSelect = () => {}, 
  onCursor = () => {}, 
  apiRef = { current: null },
  geojson,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM
}: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Leaflet.Map | null>(null);
  const LRef = useRef<typeof Leaflet | null>(null);
  const groupRef = useRef<Leaflet.LayerGroup | null>(null);
  const cb = useRef({ onSelect, onCursor });
  cb.current = { onSelect, onCursor };
  const visibleRef = useRef<MarineObservation[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let map: Leaflet.Map | null = null;
    import("leaflet").then((mod) => {
      const L = (mod as unknown as { default?: typeof Leaflet }).default ?? (mod as unknown as typeof Leaflet);
      if (cancelled || !el.current) return;
      LRef.current = L;
      map = L.map(el.current, { zoomControl: false, preferCanvas: true, worldCopyJump: true }).setView(center, zoom);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        
        maxZoom: 19,
      }).addTo(map);
      L.control.zoom({ position: "bottomright" }).addTo(map);
      L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);
      groupRef.current = L.layerGroup().addTo(map);
      map.on("mousemove", (e) => cb.current.onCursor({ lat: e.latlng.lat, lng: e.latlng.lng }));
      map.on("mouseout", () => cb.current.onCursor(null));
      map.on("click", () => cb.current.onSelect(null));
      mapRef.current = map;
      
      if (apiRef) {
        apiRef.current = {
          resetView: () => map?.flyTo(center, zoom, { duration: 0.6 }),
          fitToData: () => {
            const pts = visibleRef.current;
            if (!pts.length || !map) return;
            map.flyToBounds(L.latLngBounds(pts.map((o) => [o.latitude, o.longitude])).pad(0.2), { duration: 0.6, maxZoom: 9 });
          },
          flyTo: (lat, lon, z = 7) => map?.flyTo([lat, lon], z, { duration: 0.6 }),
        };
      }
      setReady(true);
    });
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
      apiRef.current = null;
    };
  }, [apiRef]);

  useEffect(() => {
    const L = LRef.current;
    const group = groupRef.current;
    if (!ready || !L || !group) return;
    group.clearLayers();
    const styles = getComputedStyle(document.documentElement);
    const fg = styles.getPropertyValue("--foreground").trim();
    const visible = observations.filter((o) => visibleLayers.has(layerKeyFor(o.variable) ?? o.variable));
    visibleRef.current = visible;
    for (const o of visible) {
      const color = styles.getPropertyValue(layerColorVar(o.variable)).trim();
      const selected = o.id === selectedId;
      const m = L.circleMarker([o.latitude, o.longitude], {
        radius: selected ? 8 : 5,
        color: selected ? fg : color,
        weight: selected ? 2.5 : 1,
        fillColor: color,
        fillOpacity: 0.85,
      });
      m.on("click", (e) => {
        L.DomEvent.stopPropagation(e);
        cb.current.onSelect(o.id);
      });
      
      const varName = o.variable.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
      const displayVal = `${o.value}${o.unit ? ` ${o.unit}` : ""}`;
      m.bindTooltip(`<strong>${varName}</strong><br/>${displayVal}<br/><span class="text-xs opacity-70">${o.provider || "Source"}</span>`, { direction: "top", offset: [0, -6] });
      m.addTo(group);
    }
  }, [ready, observations, visibleLayers, selectedId]);

  useEffect(() => {
    const L = LRef.current;
    const map = mapRef.current;
    if (!ready || !L || !map || !geojson) return;
    
    const layer = L.geoJSON(geojson, {
      style: (feature) => {
        if (feature?.properties?.feature_type === "hazard_polygon") {
          return { color: "#ef4444", fillColor: "#ef4444", fillOpacity: 0.2, weight: 2 };
        }
        return { color: "#3b82f6" };
      },
      pointToLayer: (feature, latlng) => {
        if (feature.properties?.feature_type === "settlement") {
          return L.circleMarker(latlng, { radius: 4, color: "#10b981", fillColor: "#10b981", fillOpacity: 0.8, weight: 1 });
        }
        if (feature.properties?.feature_type === "infrastructure") {
          const isCritical = feature.properties?.criticality === "high";
          const color = isCritical ? "#f59e0b" : "#6366f1";
          return L.circleMarker(latlng, { radius: 5, color, fillColor: color, fillOpacity: 0.8, weight: 1 });
        }
        return L.marker(latlng);
      },
      onEachFeature: (feature, layer) => {
        if (feature.properties?.name) {
          let tt = `<strong>${feature.properties.name}</strong>`;
          if (feature.properties.feature_type === "infrastructure") {
            tt += `<br/>Type: ${feature.properties.infrastructure_type}`;
          } else if (feature.properties.feature_type === "settlement") {
            tt += `<br/>Type: ${feature.properties.place_type}`;
          }
          layer.bindTooltip(tt);
        }
      }
    });
    
    layer.addTo(map);
    
    // Fit bounds
    if (geojson.features && geojson.features.length > 0) {
      map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 12 });
    }
    
    return () => {
      map.removeLayer(layer);
    };
  }, [ready, geojson]);

  return <div ref={el} className="absolute inset-0" role="application" aria-label="Marine map" />;
}

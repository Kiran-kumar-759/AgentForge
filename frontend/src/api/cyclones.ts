import { queryOptions } from "@tanstack/react-query";
import { apiGet, getApiBaseUrl } from "./client";

export const CYCLONES_ENDPOINTS = {
  list: "/cyclones",
  details: (id: string) => `/cyclones/${id}`,
  track: (id: string) => `/cyclones/${id}/track`,
} as const;

export interface CycloneEvent {
  external_id: string;
  name: string;
  classification: string;
  current_latitude: number;
  current_longitude: number;
  is_active: boolean;
  basin?: string;
  max_wind_speed?: number;
}

export interface CycloneTrackPoint {
  latitude: number;
  longitude: number;
  timestamp: string;
  max_wind_speed?: number;
  classification?: string;
}

export interface CycloneTrack {
  external_id: string;
  observed_track: CycloneTrackPoint[];
  forecast_track: CycloneTrackPoint[];
}

export interface CycloneFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: CycloneEvent;
}

export interface CycloneFeatureCollection {
  type: "FeatureCollection";
  features: CycloneFeature[];
  metadata: any;
}

export const cyclonesQuery = (activeOnly = true) =>
  queryOptions({
    queryKey: ["cyclones", { activeOnly }],
    queryFn: () => apiGet<CycloneFeatureCollection>(CYCLONES_ENDPOINTS.list, (d) => d as CycloneFeatureCollection, { params: { active_only: activeOnly } }),
  });

export const cycloneDetailsQuery = (id: string) =>
  queryOptions({
    queryKey: ["cyclones", id],
    queryFn: () => apiGet<CycloneEvent>(CYCLONES_ENDPOINTS.details(id), (d) => d as CycloneEvent),
    enabled: !!id,
  });

export const cycloneTrackQuery = (id: string) =>
  queryOptions({
    queryKey: ["cyclones", id, "track"],
    queryFn: () => apiGet<CycloneTrack>(CYCLONES_ENDPOINTS.track(id), (d) => d as CycloneTrack),
    enabled: !!id,
  });

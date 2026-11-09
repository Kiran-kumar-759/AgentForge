import { queryOptions } from "@tanstack/react-query";
import { apiGet } from "./client";

export const VESSELS_ENDPOINTS = {
  list: "/vessels",
  details: (id: string) => `/vessels/${id}`,
} as const;

export interface VesselPosition {
  latitude: number;
  longitude: number;
  speed?: number;
  course?: number;
  heading?: number;
  timestamp: string;
}

export interface Vessel {
  id: string;
  mmsi?: string;
  name?: string;
  vessel_type?: string;
  length?: number;
  width?: number;
  callsign?: string;
  destination?: string;
  updated_at?: string;
  last_position?: VesselPosition;
}

export interface VesselFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: Vessel;
}

export interface VesselFeatureCollection {
  type: "FeatureCollection";
  features: VesselFeature[];
  metadata: any;
}

export const vesselsQuery = (limit = 1000) =>
  queryOptions({
    queryKey: ["vessels", { limit }],
    queryFn: () => apiGet<VesselFeatureCollection>(VESSELS_ENDPOINTS.list, (d) => d as VesselFeatureCollection, { params: { limit } }),
  });

export const vesselDetailsQuery = (id: string) =>
  queryOptions({
    queryKey: ["vessels", id],
    queryFn: () => apiGet<Vessel>(VESSELS_ENDPOINTS.details(id), (d) => d as Vessel),
    enabled: !!id,
  });

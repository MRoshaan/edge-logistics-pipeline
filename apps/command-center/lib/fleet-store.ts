import { create } from "zustand";

import { NearestDriver, NearestDriversResponse } from "@/lib/types";
import { haversineMeters } from "@/lib/utils";

type Point = { longitude: number; latitude: number };

type FleetConnection = "connecting" | "open" | "closed";

type FleetState = {
  selectedPoint: Point;
  center: [number, number];
  maxDistanceMeters: number;
  driversById: Record<string, NearestDriver>;
  visibleDriverIds: string[];
  driverSeqById: Record<string, number>;
  connection: FleetConnection;
  lastMessageAt: string | null;
  reconnectCount: number;
  setSelectedPoint: (point: Point) => void;
  setMaxDistanceMeters: (meters: number) => void;
  setSnapshot: (snapshot: NearestDriversResponse) => void;
  mergeDriverEvent: (event: {
    driver: Partial<NearestDriver>;
    seq?: number;
    timestamp?: string;
  }) => void;
  markSocketMessage: (timestamp?: string) => void;
  incrementReconnectCount: () => void;
  setConnection: (status: FleetConnection) => void;
};

const DEFAULT_POINT: Point = { longitude: 67.0011, latitude: 24.8607 };

function recalculateVisibleDriverIds(
  driversById: Record<string, NearestDriver>,
  maxDistanceMeters: number
): string[] {
  return Object.values(driversById)
    .filter((driver) => driver.distanceMeters <= maxDistanceMeters)
    .map((driver) => driver.driverId);
}

function toEpochMs(value?: string): number {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export const useFleetStore = create<FleetState>((set) => ({
  selectedPoint: DEFAULT_POINT,
  center: [DEFAULT_POINT.latitude, DEFAULT_POINT.longitude],
  maxDistanceMeters: 5000,
  driversById: {},
  visibleDriverIds: [],
  driverSeqById: {},
  connection: "closed",
  lastMessageAt: null,
  reconnectCount: 0,
  setSelectedPoint: (point) =>
    set((state) => {
      const center = [point.latitude, point.longitude] as [number, number];
      const driversById: Record<string, NearestDriver> = {};

      for (const [driverId, driver] of Object.entries(state.driversById)) {
        const [driverLon, driverLat] = driver.location.coordinates;
        const distanceMeters = haversineMeters(
          point.latitude,
          point.longitude,
          driverLat,
          driverLon
        );
        driversById[driverId] = { ...driver, distanceMeters };
      }

      return {
        selectedPoint: point,
        center,
        driversById,
        visibleDriverIds: recalculateVisibleDriverIds(driversById, state.maxDistanceMeters),
      };
    }),
  setMaxDistanceMeters: (meters) =>
    set((state) => ({
      maxDistanceMeters: meters,
      visibleDriverIds: recalculateVisibleDriverIds(state.driversById, meters),
    })),
  setSnapshot: (snapshot) =>
    set((state) => {
      const selectedPoint: Point = {
        longitude: snapshot.center.coordinates[0],
        latitude: snapshot.center.coordinates[1],
      };
      const driversById: Record<string, NearestDriver> = {};
      for (const driver of snapshot.drivers) {
        driversById[driver.driverId] = driver;
      }
      return {
        selectedPoint,
        driversById,
        visibleDriverIds: recalculateVisibleDriverIds(driversById, state.maxDistanceMeters),
        center: [snapshot.center.coordinates[1], snapshot.center.coordinates[0]],
      };
    }),
  mergeDriverEvent: (event) =>
    set((state) => {
      const driver = event.driver;
      const key = driver.driverId ?? driver.id;
      if (!key) {
        return state;
      }
      const existing = state.driversById[key];
      if (!driver.location) {
        return state;
      }

      const previousSeq = state.driverSeqById[key] ?? 0;
      const incomingSeq = event.seq ?? previousSeq + 1;
      if (incomingSeq <= previousSeq) {
        return state;
      }

      const incomingTimestamp = driver.updatedAt ?? event.timestamp;
      const previousTimestamp = existing?.updatedAt;
      if (toEpochMs(incomingTimestamp) < toEpochMs(previousTimestamp)) {
        return state;
      }

      const [centerLon, centerLat] = [state.selectedPoint.longitude, state.selectedPoint.latitude];
      const [driverLon, driverLat] = driver.location.coordinates;
      const distanceMeters = haversineMeters(centerLat, centerLon, driverLat, driverLon);

      const merged: NearestDriver = {
        id: driver.id ?? existing?.id ?? key,
        driverId: key,
        status: driver.status ?? existing?.status ?? "online",
        distanceMeters,
        location: driver.location,
        updatedAt: incomingTimestamp ?? existing?.updatedAt,
      };

      const driversById = {
        ...state.driversById,
        [key]: merged,
      };

      return {
        driversById,
        driverSeqById: {
          ...state.driverSeqById,
          [key]: incomingSeq,
        },
        lastMessageAt: event.timestamp ?? new Date().toISOString(),
        visibleDriverIds: recalculateVisibleDriverIds(driversById, state.maxDistanceMeters),
      };
    }),
  markSocketMessage: (timestamp) =>
    set({
      lastMessageAt: timestamp ?? new Date().toISOString(),
    }),
  incrementReconnectCount: () =>
    set((state) => ({
      reconnectCount: state.reconnectCount + 1,
    })),
  setConnection: (status) => set({ connection: status }),
}));

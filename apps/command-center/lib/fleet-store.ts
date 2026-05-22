import { create } from "zustand";

import { NearestDriver, NearestDriversResponse } from "@/lib/types";

type Point = { longitude: number; latitude: number };

type FleetConnection = "connecting" | "open" | "closed";

type FleetState = {
  selectedPoint: Point;
  center: [number, number];
  driversById: Record<string, NearestDriver>;
  connection: FleetConnection;
  setSelectedPoint: (point: Point) => void;
  setSnapshot: (snapshot: NearestDriversResponse) => void;
  mergeDriverUpdate: (driver: Partial<NearestDriver>) => void;
  setConnection: (status: FleetConnection) => void;
};

const DEFAULT_POINT: Point = { longitude: 67.0011, latitude: 24.8607 };

export const useFleetStore = create<FleetState>((set) => ({
  selectedPoint: DEFAULT_POINT,
  center: [DEFAULT_POINT.latitude, DEFAULT_POINT.longitude],
  driversById: {},
  connection: "closed",
  setSelectedPoint: (point) => set({ selectedPoint: point, center: [point.latitude, point.longitude] }),
  setSnapshot: (snapshot) =>
    set(() => {
      const driversById: Record<string, NearestDriver> = {};
      for (const driver of snapshot.drivers) {
        driversById[driver.driverId] = driver;
      }
      return {
        driversById,
        center: [snapshot.center.coordinates[1], snapshot.center.coordinates[0]],
      };
    }),
  mergeDriverUpdate: (driver) =>
    set((state) => {
      const key = driver.driverId ?? driver.id;
      if (!key) {
        return state;
      }
      const existing = state.driversById[key];
      if (!driver.location) {
        return state;
      }

      const merged: NearestDriver = {
        id: driver.id ?? existing?.id ?? key,
        driverId: key,
        status: driver.status ?? existing?.status ?? "online",
        distanceMeters: driver.distanceMeters ?? existing?.distanceMeters ?? 0,
        location: driver.location,
        updatedAt: driver.updatedAt ?? existing?.updatedAt,
      };

      return {
        driversById: {
          ...state.driversById,
          [key]: merged,
        },
      };
    }),
  setConnection: (status) => set({ connection: status }),
}));

"use client";

import { useEffect, useRef } from "react";

import { fetchNearestDrivers } from "@/lib/api";
import { useFleetStore } from "@/lib/fleet-store";

type DispatchEvent = {
  eventId?: string;
  seq?: number;
  type: string;
  timestamp?: string;
  payload?: {
    id?: string;
    driverId?: string;
    status?: "online" | "active" | "busy" | "offline";
    distanceMeters?: number;
    location?: { type: "Point"; coordinates: [number, number] };
    updatedAt?: string;
  };
};

function getSocketUrl() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const url = new URL(apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/dispatch";
  return url.toString();
}

export function useDispatchSocket() {
  const selectedPoint = useFleetStore((state) => state.selectedPoint);
  const socketRef = useRef<WebSocket | null>(null);
  const lastSnapshotKeyRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const snapshotKey = `${selectedPoint.latitude.toFixed(6)}:${selectedPoint.longitude.toFixed(6)}`;

    if (lastSnapshotKeyRef.current === snapshotKey) {
      return;
    }
    lastSnapshotKeyRef.current = snapshotKey;

    const loadSnapshot = async () => {
      try {
        const snapshot = await fetchNearestDrivers({
          longitude: selectedPoint.longitude,
          latitude: selectedPoint.latitude,
          maxDistanceMeters: 5000,
        });
        if (!cancelled) {
          useFleetStore.getState().setSnapshot(snapshot);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Snapshot fetch failed", error);
        }
      }
    };

    void loadSnapshot();

    return () => {
      cancelled = true;
    };
  }, [selectedPoint.latitude, selectedPoint.longitude]);

  useEffect(() => {
    let retryTimer: number | null = null;

    const connect = () => {
      if (socketRef.current) {
        socketRef.current.close();
      }

      useFleetStore.getState().setConnection("connecting");
      const url = getSocketUrl();
      console.log("Dispatch WS connecting", url);

      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log("Dispatch WS open");
        useFleetStore.getState().setConnection("open");
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as DispatchEvent;
          console.log("Dispatch WS event", parsed);
          useFleetStore.getState().markSocketMessage(parsed.timestamp);
          if (
            (parsed.type === "driver.location.updated" || parsed.type === "driver.status.updated") &&
            parsed.payload
          ) {
            useFleetStore.getState().mergeDriverEvent({
              driver: parsed.payload,
              seq: parsed.seq,
              timestamp: parsed.timestamp,
            });
          }
        } catch (error) {
          console.error("Dispatch WS parse error", error);
        }
      };

      ws.onerror = (error) => {
        console.error("Dispatch WS error", error);
      };

      ws.onclose = () => {
        useFleetStore.getState().setConnection("closed");
        useFleetStore.getState().incrementReconnectCount();
        console.log("Dispatch WS closed, retrying in 2s");
        retryTimer = window.setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
      useFleetStore.getState().setConnection("closed");
    };
  }, []);
}

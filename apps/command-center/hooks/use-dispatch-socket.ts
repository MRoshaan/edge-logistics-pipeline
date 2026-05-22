"use client";

import { useEffect, useRef } from "react";

import { fetchNearestDrivers } from "@/lib/api";
import { useFleetStore } from "@/lib/fleet-store";

type DispatchEvent = {
  type: string;
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
  const setSnapshot = useFleetStore((state) => state.setSnapshot);
  const mergeDriverUpdate = useFleetStore((state) => state.mergeDriverUpdate);
  const setConnection = useFleetStore((state) => state.setConnection);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadSnapshot = async () => {
      const snapshot = await fetchNearestDrivers({
        longitude: selectedPoint.longitude,
        latitude: selectedPoint.latitude,
        maxDistanceMeters: 5000,
      });
      if (!cancelled) {
        setSnapshot(snapshot);
      }
    };

    void loadSnapshot();
  }, [selectedPoint.latitude, selectedPoint.longitude, setSnapshot]);

  useEffect(() => {
    let retryTimer: number | null = null;

    const connect = () => {
      if (socketRef.current) {
        socketRef.current.close();
      }

      setConnection("connecting");
      const url = getSocketUrl();
      console.log("Dispatch WS connecting", url);

      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log("Dispatch WS open");
        setConnection("open");
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as DispatchEvent;
          console.log("Dispatch WS event", parsed);
          if (parsed.type === "driver.location.updated" && parsed.payload) {
            mergeDriverUpdate(parsed.payload);
          }
        } catch (error) {
          console.error("Dispatch WS parse error", error);
        }
      };

      ws.onerror = (error) => {
        console.error("Dispatch WS error", error);
      };

      ws.onclose = () => {
        setConnection("closed");
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
      setConnection("closed");
    };
  }, [mergeDriverUpdate, setConnection]);
}

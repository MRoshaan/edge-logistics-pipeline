"use client";

import { useEffect, useRef, useState } from "react";

import { fetchNearestDrivers } from "@/lib/api";
import { NearestDriversResponse } from "@/lib/types";

const DEFAULT_CENTER = { longitude: 67.0011, latitude: 24.8607 };

export function useNearestDrivers(intervalMs = 5000) {
  const [data, setData] = useState<NearestDriversResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPoint, setSelectedPoint] = useState(DEFAULT_CENTER);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const nextData = await fetchNearestDrivers({
          longitude: selectedPoint.longitude,
          latitude: selectedPoint.latitude,
          maxDistanceMeters: 5000,
        });
        if (!cancelled) {
          setData(nextData);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown polling error");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    run();
    timerRef.current = window.setInterval(run, intervalMs);

    return () => {
      cancelled = true;
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
      }
    };
  }, [intervalMs, selectedPoint.latitude, selectedPoint.longitude]);

  return { data, loading, error, selectedPoint, setSelectedPoint };
}

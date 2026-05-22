"use client";

import { useEffect, useRef, useState } from "react";

import { fetchNearestDrivers } from "@/lib/api";
import { NearestDriversResponse } from "@/lib/types";

export function useNearestDrivers(intervalMs = 5000) {
  const [data, setData] = useState<NearestDriversResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const nextData = await fetchNearestDrivers();
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
  }, [intervalMs]);

  return { data, loading, error };
}

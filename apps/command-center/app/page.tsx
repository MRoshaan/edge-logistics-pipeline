"use client";

import { DispatchTable } from "@/components/dispatch-table";
import { MapView } from "@/components/map-view";
import { useNearestDrivers } from "@/hooks/use-nearest-drivers";

export default function Page() {
  const { data, loading, error, selectedPoint, setSelectedPoint } = useNearestDrivers(5000);

  const center = data
    ? ([data.center.coordinates[1], data.center.coordinates[0]] as [number, number])
    : ([24.8607, 67.0011] as [number, number]);

  const drivers = data?.drivers ?? [];

  return (
    <main className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-4 p-4 lg:grid-cols-[2fr_1fr]">
      <section className="space-y-3">
        <header className="rounded-2xl border border-border bg-card/80 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Karachi Dispatch Grid
          </p>
          <h1 className="text-2xl font-bold">Fleet Command Center</h1>
          <p className="text-sm text-muted-foreground">
            Live nearest active drivers using Motor-powered geospatial queries.
          </p>
          <p className="text-xs text-muted-foreground">
            Query center: {selectedPoint.latitude.toFixed(5)}, {selectedPoint.longitude.toFixed(5)}
          </p>
          {loading ? <p className="text-xs text-accent">Syncing...</p> : null}
          {error ? <p className="text-xs text-red-400">{error}</p> : null}
        </header>
        <MapView
          center={center}
          drivers={drivers}
          onMapClick={(point) => {
            console.log("Map Click Handler Updating Query Center", point);
            setSelectedPoint(point);
          }}
        />
      </section>
      <aside>
        <DispatchTable drivers={drivers} />
      </aside>
    </main>
  );
}

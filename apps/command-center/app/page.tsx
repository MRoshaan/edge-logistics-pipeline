"use client";

import { DispatchTable } from "@/components/dispatch-table";
import { MapView } from "@/components/map-view";
import { useDispatchSocket } from "@/hooks/use-dispatch-socket";
import { useFleetStore } from "@/lib/fleet-store";

export default function Page() {
  useDispatchSocket();

  const center = useFleetStore((state) => state.center);
  const selectedPoint = useFleetStore((state) => state.selectedPoint);
  const setSelectedPoint = useFleetStore((state) => state.setSelectedPoint);
  const connection = useFleetStore((state) => state.connection);
  const drivers = useFleetStore((state) => Object.values(state.driversById));

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
          <p className="text-xs text-accent">Realtime socket: {connection}</p>
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

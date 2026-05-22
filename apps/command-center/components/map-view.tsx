"use client";

import "leaflet/dist/leaflet.css";

import dynamic from "next/dynamic";

import { NearestDriver } from "@/lib/types";

const MapContainer = dynamic(
  async () => (await import("react-leaflet")).MapContainer,
  { ssr: false }
);
const TileLayer = dynamic(async () => (await import("react-leaflet")).TileLayer, {
  ssr: false,
});
const Marker = dynamic(async () => (await import("react-leaflet")).Marker, {
  ssr: false,
});
const Popup = dynamic(async () => (await import("react-leaflet")).Popup, {
  ssr: false,
});

type MapViewProps = {
  center: [number, number];
  drivers: NearestDriver[];
};

export function MapView({ center, drivers }: MapViewProps) {
  return (
    <div className="h-[70vh] w-full overflow-hidden rounded-2xl border border-border">
      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {drivers.map((driver) => {
          const [lon, lat] = driver.location.coordinates;
          return (
            <Marker key={driver.driverId} position={[lat, lon]}>
              <Popup>
                <div>
                  <div>{driver.driverId}</div>
                  <div>Status: {driver.status}</div>
                  <div>{Math.round(driver.distanceMeters)} m away</div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

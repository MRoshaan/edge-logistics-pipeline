"use client";

import "leaflet/dist/leaflet.css";

import dynamic from "next/dynamic";
import { useMap, useMapEvents } from "react-leaflet";

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
  onMapClick: (point: { longitude: number; latitude: number }) => void;
};

function MapClickHandler({
  onMapClick,
}: {
  onMapClick: (point: { longitude: number; latitude: number }) => void;
}) {
  useMapEvents({
    click(event) {
      const point = {
        longitude: event.latlng.lng,
        latitude: event.latlng.lat,
      };
      console.log("Map Clicked", point);
      onMapClick(point);
    },
  });

  return null;
}

function RecenterMap({ center }: { center: [number, number] }) {
  const map = useMap();
  map.setView(center);
  return null;
}

export function MapView({ center, drivers, onMapClick }: MapViewProps) {
  return (
    <div className="h-[70vh] w-full overflow-hidden rounded-2xl border border-border">
      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom
        className="h-full w-full"
      >
        <MapClickHandler onMapClick={onMapClick} />
        <RecenterMap center={center} />
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

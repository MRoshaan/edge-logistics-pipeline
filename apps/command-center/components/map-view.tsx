"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
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

let isLeafletIconPatched = false;

const markerIconUrl = typeof markerIcon === "string" ? markerIcon : markerIcon.src;
const markerIcon2xUrl = typeof markerIcon2x === "string" ? markerIcon2x : markerIcon2x.src;
const markerShadowUrl = typeof markerShadow === "string" ? markerShadow : markerShadow.src;

const DEFAULT_MARKER_ICON = L.icon({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const BUSY_MARKER_ICON = L.icon({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "busy-driver-marker",
});

function patchLeafletDefaultIcon() {
  if (isLeafletIconPatched) {
    return;
  }

  delete (L.Icon.Default.prototype as L.Icon.Default & { _getIconUrl?: unknown })._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2xUrl,
    iconUrl: markerIconUrl,
    shadowUrl: markerShadowUrl,
  });

  isLeafletIconPatched = true;
}

if (typeof window !== "undefined") {
  patchLeafletDefaultIcon();
}

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
        {drivers.map((driver) => (
          <DriverMarker key={driver.driverId} driver={driver} />
        ))}
      </MapContainer>
    </div>
  );
}

function DriverMarker({ driver }: { driver: NearestDriver }) {
  const [lon, lat] = driver.location.coordinates;
  const [position, setPosition] = useState<[number, number]>([lat, lon]);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const start = position;
    const target: [number, number] = [lat, lon];
    const startTime = performance.now();
    const durationMs = 800;

    const step = (currentTime: number) => {
      const t = Math.min((currentTime - startTime) / durationMs, 1);
      const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      setPosition([
        start[0] + (target[0] - start[0]) * eased,
        start[1] + (target[1] - start[1]) * eased,
      ]);

      if (t < 1) {
        animationRef.current = requestAnimationFrame(step);
      }
    };

    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
    }
    animationRef.current = requestAnimationFrame(step);

    return () => {
      if (animationRef.current !== null) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [lat, lon]);

  return (
    <Marker
      position={position}
      icon={driver.status === "busy" ? BUSY_MARKER_ICON : DEFAULT_MARKER_ICON}
    >
      <Popup>
        <div>
          <div>{driver.driverId}</div>
          <div>Status: {driver.status}</div>
          <div>{Math.round(driver.distanceMeters)} m away</div>
        </div>
      </Popup>
    </Marker>
  );
}

"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef } from "react";
import { Marker as LeafletMarker } from "leaflet";
import { useMap, useMapEvents } from "react-leaflet";

import { NearestDriver } from "@/lib/types";
import { bearingDegrees } from "@/lib/utils";

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

function vehicleIcon(status: NearestDriver["status"]) {
  const stateClass = status === "busy" ? "busy" : "online";
  return L.divIcon({
    className: `vehicle-marker ${stateClass}`,
    html: `<div class="vehicle-marker-inner"><span class="vehicle-glyph">🚗</span></div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -16],
  });
}

function vehicleGlyph(driver: NearestDriver): string {
  if (driver.vehicleType === "Bike") {
    return "🏍️";
  }
  return driver.status === "busy" ? "🚕" : "🚗";
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
  const markerRef = useRef<LeafletMarker | null>(null);
  const previousRef = useRef<{ lat: number; lon: number } | null>(null);
  const lastBearingRef = useRef<number>(driver.heading ?? 0);

  const icon = useMemo(() => vehicleIcon(driver.status), [driver.status]);
  const animationMs = useMemo(() => {
    const speed = driver.speedKph ?? 40;
    const normalized = Math.max(20, Math.min(80, speed));
    // Faster vehicle -> slightly shorter animation for natural pacing
    const value = 3600 - (normalized - 20) * 25;
    return Math.max(1800, Math.min(3600, Math.round(value)));
  }, [driver.speedKph]);

  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) {
      previousRef.current = { lat, lon };
      return;
    }

    marker.setLatLng([lat, lon]);

    const markerElement = marker.getElement();
    if (!markerElement) {
      previousRef.current = { lat, lon };
      return;
    }

    markerElement.style.transitionDuration = `${animationMs}ms`;

    const previous = previousRef.current;
    const computedBearing = previous ? bearingDegrees(previous.lat, previous.lon, lat, lon) : null;
    const nextBearing =
      computedBearing !== null && Number.isFinite(computedBearing)
        ? computedBearing
        : (driver.heading ?? lastBearingRef.current);
    lastBearingRef.current = nextBearing;

    const glyph = markerElement.querySelector(".vehicle-glyph") as HTMLElement | null;
    if (glyph) {
      glyph.style.transform = `rotate(${nextBearing.toFixed(2)}deg)`;
    }

    previousRef.current = { lat, lon };
  }, [animationMs, lat, lon]);


  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) {
      return;
    }

    const markerElement = marker.getElement();
    if (!markerElement) {
      return;
    }

    const glyph = markerElement.querySelector(".vehicle-glyph") as HTMLElement | null;
    if (!glyph) {
      return;
    }

    glyph.textContent = vehicleGlyph(driver);
  }, [driver.status, driver.vehicleType]);

  return (
    <Marker
      position={[lat, lon]}
      icon={icon}
      ref={(marker) => {
        markerRef.current = marker as LeafletMarker | null;
      }}
    >
      <Popup>
        <div>
          <div className="font-semibold">{driver.driverName}</div>
          <div className="text-xs text-muted-foreground">{driver.plateNumber}</div>
          <div className="text-xs text-muted-foreground">{driver.vehicleType}</div>
          <div className="text-xs text-muted-foreground">Heading: {Math.round(driver.heading ?? 0)}°</div>
          <div>Status: {driver.status}</div>
          <div>{Math.round(driver.distanceMeters)} m away</div>
        </div>
      </Popup>
    </Marker>
  );
}

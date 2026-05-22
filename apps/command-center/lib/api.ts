import { NearestDriversResponse } from "@/lib/types";

const FALLBACK_CENTER = { longitude: 67.0011, latitude: 24.8607 };

export async function fetchNearestDrivers(): Promise<NearestDriversResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_EDGE_API_BASE_URL;

  if (!baseUrl) {
    return {
      center: {
        type: "Point",
        coordinates: [FALLBACK_CENTER.longitude, FALLBACK_CENTER.latitude],
      },
      limit: 5,
      drivers: [],
    };
  }

  const url = new URL("/api/v1/dispatch/nearest", baseUrl);
  url.searchParams.set("longitude", String(FALLBACK_CENTER.longitude));
  url.searchParams.set("latitude", String(FALLBACK_CENTER.latitude));
  url.searchParams.set("maxDistanceMeters", "3000");
  url.searchParams.set("limit", "5");

  const response = await fetch(url.toString(), {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch drivers: ${response.status}`);
  }

  return (await response.json()) as NearestDriversResponse;
}

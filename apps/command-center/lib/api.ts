import { NearestDriversResponse } from "@/lib/types";

type FetchNearestDriversParams = {
  longitude: number;
  latitude: number;
  maxDistanceMeters?: number;
};

export async function fetchNearestDrivers({
  longitude,
  latitude,
  maxDistanceMeters = 5000,
}: FetchNearestDriversParams): Promise<NearestDriversResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  const searchParams = new URLSearchParams({
    longitude: String(longitude),
    latitude: String(latitude),
    maxDistanceMeters: String(maxDistanceMeters),
  });
  const url = `${baseUrl}/api/v1/drivers/nearby?${searchParams.toString()}`;

  console.log("API Fetching URL...", url);

  const response = await fetch(url, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch drivers: ${response.status}`);
  }

  const data = (await response.json()) as Partial<NearestDriversResponse>;
  console.log("API Response Data", data);

  return {
    center: data.center ?? { type: "Point", coordinates: [longitude, latitude] },
    limit: data.limit ?? 5,
    drivers: Array.isArray(data.drivers) ? data.drivers : [],
  };
}

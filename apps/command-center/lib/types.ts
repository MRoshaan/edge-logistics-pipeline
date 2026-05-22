export type DriverStatus = "active" | "busy" | "offline";

export type GeoPoint = {
  type: "Point";
  coordinates: [number, number];
};

export type NearestDriver = {
  driverId: string;
  status: DriverStatus;
  distanceMeters: number;
  location: GeoPoint;
  updatedAt: string;
};

export type NearestDriversResponse = {
  center: GeoPoint;
  limit: number;
  drivers: NearestDriver[];
};

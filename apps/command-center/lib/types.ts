export type DriverStatus = "online" | "active" | "busy" | "offline";

export type VehicleType = "Car" | "Bike";

export type GeoPoint = {
  type: "Point";
  coordinates: [number, number];
};

export type NearestDriver = {
  id: string;
  driverId: string;
  driverName: string;
  plateNumber: string;
  status: DriverStatus;
  distanceMeters: number;
  location: GeoPoint;
  speedKph?: number;
  heading?: number;
  vehicleType?: VehicleType;
  updatedAt?: string;
};

export type NearestDriversResponse = {
  center: GeoPoint;
  limit: number;
  drivers: NearestDriver[];
};

export type DispatchAssignRequest = {
  driverId: string;
  dispatcherId: string;
};

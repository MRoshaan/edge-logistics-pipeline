import { NearestDriver } from "@/lib/types";

type DispatchTableProps = {
  drivers: NearestDriver[];
};

export function DispatchTable({ drivers }: DispatchTableProps) {
  return (
    <div className="rounded-2xl border border-border bg-card/90 p-4">
      <h2 className="mb-4 text-lg font-semibold text-card-foreground">Nearest Drivers</h2>
      <div className="max-h-[65vh] overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="pb-2">Driver</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Distance</th>
            </tr>
          </thead>
          <tbody>
            {drivers.length === 0 ? (
              <tr>
                <td className="py-3 text-muted-foreground" colSpan={3}>
                  No active drivers in range.
                </td>
              </tr>
            ) : (
              drivers.map((driver) => (
                <tr key={driver.driverId} className="border-t border-border/50">
                  <td className="py-2">{driver.driverId}</td>
                  <td className="py-2 capitalize">{driver.status}</td>
                  <td className="py-2">{Math.round(driver.distanceMeters)} m</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

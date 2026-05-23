"use client";

import { useState } from "react";

import { assignDriver } from "@/lib/api";
import { NearestDriver } from "@/lib/types";

type DispatchTableProps = {
  drivers: NearestDriver[];
};

export function DispatchTable({ drivers }: DispatchTableProps) {
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);

  const onAssign = async (driverId: string) => {
    setAssigningId(driverId);
    setAlertMessage(null);

    try {
      await assignDriver({
        driverId,
        dispatcherId: "user-123",
      });
      setAlertMessage(`Assigned ${driverId} successfully.`);
    } catch (error) {
      const maybe = error as { status?: number };
      if (maybe.status === 409) {
        setAlertMessage("Assignment Failed: Driver claimed by another dispatcher.");
      } else {
        setAlertMessage("Assignment Failed: Network or server error.");
      }
    } finally {
      setAssigningId(null);
    }
  };

  return (
    <div className="rounded-2xl border border-border bg-card/90 p-4">
      <h2 className="mb-4 text-lg font-semibold text-card-foreground">Nearest Drivers</h2>
      {alertMessage ? (
        <div className="mb-3 rounded-md border border-border bg-muted px-3 py-2 text-xs text-foreground">
          {alertMessage}
        </div>
      ) : null}
      <div className="max-h-[65vh] overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="pb-2">Driver</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Distance</th>
              <th className="pb-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {drivers.length === 0 ? (
              <tr>
                <td className="py-3 text-muted-foreground" colSpan={4}>
                  No active drivers in range.
                </td>
              </tr>
            ) : (
              drivers.map((driver) => (
                <tr key={driver.id} className="border-t border-border/50">
                  <td className="py-2">{driver.driverId}</td>
                  <td className="py-2 capitalize">{driver.status}</td>
                  <td className="py-2">{Math.round(driver.distanceMeters)} m</td>
                  <td className="py-2">
                    <button
                      type="button"
                      className="rounded bg-accent px-2 py-1 text-xs text-accent-foreground disabled:opacity-60"
                      onClick={() => onAssign(driver.driverId)}
                      disabled={assigningId === driver.driverId || driver.status === "busy"}
                    >
                      {driver.status === "busy"
                        ? "Busy"
                        : assigningId === driver.driverId
                          ? "Assigning..."
                          : "Assign"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

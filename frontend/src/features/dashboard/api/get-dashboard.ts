import type { DashboardResponse } from "../model/dashboard.types";

export async function getDashboard(signal?: AbortSignal): Promise<DashboardResponse> {
  const response = await fetch("/api/frontend/dashboard", {
    method: "GET",
    signal,
  });

  if (!response.ok) {
    throw new Error("Failed to load dashboard");
  }

  return (await response.json()) as DashboardResponse;
}

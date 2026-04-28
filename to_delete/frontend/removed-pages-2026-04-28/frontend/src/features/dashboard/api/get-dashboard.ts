import type { DashboardRawPayload } from "../model/dashboard.types";

export async function getDashboard(signal?: AbortSignal): Promise<DashboardRawPayload> {
  const response = await fetch("/api/frontend/dashboard", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`dashboard request failed: ${response.status}`);
  }

  return (await response.json()) as DashboardRawPayload;
}

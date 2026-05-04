export async function refreshMarketDataChart(
  chartId: string,
): Promise<{ ok: boolean; point_counts: Record<string, number> }> {
  const response = await fetch(`/api/frontend/modules/market-data/sync/${chartId}`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error("refresh failed");
  }
  return response.json() as Promise<{ ok: boolean; point_counts: Record<string, number> }>;
}

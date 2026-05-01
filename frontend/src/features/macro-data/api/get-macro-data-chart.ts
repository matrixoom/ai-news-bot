import type { MacroChartPayload, MacroDataRangeSelection } from "../model/macro-data.types";

export async function getMacroDataChart(options: {
  chartId: string;
  range: MacroDataRangeSelection;
  signal?: AbortSignal;
}): Promise<MacroChartPayload> {
  const params = new URLSearchParams({ range: options.range.type });
  if (options.range.type === "custom") {
    if (options.range.startDate) {
      params.set("start_date", options.range.startDate);
    }
    if (options.range.endDate) {
      params.set("end_date", options.range.endDate);
    }
  }
  const response = await fetch(`/api/frontend/modules/macro-data/charts/${options.chartId}?${params.toString()}`, {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(`macro data chart request failed: ${response.status}`);
  }

  return (await response.json()) as MacroChartPayload;
}

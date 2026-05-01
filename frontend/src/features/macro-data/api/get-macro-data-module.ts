import type { MacroDataModulePayload, MacroDataTab } from "../model/macro-data.types";

export async function getMacroDataModule(options: {
  tab: MacroDataTab;
  signal?: AbortSignal;
}): Promise<MacroDataModulePayload> {
  const params = new URLSearchParams({ tab: options.tab });
  const response = await fetch(`/api/frontend/modules/macro-data?${params.toString()}`, {
    headers: { Accept: "application/json" },
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(`macro data module request failed: ${response.status}`);
  }

  return (await response.json()) as MacroDataModulePayload;
}

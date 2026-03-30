import type { MacroModuleRawPayload } from "../model/macro-module.types";

export async function getMacroModule(signal?: AbortSignal): Promise<MacroModuleRawPayload> {
  const response = await fetch("/api/frontend/modules/macro", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`macro request failed: ${response.status}`);
  }

  return (await response.json()) as MacroModuleRawPayload;
}

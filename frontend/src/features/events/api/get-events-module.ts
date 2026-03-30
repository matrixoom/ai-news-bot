import type { EventsModuleRawPayload } from "../model/events-module.types";

export async function getEventsModule(signal?: AbortSignal): Promise<EventsModuleRawPayload> {
  const response = await fetch("/api/frontend/modules/events", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`events request failed: ${response.status}`);
  }

  return (await response.json()) as EventsModuleRawPayload;
}

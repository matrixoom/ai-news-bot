import type { EventOutlookPayload, EventOutlookRegion } from "../model/event-outlook.types";

type GetEventOutlookModuleOptions = {
  region: EventOutlookRegion;
  startDate?: string;
  endDate?: string;
  refresh?: boolean;
  signal?: AbortSignal;
};

export async function getEventOutlookModule(options: GetEventOutlookModuleOptions): Promise<EventOutlookPayload> {
  const params = new URLSearchParams({ region: options.region });
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  if (options.refresh) params.set("refresh", "1");

  const response = await fetch(`/api/frontend/modules/event-outlook?${params.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error("Event Outlook module request failed");
  }

  return (await response.json()) as EventOutlookPayload;
}

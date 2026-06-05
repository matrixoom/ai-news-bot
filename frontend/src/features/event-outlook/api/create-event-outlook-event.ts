import type { EventOutlookCategory, EventOutlookEvent, EventOutlookRegion } from "../model/event-outlook.types";

export type CreateEventOutlookEventInput = {
  region: EventOutlookRegion;
  event_date: string;
  title: string;
  summary: string;
  category: EventOutlookCategory;
  source_name?: string;
  source_url?: string;
};

export async function createEventOutlookEvent(input: CreateEventOutlookEventInput): Promise<EventOutlookEvent> {
  const response = await fetch("/api/frontend/modules/event-outlook/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error("Outlook create request failed");
  }

  const payload = (await response.json()) as { event: EventOutlookEvent };
  return payload.event;
}

import type { EventOutlookEvent } from "../model/event-outlook.types";

export type UpdateEventOutlookEventInput = {
  id: number;
  title: string;
  summary: string;
};

export async function updateEventOutlookEvent(input: UpdateEventOutlookEventInput): Promise<EventOutlookEvent> {
  const response = await fetch(`/api/frontend/modules/event-outlook/events/${input.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: input.title,
      summary: input.summary,
    }),
  });

  if (!response.ok) {
    throw new Error("Event Outlook update request failed");
  }

  const payload = (await response.json()) as { event: EventOutlookEvent };
  return payload.event;
}

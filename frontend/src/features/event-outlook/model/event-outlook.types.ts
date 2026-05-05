import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type EventOutlookRegion = "domestic" | "international";
export type EventOutlookResolution = "day" | "week" | "month";
export type EventOutlookCategory = "technology" | "politics" | "finance";

export type EventOutlookRange = {
  start_date: string;
  end_date: string;
};

export type EventOutlookEvent = {
  id: number;
  region: EventOutlookRegion;
  event_date: string;
  title: string;
  summary: string;
  category: EventOutlookCategory;
  source_name: string;
  source_url: string;
  updated_at: string;
};

export type EventOutlookPayload = {
  generated_at: string;
  module: {
    id: "event-outlook";
    title: string;
    description: string;
  };
  region: EventOutlookRegion;
  tabs: ModuleTabDefinition<EventOutlookRegion>[];
  range: EventOutlookRange;
  resolution_options: Array<{ value: EventOutlookResolution; label: string }>;
  events: EventOutlookEvent[];
};

export const EVENT_OUTLOOK_TABS: readonly ModuleTabDefinition<EventOutlookRegion>[] = [
  { value: "domestic", label: "国内" },
  { value: "international", label: "国际" },
];

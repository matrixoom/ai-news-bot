import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type EventsModuleTab = "timeline" | "calendar" | "watch" | "sources";

export const EVENTS_MODULE_TABS: readonly ModuleTabDefinition<EventsModuleTab>[] = [
  { value: "timeline", label: "Timeline" },
  { value: "calendar", label: "Calendar" },
  { value: "watch", label: "Watch" },
  { value: "sources", label: "Sources" },
];

export type EventWindowItemView = {
  title: string;
  region: string;
  expectedDate: string;
  timeWindow: string;
  confidence: string;
  impactSummary: string;
  source: string;
};

export type EventOfficialLinkView = {
  region: string;
  label: string;
  url: string;
};

export type EventWindowSectionView = {
  key: string;
  title: string;
  status: string;
  note: string;
  itemCount: number;
  items: EventWindowItemView[];
  officialLinks: EventOfficialLinkView[];
};

export type EventWatchItemView = EventWindowItemView & {
  windowKey: string;
  windowTitle: string;
};

export type EventsModuleRawPayload = {
  generated_at: string;
  module: {
    id: "events";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      kind: "events";
      note: string;
      section: {
        key: string;
        title: string;
        status: string;
        items: Array<{
          title: string;
          region: string;
          expected_date: string;
          time_window: string;
          confidence: string;
          impact_summary: string;
          source: string;
        }>;
        official_links: Array<{
          region: string;
          label: string;
          url: string;
        }>;
      };
    }>;
  };
};

export type EventsModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  windowSections: EventWindowSectionView[];
  officialLinks: EventOfficialLinkView[];
  watchItems: EventWatchItemView[];
  totalItems: number;
};

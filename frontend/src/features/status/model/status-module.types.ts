import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type StatusModuleRawPayload = {
  generated_at: string;
  coverage_note: string;
  module: {
    id: "status";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      kind: "status";
      note: string;
      section: {
        key: string;
        label: string;
        status: string;
        detail: string;
      };
    }>;
  };
};

export type StatusModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  coverageNote: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  statusItems: Array<{
    id: string;
    label: string;
    status: string;
    detail: string;
  }>;
};

export type StatusModuleTab = "overview" | "freshness" | "sources";

export const STATUS_MODULE_TABS: readonly ModuleTabDefinition<StatusModuleTab>[] = [
  { value: "overview", label: "Overview" },
  { value: "freshness", label: "Freshness" },
  { value: "sources", label: "Sources" },
];

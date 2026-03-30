import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MacroModuleTab = "overview" | "compare" | "indicators" | "sources";

export const MACRO_MODULE_TABS: readonly ModuleTabDefinition<MacroModuleTab>[] = [
  { value: "overview", label: "Overview" },
  { value: "compare", label: "Compare" },
  { value: "indicators", label: "Indicators" },
  { value: "sources", label: "Sources" },
];

export type MacroIndicatorPoint = {
  periodEnd: string;
  periodLabel: string;
  value: number;
};

export type MacroIndicatorView = {
  key: string;
  label: string;
  status: string;
  latestValue: string;
  previousValue: string;
  changeLabel: string;
  trend: string;
  frequency: string;
  sourceLabel: string;
  sourceUrl: string;
  updatedAt: string;
  periodLabel: string;
  context: string;
  unit: string;
  points: MacroIndicatorPoint[];
};

export type MacroComparisonSection = {
  key: string;
  title: string;
  status: string;
  description: string;
  summary: string;
  primary: MacroIndicatorView;
  secondary: MacroIndicatorView | null;
  deltaLabel: string;
  deltaPoints: MacroIndicatorPoint[];
  sources: Array<{
    label: string;
    url: string;
  }>;
};

export type MacroModuleRawPayload = {
  generated_at: string;
  module: {
    id: "macro";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      kind: "macro";
      note: string;
      section: {
        key: string;
        title: string;
        status: string;
        description: string;
        summary: string;
        primary: {
          key: string;
          label: string;
          status: string;
          latest_value: string;
          previous_value: string;
          change_label: string;
          trend: string;
          frequency: string;
          source_label: string;
          source_url: string;
          updated_at: string;
          period_label: string;
          context: string;
          unit: string;
          points: Array<{
            period_end: string;
            period_label: string;
            value: number;
          }>;
        };
        secondary: null | {
          key: string;
          label: string;
          status: string;
          latest_value: string;
          previous_value: string;
          change_label: string;
          trend: string;
          frequency: string;
          source_label: string;
          source_url: string;
          updated_at: string;
          period_label: string;
          context: string;
          unit: string;
          points: Array<{
            period_end: string;
            period_label: string;
            value: number;
          }>;
        };
        delta_label: string;
        delta_points: Array<{
          period_end: string;
          period_label: string;
          value: number;
        }>;
        sources: Array<{
          label: string;
          url: string;
        }>;
      };
    }>;
  };
};

export type MacroSourceReference = {
  label: string;
  url: string;
  sectionTitles: string[];
};

export type MacroModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  comparisonSections: MacroComparisonSection[];
  indicators: MacroIndicatorView[];
  sources: MacroSourceReference[];
};

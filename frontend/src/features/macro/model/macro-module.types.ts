export type MacroModuleRawPayload = {
  generated_at: string;
  macro_sections: MacroSectionRaw[];
};

export type MacroIndicatorRaw = {
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

export type MacroSectionRaw = {
  key: string;
  title: string;
  status: string;
  description: string;
  summary: string;
  primary: MacroIndicatorRaw;
  secondary: MacroIndicatorRaw | null;
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

export type MacroIndicatorView = {
  key: string;
  label: string;
  latestValue: string;
  changeLabel: string;
  trend: string;
  frequency: string;
  sourceLabel: string;
  updatedAt: string;
  periodLabel: string;
  context: string;
};

export type MacroCardView = {
  key: string;
  title: string;
  status: string;
  description: string;
  summary: string;
  primary: MacroIndicatorView;
  secondary: MacroIndicatorView | null;
  sourceLabels: string[];
};

export type MacroStatusSummary = {
  label: string;
  value: string;
  detail: string;
};

export type MacroModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  moduleStatus: string;
  macroCards: MacroCardView[];
  statusSummaries: MacroStatusSummary[];
};

import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MacroDataTab = "gdp" | "credit" | "leverage" | "prices";

export type MacroDataRange = "6m" | "1y" | "3y" | "5y" | "10y" | "15y" | "20y" | "25y" | "30y" | "custom";

export type MacroDataRangeSelection = {
  type: MacroDataRange;
  startDate?: string;
  endDate?: string;
};

export type MacroRangeOption = {
  value: MacroDataRange;
  label: string;
};

export type MacroChartDefinition = {
  id: string;
  title: string;
  unit: string;
  frequency: string;
  status: string;
};

export type MacroDataModulePayload = {
  generated_at: string;
  module: {
    id: "macro-data";
    label: string;
    description: string;
    status: string;
    loading: boolean;
  };
  tabs: ModuleTabDefinition<MacroDataTab>[];
  tab: MacroDataTab;
  default_range: MacroDataRange;
  range_options: MacroRangeOption[];
  charts: MacroChartDefinition[];
};

export type MacroChartPoint = {
  date: string;
  period_label: string;
  value: number;
  unit: string;
  released_at: string;
};

export type MacroChartPayload = {
  id: string;
  title: string;
  unit: string;
  frequency: string;
  status: string;
  range: {
    type: MacroDataRange;
    start_date: string;
    end_date: string;
  };
  sync_state: {
    status: string;
    synced_at: string;
    warning_message: string;
    point_count: number;
  };
  series: Array<{
    name: string;
    points: MacroChartPoint[];
  }>;
};

export const MACRO_DATA_TABS: readonly ModuleTabDefinition<MacroDataTab>[] = [
  { value: "gdp", label: "GDP", description: "名义与实际 GDP" },
  { value: "credit", label: "信贷", description: "居民与企业新增贷款" },
  { value: "leverage", label: "杠杆率", description: "居民与企业杠杆率" },
  { value: "prices", label: "物价", description: "PPI 与 CPI" },
];

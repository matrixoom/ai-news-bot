import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MacroDataTab = "gdp" | "credit" | "climate" | "trade" | "prices" | "currency" | "expectations";

export type MacroDataRange = "6m" | "1y" | "3y" | "5y" | "10y" | "15y" | "20y" | "25y" | "30y" | "custom";

export type MacroDataFrequency = "monthly" | "quarterly" | "yearly";

export type MacroDataRangeSelection = {
  type: MacroDataRange;
  startDate?: string;
  endDate?: string;
};

export type MacroRangeOption = {
  value: MacroDataRange;
  label: string;
};

export type MacroFrequencyOption = {
  value: MacroDataFrequency;
  label: string;
};

export type MacroChartType = "line" | "bar_stacked" | "bar_stacked_line";

export type MacroChartDefinition = {
  id: string;
  title: string;
  unit: string;
  frequency: string;
  status: string;
  chart_type?: MacroChartType;
  wide?: boolean;
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
  default_frequency: MacroDataFrequency;
  frequency_options: MacroFrequencyOption[];
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
  chart_type?: MacroChartType;
  wide?: boolean;
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
  { value: "credit", label: "信贷", description: "居民与企业新增贷款、杠杆率、社融" },
  { value: "climate", label: "景气", description: "制造业与非制造业 PMI" },
  { value: "trade", label: "外贸", description: "进口与出口" },
  { value: "prices", label: "物价", description: "PPI 与 CPI" },
  { value: "currency", label: "货币", description: "M0、M1、M2 货币供应量" },
  { value: "expectations", label: "预期", description: "国债收益率、汇率与信用利差" },
];

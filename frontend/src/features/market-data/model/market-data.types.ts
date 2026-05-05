import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MarketDataTab = "commodities" | "precious_metals" | "stock_market" | "real_estate";

export type MarketDataRange = "6m" | "1y" | "3y" | "5y" | "10y" | "custom";

export type MarketDataFrequency = "daily" | "monthly" | "yearly";

export type MarketDataRangeSelection = {
  type: MarketDataRange;
  startDate?: string;
  endDate?: string;
};

export type MarketRangeOption = {
  value: MarketDataRange;
  label: string;
};

export type MarketFrequencyOption = {
  value: MarketDataFrequency;
  label: string;
};

export type MarketChartDefinition = {
  id: string;
  title: string;
  unit: string;
  frequency: string;
  status: string;
  chart_type?: string;
};

export type MarketDataModulePayload = {
  generated_at: string;
  module: {
    id: "market-data";
    label: string;
    description: string;
    status: string;
    loading: boolean;
  };
  tabs: ModuleTabDefinition<MarketDataTab>[];
  tab: MarketDataTab;
  default_range: MarketDataRange;
  default_frequency: MarketDataFrequency;
  frequency_options: MarketFrequencyOption[];
  range_options: MarketRangeOption[];
  charts: MarketChartDefinition[];
  housing_cities?: string[];
};

export type MarketChartPoint = {
  date: string;
  period_label: string;
  value: number;
  unit: string;
  released_at: string;
};

export type MarketChartPayload = {
  id: string;
  title: string;
  unit: string;
  frequency: string;
  status: string;
  chart_type?: string;
  range: {
    type: string;
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
    points: MarketChartPoint[];
  }>;
  housing_cities?: string[];
};

export const MARKET_DATA_TABS: readonly ModuleTabDefinition<MarketDataTab>[] = [
  { value: "commodities", label: "商品", description: "WTI原油、布伦特原油" },
  { value: "precious_metals", label: "贵金属", description: "黄金、白银、铜" },
  { value: "stock_market", label: "股票市场", description: "股指数据（待补充）" },
  { value: "real_estate", label: "房地产", description: "70城二手房价格指数" },
];

import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MarketDataTab = "commodities" | "precious_metals" | "stock_market" | "real_estate";

export type MarketDataRange = "1m" | "3m" | "6m" | "1y" | "3y" | "5y" | "10y" | "15y" | "20y" | "25y" | "30y" | "custom";

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
    metric?: "yoy" | "mom" | "global_index" | string;
    points: MarketChartPoint[];
  }>;
  housing_cities?: string[];
};

export type StockInstrument = {
  symbol: string;
  code: string;
  exchange: string;
  name: string;
  instrument_type: "stock" | "etf" | "lof";
  market_board: string;
  listing_status: string;
  updated_at: string;
  latest_price?: number | null;
};

export type StockInstrumentListPayload = {
  generated_at: string;
  items: StockInstrument[];
  total: number;
  limit: number;
  offset: number;
  universe_count: number;
  warning_message: string;
};

export type StockMarketAllRefreshJob = {
  id: string;
  status: "pending" | "running" | "canceling" | "completed" | "completed_with_warnings" | "failed" | "skipped" | "canceled";
  trigger: "manual" | "scheduled" | string;
  refresh_mode: StockMarketAllRefreshMode;
  completed: number;
  total: number;
  percentage: number;
  current_symbol: string;
  current_label: string;
  message: string;
  errors: string[];
  started_at: string;
  finished_at: string;
};

export type StockMarketAllRefreshMode = "history" | "today";

export type StockMarketAllRefreshPayload = {
  job: StockMarketAllRefreshJob | null;
  state?: {
    last_refresh_date?: string;
    last_refresh_at?: string;
    last_trigger?: string;
  };
};

export type StockMarketOverviewPayload = {
  generated_at: string;
  indices: Array<{
    symbol: "SSE" | "SZSE" | string;
    display_name: string;
    close: number | null;
    change: number | null;
    change_pct: number | null;
    trade_date: string | null;
    status: string;
    daily_bars?: StockDailyBar[];
  }>;
  breadth: {
    trade_date: string | null;
    advanced: number;
    declined: number;
    unchanged: number;
    total: number;
    status: string;
  };
};

export type StockDailyBar = {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  ma5: number | null;
  ma10: number | null;
  ma20: number | null;
  ma60: number | null;
  ma120: number | null;
  pe_ttm: number | null;
  pb_mrq: number | null;
  dividend_yield_ttm: number | null;
  total_market_cap: number | null;
};

export type StockProfile = {
  company_name: string;
  industry: string;
  sector: string;
  region: string;
  listing_date: string;
  attributes: string[];
  summary: string;
  updated_at: string;
};

export type StockFinancialSeries = {
  metric: string;
  label: string;
  points: Array<{
    period: string;
    value: number;
    unit: string;
  }>;
};

export type StockFinancialReportType = "quarterly" | "yearly";

export type StockDetailPayload = {
  generated_at: string;
  instrument: StockInstrument;
  range: {
    type: MarketDataRange;
    start_date: string;
    end_date: string;
  };
  daily_bars: StockDailyBar[];
  profile: StockProfile;
  financials: {
    report_type: StockFinancialReportType;
    unit: string;
    series: StockFinancialSeries[];
  };
  sync_state: {
    latest_trade_date: string | null;
    earliest_trade_date: string | null;
    daily_point_count: number;
    profile_status: string;
    financial_status: string;
    warning_message: string;
    synced_at: string;
  };
  refresh_result?: Record<string, number>;
};

export const MARKET_DATA_TABS: readonly ModuleTabDefinition<MarketDataTab>[] = [
  { value: "commodities", label: "商品", description: "WTI原油、布伦特原油" },
  { value: "precious_metals", label: "贵金属", description: "黄金、白银、铜" },
  { value: "stock_market", label: "股市", description: "A股、ETF日线与财报" },
  { value: "real_estate", label: "房地产", description: "70城二手房价格指数" },
];

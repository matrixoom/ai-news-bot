import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MarketModuleTab = "overview" | "signals" | "models" | "watchlist";

export const MARKET_MODULE_TABS: readonly ModuleTabDefinition<MarketModuleTab>[] = [
  { value: "overview", label: "Overview" },
  { value: "signals", label: "Signals" },
  { value: "models", label: "Models" },
  { value: "watchlist", label: "Watchlist" },
];

export type MarketChartPoint = {
  tradeDate: string;
  closePrice: number;
  ma20Price: number | null;
  deviationPct: number | null;
};

export type MarketSignalCard = {
  key: string;
  label: string;
  status: string;
  closeValue: string;
  ma20Value: string;
  signal: string;
  deviationLabel: string;
  tradeDate: string;
  sourceLabel: string;
  explanation: string;
  dataWindowLabel: string;
  historyWarning: string;
  chartPoints: MarketChartPoint[];
};

export type MarketWatchSummary = {
  label: string;
  value: string;
  detail: string;
};

export type MarketWatchItem = {
  key: string;
  label: string;
  signal: string;
  tradeDate: string;
  sourceLabel: string;
  status: string;
};

export type MarketModuleRawPayload = {
  generated_at: string;
  module: {
    id: "market";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      kind: "market";
      note: string;
      section: {
        key: string;
        label: string;
        status: string;
        close_value: string;
        ma20_value: string;
        signal: string;
        deviation_pct: number | string | null;
        trade_date: string;
        source_label: string;
        explanation: string;
        data_window_label: string;
        history_warning: string;
        chart_points: Array<{
          trade_date: string;
          close_price: number;
          ma20_price: number | null;
          deviation_pct: number | null;
        }>;
      };
    }>;
  };
};

export type MarketModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  signalCards: MarketSignalCard[];
  watchSummaries: MarketWatchSummary[];
  watchItems: MarketWatchItem[];
};

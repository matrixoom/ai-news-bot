import type { MarketModuleRawPayload, MarketModuleViewModel } from "./market-module.types";

export function adaptMarketModule(response: MarketModuleRawPayload): MarketModuleViewModel {
  const signalCards = response.module.details.map((detail) => {
    const section = detail.section;

    return {
      key: section.key,
      label: section.label,
      status: section.status,
      closeValue: section.close_value,
      ma20Value: section.ma20_value,
      signal: section.signal,
      deviationLabel: formatDeviation(section.deviation_pct),
      tradeDate: section.trade_date,
      sourceLabel: section.source_label,
      explanation: section.explanation,
      dataWindowLabel: section.data_window_label,
      historyWarning: section.history_warning,
      chartPoints: section.chart_points.map((point) => ({
        tradeDate: point.trade_date,
        closePrice: point.close_price,
        ma20Price: point.ma20_price,
        deviationPct: point.deviation_pct,
      })),
    };
  });

  const watchItems = signalCards.slice(0, 4).map((card) => ({
    key: card.key,
    label: card.label,
    signal: card.signal,
    tradeDate: card.tradeDate,
    sourceLabel: card.sourceLabel,
    status: card.status,
  }));

  const averageDeviation = signalCards.length
    ? signalCards.reduce((sum, card) => sum + parseDeviation(card.deviationLabel), 0) / signalCards.length
    : 0;

  return {
    generatedAt: response.generated_at,
    pageTitle: "Market",
    pageDescription: response.module.description,
    moduleLabel: response.module.label,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    signalCards,
    watchSummaries: [
      {
        label: "Tracked signals",
        value: `${signalCards.length} tracked signals`,
        detail: "Market models returned by /api/frontend/modules/market.",
      },
      {
        label: "Leading signal",
        value: signalCards[0]?.signal ?? "n/a",
        detail: signalCards[0]?.label ?? "No market models returned.",
      },
      {
        label: "Average deviation",
        value: formatDeviation(averageDeviation),
        detail: "Mean deviation across the returned cards.",
      },
      {
        label: "Module state",
        value: response.module.status,
        detail: response.module.loading ? "Backend is still loading this module." : response.module.note,
      },
    ],
    watchItems,
  };
}

function formatDeviation(value: number | string | null): string {
  if (typeof value === "string") {
    return value;
  }

  if (value === null) {
    return "n/a";
  }

  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function parseDeviation(value: string): number {
  const parsed = Number.parseFloat(value.replace("%", ""));
  return Number.isNaN(parsed) ? 0 : parsed;
}

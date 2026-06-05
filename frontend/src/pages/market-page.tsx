import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MarketChartCard } from "../features/market-data/components/market-chart-card";
import { RealEstateChartCard } from "../features/market-data/components/real-estate-chart-card";
import { StockMarketWorkspace } from "../features/market-data/components/stock-market-workspace";
import { useMarketDataModuleQuery } from "../features/market-data/hooks/use-market-data-module-query";
import {
  MARKET_DATA_TABS,
  type MarketDataFrequency,
  type MarketDataRangeSelection,
  type MarketDataTab,
} from "../features/market-data/model/market-data.types";
import { resolveModuleTab } from "../shared/lib/module-tabs";
import {
  MARKET_CHART_FREQUENCIES_KEY,
  MARKET_CHART_RANGES_KEY,
  readJSONPreference,
  writeJSONPreference,
} from "../shared/lib/workbench-preferences";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { EmptyPanelState, ErrorPanelState, LoadingPanelState } from "../shared/ui/panel-state";

export function MarketPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), MARKET_DATA_TABS, "commodities");
  const query = useMarketDataModuleQuery(activeTab);
  const [rangesByChartId, setRangesByChartId] = useState<Record<string, MarketDataRangeSelection>>(
    () => readJSONPreference(MARKET_CHART_RANGES_KEY, {} as Record<string, MarketDataRangeSelection>),
  );
  const [frequenciesByChartId, setFrequenciesByChartId] = useState<Record<string, MarketDataFrequency>>(
    () => readJSONPreference(MARKET_CHART_FREQUENCIES_KEY, {} as Record<string, MarketDataFrequency>),
  );

  useEffect(() => {
    writeJSONPreference(MARKET_CHART_RANGES_KEY, rangesByChartId);
  }, [rangesByChartId]);

  useEffect(() => {
    writeJSONPreference(MARKET_CHART_FREQUENCIES_KEY, frequenciesByChartId);
  }, [frequenciesByChartId]);

  useEffect(() => {
    if (searchParams.get("tab") === activeTab) {
      return;
    }
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("tab", activeTab);
    setSearchParams(nextSearchParams, { replace: true });
  }, [activeTab, searchParams, setSearchParams]);

  const defaultRange = query.data?.default_range ?? "1y";
  const rangeOptions = useMemo(
    () =>
      query.data?.range_options ?? [
        { value: "6m" as const, label: "半年" },
        { value: "1y" as const, label: "1年" },
        { value: "3y" as const, label: "3年" },
        { value: "5y" as const, label: "5年" },
        { value: "10y" as const, label: "10年" },
        { value: "custom" as const, label: "自定义" },
      ],
    [query.data?.range_options],
  );
  const defaultFrequency = query.data?.default_frequency ?? "daily";
  const frequencyOptions = useMemo(
    () => query.data?.frequency_options ?? [],
    [query.data?.frequency_options],
  );

  function chartRange(chartId: string): MarketDataRangeSelection {
    return rangesByChartId[chartId] ?? { type: defaultRange };
  }

  function chartFrequency(chartId: string, chartDefaultFrequency: string): MarketDataFrequency {
    return frequenciesByChartId[chartId] ?? (chartDefaultFrequency as MarketDataFrequency) ?? defaultFrequency;
  }

  function updateChartRange(chartId: string, nextRange: MarketDataRangeSelection) {
    setRangesByChartId((prev) => ({
      ...prev,
      [chartId]: nextRange,
    }));
  }

  function updateChartFrequency(chartId: string, nextFrequency: MarketDataFrequency) {
    setFrequenciesByChartId((prev) => ({
      ...prev,
      [chartId]: nextFrequency,
    }));
  }

  if (query.isPending) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="Commodities, precious metals, and stock indices."
        main={<LoadingPanelState title="Loading market data" description="Fetching chart definitions and data ranges." />}
        showHeader={false}
        title="Market Data"
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="Commodities, precious metals, and stock indices."
        main={<ErrorPanelState title="Market data unavailable" description="The market data payload could not be loaded." />}
        showHeader={false}
        title="Market Data"
      />
    );
  }

  const charts = query.data.charts;
  const mainContent =
    activeTab === "stock_market" ? (
      <StockMarketWorkspace />
    ) : charts.length === 0 ? (
      <EmptyPanelState title="No market charts" description="The selected category has no chart definitions yet." />
    ) : (
      <div className="flex flex-col items-stretch gap-6">
        {activeTab === "real_estate"
          ? charts.map((chart) => (
              <RealEstateChartCard
                key={chart.id}
                chart={chart}
                className="w-full"
                frequency={chartFrequency(chart.id, chart.frequency)}
                frequencyOptions={frequencyOptions}
                onFrequencyChange={(nextFrequency) => updateChartFrequency(chart.id, nextFrequency)}
                onRangeChange={(nextRange) => updateChartRange(chart.id, nextRange)}
                range={chartRange(chart.id)}
                rangeOptions={rangeOptions}
                housingCities={query.data.housing_cities ?? []}
              />
            ))
          : charts.map((chart) => (
              <MarketChartCard
                key={chart.id}
                chart={chart}
                className="w-full"
                frequency={chartFrequency(chart.id, chart.frequency)}
                frequencyOptions={frequencyOptions}
                onFrequencyChange={(nextFrequency) => updateChartFrequency(chart.id, nextFrequency)}
                onRangeChange={(nextRange) => updateChartRange(chart.id, nextRange)}
                range={chartRange(chart.id)}
                rangeOptions={rangeOptions}
              />
            ))}
      </div>
    );

  return (
    <ModulePageFrame
      contentLayoutClassName="grid gap-6"
      description={query.data.module.description}
      main={mainContent}
      showHeader={false}
      title="Market Data"
    />
  );
}

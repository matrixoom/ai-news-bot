import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { MarketChartCard } from "../features/market-data/components/market-chart-card";
import { useMarketDataModuleQuery } from "../features/market-data/hooks/use-market-data-module-query";
import {
  MARKET_DATA_TABS,
  type MarketDataFrequency,
  type MarketDataRangeSelection,
  type MarketDataTab,
} from "../features/market-data/model/market-data.types";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { EmptyPanelState, ErrorPanelState, LoadingPanelState } from "../shared/ui/panel-state";

export function MarketPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), MARKET_DATA_TABS, "commodities");
  const query = useMarketDataModuleQuery(activeTab);
  const [rangesByChartId, setRangesByChartId] = useState<Record<string, MarketDataRangeSelection>>({});
  const [frequenciesByChartId, setFrequenciesByChartId] = useState<Record<string, MarketDataFrequency>>({});

  useEffect(() => {
    if (searchParams.get("tab") === activeTab) {
      return;
    }
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("tab", activeTab);
    setSearchParams(nextSearchParams, { replace: true });
  }, [activeTab, searchParams, setSearchParams]);

  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Market Data category tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={MARKET_DATA_TABS}
    />
  );

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
        lastUpdated={null}
        main={<LoadingPanelState title="Loading market data" description="Fetching chart definitions and data ranges." />}
        title="Market Data"
        toolbar={toolbar}
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="Commodities, precious metals, and stock indices."
        lastUpdated={null}
        main={<ErrorPanelState title="Market data unavailable" description="The market data payload could not be loaded." />}
        title="Market Data"
        toolbar={toolbar}
      />
    );
  }

  const charts = query.data.charts;

  return (
    <ModulePageFrame
      contentLayoutClassName="grid gap-6"
      description={query.data.module.description}
      lastUpdated={<LastUpdatedBadge value={query.data.generated_at} />}
      main={
        charts.length === 0 ? (
          <EmptyPanelState title="No market charts" description="The selected category has no chart definitions yet." />
        ) : (
          <div className="grid gap-6 xl:grid-cols-2">
            {charts.map((chart) => (
              <MarketChartCard
                key={chart.id}
                chart={chart}
                frequency={chartFrequency(chart.id, chart.frequency)}
                frequencyOptions={frequencyOptions}
                onFrequencyChange={(nextFrequency) => updateChartFrequency(chart.id, nextFrequency)}
                onRangeChange={(nextRange) => updateChartRange(chart.id, nextRange)}
                range={chartRange(chart.id)}
                rangeOptions={rangeOptions}
              />
            ))}
          </div>
        )
      }
      title="Market Data"
      toolbar={toolbar}
    />
  );
}

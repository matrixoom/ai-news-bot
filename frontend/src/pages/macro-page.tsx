import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { MacroChartCard } from "../features/macro-data/components/macro-chart-card";
import { useMacroDataModuleQuery } from "../features/macro-data/hooks/use-macro-data-module-query";
import {
  MACRO_DATA_TABS,
  type MacroDataFrequency,
  type MacroDataRangeSelection,
  type MacroDataTab,
} from "../features/macro-data/model/macro-data.types";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { EmptyPanelState, ErrorPanelState, LoadingPanelState } from "../shared/ui/panel-state";

export function MacroPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), MACRO_DATA_TABS, "gdp");
  const query = useMacroDataModuleQuery(activeTab);
  const [rangesByChartId, setRangesByChartId] = useState<Record<string, MacroDataRangeSelection>>({});
  const [frequenciesByChartId, setFrequenciesByChartId] = useState<Record<string, MacroDataFrequency>>({});

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
      ariaLabel="Macro Data category tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={MACRO_DATA_TABS}
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
        { value: "15y" as const, label: "15年" },
        { value: "20y" as const, label: "20年" },
        { value: "25y" as const, label: "25年" },
        { value: "30y" as const, label: "30年" },
        { value: "custom" as const, label: "自定义" },
      ],
    [query.data?.range_options],
  );
  const defaultFrequency = query.data?.default_frequency ?? "monthly";
  const frequencyOptions = useMemo(
    () => query.data?.frequency_options ?? [],
    [query.data?.frequency_options],
  );

  function chartRange(chartId: string): MacroDataRangeSelection {
    return rangesByChartId[chartId] ?? { type: defaultRange };
  }

  function chartFrequency(chartId: string, chartDefaultFrequency: string): MacroDataFrequency {
    return frequenciesByChartId[chartId] ?? (chartDefaultFrequency as MacroDataFrequency) ?? defaultFrequency;
  }

  function updateChartRange(chartId: string, nextRange: MacroDataRangeSelection) {
    setRangesByChartId((prev) => ({
      ...prev,
      [chartId]: nextRange,
    }));
  }

  function updateChartFrequency(chartId: string, nextFrequency: MacroDataFrequency) {
    setFrequenciesByChartId((prev) => ({
      ...prev,
      [chartId]: nextFrequency,
    }));
  }

  if (query.isPending) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="GDP, credit, and inflation indicators."
        lastUpdated={null}
        main={<LoadingPanelState title="Loading macro data" description="Fetching chart definitions and data ranges." />}
        title="Macro Data"
        toolbar={toolbar}
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description="GDP, credit, and inflation indicators."
        lastUpdated={null}
        main={<ErrorPanelState title="Macro data unavailable" description="The macro data payload could not be loaded." />}
        title="Macro Data"
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
          <EmptyPanelState title="No macro charts" description="The selected category has no chart definitions yet." />
        ) : (
          <div className="grid gap-6 xl:grid-cols-2">
            {charts.map((chart) => (
              <MacroChartCard
                key={chart.id}
                chart={chart}
                className={chart.wide ? "xl:col-span-2" : undefined}
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
      title="Macro Data"
      toolbar={toolbar}
    />
  );
}

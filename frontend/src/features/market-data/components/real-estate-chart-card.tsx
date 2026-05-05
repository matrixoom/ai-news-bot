import * as echarts from "echarts";
import { ArrowsPointingOutIcon, ChevronDownIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRealEstateChartQuery } from "../hooks/use-real-estate-chart-query";
import { useMarketDataRefreshMutation } from "../hooks/use-market-data-refresh-mutation";
import type {
  MarketChartDefinition,
  MarketDataFrequency,
  MarketDataRangeSelection,
  MarketFrequencyOption,
  MarketRangeOption,
} from "../model/market-data.types";
import { RangeControl } from "../../../shared/ui/range-control";
import { ChartFullscreen } from "../../../shared/ui/chart-fullscreen";

type RealEstateChartCardProps = {
  chart: MarketChartDefinition;
  className?: string;
  frequency: MarketDataFrequency;
  frequencyOptions: MarketFrequencyOption[];
  range: MarketDataRangeSelection;
  rangeOptions: MarketRangeOption[];
  housingCities: string[];
  onFrequencyChange: (nextFrequency: MarketDataFrequency) => void;
  onRangeChange: (nextRange: MarketDataRangeSelection) => void;
};

const STORAGE_KEY = "real-estate-selected-cities";

function readSelectedCities(): string[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.every((v) => typeof v === "string")) {
      return parsed as string[];
    }
    return null;
  } catch {
    return null;
  }
}

function writeSelectedCities(cities: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cities));
  } catch {
    // storage full or disabled
  }
}

const COLORS = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
  "#ec4899", "#06b6d4", "#f97316", "#64748b", "#84cc16",
  "#14b8a6", "#e11d48", "#6366f1", "#a855f7", "#0ea5e9",
];

export function RealEstateChartCard({
  chart,
  className,
  frequency,
  frequencyOptions,
  range,
  rangeOptions,
  housingCities,
  onFrequencyChange,
  onRangeChange,
}: RealEstateChartCardProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const [selectedCities, setSelectedCities] = useState<string[]>(() => {
    const saved = readSelectedCities();
    if (saved && saved.length > 0) return saved;
    return housingCities.slice(0, 2);
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const query = useRealEstateChartQuery(chart.id, range, frequency, selectedCities);
  const refreshMutation = useMarketDataRefreshMutation(chart.id);
  const [refreshLabel, setRefreshLabel] = useState<string | null>(null);

  useEffect(() => {
    if (refreshMutation.isSuccess) {
      setRefreshLabel("已刷新");
      const timer = setTimeout(() => setRefreshLabel(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [refreshMutation.isSuccess]);

  const series = query.data?.series ?? [];

  const chartLabels = useMemo(() => {
    const allLabels = new Set<string>();
    for (const s of series) {
      for (const p of s.points) {
        allLabels.add(p.period_label || p.date);
      }
    }
    return Array.from(allLabels).sort();
  }, [series]);

  const chartSeries = useMemo(
    () =>
      series.map((s, index) => ({
        name: s.name,
        type: "line" as const,
        smooth: true,
        symbol: "circle",
        data: chartLabels.map((label) => {
          const point = s.points.find(
            (p) => (p.period_label || p.date) === label,
          );
          return point ? point.value : null;
        }),
        lineStyle: { width: 2 },
        itemStyle: { color: COLORS[index % COLORS.length] },
      })),
    [series, chartLabels],
  );

  const chartOption = useMemo((): echarts.EChartsOption | null => {
    if (chartLabels.length === 0) return null;
    return {
      animation: false,
      tooltip: { trigger: "axis" },
      legend: {
        orient: "vertical",
        right: 0,
        top: "middle",
        textStyle: { fontSize: 11 },
        data: chartSeries.map((s) => s.name),
      },
      grid: { left: 48, right: 140, top: 24, bottom: 52 },
      xAxis: { type: "category", data: chartLabels },
      yAxis: {
        type: "value",
        name: query.data?.unit ?? "%",
      },
      toolbox: {
        feature: {
          dataZoom: { title: { zoom: "框选放大", back: "还原" } },
        },
        right: 10,
        top: 0,
        itemSize: 14,
        iconStyle: { borderColor: "#64748b" },
      },
      dataZoom: [
        {
          type: "slider",
          show: false,
          start: 0,
          end: 100,
          height: 14,
          bottom: 6,
          handleSize: 12,
          borderColor: "#e2e8f0",
          backgroundColor: "#f8fafc",
          fillerColor: "rgba(148,163,184,0.15)",
          handleStyle: { color: "#94a3b8" },
          textStyle: { color: "#94a3b8", fontSize: 10 },
        },
        { type: "inside", start: 0, end: 100 },
      ],
      series: chartSeries,
    };
  }, [chartLabels, chartSeries, query.data?.unit]);

  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.userAgent.toLowerCase().includes("jsdom")) {
      return;
    }
    if (!chartRef.current || !chartOption) {
      return;
    }
    const container = chartRef.current;
    const instance = echarts.init(container, undefined, { renderer: "svg" });
    instance.setOption(chartOption);

    const handleDataZoom = () => {
      const opt = instance.getOption() as { dataZoom?: Array<{ start?: number; end?: number; show?: boolean }> };
      const slider = opt.dataZoom?.[0];
      if (slider && slider.start !== undefined && slider.end !== undefined) {
        const zoomed = slider.start > 0 || slider.end < 100;
        if (zoomed !== slider.show) {
          instance.setOption({ dataZoom: [{ show: zoomed }] }, { replaceMerge: ["dataZoom"] });
        }
      }
    };
    instance.on("datazoom", handleDataZoom);

    return () => {
      instance.off("datazoom", handleDataZoom);
      instance.dispose();
    };
  }, [chartOption]);

  function toggleCity(city: string) {
    setSelectedCities((prev) => {
      const next = prev.includes(city)
        ? prev.filter((c) => c !== city)
        : [...prev, city];
      writeSelectedCities(next);
      return next;
    });
  }

  function removeCity(city: string) {
    setSelectedCities((prev) => {
      const next = prev.filter((c) => c !== city);
      writeSelectedCities(next);
      return next;
    });
  }

  const filteredCities = searchText
    ? housingCities.filter((c) => c.toLowerCase().includes(searchText.toLowerCase()))
    : housingCities;

  return (
    <section className={`relative rounded-xl border border-slate-200 bg-white p-5 shadow-sm${className ? ` ${className}` : ""}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">{chart.title}</h3>
          <p className="mt-1 text-sm text-slate-500">
            单位：{chart.unit} · 频率：{chart.frequency} ({housingCities.length} 个城市可选)
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          {rangeOptions.find((option) => option.value === range.type)?.label ?? "1年"}
        </span>
      </div>

      {/* 城市选择器 */}
      <div className="mt-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-500">已选城市：</span>
          {selectedCities.length === 0 ? (
            <span className="text-xs text-slate-400">请选择至少一个城市</span>
          ) : (
            selectedCities.map((city) => (
              <span
                key={city}
                className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700"
              >
                {city}
                <button
                  type="button"
                  className="ml-0.5 rounded-full hover:bg-blue-200"
                  onClick={() => removeCity(city)}
                  aria-label={`移除 ${city}`}
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>

        <div className="relative">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            {selectedCities.length === 0 ? "选择城市" : `${selectedCities.length} 个城市已选`}
            <ChevronDownIcon className="h-4 w-4 text-slate-400" />
          </button>

          {dropdownOpen && (
            <div className="absolute left-0 z-30 mt-1 max-h-64 w-60 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
              <div className="sticky top-0 border-b border-slate-100 bg-white p-2">
                <input
                  type="text"
                  className="w-full rounded border border-slate-200 px-2 py-1 text-sm outline-none focus:border-blue-400"
                  placeholder="搜索城市..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                />
              </div>
              <div className="p-1">
                {filteredCities.map((city) => (
                  <label
                    key={city}
                    className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-50"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-blue-600"
                      checked={selectedCities.includes(city)}
                      onChange={() => toggleCity(city)}
                    />
                    {city}
                  </label>
                ))}
              </div>
              <div className="border-t border-slate-100 p-2 flex gap-2">
                <button
                  type="button"
                  className="flex-1 rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
                  onClick={() => {
                    setSelectedCities([]);
                    writeSelectedCities([]);
                  }}
                >
                  清空
                </button>
                <button
                  type="button"
                  className="flex-1 rounded bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-200"
                  onClick={() => setDropdownOpen(false)}
                >
                  确定
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4">
        <RangeControl
          options={rangeOptions}
          value={range}
          onChange={(nextRange) => onRangeChange(nextRange as MarketDataRangeSelection)}
          frequencyOptions={frequencyOptions}
          frequency={frequency}
          onFrequencyChange={(next) => onFrequencyChange(next as MarketDataFrequency)}
        />
      </div>

      {query.isPending ? (
        <div className="mt-5 rounded-lg border border-dashed border-slate-200 p-8 text-sm text-slate-500">图表加载中...</div>
      ) : query.isError ? (
        <div className="mt-5 rounded-lg border border-rose-200 bg-rose-50 p-8 text-sm text-rose-700">图表数据加载失败。</div>
      ) : chartLabels.length === 0 ? (
        <div className="mt-5 rounded-lg border border-dashed border-slate-200 p-8 text-sm text-slate-500">请选择至少一个城市以查看数据。</div>
      ) : (
        <div className="mt-5">
          <div ref={chartRef} aria-label={`${chart.title} 图表`} role="img" className="h-72 w-full" />
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            <span>城市数：{selectedCities.length}</span>
            <span>状态：{query.data?.sync_state.status ?? chart.status}</span>
            {query.data?.sync_state.warning_message ? <span>{query.data.sync_state.warning_message}</span> : null}
          </div>
        </div>
      )}

      <div className="absolute bottom-3 right-3 flex gap-1">
        <button
          type="button"
          className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
          disabled={!chartOption}
          onClick={() => setIsFullscreen(true)}
          aria-label="全屏查看图表"
        >
          <ArrowsPointingOutIcon aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
          disabled={refreshMutation.isPending}
          onClick={() => refreshMutation.mutate()}
        >
          {refreshMutation.isPending ? "刷新中..." : refreshLabel ?? "刷新"}
        </button>
      </div>

      <ChartFullscreen
        open={isFullscreen}
        onClose={() => setIsFullscreen(false)}
        title={chart.title}
        option={chartOption}
      />
    </section>
  );
}

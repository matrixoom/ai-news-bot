import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MacroChartCard } from "../components/macro-chart-card";

const mocks = vi.hoisted(() => ({
  setOption: vi.fn(),
  dispose: vi.fn(),
}));

vi.mock("echarts", () => ({
  init: vi.fn(() => ({
    setOption: mocks.setOption,
    dispose: mocks.dispose,
  })),
}));

vi.mock("../hooks/use-macro-data-chart-query", () => ({
  useMacroDataChartQuery: () => ({
    isPending: false,
    isError: false,
    data: {
      id: "new_rmb_loans",
      title: "新增人民币贷款",
      unit: "亿元",
      frequency: "monthly",
      status: "live",
      chart_type: "bar_stacked_line",
      wide: true,
      sync_state: { status: "live", synced_at: "", warning_message: "", point_count: 10 },
      series: [
        {
          name: "新增人民币贷款总计",
          points: [{ date: "2026-01-31", period_label: "2026-01", value: 50000, unit: "亿元", released_at: "" }],
        },
        {
          name: "居民新增短期贷款",
          points: [{ date: "2026-01-31", period_label: "2026-01", value: 3000, unit: "亿元", released_at: "" }],
        },
        {
          name: "居民新增长期贷款",
          points: [{ date: "2026-01-31", period_label: "2026-01", value: 7000, unit: "亿元", released_at: "" }],
        },
        {
          name: "企业新增短期贷款",
          points: [{ date: "2026-01-31", period_label: "2026-01", value: 10000, unit: "亿元", released_at: "" }],
        },
        {
          name: "企业新增长期贷款",
          points: [{ date: "2026-01-31", period_label: "2026-01", value: 30000, unit: "亿元", released_at: "" }],
        },
      ],
    },
  }),
}));

vi.mock("../hooks/use-macro-data-refresh-mutation", () => ({
  useMacroDataRefreshMutation: () => ({
    isPending: false,
    isSuccess: false,
    mutate: vi.fn(),
  }),
}));

describe("MacroChartCard", () => {
  it("pairs every new RMB loan component bar with a same-name line series", async () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Chrome",
      configurable: true,
    });

    render(
      <MacroChartCard
        chart={{
          id: "new_rmb_loans",
          title: "新增人民币贷款",
          unit: "亿元",
          frequency: "monthly",
          status: "live",
          chart_type: "bar_stacked_line",
        }}
        frequency="monthly"
        frequencyOptions={[{ value: "monthly", label: "月度" }]}
        onFrequencyChange={vi.fn()}
        onRangeChange={vi.fn()}
        range={{ type: "1y" }}
        rangeOptions={[{ value: "1y", label: "1年" }]}
      />,
    );

    await waitFor(() => expect(mocks.setOption).toHaveBeenCalled());
    const option = mocks.setOption.mock.calls.at(-1)?.[0] as { series: Array<{ name: string; type: string }> };
    const nameCounts = option.series.reduce<Record<string, number>>((acc, series) => {
      acc[series.name] = (acc[series.name] ?? 0) + 1;
      return acc;
    }, {});

    expect(option.series).toHaveLength(9);
    expect(nameCounts["新增人民币贷款总计"]).toBe(1);
    expect(nameCounts["居民新增短期贷款"]).toBe(2);
    expect(nameCounts["居民新增长期贷款"]).toBe(2);
    expect(nameCounts["企业新增短期贷款"]).toBe(2);
    expect(nameCounts["企业新增长期贷款"]).toBe(2);
  });
});

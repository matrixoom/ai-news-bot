import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RealEstateChartCard } from "../components/real-estate-chart-card";

const mocks = vi.hoisted(() => ({
  setOption: vi.fn(),
  dispose: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  getOption: vi.fn(() => ({ dataZoom: [{ start: 0, end: 100, show: false }] })),
  queryCities: vi.fn(),
}));

vi.mock("echarts", () => ({
  init: vi.fn(() => ({
    setOption: mocks.setOption,
    dispose: mocks.dispose,
    on: mocks.on,
    off: mocks.off,
    getOption: mocks.getOption,
  })),
}));

vi.mock("../hooks/use-real-estate-chart-query", () => ({
  useRealEstateChartQuery: (_chartId: string, _range: unknown, _frequency: unknown, cities: string[]) => {
    mocks.queryCities(cities);
    return {
      isPending: false,
      isError: false,
      data: {
        id: "second_hand_housing",
        title: "全国70城二手房价格指数",
        unit: "% / 指数",
        frequency: "monthly",
        status: "live",
        chart_type: "housing_multi_metric",
        sync_state: { status: "live", synced_at: "", warning_message: "", point_count: 12 },
        series: [
          {
            name: "北京 同比",
            metric: "yoy",
            points: [{ date: "2026-03-01", period_label: "2026-03", value: -8.3, unit: "%", released_at: "" }],
          },
          {
            name: "北京 环比",
            metric: "mom",
            points: [{ date: "2026-03-01", period_label: "2026-03", value: 0.6, unit: "%", released_at: "" }],
          },
          {
            name: "北京 全局走势",
            metric: "global_index",
            points: [{ date: "2026-03-01", period_label: "2026-03", value: 188.7, unit: "指数", released_at: "" }],
          },
          {
            name: "上海 同比",
            metric: "yoy",
            points: [{ date: "2026-03-01", period_label: "2026-03", value: -6.2, unit: "%", released_at: "" }],
          },
        ],
      },
    };
  },
}));

vi.mock("../hooks/use-market-data-refresh-mutation", () => ({
  useMarketDataRefreshMutation: () => ({
    isPending: false,
    isSuccess: false,
    mutate: vi.fn(),
  }),
}));

function renderCard() {
  Object.defineProperty(window.navigator, "userAgent", {
    value: "Chrome",
    configurable: true,
  });
  window.localStorage.setItem("real-estate-selected-cities", JSON.stringify(["北京"]));

  return render(
    <div>
      <button type="button">外部区域</button>
      <RealEstateChartCard
        chart={{
          id: "second_hand_housing",
          title: "全国70城二手房价格指数",
          unit: "% / 指数",
          frequency: "monthly",
          status: "live",
          chart_type: "housing_multi_metric",
        }}
        frequency="monthly"
        frequencyOptions={[{ value: "monthly", label: "月度" }]}
        housingCities={["北京", "上海", "广州"]}
        onFrequencyChange={vi.fn()}
        onRangeChange={vi.fn()}
        range={{ type: "1y" }}
        rangeOptions={[{ value: "1y", label: "1年" }]}
      />
    </div>,
  );
}

describe("RealEstateChartCard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mocks.setOption.mockClear();
    mocks.dispose.mockClear();
    mocks.on.mockClear();
    mocks.off.mockClear();
    mocks.getOption.mockClear();
    mocks.queryCities.mockClear();
  });

  it("applies city selection when clicking outside the dropdown", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /个城市已选/ }));
    await user.click(screen.getByLabelText("上海"));
    await user.click(screen.getByRole("button", { name: "外部区域" }));

    await waitFor(() => {
      expect(screen.queryByPlaceholderText("搜索城市...")).not.toBeInTheDocument();
      expect(mocks.queryCities).toHaveBeenLastCalledWith(["北京", "上海"]);
    });
  });

  it("renders icon-only confirm and cancel controls next to city search", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /个城市已选/ }));

    expect(screen.getByRole("button", { name: "确定城市选择" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消城市选择" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "确定" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "清空" })).not.toBeInTheDocument();
  });

  it("discards draft city selection from the cancel icon", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /个城市已选/ }));
    await user.click(screen.getByLabelText("上海"));
    await user.click(screen.getByRole("button", { name: "取消城市选择" }));

    await waitFor(() => {
      expect(screen.queryByPlaceholderText("搜索城市...")).not.toBeInTheDocument();
      expect(mocks.queryCities).toHaveBeenLastCalledWith(["北京"]);
    });
  });

  it("uses one color per city and differentiates metrics by line style", async () => {
    renderCard();

    await waitFor(() => expect(mocks.setOption).toHaveBeenCalled());
    const option = mocks.setOption.mock.calls.at(-1)?.[0] as {
      series: Array<{ name: string; itemStyle?: { color?: string }; lineStyle?: { type?: string } }>;
    };
    const beijingSeries = option.series.filter((series) => series.name.startsWith("北京 "));
    const beijingColors = new Set(beijingSeries.map((series) => series.itemStyle?.color));
    const beijingLineTypes = new Set(beijingSeries.map((series) => series.lineStyle?.type));
    const shanghai = option.series.find((series) => series.name === "上海 同比");

    expect(beijingColors.size).toBe(1);
    expect(shanghai?.itemStyle?.color).not.toBe(beijingSeries[0].itemStyle?.color);
    expect(beijingLineTypes).toEqual(new Set(["dashed", "dotted", "solid"]));
  });
});

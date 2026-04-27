import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MacroPage } from "../../../pages/macro-page";

const macroPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "macro",
    label: "Macro",
    note: "数据因子、数据源矩阵与数据模型",
    description: "以数据因子为核心的宏观数据工作台。",
    status: "candidate",
    loading: false,
    details: [],
  },
  data_factors: {
    status: "candidate",
    label: "数据因子",
    default_factor_code: "housing_price",
    groups: [
      { value: "housing", label: "房价数据" },
      { value: "growth", label: "经济增长" },
    ],
    factors: [
      {
        factor_code: "housing_price",
        factor_label: "房价数据",
        category: "housing",
        description: "全国、一线城市、新一线样本城市的新房和二手房价格变化。",
        default_unit: "%",
        frequency: "monthly",
        source_key: "nbs_70_city_price",
        storage_table: "macro_housing_price_history",
        calculation_method: "official_raw",
        display_order: 10,
        status: "candidate",
      },
      {
        factor_code: "household_demand_deposit_growth",
        factor_label: "居民活期存款增速",
        category: "deposit",
        description: "居民活期存款同比增速；公开连续序列需验证。",
        default_unit: "%",
        frequency: "mixed",
        source_key: "pbc_deposit_statistics_pending",
        storage_table: "macro_household_deposit_history",
        calculation_method: "official_raw",
        display_order: 80,
        status: "degraded",
      },
    ],
    series: [
      {
        factor_code: "housing_price",
        label: "房价数据",
        unit: "%",
        frequency: "monthly",
        status: "candidate",
        source_label: "国家统计局 70 城商品住宅销售价格指数",
        points: [],
      },
    ],
    table_rows: [
      {
        factor_code: "housing_price",
        factor_label: "房价数据",
        period_label: "暂无数据",
        dimension: "全国 / 新房同比",
        value: "暂无数据",
        unit: "%",
        source_label: "国家统计局 70 城商品住宅销售价格指数",
        status: "candidate",
        updated_at: "2026-04-26T00:00:00Z",
      },
    ],
    sources: [],
  },
  source_matrix: {
    status: "candidate",
    label: "数据源矩阵",
    summary: {
      factor_count: 2,
      source_count: 2,
      official_primary_count: 2,
      degraded_count: 1,
      unavailable_count: 0,
      last_verified_at: "2026-04-26T00:00:00Z",
    },
    rows: [
      {
        matrix_id: "housing_price:nbs_70_city_price:primary",
        factor_code: "housing_price",
        factor_label: "房价数据",
        source_key: "nbs_70_city_price",
        source_label: "国家统计局 70 城商品住宅销售价格指数",
        source_role: "primary",
        source_type: "official",
        availability_status: "candidate",
        reliability_level: "official",
        coverage_scope: "70 城新房、二手房环比、同比和定基指数。",
        coverage_start: "2011-01",
        coverage_end: "",
        frequency: "monthly",
        access_method: "official_page_parse",
        field_mapping_status: "partial",
        parser_status: "pending",
        license_note: "官方公开发布页面，需按页面口径引用。",
        priority_order: 1,
        warning_message: "官方源最可信，但需要稳定解析月度发布页面。",
        last_verified_at: "2026-04-26T00:00:00Z",
      },
      {
        matrix_id: "household_demand_deposit_growth:pbc_deposit_statistics_pending:primary",
        factor_code: "household_demand_deposit_growth",
        factor_label: "居民活期存款增速",
        source_key: "pbc_deposit_statistics_pending",
        source_label: "人民银行居民活期存款口径待确认",
        source_role: "primary",
        source_type: "official",
        availability_status: "degraded",
        reliability_level: "official",
        coverage_scope: "住户或个人活期存款同比增速。",
        coverage_start: "",
        coverage_end: "",
        frequency: "mixed",
        access_method: "official_page_parse",
        field_mapping_status: "blocked",
        parser_status: "pending",
        license_note: "待确认。",
        priority_order: 1,
        warning_message: "公开连续序列不稳定，需进一步确认。",
        last_verified_at: "2026-04-26T00:00:00Z",
      },
    ],
  },
  data_models: {
    status: "reserved",
    label: "数据模型",
    models: [],
  },
};

describe("MacroPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderMacroPage(initialEntry = "/macro") {
    const router = createMemoryRouter(
      [
        {
          path: "/macro",
          element: <MacroPage />,
        },
      ],
      {
        initialEntries: [initialEntry],
      },
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
  }

  it("renders the new Macro tabs and data factors by default", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro");

    expect(await screen.findByRole("heading", { name: "数据因子" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "数据因子" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "数据源矩阵" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "数据模型" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Overview" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Compare" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Indicators" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sources" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "房价数据" }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("国家统计局 70 城商品住宅销售价格指数").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the source matrix tab with degraded reasons", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=source_matrix");

    expect(await screen.findByRole("heading", { name: "数据源矩阵" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "数据源矩阵" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("人民银行居民活期存款口径待确认")).toBeInTheDocument();
    expect(screen.getByText("公开连续序列不稳定，需进一步确认。")).toBeInTheDocument();
  });

  it("falls back to data factors when the tab query is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=nope");

    expect(await screen.findByRole("heading", { name: "数据因子" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "数据因子" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the loading state inside the shared module frame", () => {
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => new Promise(() => {}));

    renderMacroPage("/macro?tab=data_factors");

    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByText("Loading Macro data")).toBeInTheDocument();
    expect(screen.getByText("Macro side panel loading")).toBeInTheDocument();
  });

  it("renders the error state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    renderMacroPage("/macro?tab=data_factors");

    expect(await screen.findByText("Macro module unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the data model reserved tab", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=data_models");

    expect(await screen.findByRole("heading", { name: "数据模型" })).toBeInTheDocument();
    expect(screen.getByText("模型入口已预留，第一阶段不输出预测、方向判断或置信度。")).toBeInTheDocument();
  });
});

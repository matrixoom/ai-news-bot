import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MacroPage } from "../../../pages/macro-page";

const macroPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  macro_sections: [
    {
      key: "inflation-growth",
      title: "Inflation vs growth",
      status: "live",
      description: "A calm comparison of price pressure and activity.",
      summary: "CPI: 0.3% | GDP: 2.4%",
      primary: {
        key: "cpi",
        label: "CPI",
        status: "live",
        latest_value: "0.3%",
        previous_value: "0.2%",
        change_label: "+0.1 pts",
        trend: "up",
        frequency: "monthly",
        source_label: "National Bureau of Statistics",
        source_url: "https://example.com/cpi",
        updated_at: "2026-03-30T08:30:00Z",
        period_label: "Feb 2026",
        context: "Price growth stayed contained.",
        unit: "%",
        points: [],
      },
      secondary: {
        key: "gdp",
        label: "GDP",
        status: "live",
        latest_value: "2.4%",
        previous_value: "2.1%",
        change_label: "+0.3 pts",
        trend: "up",
        frequency: "quarterly",
        source_label: "BEA",
        source_url: "https://example.com/gdp",
        updated_at: "2026-03-30T08:00:00Z",
        period_label: "Q1 2026",
        context: "Real activity held firm.",
        unit: "%",
        points: [],
      },
      delta_label: "Gap",
      delta_points: [],
      sources: [{ label: "National Bureau of Statistics", url: "https://example.com/cpi" }],
    },
  ],
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

  it("renders macro overview without child tabs", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro");

    expect(await screen.findByRole("heading", { name: "Macro overview" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Inflation vs growth" })).toBeInTheDocument();
    expect(screen.getByText("CPI: 0.3% | GDP: 2.4%")).toBeInTheDocument();
    expect(screen.getByText("National Bureau of Statistics")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "数据因子" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "数据源矩阵" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "数据模型" })).not.toBeInTheDocument();
  });

  it("ignores removed tab queries and keeps the single overview", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(macroPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro?tab=source_matrix");

    expect(await screen.findByRole("heading", { name: "Macro overview" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "数据源矩阵" })).not.toBeInTheDocument();
  });

  it("renders the loading state inside the shared module frame", () => {
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => new Promise(() => {}));

    renderMacroPage("/macro");

    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByText("Loading Macro data")).toBeInTheDocument();
    expect(screen.getByText("Macro side panel loading")).toBeInTheDocument();
  });

  it("renders the error state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    renderMacroPage("/macro");

    expect(await screen.findByText("Macro module unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the empty state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ ...macroPayload, macro_sections: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderMacroPage("/macro");

    expect(await screen.findByText("No macro indicators yet")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Macro" })).toBeInTheDocument();
  });
});

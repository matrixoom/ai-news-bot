import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock } from "../../../app/__tests__/workbench-api-mocks";

describe("MacroDataPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderMacroApp(initialEntry = "/macro-data?tab=gdp") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  it("renders category subtabs, GDP charts, and preset range controls", async () => {
    installWorkbenchFetchMock();

    renderMacroApp();

    expect((await screen.findAllByRole("heading", { name: "Macro Data" })).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "GDP" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "信贷" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "杠杆率" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "物价" })).toBeInTheDocument();
    expect(await screen.findByText("名义GDP")).toBeInTheDocument();
    expect(await screen.findByText("实际GDP")).toBeInTheDocument();
    expect(await screen.findByText("GDP增速")).toBeInTheDocument();
    expect(await screen.findByText(/名义GDP增速 \/ 实际GDP增速/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "半年" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "一年" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "三年" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "5年" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "10年" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "自定义" }).length).toBeGreaterThan(0);
  });

  it("normalizes unknown tabs to GDP", async () => {
    installWorkbenchFetchMock();

    renderMacroApp("/macro-data?tab=unknown");

    await waitFor(() => {
      expect(window.location.search).toContain("tab=gdp");
    });
    expect(await screen.findByRole("link", { name: "GDP" })).toHaveAttribute("aria-current", "page");
  });

  it("lets a chart switch to a custom date range", async () => {
    const fetchMock = installWorkbenchFetchMock();
    const user = userEvent.setup();

    renderMacroApp();

    const customButtons = await screen.findAllByRole("button", { name: "自定义" });
    await user.click(customButtons[0]);
    await user.type(screen.getByLabelText("起始日期"), "2025-01-01");
    await user.type(screen.getByLabelText("结束日期"), "2026-05-01");
    await user.click(screen.getByRole("button", { name: "应用自定义范围" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const value = String(input);
          return (
            value.includes("/api/frontend/modules/macro-data/charts/nominal_gdp") &&
            value.includes("range=custom") &&
            value.includes("start_date=2025-01-01") &&
            value.includes("end_date=2026-05-01")
          );
        }),
      ).toBe(true);
    });
  });
});

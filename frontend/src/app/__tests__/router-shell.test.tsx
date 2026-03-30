import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";
import {
  dashboardPayload,
  installWorkbenchFetchMock,
  macroPayload,
  marketPayload,
  newsPayload,
  statusPayload,
} from "./workbench-api-mocks";

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderApp(pathname: string) {
    window.history.pushState({}, "", pathname);
    render(<App />);
  }

  it("renders the /status route as a real page instead of the placeholder", async () => {
    installWorkbenchFetchMock();

    renderApp("/status");

    expect(await screen.findByRole("heading", { name: "Freshness snapshot" })).toBeInTheDocument();
    expect(screen.getByText("Coverage note")).toBeInTheDocument();
    expect(screen.queryByText("Module page coming in the next slice.")).not.toBeInTheDocument();
  });

  it("keeps the /news tab state in the URL", async () => {
    installWorkbenchFetchMock({ news: newsPayload, status: statusPayload, market: marketPayload });
    const user = userEvent.setup();

    renderApp("/news?tab=channels");

    expect(await screen.findByRole("link", { name: "Channels" })).toHaveAttribute("aria-current", "page");

    await user.click(screen.getByRole("link", { name: "Sources" }));

    expect(window.location.search).toContain("tab=sources");
    expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the Macro route as a real page", async () => {
    installWorkbenchFetchMock({ macro: macroPayload, status: statusPayload, market: marketPayload });

    renderApp("/macro?tab=compare");

    expect(await screen.findByRole("heading", { name: "Inflation vs growth" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the Market route as a real page", async () => {
    installWorkbenchFetchMock({ market: marketPayload, status: statusPayload });

    renderApp("/market?tab=signals");

    expect(await screen.findByRole("heading", { name: "CSI 300" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Signals" })).toHaveAttribute("aria-current", "page");
  });

  it("converges the root path to /dashboard", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });

    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
  });

  it("updates the news mode in the URL and refetches with the active mode", async () => {
    const fetchMock = installWorkbenchFetchMock({ news: newsPayload, status: statusPayload, market: marketPayload });
    const user = userEvent.setup();

    renderApp("/news?tab=overview");

    expect(await screen.findByRole("button", { name: "Hybrid" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "API" }));

    await waitFor(() => {
      expect(window.location.search).toContain("news_mode=api");
      expect(screen.getByRole("button", { name: "API" })).toHaveAttribute("aria-pressed", "true");
      expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/news?news_mode=api"))).toBe(true);
    });
  });

  it("persists the theme preference and binds it to the document root", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });
    window.localStorage.setItem("dashboard-theme", "light");
    const user = userEvent.setup();

    renderApp("/dashboard");

    const toggle = await screen.findByRole("button", { name: /switch to dark theme/i });
    await user.click(toggle);

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-theme")).toBe("dark");
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
      expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeInTheDocument();
    });
  });

  it("renders the freshness badge and compact market ticker from shell data", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });

    renderApp("/dashboard");

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    await screen.findByText("CSI 300");
    const ticker = screen.getByRole("region", { name: "Market ticker" });
    expect(within(ticker).getByText("CSI 300")).toBeInTheDocument();
    expect(within(ticker).getByText("neutral")).toBeInTheDocument();
    expect(screen.getByText("Freshness")).toBeInTheDocument();
    expect(screen.getByText(/Mar 30, 9:00 AM UTC/, { selector: "time" })).toBeInTheDocument();
  });
});

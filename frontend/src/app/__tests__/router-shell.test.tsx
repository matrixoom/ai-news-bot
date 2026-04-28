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
  pushPayload,
  statusPayload,
} from "./workbench-api-mocks";

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderApp(pathname: string) {
    window.history.pushState({}, "", pathname);
    return render(<App />);
  }

  it("renders the /status route as a real page instead of the placeholder", async () => {
    installWorkbenchFetchMock();

    renderApp("/status");

    expect(await screen.findByRole("heading", { name: "Freshness snapshot" })).toBeInTheDocument();
    expect(screen.getByText("Coverage note")).toBeInTheDocument();
    expect(screen.queryByText("Module page coming in the next slice.")).not.toBeInTheDocument();
  });

  it("renders the /push route as a real page instead of the placeholder", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload, market: marketPayload });

    renderApp("/push");

    expect(await screen.findByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();
    expect(screen.queryByText("Module page coming in the next slice.")).not.toBeInTheDocument();
  });

  it("renders the /settings route as a real page instead of the placeholder", async () => {
    installWorkbenchFetchMock({ status: statusPayload, market: marketPayload });

    renderApp("/settings");

    expect(await screen.findByRole("heading", { name: "Workspace preferences" })).toBeInTheDocument();
    expect(screen.queryByText("Module page coming in the next slice.")).not.toBeInTheDocument();
  });

  it("renders the /news route without child tabs", async () => {
    installWorkbenchFetchMock({ news: newsPayload, status: statusPayload, market: marketPayload });

    renderApp("/news");

    expect(await screen.findByRole("heading", { name: "Channel summaries" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Topics" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sources" })).not.toBeInTheDocument();
  });

  it("renders the Macro route as a real page", async () => {
    installWorkbenchFetchMock({ macro: macroPayload, status: statusPayload, market: marketPayload });

    renderApp("/macro");

    expect(await screen.findByRole("heading", { name: "数据因子" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "数据因子" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the Market route as a real page", async () => {
    installWorkbenchFetchMock({ market: marketPayload, status: statusPayload });

    renderApp("/market");

    expect(await screen.findByRole("heading", { name: "CSI 300" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Signals" })).not.toBeInTheDocument();
  });

  it("converges the root path to /dashboard", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });

    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
  });

  it("honors the stored default route before syncing a non-hybrid news mode into the URL", async () => {
    installWorkbenchFetchMock({ market: marketPayload, status: statusPayload });
    window.localStorage.setItem("dashboard-default-route", "/market");
    window.localStorage.setItem("dashboard-default-news-mode", "api");

    renderApp("/");

    await waitFor(() => {
      expect(window.location.pathname).toBe("/market");
      expect(window.location.search).toContain("news_mode=api");
    });
    expect((await screen.findAllByText("CSI 300")).length).toBeGreaterThan(0);
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
      expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/dashboard?news_mode=api"))).toBe(true);
    });
  });

  it("keeps the active news mode when navigating to another shell route", async () => {
    const fetchMock = installWorkbenchFetchMock({ news: newsPayload, status: statusPayload, market: marketPayload });
    const user = userEvent.setup();

    renderApp("/news?tab=overview");

    expect(await screen.findByRole("button", { name: "Hybrid" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "API" }));

    await waitFor(() => {
      expect(window.location.search).toContain("news_mode=api");
    });

    await user.click(screen.getByRole("link", { name: "Status" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/status");
      expect(window.location.search).toContain("news_mode=api");
      expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/status?news_mode=api"))).toBe(true);
    });
  });

  it("persists the theme preference and binds it to the document root", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });
    window.localStorage.setItem("dashboard-theme", "light");
    const user = userEvent.setup();

    renderApp("/dashboard");

    const darkButton = await screen.findByRole("button", { name: /switch to dark theme/i });
    expect(darkButton).toHaveAttribute("aria-pressed", "false");
    await user.click(darkButton);

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-theme")).toBe("dark");
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
      expect(screen.getByRole("button", { name: /switch to dark theme/i })).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByRole("button", { name: /switch to light theme/i })).toHaveAttribute("aria-pressed", "false");
    });
  });

  it("renders the compact market ticker from shell data", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });

    renderApp("/dashboard");

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    await screen.findByText("CSI 300");
    const ticker = screen.getByRole("region", { name: "Market ticker" });
    expect(within(ticker).getByText("CSI 300")).toBeInTheDocument();
    expect(within(ticker).getByText("neutral")).toBeInTheDocument();
    expect(screen.queryByText("Freshness")).not.toBeInTheDocument();
    expect(within(ticker).queryByText("2026-03-29")).not.toBeInTheDocument();
  });

  it("keeps the shell header compact and preserves horizontal scrolling for market data", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });

    renderApp("/dashboard");

    await screen.findByRole("heading", { name: "Dashboard" });
    await screen.findByText("CSI 300");
    const headerRow = screen.getByTestId("shell-header-row");
    const titleBlock = screen.getByTestId("shell-header-title");
    const themeBlock = screen.getByTestId("shell-header-theme");
    const ticker = screen.getByRole("region", { name: "Market ticker" });

    expect(headerRow.className).toContain("flex");
    expect(headerRow.className).not.toContain("grid-cols");
    expect(titleBlock.className).toContain("shrink-0");
    expect(themeBlock.className).toContain("shrink-0");
    expect(ticker.className).toContain("overflow-x-auto");
    expect(ticker.className).toContain("market-ticker-scroll");
    expect(ticker.firstElementChild?.className).toContain("min-w-max");
    expect(screen.queryByText(/^Theme$/)).not.toBeInTheDocument();
  });

  it("renders module directories collapsed by default on first load", async () => {
    installWorkbenchFetchMock({ market: marketPayload, status: statusPayload });

    renderApp("/market");

    expect(await screen.findByRole("link", { name: "Market" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "News" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /expand market directory/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /expand news directory/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Market > Signals" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "News > Topics" })).not.toBeInTheDocument();
  });

  it("keeps macro directory expansion state after a refresh", async () => {
    installWorkbenchFetchMock({ market: marketPayload, status: statusPayload });
    const user = userEvent.setup();

    const firstRender = renderApp("/macro");

    await user.click(await screen.findByRole("button", { name: /expand macro directory/i }));
    expect(await screen.findByRole("link", { name: "Macro > Overview" })).toBeInTheDocument();

    firstRender.unmount();

    renderApp("/macro");

    expect(await screen.findByRole("button", { name: /collapse macro directory/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Macro > Overview" })).toBeInTheDocument();
  });

  it("collapses and expands the sidebar while persisting preference", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, status: statusPayload, market: marketPayload });
    const user = userEvent.setup();

    renderApp("/dashboard");

    await screen.findByRole("heading", { name: "Dashboard" });
    await user.click(screen.getByRole("button", { name: /collapse sidebar/i }));

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-sidebar-collapsed")).toBe("true");
      expect(screen.getByRole("button", { name: /expand sidebar/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /expand sidebar/i }));

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-sidebar-collapsed")).toBe("false");
      expect(screen.getByRole("button", { name: /collapse sidebar/i })).toBeInTheDocument();
    });
  });

  it("shows the news mode switch only inside the news module", async () => {
    installWorkbenchFetchMock({ dashboard: dashboardPayload, news: newsPayload, status: statusPayload, market: marketPayload });

    renderApp("/dashboard");

    await screen.findByRole("heading", { name: "Dashboard" });
    expect(screen.queryByRole("group", { name: "News mode" })).not.toBeInTheDocument();
  });

  it("allows collapsing and expanding a remaining grouped navigation card", async () => {
    installWorkbenchFetchMock({ news: newsPayload, status: statusPayload, market: marketPayload });
    const user = userEvent.setup();

    renderApp("/macro");

    expect(await screen.findByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /collapse workspace section/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Research Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("Loading workspace...")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /expand macro directory/i }));
    expect(await screen.findByRole("link", { name: "Macro > Overview" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /collapse macro directory/i }));
    expect(screen.queryByRole("link", { name: "Macro > Overview" })).not.toBeInTheDocument();
  });
});


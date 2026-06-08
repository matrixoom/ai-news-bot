import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";
import { installWorkbenchFetchMock, pushPayload } from "./workbench-api-mocks";

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderApp(pathname: string) {
    window.history.pushState({}, "", pathname);
    return render(<App />);
  }

  it("renders the remaining Macro Data, Outlook, Notes, AI Agent, Push Center, and Settings routes", async () => {
    installWorkbenchFetchMock({ push: pushPayload });

    renderApp("/macro-data");
    expect((await screen.findAllByRole("heading", { name: "Macro Data" })).length).toBeGreaterThan(0);

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/event-outlook");
    expect((await screen.findAllByRole("heading", { name: "Outlook" })).length).toBeGreaterThan(0);

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/notes");
    expect((await screen.findAllByRole("heading", { name: "Notes" })).length).toBeGreaterThan(0);

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/push");
    expect(await screen.findByTitle("Push preview")).toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/ai-agent");
    expect(await screen.findByRole("heading", { name: "Route ready" })).toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/settings");
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workspace preferences" })).not.toBeInTheDocument();
  });

  it("converges the root path to /push", async () => {
    installWorkbenchFetchMock({ push: pushPayload });

    renderApp("/");

    await waitFor(() => {
      expect(window.location.pathname).toBe("/push");
    });
    expect(await screen.findByTitle("Push preview")).toBeInTheDocument();
  });

  it("ignores removed default routes and falls back to /push", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    window.localStorage.setItem("dashboard-default-route", "/status");

    renderApp("/");

    await waitFor(() => {
      expect(window.location.pathname).toBe("/push");
    });
  });

  it("shows Macro Data and removes Dashboard, News, Market, Events, and market ticker from the shell", async () => {
    installWorkbenchFetchMock({ push: pushPayload });

    renderApp("/push");

    expect(await screen.findByRole("link", { name: "Push Center" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Macro Data" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Macro Data > GDP" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Macro Data > 就业" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "News" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Market" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Outlook" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Outlook > 国内" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Outlook > 国际" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Outlook > 事件列表" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Outlook > 主题溯源" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Outlook > 关系网络" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Notes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "AI Agent" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Status" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Market ticker" })).not.toBeInTheDocument();
  });

  it("keeps push directory expansion state after a refresh", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    const user = userEvent.setup();

    const firstRender = renderApp("/push");

    await user.click(await screen.findByRole("button", { name: /expand push center directory/i }));
    expect(await screen.findByRole("link", { name: "Push Center > Schedules" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Push Center > History" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Push Center > Overview" })).not.toBeInTheDocument();

    firstRender.unmount();

    renderApp("/push");

    expect(await screen.findByRole("button", { name: /collapse push center directory/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Push Center > Schedules" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Push Center > Overview" })).not.toBeInTheDocument();
  });

  it("persists the theme and sidebar preferences", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    const user = userEvent.setup();

    renderApp("/push");

    const darkButton = await screen.findByRole("button", { name: /switch to dark theme/i });
    await user.click(darkButton);
    await user.click(screen.getByRole("button", { name: /collapse sidebar/i }));

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-theme")).toBe("dark");
      expect(window.localStorage.getItem("dashboard-sidebar-collapsed")).toBe("true");
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });
  });

  it("uses icon-only navigation without text initials when the sidebar is collapsed", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    const user = userEvent.setup();

    renderApp("/push");

    await user.click(await screen.findByRole("button", { name: /collapse sidebar/i }));

    const primaryNavigation = screen.getByRole("navigation", { name: "Primary" });
    const links = within(primaryNavigation).getAllByRole("link");

    expect(links).toHaveLength(8);
    expect(within(primaryNavigation).getByRole("link", { name: "Macro Data" })).toBeInTheDocument();
    expect(within(primaryNavigation).getByRole("link", { name: "Outlook" })).toBeInTheDocument();
    expect(within(primaryNavigation).getByRole("link", { name: "Notes" })).toBeInTheDocument();
    expect(within(primaryNavigation).getByRole("link", { name: "Push Center" })).toBeInTheDocument();
    expect(within(primaryNavigation).getByRole("link", { name: "Market Data" })).toBeInTheDocument();
    expect(within(primaryNavigation).getByRole("link", { name: "AI Agent" })).toBeInTheDocument();
    expect(within(primaryNavigation).getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(within(primaryNavigation).queryByText("TI")).not.toBeInTheDocument();
    expect(within(primaryNavigation).queryByText("PC")).not.toBeInTheDocument();
    expect(within(primaryNavigation).queryByText("SE")).not.toBeInTheDocument();
  });

  it("uses distinct collapsed icons for Market Data, Trend Models, and Push Center", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    const user = userEvent.setup();

    renderApp("/push");

    await user.click(await screen.findByRole("button", { name: /collapse sidebar/i }));

    const primaryNavigation = screen.getByRole("navigation", { name: "Primary" });
    const marketIcon = within(primaryNavigation).getByRole("link", { name: "Market Data" }).querySelector("svg");
    const trendIcon = within(primaryNavigation).getByRole("link", { name: "Trend Models" }).querySelector("svg");
    const pushIcon = within(primaryNavigation).getByRole("link", { name: "Push Center" }).querySelector("svg");

    expect(marketIcon?.innerHTML).toBeTruthy();
    expect(trendIcon?.innerHTML).toBeTruthy();
    expect(pushIcon?.innerHTML).toBeTruthy();
    expect(new Set([marketIcon?.innerHTML, trendIcon?.innerHTML, pushIcon?.innerHTML]).size).toBe(3);
  });

  it("does not render first-level module description copy in the shell chrome", async () => {
    installWorkbenchFetchMock({ push: pushPayload });

    renderApp("/market-data");

    expect((await screen.findAllByRole("heading", { name: "Market Data" })).length).toBeGreaterThan(0);
    expect(screen.queryAllByText("Commodities, precious metals, and stock indices")).toHaveLength(0);
  });

  it("does not render redundant module workspace labels in data and push tabs", async () => {
    installWorkbenchFetchMock({ push: pushPayload });

    renderApp("/macro-data?tab=credit");
    expect((await screen.findAllByRole("heading", { name: "Macro Data" })).length).toBeGreaterThan(0);
    expect(await screen.findByText("新增人民币贷款")).toBeInTheDocument();
    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByText("Updated")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "信贷" })).not.toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/market-data?tab=real_estate");
    expect((await screen.findAllByRole("heading", { name: "Market Data" })).length).toBeGreaterThan(0);
    expect(window.location.search).toContain("tab=real_estate");
    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByText("Updated")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "房地产" })).not.toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload });
    renderApp("/push?tab=history");
    expect(await screen.findByText("Market Daily")).toBeInTheDocument();
    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByText("Updated")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "History" })).not.toBeInTheDocument();
  });
});

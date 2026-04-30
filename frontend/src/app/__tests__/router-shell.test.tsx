import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";
import { installWorkbenchFetchMock, pushPayload, statusPayload } from "./workbench-api-mocks";

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderApp(pathname: string) {
    window.history.pushState({}, "", pathname);
    return render(<App />);
  }

  it("renders the remaining Push Center, Status, and Settings routes", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });

    renderApp("/push");
    expect(await screen.findByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
    renderApp("/status");
    expect(await screen.findByRole("heading", { name: "Freshness snapshot" })).toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
    renderApp("/settings");
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workspace preferences" })).not.toBeInTheDocument();
  });

  it("converges the root path to /push", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });

    renderApp("/");

    await waitFor(() => {
      expect(window.location.pathname).toBe("/push");
    });
    expect(await screen.findByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();
  });

  it("ignores removed default routes and falls back to /push", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
    window.localStorage.setItem("dashboard-default-route", "/market");

    renderApp("/");

    await waitFor(() => {
      expect(window.location.pathname).toBe("/push");
    });
  });

  it("removes Dashboard, News, Macro, Market, Events, and market ticker from the shell", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });

    renderApp("/push");

    expect(await screen.findByRole("link", { name: "Push Center" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "News" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Macro" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Market" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Events" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Market ticker" })).not.toBeInTheDocument();
  });

  it("keeps push directory expansion state after a refresh", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
    const user = userEvent.setup();

    const firstRender = renderApp("/push");

    await user.click(await screen.findByRole("button", { name: /expand push center directory/i }));
    expect(await screen.findByRole("link", { name: "Push Center > Overview" })).toBeInTheDocument();

    firstRender.unmount();

    renderApp("/push");

    expect(await screen.findByRole("button", { name: /collapse push center directory/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Push Center > Overview" })).toBeInTheDocument();
  });

  it("persists the theme and sidebar preferences", async () => {
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
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
});

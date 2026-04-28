import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock, marketPayload, statusPayload } from "../../../app/__tests__/workbench-api-mocks";

describe("SettingsPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderSettingsApp(initialEntry = "/settings") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  it("persists workspace preferences and applies them to shell defaults", async () => {
    const user = userEvent.setup();

    installWorkbenchFetchMock({ status: statusPayload, market: marketPayload });
    renderSettingsApp("/settings");

    expect(await screen.findByRole("heading", { name: "Workspace preferences" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Market ticker" })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Default landing page"), "/market");
    await user.selectOptions(screen.getByLabelText("Default news mode"), "api");
    await user.click(screen.getByLabelText("Show market ticker"));
    await user.click(screen.getByRole("button", { name: "Save preferences" }));

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-default-route")).toBe("/market");
      expect(window.localStorage.getItem("dashboard-default-news-mode")).toBe("api");
      expect(window.localStorage.getItem("dashboard-show-market-ticker")).toBe("false");
    });

    expect(await screen.findByText("Preferences saved.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Market ticker" })).not.toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ status: statusPayload, market: marketPayload });
    window.history.pushState({}, "", "/");
    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe("/market");
    });
    expect(await screen.findByRole("heading", { name: "Market overview" })).toBeInTheDocument();

    cleanup();
    const fetchMock = installWorkbenchFetchMock({ status: statusPayload, market: marketPayload });
    window.history.pushState({}, "", "/news");
    render(<App />);

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/dashboard?news_mode=api")),
      ).toBe(true);
    });
  });
});

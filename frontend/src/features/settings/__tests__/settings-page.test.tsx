import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock, pushPayload, statusPayload } from "../../../app/__tests__/workbench-api-mocks";

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

  it("persists the remaining workspace route preference", async () => {
    const user = userEvent.setup();

    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
    renderSettingsApp("/settings");

    expect(await screen.findByRole("heading", { name: "Workspace preferences" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Default news mode")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Show market ticker")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Default landing page"), "/status");
    await user.click(screen.getByRole("button", { name: "Save preferences" }));

    await waitFor(() => {
      expect(window.localStorage.getItem("dashboard-default-route")).toBe("/status");
    });

    expect(await screen.findByText("Preferences saved.")).toBeInTheDocument();

    cleanup();
    installWorkbenchFetchMock({ push: pushPayload, status: statusPayload });
    window.history.pushState({}, "", "/");
    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe("/status");
    });
    expect(await screen.findByRole("heading", { name: "Freshness snapshot" })).toBeInTheDocument();
  });
});

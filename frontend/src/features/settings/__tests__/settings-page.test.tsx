import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock, pushPayload } from "../../../app/__tests__/workbench-api-mocks";

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

  it("removes the unused settings body cards", async () => {
    installWorkbenchFetchMock({ push: pushPayload });
    renderSettingsApp("/settings");

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByText("Module workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workspace preferences" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Current defaults" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Default landing page")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save preferences" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Default news mode")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Show market ticker")).not.toBeInTheDocument();
  });
});

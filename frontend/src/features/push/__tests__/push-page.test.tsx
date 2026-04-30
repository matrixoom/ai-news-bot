import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import {
  installWorkbenchFetchMock,
  marketPayload,
  pushPayload,
} from "../../../app/__tests__/workbench-api-mocks";

describe("PushPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function renderPushApp(initialEntry = "/push?tab=schedules") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  it("renders the schedules workspace as the first push tab", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    expect(await screen.findByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();
    expect(screen.getByLabelText("SMTP server")).toHaveValue("smtp.example.com");
    expect(screen.getByRole("link", { name: "Schedules" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Overview" })).not.toBeInTheDocument();
    expect(screen.getByTitle("Push preview")).toBeInTheDocument();
    expect(screen.queryByText("Text fallback")).not.toBeInTheDocument();

    expect(window.location.search).toContain("tab=schedules");
    expect(screen.getByTitle("Push preview")).toBeInTheDocument();
    expect(screen.queryByText("Manual runs and scheduled deliveries")).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "History" }));

    expect(window.location.search).toContain("tab=history");
    expect(screen.getByRole("link", { name: "History" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByTitle("Push preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Text fallback")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Run controls" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send now" })).not.toBeInTheDocument();
    expect(screen.getByText("Market Daily")).toBeInTheDocument();

    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/push?refresh=1")),
    ).toBe(true);
  });

  it("falls back to schedules when the old overview tab is requested", async () => {
    installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });

    renderPushApp("/push?tab=overview");

    expect(await screen.findByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Schedules" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link", { name: "Overview" })).not.toBeInTheDocument();
  });

  it("saves configuration and refreshes preview from the current draft", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    const smtpServerInput = await screen.findByLabelText("SMTP server");
    await user.clear(smtpServerInput);
    await user.type(smtpServerInput, "smtp.internal.example");
    await user.selectOptions(screen.getByLabelText("Report style"), "briefing");

    await user.click(screen.getByRole("button", { name: "Save configuration" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/config") && init?.method === "PUT",
        ),
      ).toBe(true);
    });
    expect(await screen.findByText(/Saved to/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Refresh preview" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/preview") && init?.method === "POST",
        ),
      ).toBe(true);
    });
    expect(await screen.findByText("Preview refreshed.")).toBeInTheDocument();
    expect(screen.getByText("Preview for briefing")).toBeInTheDocument();
  });

  it("triggers a manual push from the schedules controls", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();

    renderPushApp("/push?tab=schedules");

    await user.click(await screen.findByRole("button", { name: "Send now" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).includes("/api/push/trigger") && init?.method === "POST",
        ),
      ).toBe(true);
    });

    expect(await screen.findByText("Manual push sent.")).toBeInTheDocument();
  });
});

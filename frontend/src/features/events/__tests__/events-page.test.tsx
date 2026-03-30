import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";

const eventsPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  module: {
    id: "events",
    label: "Events Outlook",
    note: "4 window cards",
    description: "Timeline and watch windows for official calendars.",
    status: "live",
    loading: false,
    details: [
      {
        id: "next-7-days",
        label: "Next 7 Days",
        kind: "events",
        note: "2 items",
        section: {
          key: "next-7-days",
          title: "Next 7 Days",
          status: "live",
          items: [
            {
              title: "National Bureau of Statistics release window",
              region: "China",
              expected_date: "2026-04-01",
              time_window: "Morning",
              confidence: "high",
              impact_summary: "Inflation and activity releases may reset the near-term tone.",
              source: "National Bureau of Statistics",
            },
            {
              title: "Federal Reserve speaker slate",
              region: "US",
              expected_date: "2026-04-02",
              time_window: "All day",
              confidence: "medium",
              impact_summary: "Policy commentary could move rate expectations again.",
              source: "Federal Reserve",
            },
          ],
          official_links: [
            {
              region: "US",
              label: "Federal Reserve Calendar",
              url: "https://www.federalreserve.gov/newsevents/calendar.htm",
            },
          ],
        },
      },
      {
        id: "next-30-days",
        label: "Next 30 Days",
        kind: "events",
        note: "1 item",
        section: {
          key: "next-30-days",
          title: "Next 30 Days",
          status: "sample",
          items: [
            {
              title: "Japan CPI release",
              region: "Japan",
              expected_date: "2026-04-15",
              time_window: "Asia session",
              confidence: "high",
              impact_summary: "The release could guide regional policy expectations.",
              source: "Statistics Bureau of Japan",
            },
          ],
          official_links: [],
        },
      },
    ],
  },
};

describe("EventsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders time windows, official links, and keeps tab state in the URL", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(eventsPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    window.history.pushState({}, "", "/events?tab=timeline");

    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Next 7 Days" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "National Bureau of Statistics release window" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Federal Reserve Calendar/i })).toHaveAttribute(
      "href",
      "https://www.federalreserve.gov/newsevents/calendar.htm",
    );

    await user.click(screen.getByRole("link", { name: "Sources" }));

    expect(window.location.search).toBe("?tab=sources");
    expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("aria-current", "page");
  });

  it("falls back to timeline when the tab query is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(eventsPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    window.history.pushState({}, "", "/events?tab=unknown");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Next 7 Days" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Timeline" })).toHaveAttribute("aria-current", "page");
  });
});

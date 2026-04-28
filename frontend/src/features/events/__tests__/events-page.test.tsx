import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../../app/app";
import { installWorkbenchFetchMock } from "../../../app/__tests__/workbench-api-mocks";
import { EventsPage } from "../../../pages/events-page";

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

  function renderEventsApp(initialEntry = "/events") {
    window.history.pushState({}, "", initialEntry);
    render(<App />);
  }

  function renderEventsPage(initialEntry = "/events") {
    const router = createMemoryRouter(
      [
        {
          path: "/events",
          element: <EventsPage />,
        },
      ],
      {
        initialEntries: [initialEntry],
      },
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
  }

  it("renders time windows and official links without child tabs", async () => {
    installWorkbenchFetchMock({ events: eventsPayload });

    renderEventsApp("/events");

    expect(await screen.findByRole("heading", { name: "Next 7 Days" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "National Bureau of Statistics release window" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Federal Reserve Calendar/i })).toHaveAttribute(
      "href",
      "https://www.federalreserve.gov/newsevents/calendar.htm",
    );

    expect(screen.queryByRole("link", { name: "近1个月" })).not.toBeInTheDocument();
  });

  it("ignores removed tab queries and renders the consolidated timeline", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(eventsPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderEventsApp("/events?tab=unknown");

    expect(await screen.findByRole("heading", { name: "Next 7 Days" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "近一周" })).not.toBeInTheDocument();
  });

  it("renders the loading state inside the shared module frame", () => {
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => new Promise(() => {}));

    renderEventsPage("/events");

    expect(screen.getAllByRole("heading", { name: "Events" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Loading event windows")).toBeInTheDocument();
    expect(screen.getByText("Official links loading")).toBeInTheDocument();
  });

  it("renders the error state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    renderEventsPage("/events");

    expect(await screen.findByText("Events module unavailable")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Events" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the empty state inside the shared module frame", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...eventsPayload,
          module: {
            ...eventsPayload.module,
            details: [],
            note: "0 window cards",
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderEventsPage("/events");

    expect(await screen.findByText("No event windows yet")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Events" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Timeline and watch windows for official calendars.")).toBeInTheDocument();
  });
});

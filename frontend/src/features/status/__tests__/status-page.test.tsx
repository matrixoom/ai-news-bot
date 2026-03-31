import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StatusPage } from "../../../pages/status-page";

const statusPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  coverage_note: "128 stories indexed in the last 24 hours.",
  module: {
    id: "status",
    label: "Data Status",
    note: "2 data cards",
    description: "Freshness and source health across the workbench.",
    status: "live",
    loading: false,
    details: [
      {
        id: "news-coverage",
        label: "News coverage",
        kind: "status",
        note: "live",
        section: {
          key: "news-coverage",
          label: "News coverage",
          status: "live",
          detail: "128 stories indexed in the last 24 hours.",
        },
      },
      {
        id: "upstream-health",
        label: "Upstream health",
        kind: "status",
        note: "running",
        section: {
          key: "upstream-health",
          label: "Upstream health",
          status: "live",
          detail: "upstream service is reachable",
        },
      },
    ],
  },
};

describe("StatusPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderStatusPage(initialEntry = "/status") {
    const router = createMemoryRouter(
      [
        {
          path: "/status",
          element: <StatusPage />,
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

  it("renders the status snapshot and source health cards", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(statusPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderStatusPage();

    expect(await screen.findByRole("heading", { name: "Freshness snapshot" })).toBeInTheDocument();
    expect(screen.getAllByText("128 stories indexed in the last 24 hours.").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Upstream health" })).toBeInTheDocument();
    expect(screen.getByText("upstream service is reachable")).toBeInTheDocument();
  });

  it("renders loading chrome while the query is pending", () => {
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => new Promise(() => {}));

    renderStatusPage();

    expect(screen.getAllByRole("heading", { name: "Status" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Loading status snapshot")).toBeInTheDocument();
    expect(screen.getByText("Status summary loading")).toBeInTheDocument();
  });

  it("renders the error state inside the shared frame", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("network down"));

    renderStatusPage();

    expect(await screen.findByText("Status module unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the empty state when the backend returns no status items", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...statusPayload,
          module: {
            ...statusPayload.module,
            details: [],
            note: "0 data cards",
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderStatusPage();

    expect(await screen.findByText("No status items yet")).toBeInTheDocument();
    expect(screen.getByText("Freshness and source health across the workbench.")).toBeInTheDocument();
  });
});

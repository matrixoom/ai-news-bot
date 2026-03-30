import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NewsPage } from "../../../pages/news-page";

const newsPayload = {
  generated_at: "2026-03-30T09:00:00Z",
  news_mode: "hybrid",
  news_mode_options: [
    { value: "hybrid", label: "Hybrid" },
    { value: "api", label: "API" },
    { value: "upstream", label: "Upstream" },
  ],
  upstream_service_status: "available",
  module: {
    id: "news",
    label: "News Intelligence",
    note: "3 channels, 6 headlines",
    description: "Technology, finance, and policy headlines in one calm workbench.",
    status: "live",
    loading: false,
    details: [
      {
        id: "technology",
        label: "Technology",
        kind: "news",
        note: "2 stories",
        section: {
          key: "technology",
          title: "Technology",
          status: "live",
          description: "Platform and AI coverage.",
          item_count: 2,
          items: [
            {
              rank: 1,
              title: "AI chip makers extended the overnight bid.",
              source: "Newswire",
              url: "https://example.com/ai-chip-makers",
              published_at: "2026-03-30T08:30:00Z",
              tag: "technology",
              summary: "Large-cap semis led the session higher.",
              is_placeholder: false,
            },
            {
              rank: 2,
              title: "Model release cadence stayed brisk.",
              source: "TechBrief",
              url: "https://example.com/model-release-cadence",
              published_at: "2026-03-30T08:10:00Z",
              tag: "technology",
              summary: "New tooling kept developer interest elevated.",
              is_placeholder: false,
            },
          ],
        },
      },
      {
        id: "finance",
        label: "Finance",
        kind: "news",
        note: "1 story",
        section: {
          key: "finance",
          title: "Finance",
          status: "live",
          description: "Rates and liquidity coverage.",
          item_count: 1,
          items: [
            {
              rank: 1,
              title: "Credit spreads held steady into the close.",
              source: "Markets Desk",
              url: "https://example.com/credit-spreads",
              published_at: "2026-03-30T07:55:00Z",
              tag: "finance",
              summary: "Macro conditions remained broadly constructive.",
              is_placeholder: false,
            },
          ],
        },
      },
      {
        id: "policy",
        label: "Policy",
        kind: "news",
        note: "3 stories",
        section: {
          key: "policy",
          title: "Policy",
          status: "sample",
          description: "Regulatory and government coverage.",
          item_count: 3,
          items: [
            {
              rank: 1,
              title: "Officials flagged a measured policy stance.",
              source: "Policy Wire",
              url: "https://example.com/policy-stance",
              published_at: "2026-03-30T07:20:00Z",
              tag: "policy",
              summary: "The update signaled patience on next steps.",
              is_placeholder: false,
            },
          ],
        },
      },
    ],
  },
};

describe("NewsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders channel summaries, ranked headlines, and upstream status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(newsPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const router = createMemoryRouter(
      [
        {
          path: "/news",
          element: <NewsPage />,
        },
      ],
      {
        initialEntries: ["/news?tab=overview"],
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

    expect(await screen.findByRole("heading", { name: "Channel summaries" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Technology" })).toBeInTheDocument();
    expect(screen.getAllByText("2 stories").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Ranked headlines" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "1. AI chip makers extended the overnight bid." }),
    ).toHaveAttribute("href", "https://example.com/ai-chip-makers");
    expect(screen.getByText("Source status")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Operational snapshot" })).toBeInTheDocument();
    expect(screen.getByText("available")).toBeInTheDocument();
    expect(screen.getAllByText("Hybrid").length).toBeGreaterThan(0);
  });
});

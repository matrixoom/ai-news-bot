import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppProviders } from "../../../app/providers";
import { appRoutes } from "../../../app/routes";

const dashboardPayload = {
  hero: {
    eyebrow: "Trend Insights",
    title: "Trend Insights",
    summary: "Technology headlines turned constructive overnight.",
  },
  stats: [
    {
      id: "news-coverage",
      label: "News coverage",
      value: "128 stories",
      change: "+12 vs yesterday",
    },
  ],
  brief: {
    title: "Today Brief",
    summary: "Technology headlines turned constructive overnight.",
    ctaLabel: "Open News",
    ctaHref: "/news",
  },
  modules: [
    {
      id: "news",
      title: "News",
      summary: "Top developments and story flow.",
      ctaLabel: "Open module",
      ctaHref: "/news",
    },
  ],
};

describe("DashboardPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the dashboard overview from the dashboard endpoint", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => dashboardPayload,
    } as Response);

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/dashboard"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByRole("heading", { name: "Trend Insights" })).toBeInTheDocument();
    expect(screen.getByText("Today Brief")).toBeInTheDocument();
    expect(screen.getAllByText("Technology headlines turned constructive overnight.")[0]).toBeInTheDocument();
    expect(screen.getByText("News coverage")).toBeInTheDocument();
    expect(screen.getByText("Module snapshots")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open News" })).toBeInTheDocument();
  });
});

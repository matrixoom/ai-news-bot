import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { App } from "../app";
import { AppProviders } from "../providers";
import { appRoutes } from "../routes";

describe("Workbench shell", () => {
  it("renders the sidebar and the active route title", async () => {
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/news"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Push Center" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "News" })).toBeInTheDocument();
    expect(screen.getByText("Module page coming in the next slice.")).toBeInTheDocument();
  });

  it("renders the dashboard route with the shared placeholder", async () => {
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/dashboard"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Module page coming in the next slice.")).toBeInTheDocument();
  });

  it("uses the real App entry to keep URL and title in sync", async () => {
    window.history.pushState({}, "", "/news");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "News" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("link", { name: "Dashboard" }));

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
  });

  it("converges the root path to /dashboard", async () => {
    window.history.pushState({}, "", "/");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
  });
});

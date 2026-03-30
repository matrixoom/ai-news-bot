import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
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
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";

describe("Workbench shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps the /news tab state in the URL", async () => {
    window.history.pushState({}, "", "/news?tab=channels");

    render(<App />);

    expect(await screen.findByRole("tab", { name: "Channels" })).toHaveAttribute("aria-selected", "true");

    await userEvent.click(screen.getByRole("tab", { name: "Sources" }));

    expect(window.location.pathname).toBe("/news");
    expect(window.location.search).toBe("?tab=sources");
  });

  it("falls back to overview when the tab query is unknown", async () => {
    window.history.pushState({}, "", "/news?tab=unknown");

    render(<App />);

    expect(await screen.findByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });
});

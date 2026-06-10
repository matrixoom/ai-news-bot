import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../dashboard-page";
import { EventsPage } from "../events-page";
import { NewsPage } from "../news-page";

const placeholderPages = [
  ["DashboardPage", DashboardPage],
  ["NewsPage", NewsPage],
] as const;

describe("removed module pages", () => {
  it.each(placeholderPages)("%s renders a professional placeholder and requests no data", (_name, Page) => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<Page />);

    expect(screen.getByRole("heading")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("keeps the removed EventsPage empty and requests no data", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<EventsPage />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

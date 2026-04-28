import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../dashboard-page";
import { EventsPage } from "../events-page";
import { MacroPage } from "../macro-page";
import { MarketPage } from "../market-page";
import { NewsPage } from "../news-page";

const removedPages = [
  ["DashboardPage", DashboardPage],
  ["NewsPage", NewsPage],
  ["MacroPage", MacroPage],
  ["MarketPage", MarketPage],
  ["EventsPage", EventsPage],
] as const;

describe("removed module pages", () => {
  it.each(removedPages)("%s renders no elements and requests no data", (_name, Page) => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<Page />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

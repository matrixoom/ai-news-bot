import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MarketPage } from "../../../pages/market-page";

describe("MarketPage", () => {
  it("renders no page elements and does not request market data", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<MarketPage />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

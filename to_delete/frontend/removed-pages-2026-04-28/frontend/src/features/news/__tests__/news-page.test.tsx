import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NewsPage } from "../../../pages/news-page";

describe("NewsPage", () => {
  it("renders no page elements and does not request news data", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<NewsPage />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

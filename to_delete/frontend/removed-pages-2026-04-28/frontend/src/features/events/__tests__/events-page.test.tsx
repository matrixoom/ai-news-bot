import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EventsPage } from "../../../pages/events-page";

describe("EventsPage", () => {
  it("renders no page elements and does not request events data", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<EventsPage />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

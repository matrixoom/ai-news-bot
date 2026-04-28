import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MacroPage } from "../../../pages/macro-page";

describe("MacroPage", () => {
  it("renders no page elements and does not request macro data", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<MacroPage />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

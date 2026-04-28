import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../../../pages/dashboard-page";

describe("DashboardPage", () => {
  it("renders no page elements and does not request dashboard data", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<DashboardPage />);

    expect(container).toBeEmptyDOMElement();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

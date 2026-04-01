import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../app";
import { installWorkbenchFetchMock } from "./workbench-api-mocks";

describe("App bootstrap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the initial frontend title", () => {
    installWorkbenchFetchMock();

    render(<App />);

    expect(screen.getByRole("heading", { name: "Trend Insight" })).toBeInTheDocument();
    expect(screen.queryByText("Loading workspace...")).not.toBeInTheDocument();
  });
});

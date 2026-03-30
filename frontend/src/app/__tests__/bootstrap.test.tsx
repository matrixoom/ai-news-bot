import { render, screen } from "@testing-library/react";
import { App } from "../app";

describe("App bootstrap", () => {
  it("renders the initial frontend title", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "AI News Bot" })).toBeInTheDocument();
    expect(screen.getByText("Loading workspace...")).toBeInTheDocument();
  });
});

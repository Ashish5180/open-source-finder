import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

describe("Frontend Environment Smoke Test", () => {
  it("renders a test element in JSDOM", () => {
    render(<div data-testid="test-node">Opportunity Finder</div>);
    const element = screen.getByTestId("test-node");
    expect(element).toBeInTheDocument();
    expect(element).toHaveTextContent("Opportunity Finder");
  });
});

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProfileForm } from "../src/components/profile/ProfileForm";

describe("ProfileForm Component", () => {
  it("renders profile fields and common presets", () => {
    render(<ProfileForm isLoading={false} onSearch={vi.fn()} />);

    expect(screen.getByText("Candidate Profile")).toBeInTheDocument();
    expect(screen.getAllByText("Python").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("FastAPI").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Beginner")).toBeInTheDocument();
    expect(screen.getByText("Intermediate")).toBeInTheDocument();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  it("submits the profile when Find Opportunities is clicked", () => {
    const handleSearch = vi.fn();
    render(<ProfileForm isLoading={false} onSearch={handleSearch} />);

    const submitBtn = screen.getByRole("button", { name: /find opportunities/i });
    fireEvent.click(submitBtn);

    expect(handleSearch).toHaveBeenCalledTimes(1);
    const [profile, includeUncertain] = handleSearch.mock.calls[0];
    expect(profile.languages).toContain("Python");
    expect(profile.experience).toBe("INTERMEDIATE");
    expect(includeUncertain).toBe(true);
  });

  it("adds a new language when typing and clicking Add", () => {
    const handleSearch = vi.fn();
    render(<ProfileForm isLoading={false} onSearch={handleSearch} />);

    const langInput = screen.getByPlaceholderText(/Add language/i);
    fireEvent.change(langInput, { target: { value: "Rust" } });
    fireEvent.keyDown(langInput, { key: "Enter", code: "Enter" });

    expect(screen.getAllByText("Rust").length).toBeGreaterThanOrEqual(1);

    const submitBtn = screen.getByRole("button", { name: /find opportunities/i });
    fireEvent.click(submitBtn);

    const [profile] = handleSearch.mock.calls[0];
    expect(profile.languages).toContain("Rust");
  });

  it("shows loading state when search is in flight", () => {
    render(<ProfileForm isLoading={true} onSearch={vi.fn()} />);

    expect(screen.getByText(/Searching Opportunities/i)).toBeInTheDocument();
    const submitBtn = screen.getByRole("button", { name: /searching opportunities/i });
    expect(submitBtn).toBeDisabled();
  });
});

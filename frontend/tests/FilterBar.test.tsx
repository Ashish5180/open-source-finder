import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FilterBar } from "../src/components/filters/FilterBar";

describe("FilterBar Component", () => {
  it("renders search input, language filter, sort dropdown and counts", () => {
    render(
      <FilterBar
        searchQuery=""
        onSearchQueryChange={vi.fn()}
        selectedLanguage="ALL"
        onLanguageChange={vi.fn()}
        availableLanguages={["Python", "Go"]}
        sortBy="composite"
        onSortByChange={vi.fn()}
        hideUncertain={false}
        onHideUncertainChange={vi.fn()}
        totalFiltered={12}
        totalFound={15}
        onResetFilters={vi.fn()}
      />
    );

    expect(screen.getByPlaceholderText(/Filter by keyword/i)).toBeInTheDocument();
    expect(screen.getByText(/Showing/i)).toHaveTextContent("Showing 12 of 15 opportunities");
    expect(screen.getByLabelText(/language:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/sort by:/i)).toBeInTheDocument();
  });

  it("calls onSearchQueryChange when query input changes", () => {
    const handleQueryChange = vi.fn();
    render(
      <FilterBar
        searchQuery=""
        onSearchQueryChange={handleQueryChange}
        selectedLanguage="ALL"
        onLanguageChange={vi.fn()}
        availableLanguages={["Python"]}
        sortBy="composite"
        onSortByChange={vi.fn()}
        hideUncertain={false}
        onHideUncertainChange={vi.fn()}
        totalFiltered={5}
        totalFound={5}
        onResetFilters={vi.fn()}
      />
    );

    const input = screen.getByPlaceholderText(/Filter by keyword/i);
    fireEvent.change(input, { target: { value: "bug" } });

    expect(handleQueryChange).toHaveBeenCalledWith("bug");
  });

  it("calls onSortByChange when sort selection changes", () => {
    const handleSortChange = vi.fn();
    render(
      <FilterBar
        searchQuery=""
        onSearchQueryChange={vi.fn()}
        selectedLanguage="ALL"
        onLanguageChange={vi.fn()}
        availableLanguages={[]}
        sortBy="composite"
        onSortByChange={handleSortChange}
        hideUncertain={false}
        onHideUncertainChange={vi.fn()}
        totalFiltered={5}
        totalFound={5}
        onResetFilters={vi.fn()}
      />
    );

    const select = screen.getByLabelText(/sort by:/i);
    fireEvent.change(select, { target: { value: "freshness" } });

    expect(handleSortChange).toHaveBeenCalledWith("freshness");
  });

  it("displays reset filters button when filtered and triggers callback", () => {
    const handleReset = vi.fn();
    render(
      <FilterBar
        searchQuery="test"
        onSearchQueryChange={vi.fn()}
        selectedLanguage="ALL"
        onLanguageChange={vi.fn()}
        availableLanguages={[]}
        sortBy="composite"
        onSortByChange={vi.fn()}
        hideUncertain={false}
        onHideUncertainChange={vi.fn()}
        totalFiltered={2}
        totalFound={10}
        onResetFilters={handleReset}
      />
    );

    const resetBtn = screen.getByText(/Reset Filters/i);
    fireEvent.click(resetBtn);

    expect(handleReset).toHaveBeenCalledTimes(1);
  });

  it("toggles advanced filters tray and triggers assignment filter change", () => {
    const handleAssignmentChange = vi.fn();
    render(
      <FilterBar
        searchQuery=""
        onSearchQueryChange={vi.fn()}
        selectedLanguage="ALL"
        onLanguageChange={vi.fn()}
        availableLanguages={[]}
        sortBy="composite"
        onSortByChange={vi.fn()}
        hideUncertain={false}
        onHideUncertainChange={vi.fn()}
        totalFiltered={10}
        totalFound={10}
        onResetFilters={vi.fn()}
        assignmentFilter="ALL"
        onAssignmentFilterChange={handleAssignmentChange}
      />
    );

    // Click Filters toggle button
    const filtersBtn = screen.getByRole("button", { name: /filters/i });
    fireEvent.click(filtersBtn);

    // Assignment filter select is now visible
    const assignmentSelect = screen.getByLabelText(/assignment:/i);
    expect(assignmentSelect).toBeInTheDocument();

    fireEvent.change(assignmentSelect, { target: { value: "UNASSIGNED" } });
    expect(handleAssignmentChange).toHaveBeenCalledWith("UNASSIGNED");
  });
});

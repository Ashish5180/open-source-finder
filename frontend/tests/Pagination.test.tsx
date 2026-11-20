import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Pagination } from "../src/components/shared/Pagination";

describe("Pagination Component", () => {
  it("renders page info and navigation buttons", () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        pageSize={10}
        totalItems={45}
        onPageChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    );

    expect(screen.getByText(/showing/i)).toHaveTextContent("Showing 1–10 of 45 opportunities");
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /next/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Page 1" })).toHaveAttribute("aria-current", "page");
  });

  it("calls onPageChange when next page is clicked", () => {
    const handlePageChange = vi.fn();
    render(
      <Pagination
        currentPage={1}
        totalPages={3}
        pageSize={10}
        totalItems={25}
        onPageChange={handlePageChange}
      />
    );

    const nextBtn = screen.getByRole("button", { name: /next/i });
    fireEvent.click(nextBtn);

    expect(handlePageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange when specific page number is clicked", () => {
    const handlePageChange = vi.fn();
    render(
      <Pagination
        currentPage={1}
        totalPages={4}
        pageSize={10}
        totalItems={35}
        onPageChange={handlePageChange}
      />
    );

    const page3Btn = screen.getByRole("button", { name: "Page 3" });
    fireEvent.click(page3Btn);

    expect(handlePageChange).toHaveBeenCalledWith(3);
  });

  it("calls onPageSizeChange when page size dropdown changes", () => {
    const handleSizeChange = vi.fn();
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        pageSize={10}
        totalItems={50}
        onPageChange={vi.fn()}
        onPageSizeChange={handleSizeChange}
      />
    );

    const select = screen.getByLabelText(/per page:/i);
    fireEvent.change(select, { target: { value: "25" } });

    expect(handleSizeChange).toHaveBeenCalledWith(25);
  });

  it("returns null when totalItems is 0", () => {
    const { container } = render(
      <Pagination
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalItems={0}
        onPageChange={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { OpportunityCard } from "../src/components/opportunities/OpportunityCard";
import type { Opportunity } from "../src/types/opportunity";

const mockOpportunity: Opportunity = {
  issue_key: "tiangolo/fastapi#1234",
  github_issue_id: 123456,
  url: "https://github.com/tiangolo/fastapi/issues/1234",
  title: "Add validation error detail to exception handler",
  repository: "tiangolo/fastapi",
  labels: ["good first issue", "help wanted"],
  language: "Python",
  state: "open",
  is_assigned: false,
  has_linked_pr: false,
  created_at: "2024-03-01T12:00:00Z",
  updated_at: "2024-03-10T12:00:00Z",
  observed_at: "2024-03-11T12:00:00Z",
  scores: {
    fit_score: 0.9,
    actionability_score: 0.8,
    health_score: 0.85,
    freshness_score: 0.75,
    composite_score: 0.83,
  },
  eligibility: "ELIGIBLE",
  exclusion_reason: null,
  reasons: [
    "Primary repository language match: Python",
    "Clear reproduction steps and code snippets present",
  ],
  uncertainties: [
    "Assignment state unverified in snapshot",
  ],
  scoring_config_version: "v1.0.0",
  feedback: null,
};

describe("OpportunityCard Component", () => {
  it("renders repository, issue title, external link and evidence reasons", () => {
    render(
      <OpportunityCard
        opportunity={mockOpportunity}
        onFeedbackChange={vi.fn()}
        onRecheck={vi.fn()}
      />
    );

    expect(screen.getByText("tiangolo/fastapi")).toBeInTheDocument();
    expect(screen.getByText("#1234")).toBeInTheDocument();
    expect(
      screen.getByText("Add validation error detail to exception handler")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Primary repository language match: Python")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Assignment state unverified in snapshot")
    ).toBeInTheDocument();
    expect(screen.getByText("Score: 83%")).toBeInTheDocument();
  });

  it("toggles score breakdown when score button is clicked", () => {
    render(
      <OpportunityCard
        opportunity={mockOpportunity}
        onFeedbackChange={vi.fn()}
      />
    );

    expect(screen.queryByText("Heuristic Score Breakdown")).not.toBeInTheDocument();

    const scoreBtn = screen.getByLabelText(/toggle score details/i);
    fireEvent.click(scoreBtn);

    expect(screen.getByText("Heuristic Score Breakdown")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument(); // fit score
    expect(screen.getByText("80%")).toBeInTheDocument(); // actionability
  });

  it("calls onFeedbackChange when a feedback button is clicked", async () => {
    const handleFeedback = vi.fn().mockResolvedValue(undefined);
    render(
      <OpportunityCard
        opportunity={mockOpportunity}
        onFeedbackChange={handleFeedback}
      />
    );

    const interestedBtn = screen.getByRole("button", { name: "Interested" });
    fireEvent.click(interestedBtn);

    expect(handleFeedback).toHaveBeenCalledWith("tiangolo/fastapi#1234", "INTERESTED");
  });

  it("calls onRecheck when recheck live is clicked", async () => {
    const handleRecheck = vi.fn().mockResolvedValue(undefined);
    render(
      <OpportunityCard
        opportunity={mockOpportunity}
        onFeedbackChange={vi.fn()}
        onRecheck={handleRecheck}
      />
    );

    const recheckBtn = screen.getByRole("button", { name: /recheck live/i });
    fireEvent.click(recheckBtn);

    expect(handleRecheck).toHaveBeenCalledWith("tiangolo", "fastapi", 1234);
  });
});

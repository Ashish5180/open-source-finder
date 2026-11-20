"use client";

import React, { useState } from "react";
import type { FeedbackStatus, Opportunity } from "../../types/opportunity";
import { EligibilityBadge, FeedbackBadge } from "../shared/Badges";

interface OpportunityCardProps {
  opportunity: Opportunity;
  onFeedbackChange: (issueKey: string, status: FeedbackStatus) => Promise<void>;
  onRecheck?: (owner: string, repo: string, number: number) => Promise<void>;
}

export function OpportunityCard({
  opportunity,
  onFeedbackChange,
  onRecheck,
}: OpportunityCardProps) {
  const [showScores, setShowScores] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [isRechecking, setIsRechecking] = useState(false);
  const [recheckMessage, setRecheckMessage] = useState<string | null>(null);

  const {
    issue_key,
    title,
    url,
    repository,
    labels,
    language,
    is_assigned,
    scores,
    eligibility,
    reasons,
    uncertainties,
    feedback,
  } = opportunity;

  const [repoFromKey, issueNumStr] = issue_key.split("#");
  const issueNumber = parseInt(issueNumStr || "0", 10);
  const [owner, repoName] = (repository || repoFromKey || "").split("/");

  const handleFeedback = async (status: FeedbackStatus) => {
    setIsSubmittingFeedback(true);
    try {
      await onFeedbackChange(issue_key, status);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const handleRecheckClick = async () => {
    if (!onRecheck || !owner || !repoName || !issueNumber) return;
    setIsRechecking(true);
    setRecheckMessage(null);
    try {
      await onRecheck(owner, repoName, issueNumber);
      setRecheckMessage("State verified with GitHub");
      setTimeout(() => setRecheckMessage(null), 3000);
    } catch {
      setRecheckMessage("Failed to recheck state");
      setTimeout(() => setRecheckMessage(null), 3000);
    } finally {
      setIsRechecking(false);
    }
  };

  const compositePct = Math.round(scores.composite_score * 100);

  return (
    <article
      data-testid={`opportunity-card-${issue_key}`}
      className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 transition-all hover:shadow-[0_4px_20px_rgba(15,23,42,0.06)] hover:border-slate-300 focus-within:ring-2 focus-within:ring-indigo-500/20 text-sm shadow-[0_1px_3px_rgba(15,23,42,0.04)]"
    >
      {/* Top Header: Repo, Issue #, Score, and External Link */}
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <span className="font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
            {repository}
          </span>
          <span className="text-slate-400 font-medium">#{issueNumber}</span>
          {language && (
            <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200/80 text-[11px] font-sans font-medium">
              {language}
            </span>
          )}
          <EligibilityBadge eligibility={eligibility} />
          {feedback && <FeedbackBadge status={feedback} />}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setShowScores(!showScores)}
            aria-expanded={showScores}
            aria-label="Toggle score details"
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200/80 shadow-2xs transition-colors cursor-pointer"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
            <span>Score: {compositePct}%</span>
            <span className="text-[10px] text-indigo-500">
              {showScores ? "▲" : "▼"}
            </span>
          </button>

          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            title="Open issue on GitHub"
          >
            <span>GitHub</span>
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        </div>
      </div>

      {/* Issue Title */}
      <h3 className="text-base font-bold text-slate-900 leading-snug mb-3">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-indigo-600 transition-colors"
        >
          {title}
        </a>
      </h3>

      {/* Labels row */}
      {labels.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3.5">
          {labels.map((lbl) => (
            <span
              key={lbl}
              className="px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-slate-100/90 text-slate-700 border border-slate-200/80"
            >
              {lbl}
            </span>
          ))}
        </div>
      )}

      {/* Detailed Score Breakdown (Collapsible) */}
      {showScores && (
        <div className="mb-4 p-4 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs">
          <div className="flex justify-between items-center mb-2.5">
            <span className="font-bold text-slate-900">
              Heuristic Score Breakdown
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Config: {opportunity.scoring_config_version}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
            <div>
              <span className="text-[11px] text-slate-500 block">Candidate Fit</span>
              <span className="font-bold text-slate-900 text-sm">
                {Math.round(scores.fit_score * 100)}%
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 block">Actionability</span>
              <span className="font-bold text-slate-900 text-sm">
                {Math.round(scores.actionability_score * 100)}%
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 block">Repo Health</span>
              <span className="font-bold text-slate-900 text-sm">
                {scores.health_score !== null ? `${Math.round(scores.health_score * 100)}%` : "N/A"}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 block">Freshness</span>
              <span className="font-bold text-slate-900 text-sm">
                {Math.round(scores.freshness_score * 100)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Evidence-Backed Fit Reasons (Section 4 & 6) */}
      {reasons.length > 0 && (
        <div className="mb-3.5 p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-100 text-xs">
          <span className="font-bold text-emerald-900 block mb-1.5 flex items-center gap-1.5">
            <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
            </svg>
            Why This Matches You:
          </span>
          <ul className="list-disc list-inside space-y-1 text-emerald-800">
            {reasons.map((r, i) => (
              <li key={i} className="leading-relaxed">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Visible Uncertainties / Warnings (Section 4 & 6) */}
      {uncertainties.length > 0 && (
        <div className="mb-3.5 p-3.5 rounded-xl bg-amber-50/60 border border-amber-200/80 text-xs">
          <span className="font-bold text-amber-900 block mb-1.5 flex items-center gap-1.5">
            <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Caution / Unverified Factors:
          </span>
          <ul className="list-disc list-inside space-y-1 text-amber-800">
            {uncertainties.map((u, i) => (
              <li key={i} className="leading-relaxed">
                {u}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metadata Bar: Assignee state, Last update, PR status */}
      <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 font-mono mb-4 pt-1">
        <div>
          Status:{" "}
          <span className="font-semibold text-slate-800">
            {is_assigned ? "Assigned" : "Unassigned"}
          </span>
        </div>
        <div>
          PR State:{" "}
          <span className="font-semibold text-slate-800">
            {opportunity.has_linked_pr === false
              ? "No open PR observed"
              : "Unverified"}
          </span>
        </div>
        {recheckMessage && (
          <span className="text-emerald-700 text-xs font-sans font-semibold">
            {recheckMessage}
          </span>
        )}
      </div>

      {/* Bottom Footer: Feedback Actions & Recheck */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3.5 border-t border-slate-100">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-500 font-medium mr-1">Feedback:</span>
          {(
            [
              { status: "INTERESTED", label: "Interested" },
              { status: "STARTED", label: "Started" },
              { status: "PR_OPENED", label: "PR Opened" },
              { status: "MERGED", label: "Merged" },
              { status: "NOT_SUITABLE", label: "Not Suitable" },
              { status: "NOT_ACTIONABLE", label: "Not Actionable" },
            ] as const
          ).map((item) => {
            const isSelected = feedback === item.status;
            return (
              <button
                type="button"
                key={item.status}
                disabled={isSubmittingFeedback}
                onClick={() => handleFeedback(item.status)}
                className={`px-2.5 py-1 rounded-lg text-xs transition-all border cursor-pointer ${
                  isSelected
                    ? "bg-slate-900 text-white border-slate-900 font-semibold shadow-2xs"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </div>

        {onRecheck && (
          <button
            type="button"
            disabled={isRechecking}
            onClick={handleRecheckClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 transition-colors disabled:opacity-50 cursor-pointer"
            title="Recheck issue status before starting work"
          >
            {isRechecking ? (
              <span>Verifying...</span>
            ) : (
              <>
                <span>↻</span>
                <span>Recheck Live</span>
              </>
            )}
          </button>
        )}
      </div>
    </article>
  );
}

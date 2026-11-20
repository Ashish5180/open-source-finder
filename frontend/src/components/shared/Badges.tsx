import React from "react";
import type { Eligibility, FeedbackStatus } from "../../types/opportunity";

export function EligibilityBadge({ eligibility }: { eligibility: Eligibility }) {
  if (eligibility === "ELIGIBLE") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80 shadow-2xs">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
        Eligible
      </span>
    );
  }
  if (eligibility === "UNCERTAIN") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200/80 shadow-2xs">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
        Uncertain
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200/80 shadow-2xs">
      <span className="w-1.5 h-1.5 rounded-full bg-rose-600" />
      Excluded
    </span>
  );
}

export function FeedbackBadge({ status }: { status: FeedbackStatus }) {
  const labelMap: Record<FeedbackStatus, { label: string; bg: string; text: string; border: string }> = {
    INTERESTED: { label: "Interested", bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
    STARTED: { label: "In Progress", bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200" },
    PR_OPENED: { label: "PR Opened", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
    MERGED: { label: "Merged", bg: "bg-emerald-50", text: "text-emerald-800", border: "border-emerald-200" },
    NOT_SUITABLE: { label: "Not Suitable", bg: "bg-slate-100", text: "text-slate-600", border: "border-slate-200" },
    NOT_ACTIONABLE: { label: "Not Actionable", bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  };

  const config = labelMap[status] || {
    label: status,
    bg: "bg-slate-100",
    text: "text-slate-700",
    border: "border-slate-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border shadow-2xs ${config.bg} ${config.text} ${config.border}`}
    >
      {config.label}
    </span>
  );
}

export function TagChip({ text, onRemove }: { text: string; onRemove?: () => void }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200/80 shadow-2xs group hover:bg-slate-200/60 transition-colors">
      <span>{text}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="w-3.5 h-3.5 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-800 hover:bg-slate-300/80 transition-colors focus:outline-none"
          aria-label={`Remove ${text}`}
        >
          <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </span>
  );
}

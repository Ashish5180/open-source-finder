"use client";

import React from "react";

export function LoadingSkeletonList() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading opportunities">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 animate-pulse space-y-3.5 shadow-[0_1px_3px_rgba(15,23,42,0.04)]"
        >
          <div className="flex justify-between items-center">
            <div className="h-4 bg-slate-100 rounded-md w-1/3" />
            <div className="h-6 bg-slate-100 rounded-full w-24" />
          </div>
          <div className="h-5 bg-slate-100 rounded-md w-3/4" />
          <div className="flex gap-2">
            <div className="h-4 bg-slate-100 rounded-md w-16" />
            <div className="h-4 bg-slate-100 rounded-md w-24" />
          </div>
          <div className="space-y-2 pt-2">
            <div className="h-3 bg-slate-100 rounded-md w-2/3" />
            <div className="h-3 bg-slate-100 rounded-md w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

interface EmptyStateProps {
  hasFilters: boolean;
  onResetFilters?: () => void;
}

export function EmptyState({ hasFilters, onResetFilters }: EmptyStateProps) {
  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl p-8 sm:p-12 text-center space-y-3.5 shadow-[0_2px_12px_rgba(15,23,42,0.03)]">
      <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto text-indigo-600 text-lg shadow-2xs">
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      <h3 className="text-sm font-bold text-slate-900">
        {hasFilters
          ? "No opportunities match your active filters"
          : "No contribution opportunities found"}
      </h3>
      <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
        {hasFilters
          ? "Try resetting your search query, clearing specific language filters, or enabling uncertain issues."
          : "Try adding more widely used languages (e.g. Python, TypeScript, Go), reducing specific framework constraints, or allowing higher setup time."}
      </p>
      {hasFilters && onResetFilters && (
        <button
          type="button"
          onClick={onResetFilters}
          className="mt-2 inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors shadow-2xs"
        >
          Reset Filters
        </button>
      )}
    </div>
  );
}

interface ErrorBannerProps {
  message: string;
  requestId?: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, requestId, onRetry }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="bg-rose-50/90 border border-rose-200 rounded-2xl p-4 sm:p-5 text-xs text-rose-700 space-y-2 shadow-2xs"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="font-bold text-rose-900 block mb-0.5">Search Request Failed</span>
          <p className="text-rose-700">{message}</p>
          {requestId && (
            <span className="block mt-1.5 font-mono text-[10px] text-rose-600">
              Request ID: {requestId}
            </span>
          )}
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="px-3.5 py-1.5 rounded-xl bg-white border border-rose-200 text-rose-700 font-semibold hover:bg-rose-100 transition-colors shrink-0 shadow-2xs"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

interface RateLimitWarningProps {
  remaining: number;
}

export function RateLimitWarning({ remaining }: RateLimitWarningProps) {
  return (
    <div className="bg-amber-50/90 border border-amber-200/90 rounded-2xl p-3.5 sm:p-4 text-xs text-amber-900 flex items-center justify-between gap-3 shadow-2xs">
      <div className="flex items-center gap-2.5">
        <span className="flex h-5 w-5 rounded-full bg-amber-100 text-amber-700 items-center justify-center font-bold text-xs shrink-0">
          !
        </span>
        <span className="leading-relaxed">
          GitHub API rate budget low: <strong className="font-semibold text-amber-950">{remaining} requests remaining</strong>.
          Results are served from local snapshot cache where available.
        </span>
      </div>
    </div>
  );
}

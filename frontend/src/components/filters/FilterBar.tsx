"use client";

import React, { useState } from "react";
import type { FeedbackStatus } from "../../types/opportunity";

export type SortOption = "composite" | "freshness" | "actionability" | "fit";
export type AssignmentFilter = "ALL" | "UNASSIGNED" | "ASSIGNED";
export type PRFilter = "ALL" | "NO_PR" | "HAS_PR";
export type EligibilityFilter = "ALL" | "ELIGIBLE" | "UNCERTAIN";
export type FeedbackFilter = "ALL" | "UNREVIEWED" | FeedbackStatus;

interface FilterBarProps {
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  selectedLanguage: string;
  onLanguageChange: (language: string) => void;
  availableLanguages: string[];
  sortBy: SortOption;
  onSortByChange: (sort: SortOption) => void;
  hideUncertain: boolean;
  onHideUncertainChange: (hide: boolean) => void;
  totalFiltered: number;
  totalFound: number;
  onResetFilters: () => void;

  // Additional Filter Options
  assignmentFilter?: AssignmentFilter;
  onAssignmentFilterChange?: (filter: AssignmentFilter) => void;
  prFilter?: PRFilter;
  onPrFilterChange?: (filter: PRFilter) => void;
  minScore?: number;
  onMinScoreChange?: (score: number) => void;
  feedbackFilter?: FeedbackFilter;
  onFeedbackFilterChange?: (filter: FeedbackFilter) => void;
  selectedTag?: string;
  onTagChange?: (tag: string) => void;
  availableTags?: string[];
}

export function FilterBar({
  searchQuery,
  onSearchQueryChange,
  selectedLanguage,
  onLanguageChange,
  availableLanguages,
  sortBy,
  onSortByChange,
  hideUncertain,
  onHideUncertainChange,
  totalFiltered,
  totalFound,
  onResetFilters,
  assignmentFilter = "ALL",
  onAssignmentFilterChange,
  prFilter = "ALL",
  onPrFilterChange,
  minScore = 0,
  onMinScoreChange,
  feedbackFilter = "ALL",
  onFeedbackFilterChange,
  selectedTag = "ALL",
  onTagChange,
  availableTags = [],
}: FilterBarProps) {
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

  // Count active filters
  const advancedActiveCount =
    (assignmentFilter !== "ALL" ? 1 : 0) +
    (prFilter !== "ALL" ? 1 : 0) +
    (minScore > 0 ? 1 : 0) +
    (feedbackFilter !== "ALL" ? 1 : 0) +
    (selectedTag !== "ALL" ? 1 : 0);

  const isFiltered =
    searchQuery.trim() !== "" ||
    selectedLanguage !== "ALL" ||
    hideUncertain ||
    sortBy !== "composite" ||
    advancedActiveCount > 0;

  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 text-xs space-y-4 shadow-[0_2px_12px_rgba(15,23,42,0.03)]">
      {/* Primary Row: Keyword Search, Quick Language, Sort By, and More Filters Toggle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            placeholder="Filter by keyword, title, repo, or label..."
            className="w-full px-3.5 py-2 pl-9 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none transition-colors"
          />
          <svg
            className="absolute left-3 top-2.5 w-4 h-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Language Filter */}
          {availableLanguages.length > 0 && (
            <div className="flex items-center gap-1.5 shrink-0">
              <label htmlFor="lang-filter" className="text-slate-600 font-semibold">
                Language:
              </label>
              <select
                id="lang-filter"
                value={selectedLanguage}
                onChange={(e) => onLanguageChange(e.target.value)}
                className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 focus:border-indigo-500 focus:outline-none font-medium transition-colors cursor-pointer"
              >
                <option value="ALL">All Languages</option>
                {availableLanguages.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Sort Select */}
          <div className="flex items-center gap-1.5 shrink-0">
            <label htmlFor="sort-select" className="text-slate-600 font-semibold">
              Sort by:
            </label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => onSortByChange(e.target.value as SortOption)}
              className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 focus:border-indigo-500 focus:outline-none font-medium transition-colors cursor-pointer"
            >
              <option value="composite">Overall Score</option>
              <option value="freshness">Freshness (Newest)</option>
              <option value="actionability">Actionability</option>
              <option value="fit">Candidate Fit</option>
            </select>
          </div>

          {/* More Filters Toggle Button */}
          <button
            type="button"
            onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
            aria-expanded={isAdvancedOpen}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border font-semibold text-xs transition-all cursor-pointer ${
              isAdvancedOpen || advancedActiveCount > 0
                ? "bg-indigo-50 text-indigo-700 border-indigo-200/90 shadow-2xs"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50 hover:border-slate-300"
            }`}
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
              />
            </svg>
            <span>Filters</span>
            {advancedActiveCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-indigo-600 text-white font-mono text-[10px] flex items-center justify-center">
                {advancedActiveCount}
              </span>
            )}
            <span className="text-[10px] text-slate-400">
              {isAdvancedOpen ? "▲" : "▼"}
            </span>
          </button>
        </div>
      </div>

      {/* Advanced Filter Tray (Expandable) */}
      {isAdvancedOpen && (
        <div className="pt-3 pb-1 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 bg-slate-50/60 p-3.5 rounded-xl border">
          {/* Assignment Filter */}
          {onAssignmentFilterChange && (
            <div className="space-y-1">
              <label htmlFor="assignment-filter" className="block text-[11px] font-semibold text-slate-600">
                Assignment:
              </label>
              <select
                id="assignment-filter"
                value={assignmentFilter}
                onChange={(e) => onAssignmentFilterChange(e.target.value as AssignmentFilter)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 text-xs focus:border-indigo-500 focus:outline-none cursor-pointer"
              >
                <option value="ALL">All Issues</option>
                <option value="UNASSIGNED">Unassigned Only (Open)</option>
                <option value="ASSIGNED">Assigned Only</option>
              </select>
            </div>
          )}

          {/* Linked PR Filter */}
          {onPrFilterChange && (
            <div className="space-y-1">
              <label htmlFor="pr-filter" className="block text-[11px] font-semibold text-slate-600">
                Pull Request State:
              </label>
              <select
                id="pr-filter"
                value={prFilter}
                onChange={(e) => onPrFilterChange(e.target.value as PRFilter)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 text-xs focus:border-indigo-500 focus:outline-none cursor-pointer"
              >
                <option value="ALL">All PR States</option>
                <option value="NO_PR">No Open PR (Fresh Issue)</option>
                <option value="HAS_PR">Has Linked PR</option>
              </select>
            </div>
          )}

          {/* Minimum Match Score Filter */}
          {onMinScoreChange && (
            <div className="space-y-1">
              <label htmlFor="score-filter" className="block text-[11px] font-semibold text-slate-600">
                Min Match Score:
              </label>
              <select
                id="score-filter"
                value={minScore}
                onChange={(e) => onMinScoreChange(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 text-xs focus:border-indigo-500 focus:outline-none cursor-pointer"
              >
                <option value={0}>Any Score (0%+)</option>
                <option value={60}>≥ 60% (Fair Match)</option>
                <option value={75}>≥ 75% (Strong Match)</option>
                <option value={85}>≥ 85% (Top Match)</option>
              </select>
            </div>
          )}

          {/* Feedback Status Filter */}
          {onFeedbackFilterChange && (
            <div className="space-y-1">
              <label htmlFor="feedback-filter" className="block text-[11px] font-semibold text-slate-600">
                Candidate State:
              </label>
              <select
                id="feedback-filter"
                value={feedbackFilter}
                onChange={(e) => onFeedbackFilterChange(e.target.value as FeedbackFilter)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 text-xs focus:border-indigo-500 focus:outline-none cursor-pointer"
              >
                <option value="ALL">All States</option>
                <option value="UNREVIEWED">Unreviewed</option>
                <option value="INTERESTED">Saved (Interested)</option>
                <option value="STARTED">In Progress (Started)</option>
                <option value="PR_OPENED">PR Opened</option>
                <option value="MERGED">Merged</option>
              </select>
            </div>
          )}

          {/* Topic / Label Tag Filter */}
          {onTagChange && availableTags.length > 0 && (
            <div className="space-y-1 sm:col-span-2 lg:col-span-4 pt-1">
              <span className="block text-[11px] font-semibold text-slate-600 mb-1">
                Filter by Label:
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => onTagChange("ALL")}
                  className={`px-2 py-0.5 rounded-md text-[11px] font-mono border transition-all ${
                    selectedTag === "ALL"
                      ? "bg-indigo-600 text-white border-indigo-600 font-semibold"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"
                  }`}
                >
                  All Labels
                </button>
                {availableTags.slice(0, 8).map((tag) => (
                  <button
                    type="button"
                    key={tag}
                    onClick={() => onTagChange(selectedTag === tag ? "ALL" : tag)}
                    className={`px-2 py-0.5 rounded-md text-[11px] font-mono border transition-all ${
                      selectedTag === tag
                        ? "bg-indigo-600 text-white border-indigo-600 font-semibold"
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Second row: Count Readout, Checkbox & Reset */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2.5 border-t border-slate-100">
        <div className="flex items-center gap-4">
          <span className="font-mono text-slate-500">
            Showing <strong className="text-slate-900 font-semibold">{totalFiltered}</strong> of{" "}
            <strong>{totalFound}</strong> opportunities
          </span>

          <label htmlFor="hide-uncertain" className="flex items-center gap-1.5 cursor-pointer">
            <input
              id="hide-uncertain"
              type="checkbox"
              checked={hideUncertain}
              onChange={(e) => onHideUncertainChange(e.target.checked)}
              className="rounded border-slate-300 text-indigo-600 accent-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-slate-600 font-medium">Hide Uncertain</span>
          </label>
        </div>

        {isFiltered && (
          <button
            type="button"
            onClick={onResetFilters}
            className="text-indigo-600 hover:text-indigo-700 font-semibold underline transition-colors"
          >
            Reset Filters
          </button>
        )}
      </div>
    </div>
  );
}

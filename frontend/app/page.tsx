"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  FilterBar,
  type SortOption,
  type AssignmentFilter,
  type PRFilter,
  type FeedbackFilter,
} from "../src/components/filters/FilterBar";
import { Header } from "../src/components/header/Header";
import { OpportunityCard } from "../src/components/opportunities/OpportunityCard";
import { ProfileForm } from "../src/components/profile/ProfileForm";
import { Pagination } from "../src/components/shared/Pagination";
import {
  EmptyState,
  ErrorBanner,
  LoadingSkeletonList,
  RateLimitWarning,
} from "../src/components/shared/StateViews";
import { apiClient, ApiClientError } from "../src/lib/api-client";
import type {
  CandidateProfile,
  FeedbackStatus,
  Opportunity,
  SearchRequest,
} from "../src/types/opportunity";

export default function Home() {
  const [profile, setProfile] = useState<CandidateProfile>({
    languages: ["Python"],
    frameworks: ["FastAPI"],
    topics: ["good first issue"],
    experience: "INTERMEDIATE",
    hours_per_week: 10,
    max_setup_hours: 2.0,
  });

  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [lastSearchedAt, setLastSearchedAt] = useState<string | null>(null);
  const [scoringVersion, setScoringVersion] = useState<string | null>(null);
  const [rateLimitRemaining, setRateLimitRemaining] = useState<number | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Client Filter & Sort States
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("ALL");
  const [sortBy, setSortBy] = useState<SortOption>("composite");
  const [hideUncertain, setHideUncertain] = useState(false);
  const [assignmentFilter, setAssignmentFilter] = useState<AssignmentFilter>("ALL");
  const [prFilter, setPrFilter] = useState<PRFilter>("ALL");
  const [minScore, setMinScore] = useState<number>(0);
  const [feedbackFilter, setFeedbackFilter] = useState<FeedbackFilter>("ALL");
  const [selectedTag, setSelectedTag] = useState<string>("ALL");

  // Pagination States
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Race condition protection refs
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentSearchIdRef = useRef<number>(0);

  const executeSearch = useCallback(
    async (targetProfile: CandidateProfile, includeUncertain: boolean) => {
      // 1. Abort previous search if still in flight
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;
      const searchId = ++currentSearchIdRef.current;

      setIsLoading(true);
      setError(null);
      setHasSearched(true);
      setProfile(targetProfile);
      setCurrentPage(1);

      const request: SearchRequest = {
        profile: targetProfile,
        max_results: 50,
        include_uncertain: includeUncertain,
      };

      try {
        const response = await apiClient.searchOpportunities(
          request,
          controller.signal
        );

        // Ignore stale response if a newer search has already started
        if (searchId !== currentSearchIdRef.current) {
          return;
        }

        setOpportunities(response.opportunities);
        setLastSearchedAt(response.searched_at);
        setScoringVersion(response.scoring_config_version);
        if (response.rate_limit_remaining !== undefined) {
          setRateLimitRemaining(response.rate_limit_remaining);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // Ignored cancelled search
          return;
        }
        if (searchId !== currentSearchIdRef.current) {
          return;
        }

        if (err instanceof ApiClientError) {
          setError({
            message: err.message,
            requestId: err.requestId,
          });
        } else {
          setError({
            message: err instanceof Error ? err.message : "Unexpected search error",
          });
        }
      } finally {
        if (searchId === currentSearchIdRef.current) {
          setIsLoading(false);
        }
      }
    },
    []
  );

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  };

  // Run initial search once on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      void executeSearch(profile, true);
    }, 0);
    return () => {
      clearTimeout(timer);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle Feedback Submission with Optimistic UI & Rollback
  const handleFeedbackChange = async (issueKey: string, status: FeedbackStatus) => {
    const prevOpp = opportunities.find((o) => o.issue_key === issueKey);
    const prevFeedback = prevOpp ? prevOpp.feedback : null;

    // Optimistic update
    setOpportunities((prev) =>
      prev.map((o) => (o.issue_key === issueKey ? { ...o, feedback: status } : o))
    );

    try {
      await apiClient.submitFeedback(issueKey, status);
    } catch (err: unknown) {
      // Rollback on failure
      setOpportunities((prev) =>
        prev.map((o) =>
          o.issue_key === issueKey ? { ...o, feedback: prevFeedback } : o
        )
      );
      alert(
        `Failed to record feedback: ${
          err instanceof Error ? err.message : "Please try again."
        }`
      );
    }
  };

  // Handle Live Recheck before starting work
  const handleRecheck = async (owner: string, repo: string, number: number) => {
    const updated = await apiClient.getOpportunity(owner, repo, number);
    setOpportunities((prev) =>
      prev.map((o) => (o.issue_key === updated.issue_key ? updated : o))
    );
  };

  // Derive available languages from active opportunities
  const availableLanguages = useMemo(() => {
    const langs = new Set<string>();
    opportunities.forEach((o) => {
      if (o.language) langs.add(o.language);
    });
    return Array.from(langs).sort();
  }, [opportunities]);

  // Derive available topic labels from active opportunities
  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    opportunities.forEach((o) => {
      o.labels.forEach((l) => tags.add(l));
    });
    return Array.from(tags).sort();
  }, [opportunities]);

  // Client-side filtering & sorting
  const filteredOpportunities = useMemo(() => {
    let result = [...opportunities];

    // Hide uncertain filter
    if (hideUncertain) {
      result = result.filter((o) => o.eligibility !== "UNCERTAIN");
    }

    // Language filter
    if (selectedLanguage !== "ALL") {
      result = result.filter(
        (o) => o.language?.toLowerCase() === selectedLanguage.toLowerCase()
      );
    }

    // Assignment filter
    if (assignmentFilter === "UNASSIGNED") {
      result = result.filter((o) => o.is_assigned === false || o.is_assigned === null);
    } else if (assignmentFilter === "ASSIGNED") {
      result = result.filter((o) => o.is_assigned === true);
    }

    // Pull request status filter
    if (prFilter === "NO_PR") {
      result = result.filter((o) => o.has_linked_pr === false);
    } else if (prFilter === "HAS_PR") {
      result = result.filter((o) => o.has_linked_pr === true);
    }

    // Minimum match score filter
    if (minScore > 0) {
      result = result.filter((o) => Math.round(o.scores.composite_score * 100) >= minScore);
    }

    // Candidate feedback state filter
    if (feedbackFilter === "UNREVIEWED") {
      result = result.filter((o) => !o.feedback);
    } else if (feedbackFilter !== "ALL") {
      result = result.filter((o) => o.feedback === feedbackFilter);
    }

    // Topic label tag filter
    if (selectedTag !== "ALL") {
      result = result.filter((o) =>
        o.labels.some((l) => l.toLowerCase() === selectedTag.toLowerCase())
      );
    }

    // Search query filter (matches title, repo, labels)
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      result = result.filter((o) => {
        return (
          o.title.toLowerCase().includes(q) ||
          o.repository.toLowerCase().includes(q) ||
          o.labels.some((l) => l.toLowerCase().includes(q))
        );
      });
    }

    // Sorting
    result.sort((a, b) => {
      if (sortBy === "composite") {
        return b.scores.composite_score - a.scores.composite_score;
      }
      if (sortBy === "actionability") {
        return b.scores.actionability_score - a.scores.actionability_score;
      }
      if (sortBy === "fit") {
        return b.scores.fit_score - a.scores.fit_score;
      }
      if (sortBy === "freshness") {
        return (
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
      }
      return 0;
    });

    return result;
  }, [
    opportunities,
    hideUncertain,
    selectedLanguage,
    assignmentFilter,
    prFilter,
    minScore,
    feedbackFilter,
    selectedTag,
    searchQuery,
    sortBy,
  ]);

  // Pagination Calculations
  const totalPages = Math.max(1, Math.ceil(filteredOpportunities.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedOpportunities = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return filteredOpportunities.slice(start, start + pageSize);
  }, [filteredOpportunities, safeCurrentPage, pageSize]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleResetFilters = () => {
    setSearchQuery("");
    setSelectedLanguage("ALL");
    setSortBy("composite");
    setHideUncertain(false);
    setAssignmentFilter("ALL");
    setPrFilter("ALL");
    setMinScore(0);
    setFeedbackFilter("ALL");
    setSelectedTag("ALL");
    setCurrentPage(1);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--canvas)]">
      <Header rateLimitRemaining={rateLimitRemaining} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Profile Controls & Sidebar */}
          <section className="lg:col-span-4 lg:sticky lg:top-20 space-y-4" aria-label="Profile and preferences">
            <ProfileForm
              initialProfile={profile}
              isLoading={isLoading}
              onSearch={executeSearch}
              onCancel={handleCancel}
            />

            {/* Explanatory notes adhering to Section 4 & 6 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200/90 text-xs text-slate-600 space-y-2.5 shadow-[0_2px_12px_rgba(15,23,42,0.03)]">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-600" />
                <h3 className="font-bold text-slate-900">
                  Deterministic Heuristic Standards
                </h3>
              </div>
              <ul className="list-disc list-inside space-y-1.5 text-[11px] text-slate-500 pl-1 leading-relaxed">
                <li>Strictly 0% PR contamination</li>
                <li>100% evidence-supported match reasons</li>
                <li>Explicit warnings on potential claiming comments</li>
                <li>Offline snapshot replay with WAL-mode SQLite</li>
              </ul>
            </div>
          </section>

          {/* Right Column: Opportunities Feed, Filters, and Pagination */}
          <section className="lg:col-span-8 space-y-4" aria-label="Contribution opportunities">
            {/* Rate limit banner if low */}
            {rateLimitRemaining !== null && rateLimitRemaining < 15 && (
              <RateLimitWarning remaining={rateLimitRemaining} />
            )}

            {/* Filter and Sort Toolbar */}
            {opportunities.length > 0 && (
              <FilterBar
                searchQuery={searchQuery}
                onSearchQueryChange={(q) => {
                  setSearchQuery(q);
                  setCurrentPage(1);
                }}
                selectedLanguage={selectedLanguage}
                onLanguageChange={(l) => {
                  setSelectedLanguage(l);
                  setCurrentPage(1);
                }}
                availableLanguages={availableLanguages}
                sortBy={sortBy}
                onSortByChange={setSortBy}
                hideUncertain={hideUncertain}
                onHideUncertainChange={(h) => {
                  setHideUncertain(h);
                  setCurrentPage(1);
                }}
                totalFiltered={filteredOpportunities.length}
                totalFound={opportunities.length}
                onResetFilters={handleResetFilters}
                assignmentFilter={assignmentFilter}
                onAssignmentFilterChange={(a) => {
                  setAssignmentFilter(a);
                  setCurrentPage(1);
                }}
                prFilter={prFilter}
                onPrFilterChange={(pr) => {
                  setPrFilter(pr);
                  setCurrentPage(1);
                }}
                minScore={minScore}
                onMinScoreChange={(ms) => {
                  setMinScore(ms);
                  setCurrentPage(1);
                }}
                feedbackFilter={feedbackFilter}
                onFeedbackFilterChange={(fb) => {
                  setFeedbackFilter(fb);
                  setCurrentPage(1);
                }}
                selectedTag={selectedTag}
                onTagChange={(tg) => {
                  setSelectedTag(tg);
                  setCurrentPage(1);
                }}
                availableTags={availableTags}
              />
            )}

            {/* Results metadata bar */}
            {lastSearchedAt && (
              <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 px-1 font-mono">
                <span>
                  Refreshed: {new Date(lastSearchedAt).toLocaleTimeString()}
                </span>
                <span>
                  Ranking Engine: {scoringVersion || "v1.0.0"}
                </span>
              </div>
            )}

            {/* Error View */}
            {error && (
              <ErrorBanner
                message={error.message}
                requestId={error.requestId}
                onRetry={() => executeSearch(profile, true)}
              />
            )}

            {/* Loading Skeleton */}
            {isLoading && <LoadingSkeletonList />}

            {/* Empty States */}
            {!isLoading && hasSearched && filteredOpportunities.length === 0 && !error && (
              <EmptyState
                hasFilters={opportunities.length > 0}
                onResetFilters={handleResetFilters}
              />
            )}

            {/* Cards List with Pagination */}
            {!isLoading && filteredOpportunities.length > 0 && (
              <div className="space-y-4">
                {paginatedOpportunities.map((opp) => (
                  <OpportunityCard
                    key={opp.issue_key}
                    opportunity={opp}
                    onFeedbackChange={handleFeedbackChange}
                    onRecheck={handleRecheck}
                  />
                ))}

                {/* Proper Pagination Controls */}
                <Pagination
                  currentPage={safeCurrentPage}
                  totalPages={totalPages}
                  pageSize={pageSize}
                  totalItems={filteredOpportunities.length}
                  onPageChange={handlePageChange}
                  onPageSizeChange={(newSize) => {
                    setPageSize(newSize);
                    setCurrentPage(1);
                  }}
                />
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="border-t border-slate-100 bg-white py-4 px-6 text-center text-xs text-slate-500 mt-auto font-mono">
        <span>Open-Source Opportunity Finder • Deterministic Heuristic Evaluation • Local Offline Cache Enabled</span>
      </footer>
    </div>
  );
}

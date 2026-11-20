"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiClient } from "../../lib/api-client";
import type { HealthResponse } from "../../types/opportunity";

interface HeaderProps {
  rateLimitRemaining?: number | null;
}

export function Header({ rateLimitRemaining }: HeaderProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await apiClient.getHealth();
      setHealth(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchHealth();
    }, 0);
    // Poll health every 45s
    const interval = setInterval(() => {
      void fetchHealth();
    }, 45000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [fetchHealth]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await fetchHealth();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  // Calculate rate limit metrics
  const isAuthenticated = health?.github_api_configured ?? false;
  const limit = isAuthenticated ? 5000 : 60;
  const remaining =
    rateLimitRemaining !== undefined && rateLimitRemaining !== null
      ? rateLimitRemaining
      : (health?.rate_limit_remaining ?? limit);

  const percentage = Math.min(100, Math.max(0, Math.round((remaining / limit) * 100)));

  const barColor =
    percentage > 40
      ? "bg-emerald-500"
      : percentage > 15
      ? "bg-amber-500"
      : "bg-rose-500";

  return (
    <header className="sticky top-0 z-30 glass-nav border-b border-[var(--border)] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          {/* Brand & Identity */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-600 via-indigo-600 to-blue-600 flex items-center justify-center text-white shadow-sm ring-1 ring-indigo-700/20 shrink-0">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2.2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-slate-900">
                  Opportunity Finder
                </h1>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-indigo-50 text-indigo-700 border border-indigo-200/80 shadow-2xs">
                  v1.0.0 • Verified
                </span>
                <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-500">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Deterministic Engine
                </span>
              </div>
              <p className="text-xs text-slate-500 line-clamp-1">
                Verified open-source issue matches with 0% PR contamination and evidence-backed fit.
              </p>
            </div>
          </div>

          {/* Live Data & Quota HUD */}
          <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 text-xs">
            {/* Database Engine Status */}
            {health?.database_connected ? (
              <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80 text-slate-600 font-mono text-[11px] shadow-2xs">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
                </span>
                <span className="font-medium">DB: SQLite WAL</span>
              </div>
            ) : null}

            {/* GitHub Rate Limit Monitor Card */}
            {health ? (
              <div
                className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80 shadow-2xs"
                title={`GitHub API Quota: ${remaining} of ${limit} requests remaining.`}
              >
                <div className="flex flex-col">
                  <div className="flex items-center justify-between gap-3 text-[11px] font-mono">
                    <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                      <svg
                        className="w-3.5 h-3.5 text-slate-500"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          clipRule="evenodd"
                          d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                        />
                      </svg>
                      {isAuthenticated ? (
                        <span className="text-emerald-700 font-semibold">Auth Token</span>
                      ) : (
                        <span className="text-slate-600 font-medium">Public Quota</span>
                      )}
                    </span>
                    <span className="text-slate-600">
                      <strong className="text-slate-900 font-semibold">{remaining}</strong> / {limit} left
                    </span>
                  </div>

                  {/* Quota Progress Bar */}
                  <div className="w-36 sm:w-44 h-1.5 bg-slate-200/80 rounded-full overflow-hidden mt-1">
                    <div
                      className={`h-full ${barColor} transition-all duration-300`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>

                {/* Quota Refresh Button */}
                <button
                  type="button"
                  onClick={handleManualRefresh}
                  disabled={isRefreshing}
                  className="p-1.5 rounded-md hover:bg-slate-200/80 text-slate-500 hover:text-slate-800 transition-colors focus:outline-none"
                  title="Check latest status"
                  aria-label="Refresh status"
                >
                  <svg
                    className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-indigo-600" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </button>
              </div>
            ) : error ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 font-mono text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-600" />
                API Offline
              </span>
            ) : (
              <span className="text-slate-400 animate-pulse font-mono text-xs">
                Connecting to backend...
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

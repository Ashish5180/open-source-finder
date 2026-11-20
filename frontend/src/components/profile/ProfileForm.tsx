"use client";

import React, { useState } from "react";
import type { CandidateProfile, ExperienceLevel } from "../../types/opportunity";
import { TagChip } from "../shared/Badges";

interface ProfileFormProps {
  initialProfile?: CandidateProfile;
  isLoading: boolean;
  onSearch: (profile: CandidateProfile, includeUncertain: boolean) => void;
  onCancel?: () => void;
}

const COMMON_LANGUAGES = [
  "Python",
  "TypeScript",
  "JavaScript",
  "Go",
  "Rust",
  "Java",
  "C++",
];

const COMMON_FRAMEWORKS = [
  "FastAPI",
  "React",
  "Next.js",
  "Django",
  "Node.js",
  "Gin",
  "Vue",
];

const COMMON_TOPICS = [
  "good first issue",
  "help wanted",
  "bug",
  "documentation",
  "enhancement",
];

export function ProfileForm({
  initialProfile,
  isLoading,
  onSearch,
  onCancel,
}: ProfileFormProps) {
  const [languages, setLanguages] = useState<string[]>(
    initialProfile?.languages || ["Python"]
  );
  const [frameworks, setFrameworks] = useState<string[]>(
    initialProfile?.frameworks || ["FastAPI"]
  );
  const [topics, setTopics] = useState<string[]>(
    initialProfile?.topics || ["good first issue"]
  );
  const [experience, setExperience] = useState<ExperienceLevel>(
    initialProfile?.experience || "INTERMEDIATE"
  );
  const [hoursPerWeek, setHoursPerWeek] = useState<number>(
    initialProfile?.hours_per_week || 10
  );
  const [maxSetupHours, setMaxSetupHours] = useState<number>(
    initialProfile?.max_setup_hours || 2.0
  );
  const [includeUncertain, setIncludeUncertain] = useState<boolean>(true);

  // Custom text input states
  const [langInput, setLangInput] = useState("");
  const [frameworkInput, setFrameworkInput] = useState("");
  const [topicInput, setTopicInput] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleAddLanguage = (lang: string) => {
    const trimmed = lang.trim();
    if (trimmed && !languages.map((l) => l.toLowerCase()).includes(trimmed.toLowerCase())) {
      setLanguages([...languages, trimmed]);
      setLangInput("");
      setErrorMsg(null);
    }
  };

  const handleRemoveLanguage = (lang: string) => {
    setLanguages(languages.filter((l) => l !== lang));
  };

  const handleAddFramework = (fw: string) => {
    const trimmed = fw.trim();
    if (trimmed && !frameworks.map((f) => f.toLowerCase()).includes(trimmed.toLowerCase())) {
      setFrameworks([...frameworks, trimmed]);
      setFrameworkInput("");
    }
  };

  const handleRemoveFramework = (fw: string) => {
    setFrameworks(frameworks.filter((f) => f !== fw));
  };

  const handleAddTopic = (tp: string) => {
    const trimmed = tp.trim();
    if (trimmed && !topics.map((t) => t.toLowerCase()).includes(trimmed.toLowerCase())) {
      setTopics([...topics, trimmed]);
      setTopicInput("");
    }
  };

  const handleRemoveTopic = (tp: string) => {
    setTopics(topics.filter((t) => t !== tp));
  };

  const triggerSubmit = () => {
    if (languages.length === 0) {
      setErrorMsg("Please select or add at least one programming language.");
      return;
    }
    setErrorMsg(null);

    const profile: CandidateProfile = {
      languages,
      frameworks,
      topics,
      experience,
      hours_per_week: Number(hoursPerWeek),
      max_setup_hours: Number(maxSetupHours),
    };

    onSearch(profile, includeUncertain);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    triggerSubmit();
  };

  // Support Cmd+Enter / Ctrl+Enter shortcut from anywhere in the form
  const handleFormKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      triggerSubmit();
    }
  };

  const handleResetToDefault = () => {
    setLanguages(["Python"]);
    setFrameworks(["FastAPI"]);
    setTopics(["good first issue"]);
    setExperience("INTERMEDIATE");
    setHoursPerWeek(10);
    setMaxSetupHours(2.0);
    setIncludeUncertain(true);
    setErrorMsg(null);
  };

  const activeFilterCount =
    languages.length + frameworks.length + topics.length + (includeUncertain ? 1 : 0);

  return (
    <div
      onKeyDown={handleFormKeyDown}
      className="bg-white border border-slate-200/90 rounded-2xl shadow-[0_4px_24px_rgba(15,23,42,0.04)] flex flex-col max-h-[calc(100vh-6rem)] overflow-hidden transition-all"
    >
      {/* Sidebar Header (Fixed / Non-scrolling top) */}
      <div className="p-4 sm:p-5 border-b border-slate-100 bg-white shrink-0 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2.2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                />
              </svg>
            </div>
            <h2 className="text-sm font-bold tracking-tight text-slate-900">
              Candidate Profile
            </h2>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Calibrate issues matching your stack and availability.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Refined Active Filters Pill */}
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50/90 text-indigo-700 border border-indigo-200/70 shadow-2xs font-sans">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
            {activeFilterCount} Active
          </span>
          <button
            type="button"
            onClick={handleResetToDefault}
            className="text-xs font-medium text-slate-400 hover:text-indigo-600 transition-colors flex items-center gap-1"
            title="Reset filters to standard defaults"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="hidden sm:inline">Reset</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div
          role="alert"
          className="mx-4 mt-3 p-3 rounded-xl text-xs bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-2 shrink-0"
        >
          <svg className="w-4 h-4 shrink-0 text-rose-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <span className="font-medium">{errorMsg}</span>
        </div>
      )}

      {/* Sidebar Scrollable Body */}
      <form onSubmit={handleSubmit} className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 sm:p-5 space-y-5">
          {/* Section: Languages */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label
                htmlFor="lang-input"
                className="block text-xs font-semibold text-slate-900"
              >
                Languages <span className="text-rose-500">*</span>
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                {languages.length} selected
              </span>
            </div>

            {/* Active Chips Container */}
            <div className="flex flex-wrap gap-1.5 min-h-[34px] p-2 bg-slate-50/80 rounded-xl border border-slate-200/70">
              {languages.length === 0 ? (
                <span className="text-xs text-slate-400 italic px-1 self-center">
                  Select at least one language below...
                </span>
              ) : (
                languages.map((lang) => (
                  <TagChip
                    key={lang}
                    text={lang}
                    onRemove={() => handleRemoveLanguage(lang)}
                  />
                ))
              )}
            </div>

            {/* Custom Language Input */}
            <div className="flex gap-2">
              <input
                id="lang-input"
                type="text"
                value={langInput}
                onChange={(e) => setLangInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddLanguage(langInput);
                  }
                }}
                placeholder="Add language (e.g. Rust, Go)..."
                className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => handleAddLanguage(langInput)}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-800 transition-colors shrink-0"
              >
                Add
              </button>
            </div>

            {/* Language Presets Pills */}
            <div className="space-y-1.5 pt-0.5">
              <span className="text-[11px] font-medium text-slate-400 block">Popular languages:</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {COMMON_LANGUAGES.map((preset) => {
                  const active = languages
                    .map((l) => l.toLowerCase())
                    .includes(preset.toLowerCase());
                  return (
                    <button
                      type="button"
                      key={preset}
                      onClick={() =>
                        active
                          ? handleRemoveLanguage(preset)
                          : handleAddLanguage(preset)
                      }
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                        active
                          ? "bg-indigo-600 text-white border-indigo-600 shadow-2xs font-semibold"
                          : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-300"
                      }`}
                    >
                      {active ? (
                        <svg className="w-3 h-3 text-white inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3 text-slate-400 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                        </svg>
                      )}
                      <span>{preset}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="h-px bg-slate-100" />

          {/* Section: Frameworks & Ecosystem */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label
                htmlFor="fw-input"
                className="block text-xs font-semibold text-slate-900"
              >
                Frameworks & Libraries
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                {frameworks.length} added
              </span>
            </div>

            <div className="flex flex-wrap gap-1.5 min-h-[34px] p-2 bg-slate-50/80 rounded-xl border border-slate-200/70">
              {frameworks.length === 0 ? (
                <span className="text-xs text-slate-400 italic px-1 self-center">
                  Optional (e.g. FastAPI, React)...
                </span>
              ) : (
                frameworks.map((fw) => (
                  <TagChip
                    key={fw}
                    text={fw}
                    onRemove={() => handleRemoveFramework(fw)}
                  />
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                id="fw-input"
                type="text"
                value={frameworkInput}
                onChange={(e) => setFrameworkInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddFramework(frameworkInput);
                  }
                }}
                placeholder="Add framework (e.g. PyTorch, Svelte)..."
                className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => handleAddFramework(frameworkInput)}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-800 transition-colors shrink-0"
              >
                Add
              </button>
            </div>

            <div className="space-y-1.5 pt-0.5">
              <span className="text-[11px] font-medium text-slate-400 block">Popular frameworks:</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {COMMON_FRAMEWORKS.map((preset) => {
                  const active = frameworks
                    .map((f) => f.toLowerCase())
                    .includes(preset.toLowerCase());
                  return (
                    <button
                      type="button"
                      key={preset}
                      onClick={() =>
                        active
                          ? handleRemoveFramework(preset)
                          : handleAddFramework(preset)
                      }
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                        active
                          ? "bg-sky-600 text-white border-sky-600 shadow-2xs font-semibold"
                          : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-300"
                      }`}
                    >
                      {active ? (
                        <svg className="w-3 h-3 text-white inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3 text-slate-400 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                        </svg>
                      )}
                      <span>{preset}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="h-px bg-slate-100" />

          {/* Section: Topics & Desired Labels */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label
                htmlFor="topic-input"
                className="block text-xs font-semibold text-slate-900"
              >
                Topics & Desired Labels
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                {topics.length} added
              </span>
            </div>

            <div className="flex flex-wrap gap-1.5 min-h-[34px] p-2 bg-slate-50/80 rounded-xl border border-slate-200/70">
              {topics.length === 0 ? (
                <span className="text-xs text-slate-400 italic px-1 self-center">
                  Optional issue labels...
                </span>
              ) : (
                topics.map((tp) => (
                  <TagChip
                    key={tp}
                    text={tp}
                    onRemove={() => handleRemoveTopic(tp)}
                  />
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                id="topic-input"
                type="text"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddTopic(topicInput);
                  }
                }}
                placeholder="Add topic (e.g. cli, parser, bug)..."
                className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => handleAddTopic(topicInput)}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-800 transition-colors shrink-0"
              >
                Add
              </button>
            </div>

            <div className="space-y-1.5 pt-0.5">
              <span className="text-[11px] font-medium text-slate-400 block">Common labels:</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {COMMON_TOPICS.map((preset) => {
                  const active = topics
                    .map((t) => t.toLowerCase())
                    .includes(preset.toLowerCase());
                  return (
                    <button
                      type="button"
                      key={preset}
                      onClick={() =>
                        active ? handleRemoveTopic(preset) : handleAddTopic(preset)
                      }
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                        active
                          ? "bg-slate-800 text-white border-slate-800 shadow-2xs font-semibold"
                          : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-300"
                      }`}
                    >
                      {active ? (
                        <svg className="w-3 h-3 text-white inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3 text-slate-400 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                        </svg>
                      )}
                      <span>{preset}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="h-px bg-slate-100" />

          {/* Section: Experience Level Cards */}
          <div className="space-y-2.5">
            <label className="block text-xs font-semibold text-slate-900">
              Experience Level
            </label>
            <div className="grid grid-cols-1 gap-2">
              {(
                [
                  {
                    id: "BEGINNER",
                    label: "Beginner",
                    desc: "Good first issues, documentation, starter bugs with clear repro.",
                  },
                  {
                    id: "INTERMEDIATE",
                    label: "Intermediate",
                    desc: "Feature enhancements, multi-file bugfixes, unit test additions.",
                  },
                  {
                    id: "ADVANCED",
                    label: "Advanced",
                    desc: "Architecture refactoring, concurrency, deep performance work.",
                  },
                ] as const
              ).map((opt) => {
                const selected = experience === opt.id;
                return (
                  <label
                    key={opt.id}
                    className={`relative flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                      selected
                        ? "bg-indigo-50/60 border-indigo-600 ring-1 ring-indigo-600 shadow-2xs"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60"
                    }`}
                  >
                    <input
                      type="radio"
                      name="experience"
                      value={opt.id}
                      checked={selected}
                      onChange={() => setExperience(opt.id)}
                      className="mt-0.5 text-indigo-600 accent-indigo-600 focus:ring-indigo-500 shrink-0"
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-slate-900">
                          {opt.label}
                        </span>
                        {selected && (
                          <span className="text-[11px] font-mono text-indigo-600 font-semibold">
                            Active
                          </span>
                        )}
                      </div>
                      <span className="block mt-0.5 text-[11px] text-slate-500 leading-normal">
                        {opt.desc}
                      </span>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="h-px bg-slate-100" />

          {/* Section: Bandwidth & Setup Constraints */}
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label
                  htmlFor="hours-input"
                  className="text-xs font-semibold text-slate-900"
                >
                  Available Bandwidth
                </label>
                <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-md bg-indigo-50 border border-indigo-200/80 text-indigo-700">
                  {hoursPerWeek} hrs/week
                </span>
              </div>
              <input
                id="hours-input"
                type="range"
                min="1"
                max="40"
                step="1"
                value={hoursPerWeek}
                onChange={(e) => setHoursPerWeek(Number(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer h-1.5 bg-slate-200 rounded-lg"
              />
              <span className="block mt-1 text-[11px] text-slate-400">
                Calibrates issue complexity and expected completion time.
              </span>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label
                  htmlFor="setup-input"
                  className="text-xs font-semibold text-slate-900"
                >
                  Max Dev Setup Time
                </label>
                <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-md bg-indigo-50 border border-indigo-200/80 text-indigo-700">
                  ≤ {maxSetupHours} hrs
                </span>
              </div>
              <input
                id="setup-input"
                type="range"
                min="0.5"
                max="8"
                step="0.5"
                value={maxSetupHours}
                onChange={(e) => setMaxSetupHours(Number(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer h-1.5 bg-slate-200 rounded-lg"
              />
              <span className="block mt-1 text-[11px] text-slate-400">
                Filters out repos with prohibitive onboarding or tooling friction.
              </span>
            </div>
          </div>

          <div className="h-px bg-slate-100" />

          {/* Section: Quality Filter (Include Uncertain) */}
          <div className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80">
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={includeUncertain}
                onChange={(e) => setIncludeUncertain(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-indigo-600 accent-indigo-600 focus:ring-indigo-500 shrink-0"
              />
              <div>
                <span className="block text-xs font-semibold text-slate-900">
                  Include Potential Claims (Uncertain)
                </span>
                <span className="block text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                  Shows issues containing comments like &ldquo;can I take this?&rdquo; with explicit caution badges.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Sticky Action Footer: Accessible Search Button Dock */}
        <div className="sticky bottom-0 bg-white/95 backdrop-blur-md border-t border-slate-100 p-4 shadow-[0_-4px_16px_rgba(15,23,42,0.04)] shrink-0 flex items-center gap-2.5">
          <button
            type="submit"
            disabled={isLoading}
            className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 via-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2"
          >
            {isLoading ? (
              <>
                <svg
                  className="animate-spin h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z"
                  />
                </svg>
                <span>Searching Opportunities...</span>
              </>
            ) : (
              <>
                <svg
                  className="w-4 h-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                <span>Find Opportunities</span>
                <kbd className="hidden sm:inline-block ml-1 px-1.5 py-0.5 text-[10px] font-mono bg-white/20 text-white rounded">
                  ⌘↵
                </kbd>
              </>
            )}
          </button>

          {isLoading && onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-3 rounded-xl text-xs font-semibold border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors shrink-0"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

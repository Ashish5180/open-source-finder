/**
 * Canonical types mirroring backend Pydantic models.
 * Ensures complete type safety across API boundaries.
 */

export type ExperienceLevel = "BEGINNER" | "INTERMEDIATE" | "ADVANCED";

export type Eligibility = "ELIGIBLE" | "EXCLUDED" | "UNCERTAIN";

export type ExclusionReason =
  | "CLOSED"
  | "NOT_AN_ISSUE"
  | "LOCKED"
  | "DUPLICATE"
  | "WONTFIX"
  | "ASSIGNED"
  | "HAS_LINKED_PR"
  | "INACCESSIBLE";

export type FeedbackStatus =
  | "INTERESTED"
  | "STARTED"
  | "PR_OPENED"
  | "MERGED"
  | "NOT_SUITABLE"
  | "NOT_ACTIONABLE";

export interface CandidateProfile {
  languages: string[];
  frameworks: string[];
  topics: string[];
  experience: ExperienceLevel;
  hours_per_week: number;
  max_setup_hours: number;
}

export interface ScoreBreakdown {
  fit_score: number;
  actionability_score: number;
  health_score: number | null;
  freshness_score: number;
  composite_score: number;
}

export interface Opportunity {
  issue_key: string;
  github_issue_id: number;
  url: string;
  title: string;
  repository: string;
  labels: string[];
  language: string | null;
  state: string;
  is_assigned: boolean | null;
  has_linked_pr: boolean | null;
  created_at: string;
  updated_at: string;
  observed_at: string;
  scores: ScoreBreakdown;
  eligibility: Eligibility;
  exclusion_reason: ExclusionReason | null;
  reasons: string[];
  uncertainties: string[];
  scoring_config_version: string;
  feedback: FeedbackStatus | null;
}

export interface SearchRequest {
  profile: CandidateProfile;
  max_results?: number;
  include_uncertain?: boolean;
}

export interface SearchResponse {
  opportunities: Opportunity[];
  total_found: number;
  total_eligible: number;
  scoring_config_version: string;
  searched_at: string;
  is_cached?: boolean;
  rate_limit_remaining?: number | null;
  warnings?: string[];
}

export interface FeedbackRequest {
  status: FeedbackStatus;
  note?: string;
}

export interface FeedbackResponse {
  success: boolean;
  issue_key: string;
  status: FeedbackStatus;
  recorded_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  database_connected: boolean;
  github_api_configured: boolean;
  rate_limit_remaining?: number | null;
}

export interface ApiError {
  code: string;
  message: string;
  request_id?: string;
  details?: Record<string, unknown>;
}

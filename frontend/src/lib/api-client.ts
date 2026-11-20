import type {
  ApiError,
  FeedbackRequest,
  FeedbackResponse,
  FeedbackStatus,
  HealthResponse,
  Opportunity,
  SearchRequest,
  SearchResponse,
} from "../types/opportunity";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiClientError extends Error {
  code: string;
  requestId?: string;
  details?: Record<string, unknown>;

  constructor(error: ApiError, public status: number) {
    super(error.message);
    this.name = "ApiClientError";
    this.code = error.code;
    this.requestId = error.request_id;
    this.details = error.details;
  }
}

/**
 * Perform a typed HTTP request with structured error handling.
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const requestId = `req_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", requestId);
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errPayload: ApiError;
      try {
        errPayload = (await res.json()) as ApiError;
      } catch {
        errPayload = {
          code: "HTTP_ERROR",
          message: `Request failed with status ${res.status}: ${res.statusText}`,
          request_id: requestId,
        };
      }
      throw new ApiClientError(errPayload, res.status);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiClientError(
      {
        code: "NETWORK_ERROR",
        message: err instanceof Error ? err.message : "Network error occurred",
        request_id: requestId,
      },
      0
    );
  }
}

export const apiClient = {
  /**
   * Search for open-source contribution opportunities given a candidate profile.
   */
  async searchOpportunities(
    searchRequest: SearchRequest,
    signal?: AbortSignal
  ): Promise<SearchResponse> {
    return request<SearchResponse>("/api/opportunities/search", {
      method: "POST",
      body: JSON.stringify(searchRequest),
      signal,
    });
  },

  /**
   * Submit candidate feedback for a ranked opportunity.
   */
  async submitFeedback(
    issueKey: string,
    status: FeedbackStatus,
    note?: string
  ): Promise<FeedbackResponse> {
    const body: FeedbackRequest = { status, note };
    return request<FeedbackResponse>(
      `/api/opportunities/${encodeURIComponent(issueKey)}/feedback`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    );
  },

  /**
   * Fetch live/refreshed state for an individual opportunity.
   */
  async getOpportunity(
    owner: string,
    repo: string,
    number: number
  ): Promise<Opportunity> {
    return request<Opportunity>(
      `/api/opportunities/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/${number}`,
      { method: "GET" }
    );
  },

  /**
   * Fetch health and rate budget status.
   */
  async getHealth(signal?: AbortSignal): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health", {
      method: "GET",
      signal,
    });
  },
};

/**
 * Type-safe API client using openapi-fetch and openapi-react-query
 *
 * Usage:
 * - $api.useQuery("get", "/api/endpoint") for queries in components
 * - $api.useMutation("post", "/api/endpoint") for mutations in components
 * - apiClient.GET/POST/etc for imperative usage outside React
 *
 * Legacy axios client is preserved for backward compatibility during migration.
 */

import axios, { type InternalAxiosRequestConfig } from "axios";
import createClient from "openapi-fetch";
import createQueryClient from "openapi-react-query";
import type { paths, components } from "./v1";
import { parseApiError, ApiError, RateLimitError } from "./api-error";
import { isTokenExpired } from "./jwt";

// =============================================================================
// Token Refresh State Management
// =============================================================================

interface RefreshState {
  isRefreshing: boolean;
  pendingRequests: Array<{
    resolve: (value: InternalAxiosRequestConfig | PromiseLike<InternalAxiosRequestConfig>) => void;
    reject: (error: unknown) => void;
    config: InternalAxiosRequestConfig;
  }>;
}

const refreshState: RefreshState = {
  isRefreshing: false,
  pendingRequests: [],
};

// Lock for openapi-fetch requests
let openapiRefreshPromise: Promise<string | null> | null = null;

function processPendingRequests(newAccessToken: string) {
  refreshState.pendingRequests.forEach(({ resolve, config }) => {
    config.headers.Authorization = `Bearer ${newAccessToken}`;
    resolve(api(config));
  });
  refreshState.pendingRequests = [];
}

function rejectPendingRequests(error: unknown) {
  refreshState.pendingRequests.forEach(({ reject }) => reject(error));
  refreshState.pendingRequests = [];
}

// =============================================================================
// Token Refresh Function
// =============================================================================

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  // Use raw axios to avoid interceptor loops
  const response = await axios.post(
    `${import.meta.env.VITE_API_URL || ""}/auth/refresh`,
    { refresh_token: refreshToken }
  );

  const { access_token, refresh_token: newRefreshToken } = response.data;

  // Update localStorage with new tokens
  localStorage.setItem("access_token", access_token);
  if (newRefreshToken) {
    localStorage.setItem("refresh_token", newRefreshToken);
  }

  return access_token;
}

// Export for use by WebSocket service
export { refreshAccessToken };

function clearAuthAndRedirect() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");

  // Update Zustand store if available
  import("@/stores/auth.store").then(({ useAuthStore }) => {
    useAuthStore.getState().logout();
  }).catch(() => {
    // Store not available, ignore
  });

  // Redirect to login if not already there
  if (!window.location.pathname.includes("/login")) {
    window.location.href = "/login";
  }
}

// =============================================================================
// Legacy Axios Client (preserved for backward compatibility)
// =============================================================================

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

// Request Interceptor - Add auth token and proactive refresh
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      return config;
    }

    config.headers.Authorization = `Bearer ${token}`;

    // Skip proactive refresh for the refresh endpoint itself
    if (config.url?.includes("/auth/refresh")) {
      return config;
    }

    // Check if token is expiring soon (5 minute buffer)
    if (isTokenExpired(token, 300)) {
      // If a refresh is already in progress, queue this request
      if (refreshState.isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshState.pendingRequests.push({ resolve, reject, config });
        });
      }

      // Start refresh process
      refreshState.isRefreshing = true;
      try {
        const newToken = await refreshAccessToken();
        config.headers.Authorization = `Bearer ${newToken}`;
        processPendingRequests(newToken);
        return config;
      } catch {
        rejectPendingRequests(new Error("Refresh failed"));
        // Don't log out here - let response interceptor handle it
        return config;
      } finally {
        refreshState.isRefreshing = false;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor - Handle auth errors with refresh and org 404s
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 404 errors for organization endpoints - only redirect for org-level 404s, not sub-resources
    if (error.response?.status === 404 && originalRequest.url?.includes("/api/organizations/")) {
      const orgIdMatch = originalRequest.url.match(/\/api\/organizations\/([a-f0-9-]+)/);
      if (orgIdMatch) {
        const orgId = orgIdMatch[1];

        // Only redirect if this is the org endpoint itself (not a sub-resource like passwords, documents, etc.)
        // This prevents 404s from deleted resources from redirecting to /global
        const isDirectOrgEndpoint = originalRequest.url === `/api/organizations/${orgId}`;

        if (isDirectOrgEndpoint) {
          // Clear current org from store and redirect to global
          import("@/stores/organization.store").then(({ useOrganizationStore }) => {
            useOrganizationStore.getState().clearCurrentOrg();
          }).catch(() => {
            // Store not available, ignore
          });

          // Show toast notification
          import("sonner").then(({ toast }) => {
            toast.error("Organization not found or no longer accessible");
          }).catch(() => {
            // Toast not available, ignore
          });

          // Redirect to global view if not already there
          if (!window.location.pathname.startsWith("/global")) {
            window.location.href = "/global";
          }
        }
      }
    }

    // Handle 401 errors with token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      // If this is the refresh endpoint itself, fail immediately
      if (originalRequest.url?.includes("/auth/refresh")) {
        clearAuthAndRedirect();
        return Promise.reject(error);
      }

      // If a refresh is already in progress, queue this request
      if (refreshState.isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshState.pendingRequests.push({ resolve, reject, config: originalRequest });
        });
      }

      // Mark as retrying to prevent infinite loops
      originalRequest._retry = true;
      refreshState.isRefreshing = true;

      try {
        // Attempt to refresh the token
        const newToken = await refreshAccessToken();

        // Update original request with new token
        originalRequest.headers.Authorization = `Bearer ${newToken}`;

        // Process any queued requests with new token
        processPendingRequests(newToken);

        // Retry original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear auth and redirect
        rejectPendingRequests(refreshError);
        clearAuthAndRedirect();
        return Promise.reject(refreshError);
      } finally {
        refreshState.isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;

// =============================================================================
// OpenAPI Fetch Client (new type-safe client)
// =============================================================================

// Endpoints that should skip token refresh check
const AUTH_ENDPOINTS = [
  "/auth/login",
  "/auth/refresh",
  "/auth/oauth/callback",
  "/auth/mfa/login",
  "/auth/mfa/setup",
  "/auth/setup/status",
];

/**
 * Ensure we have a valid (non-expiring) access token before making a request
 * Proactively refreshes token before it expires
 * Returns the token or null if no auth
 */
async function ensureValidToken(): Promise<string | null> {
  const token = localStorage.getItem("access_token");

  // No token at all - return null (let request proceed without auth)
  if (!token) return null;

  // Token is still valid - return it
  if (!isTokenExpired(token, 300)) return token;

  // Token is expiring soon - refresh it
  // Use lock to prevent concurrent refresh attempts
  if (openapiRefreshPromise) {
    return openapiRefreshPromise;
  }

  openapiRefreshPromise = (async () => {
    try {
      return await refreshAccessToken();
    } catch {
      return null;
    } finally {
      openapiRefreshPromise = null;
    }
  })();

  return openapiRefreshPromise;
}

// Create base openapi-fetch client
const baseClient = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL || "",
});

// Add middleware for auth and error handling
baseClient.use({
  async onRequest({ request }) {
    const url = new URL(request.url, window.location.origin);
    const isAuthEndpoint = AUTH_ENDPOINTS.some((ep) => url.pathname.startsWith(ep));

    // Skip token refresh for auth endpoints to avoid infinite loops
    if (!isAuthEndpoint) {
      const token = await ensureValidToken();
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
    } else {
      // For auth endpoints, just use current token if available
      const token = localStorage.getItem("access_token");
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
    }

    return request;
  },
  async onResponse({ request, response }) {
    // Handle 429 Too Many Requests - rate limited
    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get("Retry-After") || "60", 10);
      throw new RateLimitError(retryAfter);
    }

    // Handle 401 Unauthorized - attempt token refresh and retry
    if (response.status === 401) {
      const url = request.url;
      if (!AUTH_ENDPOINTS.some((ep) => url.includes(ep))) {
        // Try to refresh and retry
        try {
          const newToken = await refreshAccessToken();
          // Clone request and retry with new token
          const retryRequest = request.clone();
          retryRequest.headers.set("Authorization", `Bearer ${newToken}`);
          return fetch(retryRequest);
        } catch {
          // Refresh failed - redirect to login
          clearAuthAndRedirect();
        }
      } else {
        // Auth endpoint 401 - redirect to login
        clearAuthAndRedirect();
      }
    }

    // Handle org 404s
    if (response.status === 404 && request.url.includes("/api/organizations/")) {
      const orgIdMatch = request.url.match(/\/api\/organizations\/([a-f0-9-]+)/);
      if (orgIdMatch) {
        const orgId = orgIdMatch[1];
        const isDirectOrgEndpoint = request.url.endsWith(`/api/organizations/${orgId}`) ||
          request.url.endsWith(`/api/organizations/${orgId}/`);

        if (isDirectOrgEndpoint) {
          import("@/stores/organization.store").then(({ useOrganizationStore }) => {
            useOrganizationStore.getState().clearCurrentOrg();
          }).catch(() => { /* ignore */ });

          import("sonner").then(({ toast }) => {
            toast.error("Organization not found or no longer accessible");
          }).catch(() => { /* ignore */ });

          if (!window.location.pathname.startsWith("/global")) {
            window.location.href = "/global";
          }
        }
      }
    }

    return response;
  },
});

/**
 * Type-safe API client using openapi-fetch
 * Use for imperative calls outside React components
 */
export const apiClient = baseClient;

/**
 * Type-safe React Query hooks from OpenAPI spec
 * Use in React components for automatic caching, refetching, and loading states
 *
 * @example
 * // Query
 * const { data, isLoading } = $api.useQuery("get", "/api/organizations");
 *
 * // Query with parameters
 * const { data } = $api.useQuery("get", "/api/organizations/{org_id}", {
 *   params: { path: { org_id: "123" } }
 * });
 *
 * // Mutation
 * const mutation = $api.useMutation("post", "/api/organizations");
 * mutation.mutate({ body: { name: "New Org" } });
 */
export const $api = createQueryClient(baseClient);

/**
 * Helper to handle openapi-fetch errors
 * Converts the error object to an ApiError with proper message extraction
 */
export function handleApiError(error: unknown): never {
  throw parseApiError(error);
}

// Re-export error classes and helpers for convenience
export { ApiError, RateLimitError, parseApiError };
export { getErrorMessage } from "./api-error";

// =============================================================================
// Re-export types from OpenAPI spec for convenience
// =============================================================================

export type User = components["schemas"]["UserResponse"];
export type Organization = components["schemas"]["OrganizationPublic"];
export type UserRole = components["schemas"]["UserRole"];

// =============================================================================
// Legacy API Objects (preserved for backward compatibility during migration)
// =============================================================================

// Auth API (no /api prefix - auth is at root level)
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  mfa_required?: boolean;
  mfa_setup_required?: boolean;
  mfa_token?: string;
  available_methods?: string[];
  expires_in?: number;
}

// OAuth types
export interface OAuthProviderInfo {
  name: string;
  display_name: string;
}

export interface OAuthProvidersResponse {
  providers: OAuthProviderInfo[];
}

export interface OAuthInitResponse {
  authorization_url: string;
  state: string;
}

export interface OAuthCallbackRequest {
  code: string;
  state: string;
  provider: string;
}

// Setup types
export interface SetupStatusResponse {
  needs_setup: boolean;
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>("/auth/login", data),

  register: (data: RegisterRequest) =>
    api.post<User>("/auth/register", data),

  logout: () => api.post("/auth/logout"),

  me: () => api.get<User>("/auth/me"),

  refreshToken: (refreshToken: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }),

  // Setup endpoints (for first-time platform configuration)
  setupStatus: () => api.get<SetupStatusResponse>("/auth/setup/status"),

  // OAuth endpoints
  getOAuthProviders: () =>
    api.get<OAuthProvidersResponse>("/auth/oauth/providers"),

  initOAuth: (provider: string, redirectUri: string) =>
    api.get<OAuthInitResponse>(
      `/auth/oauth/init/${provider}?redirect_uri=${encodeURIComponent(redirectUri)}`
    ),

  oauthCallback: (data: OAuthCallbackRequest) =>
    api.post<LoginResponse>("/auth/oauth/callback", data),
};

// Organizations API
export const organizationsApi = {
  list: (config?: { params?: Record<string, boolean> }) => api.get<Organization[]>("/api/organizations", config),

  get: (id: string, config?: { params?: Record<string, string> }) => api.get<Organization>(`/api/organizations/${id}`, config),

  create: (data: { name: string }) =>
    api.post<Organization>("/api/organizations", data),

  update: (id: string, data: { name?: string; is_enabled?: boolean; metadata?: Record<string, unknown> }) =>
    api.put<Organization>(`/api/organizations/${id}`, data),

  delete: (id: string) => api.delete(`/api/organizations/${id}`),
};

// API Keys types
export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
}

export interface CreateApiKeyRequest {
  name: string;
  expires_at?: string;
}

export interface CreateApiKeyResponse {
  id: string;
  name: string;
  key: string; // Full key, only returned once on creation
  key_prefix: string;
  created_at: string;
  expires_at: string | null;
}

// API Keys API
export const apiKeysApi = {
  list: () => api.get<ApiKey[]>("/api/api-keys"),

  create: (data: CreateApiKeyRequest) =>
    api.post<CreateApiKeyResponse>("/api/api-keys", data),

  delete: (id: string) => api.delete(`/api/api-keys/${id}`),
};

// Password change types
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// MFA types
export interface MfaSetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export interface MfaVerifyRequest {
  code: string;
}

// Passkey types
export interface Passkey {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
}

// Settings/Security API (auth endpoints at root level)
export const settingsApi = {
  changePassword: (data: ChangePasswordRequest) =>
    api.post("/auth/change-password", data),

  // MFA endpoints
  setupMfa: () => api.post<MfaSetupResponse>("/auth/mfa/setup"),

  enableMfa: (data: MfaVerifyRequest) =>
    api.post("/auth/mfa/enable", data),

  disableMfa: (data: MfaVerifyRequest) =>
    api.post("/auth/mfa/disable", data),

  getMfaStatus: () =>
    api.get<{ enabled: boolean; backup_codes_remaining: number }>("/auth/mfa/status"),

  regenerateBackupCodes: () =>
    api.post<{ backup_codes: string[] }>("/auth/mfa/backup-codes"),

  // Passkey endpoints
  listPasskeys: () => api.get<Passkey[]>("/auth/passkeys"),

  registerPasskeyOptions: () =>
    api.post<PublicKeyCredentialCreationOptions>("/auth/passkeys/register/options", {}),

  registerPasskey: (data: { name: string; credential: unknown }) =>
    api.post<Passkey>("/auth/passkeys/register", data),

  deletePasskey: (id: string) => api.delete(`/auth/passkeys/${id}`),
};

// Admin types
export interface OrganizationUser {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateUserRequest {
  email: string;
  role?: string;
}

export interface CreateUserResponse {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
}

export interface AdminConfig {
  openai_api_key_set: boolean;
  embedding_model: string;
}

// Reindex types
export type EntityType = "password" | "configuration" | "location" | "document" | "custom_asset";

export interface ReindexStartResponse {
  message: string;
  job_id: string;
}

export interface ReindexStatusResponse {
  is_running: boolean;
  status: string | null;
  current_entity_type: string | null;
  processed: number;
  total: number;
  errors: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface ReindexCancelResponse {
  message: string;
  status: "cancelling" | "cancelled";
  processed: number;
  total: number;
}

export interface IndexStatsResponse {
  total_indexed: number;
  total_entities: number;
  total_unindexed: number;
  last_indexed_at: string | null;
}

// Admin API
export const adminApi = {
  getConfig: () => api.get<AdminConfig>("/api/admin/config"),

  updateConfig: (data: Partial<{ openai_api_key: string; embedding_model: string }>) =>
    api.patch<AdminConfig>("/api/admin/config", data),

  testOpenAiConnection: () =>
    api.post<{ success: boolean; error?: string }>("/api/admin/test-openai"),

  listUsers: () => api.get<OrganizationUser[]>("/api/admin/users"),

  createUser: (data: CreateUserRequest) =>
    api.post<CreateUserResponse>("/api/admin/users/create", data),

  removeUser: (userId: string) => api.delete(`/api/admin/users/${userId}`),

  updateUserRole: (userId: string, role: string) =>
    api.patch(`/api/admin/users/${userId}`, { role }),

  transferOwnership: (userId: string) =>
    api.post(`/api/admin/transfer-ownership`, { user_id: userId }),

  // Reindex endpoints
  startReindex: (params?: { entity_type?: EntityType; organization_id?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.entity_type) searchParams.set("entity_type", params.entity_type);
    if (params?.organization_id) searchParams.set("organization_id", params.organization_id);
    const query = searchParams.toString();
    return api.post<ReindexStartResponse>(`/api/admin/reindex${query ? `?${query}` : ""}`);
  },

  getReindexStatus: () => api.get<ReindexStatusResponse>("/api/admin/reindex/status"),

  cancelReindex: (force: boolean = false) =>
    api.post<ReindexCancelResponse>(`/api/admin/reindex/cancel?force=${force}`),

  getIndexStats: () => api.get<IndexStatsResponse>("/api/admin/index/stats"),
};

// AI Settings types
// AI Settings Types (multi-provider support)
export type LLMProvider = "openai" | "anthropic" | "openai_compatible";

export interface CompletionsConfig {
  provider: LLMProvider;
  api_key_set: boolean;
  model: string;
  endpoint: string | null;
}

export interface EmbeddingsConfig {
  api_key_set: boolean;
  model: string;
}

export interface IndexingConfig {
  enabled: boolean;
}

export interface AISettings {
  completions: CompletionsConfig | null;
  embeddings: EmbeddingsConfig | null;
  indexing: IndexingConfig | null;
}

export interface CompletionsConfigUpdate {
  provider?: LLMProvider;
  api_key?: string;
  model?: string;
  endpoint?: string;
  max_tokens?: number;
  temperature?: number;
}

export interface EmbeddingsConfigUpdate {
  api_key?: string;
  model?: string;
}

export interface IndexingConfigUpdate {
  enabled: boolean;
}

export interface ModelInfo {
  id: string;
  display_name: string;
}

export interface OpenAIModel {
  id: string;
  name: string;
  description: string;
}

export interface AITestRequest {
  provider?: LLMProvider;
  api_key: string;
  endpoint?: string;
}

export interface AIConnectionTestResponse {
  success: boolean;
  message: string;
  completions_models?: OpenAIModel[];
  embedding_models?: OpenAIModel[];
  models?: ModelInfo[];
  error?: string;
}

// Export types
export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Export {
  id: string;
  user_id: string;
  organization_ids: string[] | null;
  status: ExportStatus;
  s3_key: string | null;
  file_size_bytes: number | null;
  expires_at: string;
  revoked_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateExportRequest {
  organization_ids?: string[];
  expires_in_days?: number;
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_in_seconds: number;
}

export interface RevokeExportResponse {
  revoked: boolean;
  revoked_at: string;
}

// Exports API
export const exportsApi = {
  list: (limit?: number, offset?: number) => {
    const params = new URLSearchParams();
    if (limit !== undefined) params.set("limit", String(limit));
    if (offset !== undefined) params.set("offset", String(offset));
    const query = params.toString();
    return api.get<Export[]>(`/api/exports${query ? `?${query}` : ""}`);
  },

  get: (id: string) => api.get<Export>(`/api/exports/${id}`),

  create: (data: CreateExportRequest) =>
    api.post<Export>("/api/exports", data),

  getDownloadUrl: (id: string) =>
    api.get<DownloadUrlResponse>(`/api/exports/${id}/download`),

  revoke: (id: string) =>
    api.delete<RevokeExportResponse>(`/api/exports/${id}`),
};

// AI Settings API
export const aiSettingsApi = {
  get: () => api.get<AISettings>("/api/settings/ai"),

  updateCompletions: (data: CompletionsConfigUpdate) =>
    api.put<CompletionsConfig>("/api/settings/ai/completions", data),

  updateEmbeddings: (data: EmbeddingsConfigUpdate) =>
    api.put<EmbeddingsConfig>("/api/settings/ai/embeddings", data),

  getIndexingConfig: async (): Promise<IndexingConfig> => {
    const response = await api.get<IndexingConfig>("/api/settings/ai/indexing");
    return response.data;
  },

  updateIndexingConfig: async (data: IndexingConfigUpdate): Promise<IndexingConfig> => {
    const response = await api.put<IndexingConfig>("/api/settings/ai/indexing", data);
    return response.data;
  },

  testConnection: (data: AITestRequest) =>
    api.post<AIConnectionTestResponse>("/api/settings/ai/test", data),
};

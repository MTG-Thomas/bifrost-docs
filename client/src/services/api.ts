// API services re-export from api-client
// This file provides a central location for API service imports

export {
  organizationsApi,
  configurationsApi,
  passwordsApi,
  documentsApi,
  locationsApi,
  customAssetsApi,
  authApi,
  apiKeysApi,
  aiSettingsApi,
  auditLogsApi,
  relationshipsApi,
  attachmentsApi,
  exportsApi,
  favoritesApi,
  globalViewApi,
  indexingApi,
  notificationsApi,
  preferencesApi,
  userApi,
  usersApi,
  webSocketService,
  $api,
  apiClient,
} from "@/lib/api-client";

// Re-export types
export type {
  User,
  Organization,
  UserRole,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  LoginResponse,
  OAuthProviderInfo,
  OAuthProvidersResponse,
  OAuthInitResponse,
  OAuthCallbackRequest,
  SetupStatusResponse,
  ApiKey,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
} from "@/lib/api-client";

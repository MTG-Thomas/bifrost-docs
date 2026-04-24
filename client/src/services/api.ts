// API services
// Provides API client objects for direct API calls (outside of React Query hooks)

import api from "@/lib/api-client";

// Re-export existing APIs from api-client
export {
  authApi,
  organizationsApi,
  apiKeysApi,
  settingsApi,
  adminApi,
  exportsApi,
  aiSettingsApi,
} from "@/lib/api-client";

// Configurations API
type ListConfig = {
  params?: {
    limit?: number;
    offset?: number;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
  };
};

export const configurationsApi = {
  list: (config?: ListConfig) =>
    api.get("/api/organizations/{org_id}/configurations", config),
  get: (orgId: string, id: string) =>
    api.get(`/api/organizations/${orgId}/configurations/${id}`),
  create: (orgId: string, data: unknown) =>
    api.post(`/api/organizations/${orgId}/configurations`, data),
  update: (orgId: string, id: string, data: unknown) =>
    api.put(`/api/organizations/${orgId}/configurations/${id}`, data),
  delete: (orgId: string, id: string) =>
    api.delete(`/api/organizations/${orgId}/configurations/${id}`),
};

// Passwords API
export const passwordsApi = {
  list: (config?: ListConfig) =>
    api.get("/api/organizations/{org_id}/passwords", config),
  get: (orgId: string, id: string) =>
    api.get(`/api/organizations/${orgId}/passwords/${id}`),
  create: (orgId: string, data: unknown) =>
    api.post(`/api/organizations/${orgId}/passwords`, data),
  update: (orgId: string, id: string, data: unknown) =>
    api.put(`/api/organizations/${orgId}/passwords/${id}`, data),
  delete: (orgId: string, id: string) =>
    api.delete(`/api/organizations/${orgId}/passwords/${id}`),
};

// Documents API
export const documentsApi = {
  list: (config?: ListConfig) =>
    api.get("/api/organizations/{org_id}/documents", config),
  get: (orgId: string, id: string) =>
    api.get(`/api/organizations/${orgId}/documents/${id}`),
  create: (orgId: string, data: unknown) =>
    api.post(`/api/organizations/${orgId}/documents`, data),
  update: (orgId: string, id: string, data: unknown) =>
    api.put(`/api/organizations/${orgId}/documents/${id}`, data),
  delete: (orgId: string, id: string) =>
    api.delete(`/api/organizations/${orgId}/documents/${id}`),
};

// Locations API
export const locationsApi = {
  list: (config?: ListConfig) =>
    api.get("/api/organizations/{org_id}/locations", config),
  get: (orgId: string, id: string) =>
    api.get(`/api/organizations/${orgId}/locations/${id}`),
  create: (orgId: string, data: unknown) =>
    api.post(`/api/organizations/${orgId}/locations`, data),
  update: (orgId: string, id: string, data: unknown) =>
    api.put(`/api/organizations/${orgId}/locations/${id}`, data),
  delete: (orgId: string, id: string) =>
    api.delete(`/api/organizations/${orgId}/locations/${id}`),
};

// Custom Assets API
export const customAssetsApi = {
  list: (orgId: string, typeId: string, config?: ListConfig) =>
    api.get(`/api/organizations/${orgId}/custom-asset-types/${typeId}/assets`, config),
  get: (orgId: string, typeId: string, id: string) =>
    api.get(`/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${id}`),
  create: (orgId: string, typeId: string, data: unknown) =>
    api.post(`/api/organizations/${orgId}/custom-asset-types/${typeId}/assets`, data),
  update: (orgId: string, typeId: string, id: string, data: unknown) =>
    api.put(`/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${id}`, data),
  delete: (orgId: string, typeId: string, id: string) =>
    api.delete(`/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${id}`),
};

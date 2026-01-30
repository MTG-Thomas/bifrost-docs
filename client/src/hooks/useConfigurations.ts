/**
 * React Query hooks for configurations management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type ConfigurationType = components["schemas"]["ConfigurationTypePublic"];
export type ConfigurationStatus = components["schemas"]["ConfigurationStatusPublic"];
export type Configuration = components["schemas"]["ConfigurationPublic"];
export type ConfigurationCreate = components["schemas"]["ConfigurationCreate"];
export type ConfigurationUpdate = components["schemas"]["ConfigurationUpdate"];

// API response types
type ConfigurationListResponse = components["schemas"]["ConfigurationListResponse"];
type ConfigurationTypeCreate = components["schemas"]["ConfigurationTypeCreate"];
type ConfigurationStatusCreate = components["schemas"]["ConfigurationStatusCreate"];

// =============================================================================
// Pagination Types (client-side utilities)
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

// =============================================================================
// Configuration Types Hooks (Global - not org-scoped)
// =============================================================================

export function useConfigurationTypes(options?: { includeInactive?: boolean }) {
  return useQuery({
    queryKey: ["configuration-types", options?.includeInactive],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.includeInactive) {
        params.set("include_inactive", "true");
      }
      const response = await api.get<ConfigurationType[]>(
        `/api/configuration-types${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
  });
}

export function useCreateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConfigurationTypeCreate) => {
      const response = await api.post<ConfigurationType>(
        "/api/configuration-types",
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useUpdateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: { name: string } }) => {
      const response = await api.put<ConfigurationType>(
        `/api/configuration-types/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeleteConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/configuration-types/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeactivateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationType>(
        `/api/configuration-types/${id}/deactivate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useActivateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationType>(
        `/api/configuration-types/${id}/activate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

// =============================================================================
// Configuration Statuses Hooks (Global - not org-scoped)
// =============================================================================

export function useConfigurationStatuses(options?: { includeInactive?: boolean }) {
  return useQuery({
    queryKey: ["configuration-statuses", options?.includeInactive],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.includeInactive) {
        params.set("include_inactive", "true");
      }
      const response = await api.get<ConfigurationStatus[]>(
        `/api/configuration-statuses${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
  });
}

export function useCreateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConfigurationStatusCreate) => {
      const response = await api.post<ConfigurationStatus>(
        "/api/configuration-statuses",
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useUpdateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: { name: string } }) => {
      const response = await api.put<ConfigurationStatus>(
        `/api/configuration-statuses/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useDeleteConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/configuration-statuses/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useDeactivateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationStatus>(
        `/api/configuration-statuses/${id}/deactivate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useActivateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationStatus>(
        `/api/configuration-statuses/${id}/activate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

// =============================================================================
// Configurations Hooks
// =============================================================================

export function useConfigurations(
  orgId: string,
  options?: {
    typeId?: string;
    statusId?: string;
    pagination?: PaginationParams;
    search?: string;
    showDisabled?: boolean;
  }
) {
  return useQuery({
    queryKey: ["configurations", orgId, options],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.typeId) {
        params.set("configuration_type_id", options.typeId);
      }
      if (options?.statusId) {
        params.set("configuration_status_id", options.statusId);
      }
      if (options?.pagination?.limit !== undefined) {
        params.set("limit", String(options.pagination.limit));
      }
      if (options?.pagination?.offset !== undefined) {
        params.set("offset", String(options.pagination.offset));
      }
      if (options?.search) {
        params.set("search", options.search);
      }
      if (options?.showDisabled) {
        params.set("show_disabled", "true");
      }
      const response = await api.get<ConfigurationListResponse>(
        `/api/organizations/${orgId}/configurations${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: (prev) => prev,
  });
}

export function useConfiguration(orgId: string, id: string) {
  return useQuery({
    queryKey: ["configuration", orgId, id],
    queryFn: async () => {
      const response = await api.get<Configuration>(
        `/api/organizations/${orgId}/configurations/${id}`
      );
      return response.data;
    },
    enabled: !!orgId && !!id,
  });
}

export function useCreateConfiguration(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConfigurationCreate) => {
      const response = await api.post<Configuration>(
        `/api/organizations/${orgId}/configurations`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });
    },
  });
}

export function useUpdateConfiguration(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConfigurationUpdate) => {
      const response = await api.put<Configuration>(
        `/api/organizations/${orgId}/configurations/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });
      queryClient.invalidateQueries({ queryKey: ["configuration", orgId, id] });
    },
  });
}

export function useDeleteConfiguration(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (configId: string) => {
      await api.delete(`/api/organizations/${orgId}/configurations/${configId}`);
      return configId;
    },
    onSuccess: (configId) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      onDeleted?.(configId);

      // Remove detail query from cache
      queryClient.removeQueries({
        queryKey: ["configuration", orgId, configId],
      });

      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });

      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchToggleConfigurations(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ids,
      is_enabled,
      isEnabled,
    }: {
      ids: string[];
      is_enabled?: boolean;
      isEnabled?: boolean;
    }) => {
      const enabled = is_enabled ?? isEnabled;
      const response = await api.patch(
        `/api/organizations/${orgId}/configurations/batch`,
        { ids, is_enabled: enabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });
    },
  });
}

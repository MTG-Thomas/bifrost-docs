/**
 * React Query hooks for global view data (cross-organization)
 */

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type GlobalPassword = components["schemas"]["GlobalPasswordPublic"];
export type GlobalConfiguration = components["schemas"]["GlobalConfigurationPublic"];
export type GlobalLocation = components["schemas"]["GlobalLocationPublic"];
export type GlobalDocument = components["schemas"]["GlobalDocumentPublic"];
export type GlobalCustomAsset = components["schemas"]["GlobalCustomAssetPublic"];
export type GlobalSidebarItemCount = components["schemas"]["GlobalSidebarItemCount"];
export type GlobalSidebarData = components["schemas"]["GlobalSidebarData"];

// API response types
type GlobalPasswordListResponse = components["schemas"]["GlobalPasswordListResponse"];
type GlobalConfigurationListResponse = components["schemas"]["GlobalConfigurationListResponse"];
type GlobalLocationListResponse = components["schemas"]["GlobalLocationListResponse"];
type GlobalDocumentListResponse = components["schemas"]["GlobalDocumentListResponse"];
type GlobalCustomAssetListResponse = components["schemas"]["GlobalCustomAssetListResponse"];

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
// Global Passwords Hook
// =============================================================================

export function useGlobalPasswords(pagination?: PaginationParams) {
  return useQuery({
    queryKey: ["global", "passwords", pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (pagination?.limit !== undefined) params.limit = pagination.limit;
      if (pagination?.offset !== undefined) params.offset = pagination.offset;

      const response = await api.get<GlobalPasswordListResponse>(
        `/api/global/passwords`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Configurations Hook
// =============================================================================

export function useGlobalConfigurations(options?: {
  typeId?: string;
  statusId?: string;
  pagination?: PaginationParams;
}) {
  return useQuery({
    queryKey: ["global", "configurations", options],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.typeId) params.configuration_type_id = options.typeId;
      if (options?.statusId) params.configuration_status_id = options.statusId;
      if (options?.pagination?.limit !== undefined)
        params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined)
        params.offset = options.pagination.offset;

      const response = await api.get<GlobalConfigurationListResponse>(
        `/api/global/configurations`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Locations Hook
// =============================================================================

export function useGlobalLocations(pagination?: PaginationParams) {
  return useQuery({
    queryKey: ["global", "locations", pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (pagination?.limit !== undefined) params.limit = pagination.limit;
      if (pagination?.offset !== undefined) params.offset = pagination.offset;

      const response = await api.get<GlobalLocationListResponse>(
        `/api/global/locations`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Documents Hook
// =============================================================================

export function useGlobalDocuments(options?: {
  path?: string;
  pagination?: PaginationParams;
}) {
  return useQuery({
    queryKey: ["global", "documents", options?.path, options?.pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.path !== undefined) params.path = options.path;
      if (options?.pagination?.limit !== undefined)
        params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined)
        params.offset = options.pagination.offset;

      const response = await api.get<GlobalDocumentListResponse>(
        `/api/global/documents`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Custom Assets Hook
// =============================================================================

export function useGlobalCustomAssets(
  typeId: string,
  pagination?: PaginationParams
) {
  return useQuery({
    queryKey: ["global", "custom-assets", typeId, pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        type_id: typeId,
      };
      if (pagination?.limit !== undefined) params.limit = pagination.limit;
      if (pagination?.offset !== undefined) params.offset = pagination.offset;

      const response = await api.get<GlobalCustomAssetListResponse>(
        `/api/global/custom-assets`,
        { params }
      );
      return response.data;
    },
    enabled: !!typeId,
  });
}

// =============================================================================
// Global Sidebar Data Hook
// =============================================================================

export function useGlobalSidebarData() {
  return useQuery({
    queryKey: ["global", "sidebar"],
    queryFn: async () => {
      const response = await api.get<GlobalSidebarData>(`/api/global/sidebar`);
      return response.data;
    },
    // Sidebar data doesn't change frequently, so we can cache it longer
    staleTime: 30 * 1000, // 30 seconds
    // Refetch when window regains focus (to catch changes from other tabs)
    refetchOnWindowFocus: true,
  });
}

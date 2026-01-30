/**
 * React Query hooks for locations management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type Location = components["schemas"]["LocationPublic"];
export type LocationCreate = components["schemas"]["LocationCreate"];
export type LocationUpdate = components["schemas"]["LocationUpdate"];

// API response types
type LocationListResponse = components["schemas"]["LocationListResponse"];

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

export interface LocationsParams {
  pagination?: PaginationParams;
  search?: string;
  showDisabled?: boolean;
}

// =============================================================================
// Hooks
// =============================================================================

export function useLocations(orgId: string, options?: LocationsParams) {
  return useQuery({
    queryKey: ["locations", orgId, options],
    queryFn: async () => {
      const params = new URLSearchParams();
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
      const response = await api.get<LocationListResponse>(
        `/api/organizations/${orgId}/locations${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: (prev) => prev,
  });
}

export function useLocation(orgId: string, id: string) {
  return useQuery({
    queryKey: ["location", orgId, id],
    queryFn: async () => {
      const response = await api.get<Location>(
        `/api/organizations/${orgId}/locations/${id}`
      );
      return response.data;
    },
    enabled: !!orgId && !!id,
  });
}

export function useCreateLocation(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LocationCreate) => {
      const response = await api.post<Location>(
        `/api/organizations/${orgId}/locations`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
    },
  });
}

export function useUpdateLocation(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LocationUpdate) => {
      const response = await api.put<Location>(
        `/api/organizations/${orgId}/locations/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
      queryClient.invalidateQueries({ queryKey: ["location", orgId, id] });
    },
  });
}

export function useDeleteLocation(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (locationId: string) => {
      await api.delete(`/api/organizations/${orgId}/locations/${locationId}`);
      return locationId;
    },
    onSuccess: (locationId) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      onDeleted?.(locationId);

      // Remove detail query from cache
      queryClient.removeQueries({
        queryKey: ["location", orgId, locationId],
      });

      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });

      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchToggleLocations(orgId: string) {
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
        `/api/organizations/${orgId}/locations/batch/toggle`,
        { ids, is_enabled: enabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
    },
  });
}

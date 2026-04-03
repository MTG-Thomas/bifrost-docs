/**
 * React Query hooks for passwords management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type Password = components["schemas"]["PasswordPublic"];
export type PasswordReveal = components["schemas"]["PasswordReveal"];
export type PasswordCreate = components["schemas"]["PasswordCreate"];
export type PasswordUpdate = components["schemas"]["PasswordUpdate"];

// API response types
type PasswordListResponse = components["schemas"]["PasswordListResponse"];

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

export interface PasswordsParams {
  pagination?: PaginationParams;
  search?: string;
  showDisabled?: boolean;
  hasTotp?: boolean;
}

// =============================================================================
// Hooks
// =============================================================================

export function usePasswords(orgId: string, options?: PasswordsParams) {
  return useQuery({
    queryKey: ["passwords", orgId, options],
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
      if (options?.hasTotp !== undefined) {
        params.set("has_totp", String(options.hasTotp));
      }
      const response = await api.get<PasswordListResponse>(
        `/api/organizations/${orgId}/passwords${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: (prev) => prev,
  });
}

export function usePassword(orgId: string, id: string) {
  return useQuery({
    queryKey: ["password", orgId, id],
    queryFn: async () => {
      const response = await api.get<Password>(
        `/api/organizations/${orgId}/passwords/${id}`
      );
      return response.data;
    },
    enabled: !!orgId && !!id,
  });
}

export function useRevealPassword(orgId: string, id: string) {
  return useQuery({
    queryKey: ["password-reveal", orgId, id],
    queryFn: async () => {
      const response = await api.get<PasswordReveal>(
        `/api/organizations/${orgId}/passwords/${id}/reveal`
      );
      return response.data;
    },
    enabled: false, // Only fetch when explicitly requested
  });
}

export function useCreatePassword(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PasswordCreate) => {
      const response = await api.post<Password>(
        `/api/organizations/${orgId}/passwords`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });
    },
  });
}

export function useUpdatePassword(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PasswordUpdate) => {
      const response = await api.put<Password>(
        `/api/organizations/${orgId}/passwords/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });
      queryClient.invalidateQueries({ queryKey: ["password", orgId, id] });
    },
  });
}

export function useDeletePassword(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (passwordId: string) => {
      await api.delete(`/api/organizations/${orgId}/passwords/${passwordId}`);
      return passwordId;
    },
    onSuccess: (passwordId) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      onDeleted?.(passwordId);

      // Remove detail query from cache
      queryClient.removeQueries({
        queryKey: ["password", orgId, passwordId],
      });

      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });

      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchTogglePasswords(orgId: string) {
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
        `/api/organizations/${orgId}/passwords/batch`,
        { ids, is_enabled: enabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });
    },
  });
}

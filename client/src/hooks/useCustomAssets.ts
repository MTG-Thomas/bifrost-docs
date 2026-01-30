/**
 * React Query hooks for custom asset types and instances
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type FieldDefinition = components["schemas"]["FieldDefinition"];
export type FieldType = FieldDefinition["type"];
export type CustomAssetType = components["schemas"]["CustomAssetTypePublic"];
export type CustomAssetTypeCreate = components["schemas"]["CustomAssetTypeCreate"];
export type CustomAssetTypeUpdate = components["schemas"]["CustomAssetTypeUpdate"];
export type CustomAsset = components["schemas"]["CustomAssetPublic"];
export type CustomAssetReveal = components["schemas"]["CustomAssetReveal"];
export type CustomAssetCreate = components["schemas"]["CustomAssetCreate"];
export type CustomAssetUpdate = components["schemas"]["CustomAssetUpdate"];

// API response types
type CustomAssetListResponse = components["schemas"]["CustomAssetListResponse"];

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

export interface CustomAssetsParams {
  pagination?: PaginationParams;
  search?: string;
  showDisabled?: boolean;
}

// =============================================================================
// Custom Asset Type Hooks (Global - not org-scoped)
// =============================================================================

export function useCustomAssetTypes(options?: { includeInactive?: boolean }) {
  return useQuery({
    queryKey: ["custom-asset-types", options?.includeInactive],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.includeInactive) {
        params.set("include_inactive", "true");
      }
      const response = await api.get<CustomAssetType[]>(
        `/api/custom-asset-types${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
  });
}

export function useCustomAssetType(typeId: string) {
  return useQuery({
    queryKey: ["custom-asset-type", typeId],
    queryFn: async () => {
      const response = await api.get<CustomAssetType>(
        `/api/custom-asset-types/${typeId}`
      );
      return response.data;
    },
    enabled: !!typeId,
  });
}

export function useCreateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomAssetTypeCreate) => {
      const response = await api.post<CustomAssetType>(
        "/api/custom-asset-types",
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useUpdateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      typeId,
      id,
      data,
    }: {
      typeId?: string;
      id?: string;
      data: CustomAssetTypeUpdate;
    }) => {
      const actualId = typeId ?? id;
      if (!actualId) throw new Error("typeId or id is required");
      const response = await api.put<CustomAssetType>(
        `/api/custom-asset-types/${actualId}`,
        data
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      const actualId = variables.typeId ?? variables.id;
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({
        queryKey: ["custom-asset-type", actualId],
      });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeleteCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (typeId: string) => {
      await api.delete(`/api/custom-asset-types/${typeId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeactivateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (typeId: string) => {
      const response = await api.post<CustomAssetType>(
        `/api/custom-asset-types/${typeId}/deactivate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useActivateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (typeId: string) => {
      const response = await api.post<CustomAssetType>(
        `/api/custom-asset-types/${typeId}/activate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useReorderCustomAssetTypes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: string[]) => {
      const response = await api.patch<CustomAssetType[]>(
        "/api/custom-asset-types/reorder",
        { ids }
      );
      return response.data;
    },
    onMutate: async (newOrder) => {
      await queryClient.cancelQueries({ queryKey: ["custom-asset-types"] });
      await queryClient.cancelQueries({ queryKey: ["sidebar"] });

      const previousTypes = queryClient.getQueryData<CustomAssetType[]>([
        "custom-asset-types",
      ]);

      queryClient.setQueryData<CustomAssetType[]>(
        ["custom-asset-types"],
        (old) => {
          if (!old) return old;
          return newOrder.map((id) => old.find((t) => t.id === id)!).filter(Boolean);
        }
      );

      return { previousTypes };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousTypes) {
        queryClient.setQueryData(["custom-asset-types"], context.previousTypes);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

// =============================================================================
// Custom Asset Instance Hooks
// =============================================================================

export function useCustomAssets(
  orgId: string,
  typeId: string,
  options?: CustomAssetsParams
) {
  return useQuery({
    queryKey: ["custom-assets", orgId, typeId, options],
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
      const response = await api.get<CustomAssetListResponse>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets${params.toString() ? `?${params}` : ""}`
      );
      return response.data;
    },
    enabled: !!orgId && !!typeId,
    placeholderData: (prev) => prev,
  });
}

export function useCustomAsset(orgId: string, typeId: string, assetId: string) {
  return useQuery({
    queryKey: ["custom-asset", orgId, typeId, assetId],
    queryFn: async () => {
      const response = await api.get<CustomAsset>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}`
      );
      return response.data;
    },
    enabled: !!orgId && !!typeId && !!assetId,
  });
}

/**
 * Fetch revealed custom asset secrets.
 * Returns a function to fetch secrets on demand - no caching.
 * Secrets should never be cached in React Query.
 */
export function fetchCustomAssetSecrets(
  orgId: string,
  typeId: string,
  assetId: string
): Promise<CustomAssetReveal> {
  return api
    .get<CustomAssetReveal>(
      `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}/reveal`
    )
    .then((response) => response.data);
}

export function useCreateCustomAsset(orgId: string, typeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomAssetCreate) => {
      const response = await api.post<CustomAsset>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });
    },
  });
}

export function useUpdateCustomAsset(
  orgId: string,
  typeId: string,
  assetId: string
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomAssetUpdate) => {
      const response = await api.put<CustomAsset>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });
      queryClient.invalidateQueries({
        queryKey: ["custom-asset", orgId, typeId, assetId],
      });
    },
  });
}

export function useDeleteCustomAsset(
  orgId: string,
  typeId: string,
  onDeleted?: (id: string) => void
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assetId: string) => {
      await api.delete(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}`
      );
      return assetId;
    },
    onSuccess: (assetId) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      onDeleted?.(assetId);

      // Remove detail query from cache
      queryClient.removeQueries({
        queryKey: ["custom-asset", orgId, typeId, assetId],
      });

      // Invalidate list queries
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });

      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchToggleCustomAssets(orgId: string, typeId: string) {
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
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/batch/toggle`,
        { ids, is_enabled: enabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });
    },
  });
}

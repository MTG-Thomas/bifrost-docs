/**
 * React Query hooks for documents management
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type Document = components["schemas"]["DocumentPublic"];
export type DocumentCreate = components["schemas"]["DocumentCreate"];
export type DocumentUpdate = components["schemas"]["DocumentUpdate"];
export type FolderCount = components["schemas"]["FolderCount"];
export type FolderList = components["schemas"]["FolderList"];
export type BatchPathUpdateRequest = components["schemas"]["BatchPathUpdateRequest"];
export type BatchPathUpdateResponse = components["schemas"]["BatchPathUpdateResponse"];
export type CleanDocumentResponse = components["schemas"]["CleanDocumentResponse"];

// API response types
type DocumentListResponse = components["schemas"]["DocumentListResponse"];

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
// Hooks
// =============================================================================

export function useDocuments(
  orgId: string,
  options?: {
    path?: string;
    pagination?: PaginationParams;
    search?: string;
    showDisabled?: boolean;
  }
) {
  return useQuery({
    queryKey: ["documents", orgId, options],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {};
      if (options?.path !== undefined) params.path = options.path;
      if (options?.pagination?.limit !== undefined) params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined) params.offset = options.pagination.offset;
      if (options?.search) params.search = options.search;
      if (options?.showDisabled !== undefined) params.show_disabled = options.showDisabled;

      const response = await api.get<DocumentListResponse>(
        `/api/organizations/${orgId}/documents`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: keepPreviousData,
  });
}

export function useFolders(orgId: string) {
  return useQuery({
    queryKey: ["documents", "folders", orgId],
    queryFn: async () => {
      const response = await api.get<FolderList>(
        `/api/organizations/${orgId}/documents/folders`
      );
      return response.data;
    },
    enabled: !!orgId,
  });
}

export function useDocument(
  orgId: string,
  id: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: ["documents", orgId, "detail", id],
    queryFn: async () => {
      const response = await api.get<Document>(
        `/api/organizations/${orgId}/documents/${id}`
      );
      return response.data;
    },
    enabled: (options?.enabled ?? true) && !!orgId && !!id,
  });
}

export function useCreateDocument(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentCreate) => {
      const response = await api.post<Document>(
        `/api/organizations/${orgId}/documents`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useUpdateDocument(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentUpdate) => {
      const response = await api.put<Document>(
        `/api/organizations/${orgId}/documents/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useDeleteDocument(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/organizations/${orgId}/documents/${id}`);
      return id;
    },
    onSuccess: (_data, id) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      // This prevents the detail page query from refetching a deleted resource
      onDeleted?.(id);

      // Remove detail query from cache
      queryClient.removeQueries({ queryKey: ["documents", orgId, "detail", id] });
      // Invalidate ONLY list queries (3rd element is NOT "detail"), not detail queries
      queryClient.invalidateQueries({
        predicate: (query) => {
          const key = query.queryKey;
          return (
            key[0] === "documents" &&
            key[1] === orgId &&
            key[2] !== "detail"
          );
        },
      });
      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchToggleDocuments(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ids,
      isEnabled,
      is_enabled,
    }: {
      ids: string[];
      isEnabled?: boolean;
      is_enabled?: boolean;
    }) => {
      const enabled = is_enabled ?? isEnabled;
      const response = await api.patch<{ updated_count: number }>(
        `/api/organizations/${orgId}/documents/batch`,
        { ids, is_enabled: enabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useBatchUpdatePaths(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BatchPathUpdateRequest) => {
      const response = await api.patch<BatchPathUpdateResponse>(
        `/api/organizations/${orgId}/documents/batch/paths`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useMoveDocument(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      documentId,
      newPath,
    }: {
      documentId: string;
      newPath: string;
    }) => {
      const response = await api.put<Document>(
        `/api/organizations/${orgId}/documents/${documentId}`,
        { path: newPath }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useCleanDocument(orgId: string, documentId: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post<CleanDocumentResponse>(
        `/api/organizations/${orgId}/documents/${documentId}/clean`
      );
      return response.data;
    },
  });
}

// =============================================================================
// Client-side Utilities
// =============================================================================

// Build folder tree from flat list of paths with counts
export interface FolderNode {
  name: string;
  path: string;
  count: number;
  children: FolderNode[];
}

export function buildFolderTree(folders: FolderCount[]): FolderNode[] {
  const root: FolderNode[] = [];
  // Map for quick lookup of counts by path
  const countMap = new Map(folders.map((f) => [f.path, f.count]));

  for (const folder of folders) {
    const parts = folder.path.split("/").filter(Boolean);
    let currentLevel = root;
    let currentPath = "";

    for (const part of parts) {
      currentPath = currentPath ? `${currentPath}/${part}` : `/${part}`;
      let existing = currentLevel.find((n) => n.name === part);

      if (!existing) {
        existing = {
          name: part,
          path: currentPath,
          count: countMap.get(currentPath) ?? 0,
          children: [],
        };
        currentLevel.push(existing);
      }

      currentLevel = existing.children;
    }
  }

  return root;
}

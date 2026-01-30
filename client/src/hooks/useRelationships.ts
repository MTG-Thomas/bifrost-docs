import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { EntityType } from "@/lib/entity-icons";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type RelatedEntity = components["schemas"]["RelatedEntity"];
export type RelatedItemsResponse = components["schemas"]["RelatedItemsResponse"];
export type RelationshipCreate = components["schemas"]["RelationshipCreate"];
export type RelationshipPublic = components["schemas"]["RelationshipPublic"];

// =============================================================================
// Hooks
// =============================================================================

export function useRelationships(
  orgId: string,
  entityType: string,
  entityId: string
) {
  return useQuery({
    queryKey: ["relationships", orgId, entityType, entityId],
    queryFn: async () => {
      const response = await api.get<RelatedItemsResponse>(
        `/api/organizations/${orgId}/relationships/resolved`,
        {
          params: {
            entity_type: entityType,
            entity_id: entityId,
          },
        }
      );
      return response.data;
    },
    enabled: Boolean(orgId && entityType && entityId),
    staleTime: 30000,
  });
}

export function useCreateRelationship(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RelationshipCreate) => {
      const response = await api.post<RelationshipPublic>(
        `/api/organizations/${orgId}/relationships`,
        data
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate both source and target entity relationship queries
      queryClient.invalidateQueries({
        queryKey: [
          "relationships",
          orgId,
          variables.source_type,
          variables.source_id,
        ],
      });
      queryClient.invalidateQueries({
        queryKey: [
          "relationships",
          orgId,
          variables.target_type,
          variables.target_id,
        ],
      });
    },
  });
}

export function useDeleteRelationship(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (relationshipId: string) => {
      await api.delete(`/api/organizations/${orgId}/relationships/${relationshipId}`);
    },
    onSuccess: () => {
      // Invalidate all relationship queries for this org
      queryClient.invalidateQueries({
        queryKey: ["relationships", orgId],
      });
    },
  });
}

export function groupRelationshipsByType(
  relationships: RelatedEntity[]
): Record<EntityType, RelatedEntity[]> {
  const grouped: Record<string, RelatedEntity[]> = {};

  for (const rel of relationships) {
    const type = rel.entity_type;
    if (!grouped[type]) {
      grouped[type] = [];
    }
    grouped[type].push(rel);
  }

  return grouped as Record<EntityType, RelatedEntity[]>;
}

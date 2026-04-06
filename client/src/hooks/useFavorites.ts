import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { toast } from "sonner";

// =============================================================================
// Types
// =============================================================================

export interface Favorite {
  id: string;
  organization_id: string;
  entity_type: string;
  entity_id: string;
  custom_label: string | null;
  display_order: number;
}

export interface FavoriteCreate {
  organization_id: string;
  entity_type: string;
  entity_id: string;
  custom_label?: string | null;
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch the current user's favorite items.
 *
 * @param limit - Maximum number of items to return (default: 20)
 */
export function useFavorites(limit = 20) {
  return useQuery({
    queryKey: ["favorites", limit],
    queryFn: async () => {
      const response = await api.get<{ items: Favorite[]; total: number }>(
        "/api/me/favorites",
        {
          params: { limit },
        }
      );
      return response.data;
    },
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Check if a specific entity is favorited.
 */
export function useIsFavorite(
  organization_id: string | null,
  entity_type: string | null,
  entity_id: string | null
) {
  return useQuery({
    queryKey: ["favorite-check", organization_id, entity_type, entity_id],
    queryFn: async () => {
      if (!organization_id || !entity_type || !entity_id) {
        return { is_favorite: false };
      }
      const response = await api.get<{ is_favorite: boolean; favorite_id?: string }>(
        "/api/me/favorites/check",
        {
          params: { organization_id, entity_type, entity_id },
        }
      );
      return response.data;
    },
    enabled: !!organization_id && !!entity_type && !!entity_id,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Add an item to favorites.
 */
export function useAddFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: FavoriteCreate) => {
      const response = await api.post<Favorite>("/api/me/favorites", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      toast.success("Added to favorites");
    },
    onError: () => {
      toast.error("Failed to add favorite");
    },
  });
}

/**
 * Remove an item from favorites by ID.
 */
export function useRemoveFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (favoriteId: string) => {
      await api.delete(`/api/me/favorites/${favoriteId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      toast.success("Removed from favorites");
    },
    onError: () => {
      toast.error("Failed to remove favorite");
    },
  });
}

/**
 * Remove an item from favorites by entity reference.
 */
export function useUnfavoriteEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      organization_id,
      entity_type,
      entity_id,
    }: {
      organization_id: string;
      entity_type: string;
      entity_id: string;
    }) => {
      await api.delete("/api/me/favorites", {
        params: { organization_id, entity_type, entity_id },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      queryClient.invalidateQueries({ queryKey: ["favorite-check"] });
      toast.success("Removed from favorites");
    },
    onError: () => {
      toast.error("Failed to remove favorite");
    },
  });
}

/**
 * Toggle favorite status for an entity.
 * Uses optimistic updates for better UX.
 */
export function useToggleFavorite() {
  const queryClient = useQueryClient();
  const addFavorite = useAddFavorite();
  const unfavorite = useUnfavoriteEntity();

  const toggle = async ({
    organization_id,
    entity_type,
    entity_id,
    isFavorite,
    favoriteId,
    customLabel,
  }: {
    organization_id: string;
    entity_type: string;
    entity_id: string;
    isFavorite: boolean;
    favoriteId?: string;
    customLabel?: string | null;
  }) => {
    if (isFavorite && favoriteId) {
      await addFavorite.mutateAsync({
        organization_id,
        entity_type,
        entity_id,
        custom_label: customLabel,
      });
    } else if (!isFavorite && favoriteId) {
      await unfavorite.mutateAsync({ organization_id, entity_type, entity_id });
    }
  };

  return {
    toggle,
    isPending: addFavorite.isPending || unfavorite.isPending,
  };
}

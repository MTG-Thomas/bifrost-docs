/**
 * React Query hooks for organizations management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { organizationsApi, type Organization } from "@/lib/api-client";
import { useOrganizationStore } from "@/stores/organization.store";
import type { components } from "@/lib/v1";

// =============================================================================
// Re-export types from OpenAPI spec for component convenience
// =============================================================================

export type OrganizationWithFrequent = components["schemas"]["OrganizationWithFrequent"];
export type FrequentItem = components["schemas"]["FrequentItem"];

// =============================================================================
// Hook Types
// =============================================================================

interface UseOrganizationOptions {
  include?: string[];
}

// =============================================================================
// Hooks
// =============================================================================

export function useOrganizations(options?: { showDisabled?: boolean }) {
  const { setOrganizations, currentOrg, clearCurrentOrg } = useOrganizationStore();

  return useQuery({
    queryKey: ["organizations", options?.showDisabled],
    queryFn: async () => {
      const params: Record<string, boolean> = {};
      if (options?.showDisabled !== undefined) {
        params.show_disabled = options.showDisabled;
      }
      const response = await organizationsApi.list({ params });

      // Validate that the persisted currentOrg still exists in the fetched list
      if (currentOrg) {
        const orgStillExists = response.data.some(org => org.id === currentOrg.id);
        if (!orgStillExists) {
          clearCurrentOrg();
        }
      }

      setOrganizations(response.data);
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - data considered fresh for 5 min
    refetchOnWindowFocus: true, // Refetch when user returns to tab
    refetchOnMount: true, // Always refetch on mount to validate persisted current org
  });
}

export function useOrganization(id: string, options?: UseOrganizationOptions) {
  return useQuery({
    queryKey: ["organization", id, options?.include],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (options?.include?.length) {
        params.include = options.include.join(",");
      }
      const response = await organizationsApi.get(id, { params });
      // Cast to extended type when include param is used
      return response.data as OrganizationWithFrequent;
    },
    enabled: !!id,
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { name: string }) => organizationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<Organization>;
    }) => organizationsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

export function useDeleteOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => organizationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

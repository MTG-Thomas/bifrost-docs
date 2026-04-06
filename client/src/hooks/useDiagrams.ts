import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";

interface GenerateDiagramRequest {
  diagram_type: "network_topology" | "rack_elevation" | "cable_map" | "custom";
  rack_id?: string;
  device_id?: string;
  auto_update?: boolean;
}

interface DiagramResponse {
  id: string;
  name: string;
  content: string;
  diagram_type: string;
  auto_update: boolean;
}

export function useDiagrams() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const generateDiagram = useMutation({
    mutationFn: async (request: GenerateDiagramRequest): Promise<DiagramResponse> => {
      const response = await fetch("/api/diagrams/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to generate diagram");
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["diagrams"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({
        title: "Diagram generated",
        description: "Your diagram has been created successfully.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to generate diagram",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const refreshDiagram = useMutation({
    mutationFn: async (diagramId: string): Promise<DiagramResponse> => {
      const response = await fetch(`/api/diagrams/${diagramId}/refresh`, {
        method: "POST",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to refresh diagram");
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["diagrams"] });
      toast({
        title: "Diagram refreshed",
        description: "Diagram has been updated with latest data.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to refresh",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  return {
    generateDiagram,
    refreshDiagram,
  };
}

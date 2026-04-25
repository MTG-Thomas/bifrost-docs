import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, Network, Server, FileText, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import type { ColumnDef } from "@tanstack/react-table";
import { useToast } from "@/hooks/use-toast";
import { documentsApi } from "@/services/api";
import { MermaidDiagram } from "@/components/diagrams/MermaidDiagram";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface DiagramDocument {
  id: string;
  name: string;
  path: string;
  diagram_type: "network_topology" | "rack_elevation" | "cable_map" | "custom";
  auto_generated: boolean;
  auto_update: boolean;
  updated_at: string;
  preview?: string;
}

type DocumentWithDiagramMetadata = DiagramDocument & {
  metadata?: {
    diagram_type?: string;
  };
};

export function DiagramsPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [selectedType, setSelectedType] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);

  const { data: diagrams, isLoading, refetch } = useQuery({
    queryKey: ["diagrams"],
    queryFn: async () => {
      // Query documents with diagram metadata
      const response = await documentsApi.list({
        params: {
          limit: 100,
          sort_by: "updated_at",
          sort_dir: "desc",
        },
      });
      
      // Filter to only diagram documents
      return (response.data.items as DocumentWithDiagramMetadata[]).filter(
        (doc) => doc.metadata?.diagram_type
      );
    },
  });

  const columns: ColumnDef<DiagramDocument>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {row.original.diagram_type === "network_topology" && (
            <Network className="h-4 w-4 text-blue-500" />
          )}
          {row.original.diagram_type === "rack_elevation" && (
            <Server className="h-4 w-4 text-green-500" />
          )}
          {row.original.diagram_type === "cable_map" && (
            <FileText className="h-4 w-4 text-orange-500" />
          )}
          <span className="font-medium">{row.original.name}</span>
        </div>
      ),
    },
    {
      accessorKey: "diagram_type",
      header: "Type",
      cell: ({ row }) => (
        <span className="capitalize">
          {row.original.diagram_type.replace("_", " ")}
        </span>
      ),
    },
    {
      accessorKey: "auto_generated",
      header: "Source",
      cell: ({ row }) => (
        <span
          className={`text-xs px-2 py-1 rounded-full ${
            row.original.auto_generated
              ? "bg-blue-100 text-blue-800"
              : "bg-gray-100 text-gray-800"
          }`}
        >
          {row.original.auto_generated ? "Auto" : "Manual"}
        </span>
      ),
    },
    {
      accessorKey: "updated_at",
      header: "Last Updated",
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {new Date(row.original.updated_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/documents/${row.original.id}`)}
          >
            View
          </Button>
          {row.original.auto_update && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleRefresh(row.original.id)}
              title="Refresh diagram"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  const handleGenerate = async () => {
    if (!selectedType) return;

    setIsGenerating(true);
    try {
      // Call API to generate diagram
      const response = await fetch("/api/diagrams/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          diagram_type: selectedType,
          auto_update: true,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate diagram");
      }

      await response.json();
      
      toast({
        title: "Diagram generated",
        description: `Created ${selectedType.replace("_", " ")} diagram`,
      });

      refetch();
    } catch (error) {
      toast({
        title: "Failed to generate",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRefresh = async (id: string) => {
    try {
      await fetch(`/api/diagrams/${id}/refresh`, { method: "POST" });
      toast({ title: "Diagram refreshed" });
      refetch();
    } catch {
      toast({
        title: "Refresh failed",
        variant: "destructive",
      });
    }
  };

  const exampleNetworkDiagram = `flowchart LR
    subgraph Internet["Internet"]
      WAN["WAN Gateway"]
    end
    
    subgraph Core["Core Network"]
      FW["Firewall\\n192.168.1.1"]
      SW1["Core Switch\\n192.168.1.2"]
    end
    
    subgraph Servers["Server VLAN"]
      SRV1["App Server"]
      SRV2["DB Server"]
    end
    
    subgraph Workstations["Workstation VLAN"]
      WS1["Workstation 1"]
      WS2["Workstation 2"]
    end
    
    WAN --> FW
    FW --> SW1
    SW1 --> SRV1
    SW1 --> SRV2
    SW1 --> WS1
    SW1 --> WS2
    
    classDef up fill:#90EE90,stroke:#228B22
    classDef down fill:#FFB6C1,stroke:#DC143C
    class FW,SW1,SRV1,SRV2,WS1,WS2 up`;

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Diagrams</h1>
          <p className="text-muted-foreground">
            Network topology, rack elevations, and infrastructure diagrams
          </p>
        </div>

        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Generate Diagram
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Generate Infrastructure Diagram</DialogTitle>
              <DialogDescription>
                Create a new diagram from your infrastructure data. Auto-generated
                diagrams update when your configurations change.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Diagram Type</label>
                <Select value={selectedType} onValueChange={setSelectedType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select diagram type..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="network_topology">
                      <div className="flex items-center gap-2">
                        <Network className="h-4 w-4" />
                        Network Topology
                      </div>
                    </SelectItem>
                    <SelectItem value="rack_elevation">
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4" />
                        Rack Elevation
                      </div>
                    </SelectItem>
                    <SelectItem value="cable_map">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Cable Map
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {selectedType === "network_topology" && (
                <div className="border rounded-lg p-4 bg-muted/50">
                  <p className="text-sm font-medium mb-2">Preview</p>
                  <MermaidDiagram
                    chart={exampleNetworkDiagram}
                    className="scale-75 origin-top-left"
                  />
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                onClick={handleGenerate}
                disabled={!selectedType || isGenerating}
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Generate
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Network Diagrams
            </CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {diagrams?.filter((d) => d.diagram_type === "network_topology").length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rack Diagrams</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {diagrams?.filter((d) => d.diagram_type === "rack_elevation").length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auto-Updated</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {diagrams?.filter((d) => d.auto_update).length || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Update automatically
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Diagrams Table */}
      <Card>
        <CardHeader>
          <CardTitle>Infrastructure Diagrams</CardTitle>
          <CardDescription>
            View and manage your infrastructure visualization diagrams
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={diagrams || []}
            isLoading={isLoading}
            searchPlaceholder="Search diagrams..."
          />
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">About Infrastructure Diagrams</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong>Network Topology:</strong> Auto-generated from your configuration
            relationships and cable connections. Shows switches, routers, servers, and
            how they connect.
          </p>
          <p>
            <strong>Rack Elevations:</strong> Visual representation of equipment installed
            in racks. Shows U-positions, power consumption, and available space.
          </p>
          <p>
            <strong>Cable Maps:</strong> Detailed port-to-port cable connections for
            specific devices or patch panels.
          </p>
          <p className="pt-2">
            Integrations with NinjaOne and Meraki can auto-discover devices and generate
            diagrams from live network data.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

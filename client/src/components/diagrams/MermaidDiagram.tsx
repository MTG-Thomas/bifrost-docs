import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { AlertCircle, RefreshCw, ZoomIn, ZoomOut, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number; // seconds
  onRefresh?: () => void;
}

export function MermaidDiagram({
  chart,
  className = "",
  autoRefresh = false,
  refreshInterval = 300,
  onRefresh,
}: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      securityLevel: "strict",
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: "basis",
      },
      block: {
        useMaxWidth: true,
      },
    });
  }, []);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current || !chart) return;

      setLoading(true);
      setError(null);

      try {
        // Generate unique ID for this render
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        
        // Validate syntax first. Mermaid throws when parsing fails.
        await mermaid.parse(chart);

        // Render
        const { svg } = await mermaid.render(id, chart);
        
        // Insert SVG
        containerRef.current.innerHTML = svg;
        
        // Apply zoom scale
        const svgElement = containerRef.current.querySelector("svg");
        if (svgElement) {
          svgElement.style.transform = `scale(${scale})`;
          svgElement.style.transformOrigin = "top left";
          svgElement.style.transition = "transform 0.2s ease";
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Mermaid render error:", err);
        setError(err instanceof Error ? err.message : "Failed to render diagram");
        setLoading(false);
      }
    };

    renderDiagram();
  }, [chart, scale]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !onRefresh) return;

    const interval = setInterval(() => {
      onRefresh();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, onRefresh]);

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.1, 2));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.1, 0.5));
  };

  const handleDownload = () => {
    if (!containerRef.current) return;
    
    const svg = containerRef.current.querySelector("svg");
    if (!svg) return;

    // Convert SVG to blob
    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);

    // Download
    const link = document.createElement("a");
    link.href = url;
    link.download = "diagram.svg";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadPNG = async () => {
    if (!containerRef.current) return;
    
    const svg = containerRef.current.querySelector("svg");
    if (!svg) return;

    // Get SVG dimensions
    const rect = svg.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // Create canvas
    const canvas = document.createElement("canvas");
    canvas.width = width * 2; // 2x for retina
    canvas.height = height * 2;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Scale for retina
    ctx.scale(2, 2);

    // Create image from SVG
    const svgData = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    
    img.onload = () => {
      ctx.drawImage(img, 0, 0, width, height);
      
      // Download PNG
      canvas.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "diagram.png";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }, "image/png");
    };

    img.src = "data:image/svg+xml;base64," + btoa(svgData);
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={handleZoomOut}
            disabled={scale <= 0.5}
            title="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground w-12 text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={handleZoomIn}
            disabled={scale >= 2}
            title="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center gap-1">
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
          >
            <Download className="h-4 w-4 mr-1" />
            SVG
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadPNG}
          >
            <Download className="h-4 w-4 mr-1" />
            PNG
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Diagram */}
      <div
        ref={containerRef}
        className="border rounded-lg p-4 bg-white overflow-auto min-h-[200px]"
        style={{ maxHeight: "800px" }}
      >
        {loading && !error && (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Legend for network diagrams */}
      {chart.includes("flowchart") && (
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 rounded-full bg-[#90EE90] border border-[#228B22]"></span>
            <span>Online</span>
            <span className="inline-block w-3 h-3 rounded-full bg-[#FFD700] border border-[#FFA500] ml-2"></span>
            <span>Warning</span>
            <span className="inline-block w-3 h-3 rounded-full bg-[#FFB6C1] border border-[#DC143C] ml-2"></span>
            <span>Offline</span>
          </div>
        </div>
      )}
    </div>
  );
}

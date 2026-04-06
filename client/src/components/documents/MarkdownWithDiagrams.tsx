import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MermaidDiagram } from "@/components/diagrams/MermaidDiagram";

interface MarkdownWithDiagramsProps {
  content: string;
  className?: string;
}

/**
 * Markdown renderer that detects and renders Mermaid diagrams.
 * 
 * Mermaid code blocks (```mermaid) are extracted and rendered as interactive
 * diagrams. Regular markdown is rendered as usual.
 */
export function MarkdownWithDiagrams({
  content,
  className = "",
}: MarkdownWithDiagramsProps) {
  // Parse content to separate mermaid blocks from regular markdown
  const segments = useMemo(() => {
    const result: Array<{
      type: "markdown" | "mermaid";
      content: string;
    }> = [];

    const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = mermaidRegex.exec(content)) !== null) {
      // Add markdown before this mermaid block
      if (match.index > lastIndex) {
        result.push({
          type: "markdown",
          content: content.slice(lastIndex, match.index),
        });
      }

      // Add the mermaid block
      result.push({
        type: "mermaid",
        content: match[1].trim(),
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining markdown
    if (lastIndex < content.length) {
      result.push({
        type: "markdown",
        content: content.slice(lastIndex),
      });
    }

    return result;
  }, [content]);

  return (
    <div className={className}>
      {segments.map((segment, index) => (
        <div key={index}>
          {segment.type === "mermaid" ? (
            <div className="my-4">
              <MermaidDiagram chart={segment.content} />
            </div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className="prose prose-sm max-w-none dark:prose-invert"
              components={{
                // Override code blocks to not conflict with mermaid
                code({ inline, className, children, ...props }: any) {
                  if (inline) {
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  }
                  return (
                    <pre className={className}>
                      <code {...props}>{children}</code>
                    </pre>
                  );
                },
              }}
            >
              {segment.content}
            </ReactMarkdown>
          )}
        </div>
      ))}
    </div>
  );
}

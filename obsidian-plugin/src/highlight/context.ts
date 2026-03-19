// src/highlight/context.ts

const HIGHLIGHT_KEY = "ccodingContextHighlight";

/**
 * Manages context node highlighting when a ccoding node is selected.
 * Uses data attributes instead of CSS classes for consistency with
 * the canvas-patcher approach.
 */
export class ContextHighlighter {
  /** Map from node ID → set of connected context node IDs */
  private contextMap = new Map<string, Set<string>>();
  /** Map from node ID → set of connecting context edge IDs */
  private contextEdgeMap = new Map<string, Set<string>>();
  private canvas: any = null;

  /**
   * Build the context edge cache from canvas data (raw JSON format).
   */
  buildCache(canvasData: any): void {
    this.contextMap.clear();
    this.contextEdgeMap.clear();

    if (!canvasData?.edges) return;
    for (const edge of canvasData.edges) {
      if (edge.ccoding?.relation !== "context") continue;
      const from = edge.fromNode as string;
      const to = edge.toNode as string;

      // Both directions: selecting either end highlights the other
      for (const [src, dst] of [[from, to], [to, from]]) {
        if (!this.contextMap.has(src)) {
          this.contextMap.set(src, new Set());
          this.contextEdgeMap.set(src, new Set());
        }
        this.contextMap.get(src)!.add(dst);
        this.contextEdgeMap.get(src)!.add(edge.id);
      }
    }
  }

  attach(canvas: any): void {
    this.canvas = canvas;
  }

  detach(): void {
    this.clearHighlights();
    this.canvas = null;
  }

  onSelectionChange(selectedNodeId: string | null): void {
    this.clearHighlights();
    if (!selectedNodeId || !this.canvas) return;

    const contextNodeIds = this.contextMap.get(selectedNodeId);
    const contextEdgeIds = this.contextEdgeMap.get(selectedNodeId);
    if (!contextNodeIds) return;

    // Highlight context nodes
    if (this.canvas.nodes) {
      for (const nodeId of contextNodeIds) {
        const node = this.canvas.nodes.get(nodeId);
        const el = node?.nodeEl as HTMLElement | undefined;
        if (el) el.dataset[HIGHLIGHT_KEY] = "true";
      }
    }

    // Highlight context edges
    if (contextEdgeIds && this.canvas.edges) {
      for (const edgeId of contextEdgeIds) {
        const edge = this.canvas.edges.get(edgeId);
        const el = (edge?.lineGroupEl ?? edge?.wrapperEl ?? edge?.edgeEl) as
          | HTMLElement
          | undefined;
        if (el) el.dataset[HIGHLIGHT_KEY] = "true";
      }
    }
  }

  private clearHighlights(): void {
    if (!this.canvas) return;

    if (this.canvas.nodes) {
      for (const [, node] of this.canvas.nodes) {
        const el = node?.nodeEl as HTMLElement | undefined;
        if (el?.dataset[HIGHLIGHT_KEY]) delete el.dataset[HIGHLIGHT_KEY];
      }
    }

    if (this.canvas.edges) {
      for (const [, edge] of this.canvas.edges) {
        const el = (edge?.lineGroupEl ?? edge?.wrapperEl ?? edge?.edgeEl) as
          | HTMLElement
          | undefined;
        if (el?.dataset[HIGHLIGHT_KEY]) delete el.dataset[HIGHLIGHT_KEY];
      }
    }
  }
}

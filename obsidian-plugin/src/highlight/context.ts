// src/highlight/context.ts

const HIGHLIGHT_CLASS = "ccoding-context-highlight";

/**
 * Manages context node highlighting when a ccoding node is selected.
 * Caches context edge mapping for O(1) lookups.
 */
export class ContextHighlighter {
  /** Map from node ID → set of connected context node IDs */
  private contextMap = new Map<string, Set<string>>();
  /** Map from node ID → set of connecting context edge IDs */
  private contextEdgeMap = new Map<string, Set<string>>();
  private canvasEl: HTMLElement | null = null;
  private currentHighlighted: string[] = [];

  /**
   * Build the context edge cache from canvas data.
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

  attach(canvasEl: HTMLElement): void {
    this.canvasEl = canvasEl;
  }

  detach(): void {
    this.clearHighlights();
    this.canvasEl = null;
  }

  /**
   * Called when canvas selection changes. Pass the selected node ID or null.
   */
  onSelectionChange(selectedNodeId: string | null): void {
    this.clearHighlights();
    if (!selectedNodeId || !this.canvasEl) return;

    const contextNodeIds = this.contextMap.get(selectedNodeId);
    const contextEdgeIds = this.contextEdgeMap.get(selectedNodeId);
    if (!contextNodeIds) return;

    for (const nodeId of contextNodeIds) {
      const el = this.canvasEl.querySelector<HTMLElement>(
        `.canvas-node[data-id="${nodeId}"]`,
      );
      if (el) {
        el.classList.add(HIGHLIGHT_CLASS);
        this.currentHighlighted.push(nodeId);
      }
    }

    if (contextEdgeIds) {
      for (const edgeId of contextEdgeIds) {
        const el = this.canvasEl.querySelector<HTMLElement>(
          `.canvas-edge[data-id="${edgeId}"]`,
        );
        if (el) {
          el.classList.add(HIGHLIGHT_CLASS);
        }
      }
    }
  }

  private clearHighlights(): void {
    if (!this.canvasEl) return;
    this.canvasEl
      .querySelectorAll(`.${HIGHLIGHT_CLASS}`)
      .forEach((el) => el.classList.remove(HIGHLIGHT_CLASS));
    this.currentHighlighted = [];
  }
}

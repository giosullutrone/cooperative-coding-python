// src/canvas-patcher.ts
import { around } from "monkey-around";
import { parseCcodingMetadata, parseEdgeMetadata } from "./types";
import type { PluginSettings } from "./types";
import { nodeAttributes, edgeAttributes } from "./styling/class-mapper";

/**
 * Patches Canvas prototype methods to set data-* attributes on
 * node/edge DOM elements, enabling pure CSS styling.
 *
 * Uses monkey-around (same library as Advanced Canvas) for clean
 * method wrapping with automatic uninstall on plugin unload.
 */
export class CanvasPatcher {
  private settings: PluginSettings;
  private plugin: any;
  private canvas: any = null;
  private patched = false;

  constructor(plugin: any, settings: PluginSettings) {
    this.plugin = plugin;
    this.settings = settings;
  }

  /**
   * Attach to a canvas instance — apply attributes to all existing
   * nodes/edges and patch prototype methods for future additions.
   * Safe to call multiple times; patches are only installed once.
   */
  attach(canvas: any): void {
    this.canvas = canvas;

    // Always re-apply attributes (canvas data may have changed)
    this.applyAllAttributes();

    // Only install monkey patches once
    if (this.patched) return;
    this.patched = true;

    // Patch addNode to set attributes on newly added nodes
    this.patchMethod(canvas, "addNode", (_next: Function) => {
      const self = this;
      return function (this: any, node: any) {
        const result = _next.call(this, node);
        self.applyNodeAttributes(node);
        return result;
      };
    });

    // Patch addEdge to set attributes on newly added edges
    this.patchMethod(canvas, "addEdge", (_next: Function) => {
      const self = this;
      return function (this: any, edge: any) {
        const result = _next.call(this, edge);
        self.applyEdgeAttributes(edge);
        return result;
      };
    });

    // Patch setData to re-apply all attributes after canvas data reload
    this.patchMethod(canvas, "setData", (_next: Function) => {
      const self = this;
      return function (this: any, ...args: any[]) {
        const result = _next.call(this, ...args);
        // Use rAF to let Obsidian's rendering settle before applying
        requestAnimationFrame(() => self.applyAllAttributes());
        return result;
      };
    });
  }

  /** Re-apply all data attributes to current canvas nodes/edges. */
  reapplyAll(): void {
    this.applyAllAttributes();
  }

  /** Update settings reference. Triggers reapply if relevant settings changed. */
  updateSettings(settings: PluginSettings): void {
    const needsReapply =
      this.settings.showRejectedNodes !== settings.showRejectedNodes;
    this.settings = settings;
    if (needsReapply) this.reapplyAll();
  }

  // --- Internal ---

  private patchMethod(
    target: any,
    method: string,
    wrapper: (next: Function) => Function,
  ): void {
    if (typeof target[method] !== "function") return;
    const uninstall = around(target, {
      [method]: (next: any) => wrapper(next),
    });
    this.plugin.register(uninstall);
  }

  private applyAllAttributes(): void {
    if (!this.canvas) return;

    if (this.canvas.nodes) {
      for (const [, node] of this.canvas.nodes) {
        this.applyNodeAttributes(node);
      }
    }

    if (this.canvas.edges) {
      for (const [, edge] of this.canvas.edges) {
        this.applyEdgeAttributes(edge);
      }
    }
  }

  private applyNodeAttributes(node: any): void {
    const el = node?.nodeEl as HTMLElement | undefined;
    if (!el) return;

    const meta = parseCcodingMetadata(node.unknownData?.ccoding);
    if (!meta) return;

    const attrs = nodeAttributes(meta, !this.settings.showRejectedNodes);
    this.setDataAttributes(el, attrs);
  }

  private applyEdgeAttributes(edge: any): void {
    // Following Advanced Canvas pattern: set data attributes on edge.path.display
    // (the visible SVG <path> element) and line-end elements
    const displayPath = edge?.path?.display as HTMLElement | undefined;
    if (!displayPath) return;

    const meta = parseEdgeMetadata(edge.unknownData?.ccoding);
    if (!meta) return;

    const attrs = edgeAttributes(meta);
    this.setDataAttributes(displayPath, attrs);

    // Also set on line-end elements for arrow styling
    if (edge.fromLineEnd?.el) {
      this.setDataAttributes(edge.fromLineEnd.el as HTMLElement, attrs);
    }
    if (edge.toLineEnd?.el) {
      this.setDataAttributes(edge.toLineEnd.el as HTMLElement, attrs);
    }
  }

  private setDataAttributes(
    el: HTMLElement,
    attrs: Record<string, string | undefined>,
  ): void {
    for (const [key, value] of Object.entries(attrs)) {
      const datasetKey = key
        .replace(/^data-/, "")
        .replace(/-([a-z])/g, (_, c) => c.toUpperCase());

      if (value !== undefined) {
        el.dataset[datasetKey] = value;
      } else {
        delete el.dataset[datasetKey];
      }
    }
  }
}

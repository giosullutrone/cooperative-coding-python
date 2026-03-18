// src/styling/injector.ts
import { parseCcodingMetadata, parseEdgeMetadata } from "../types";
import type { PluginSettings } from "../types";
import { nodeClasses, edgeClasses } from "./class-mapper";
import { applyNodePatches, removeAllPatches } from "./patches";

const PROCESSED_ATTR = "data-ccoding-processed";

/**
 * Manages CSS class injection and MutationObserver for the canvas.
 *
 * Uses Obsidian's internal canvas API (canvas.nodes / canvas.edges Maps)
 * to access DOM elements directly, since Obsidian does not set data-id
 * attributes on .canvas-node elements.
 */
export class StyleInjector {
  private observer: MutationObserver | null = null;
  private canvasEl: HTMLElement | null = null;
  private canvas: any = null;
  private settings: PluginSettings;
  private applying = false;

  constructor(settings: PluginSettings) {
    this.settings = settings;
  }

  updateSettings(settings: PluginSettings): void {
    this.settings = settings;
  }

  /**
   * Attach to a canvas view element. Scans existing nodes and starts observing.
   * Accepts the Obsidian internal canvas object (with .nodes and .edges Maps).
   */
  attach(canvasEl: HTMLElement, canvas: any): void {
    this.detach();
    this.canvasEl = canvasEl;
    this.canvas = canvas;

    // Initial styling pass
    this.applyAllStyling();

    // Observe for new/changed DOM elements (viewport virtualization).
    // When Obsidian scrolls, it adds/removes node elements — re-apply styling.
    // The `applying` guard prevents feedback loops from our own DOM changes.
    this.observer = new MutationObserver(() => {
      if (!this.applying) this.applyAllStyling();
    });
    this.observer.observe(canvasEl, { childList: true, subtree: true });
  }

  /**
   * Detach from the canvas, remove observer and all patches.
   */
  detach(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    if (this.canvasEl) {
      removeAllPatches(this.canvasEl);
      // Remove ccoding classes
      this.canvasEl
        .querySelectorAll(`[${PROCESSED_ATTR}]`)
        .forEach((el) => {
          el.removeAttribute(PROCESSED_ATTR);
          // Remove all ccoding- classes
          const toRemove = Array.from(el.classList).filter((c) =>
            c.startsWith("ccoding-"),
          );
          el.classList.remove(...toRemove);
        });
      this.canvasEl = null;
    }
    this.canvas = null;
  }

  /**
   * Apply styling to all unprocessed nodes and edges using the
   * canvas object's internal Maps for direct element access.
   */
  private applyAllStyling(): void {
    if (!this.canvas) return;
    this.applying = true;

    // Style nodes via canvas.nodes Map
    if (this.canvas.nodes) {
      for (const [, node] of this.canvas.nodes) {
        const el = node.nodeEl as HTMLElement | undefined;
        if (!el || el.hasAttribute(PROCESSED_ATTR)) continue;

        const meta = parseCcodingMetadata(node.unknownData?.ccoding);
        if (!meta) continue;

        const classes = nodeClasses(meta, this.settings.showRejectedNodes);
        el.classList.add(...classes);
        el.setAttribute(PROCESSED_ATTR, "true");

        if (meta.kind) el.dataset.ccodingKind = meta.kind;
        if (meta.status) el.dataset.ccodingStatus = meta.status;

        applyNodePatches(el, meta);
      }
    }

    // Style edges via canvas.edges Map
    if (this.canvas.edges) {
      for (const [, edge] of this.canvas.edges) {
        // Obsidian edges use .lineGroupEl or .wrapperEl for the DOM element
        const el = (edge.lineGroupEl ?? edge.wrapperEl ?? edge.edgeEl) as HTMLElement | undefined;
        if (!el || el.hasAttribute(PROCESSED_ATTR)) continue;

        const meta = parseEdgeMetadata(edge.unknownData?.ccoding);
        if (!meta) continue;

        const classes = edgeClasses(meta);
        el.classList.add(...classes);
        el.setAttribute(PROCESSED_ATTR, "true");
      }
    }

    this.applying = false;
  }
}

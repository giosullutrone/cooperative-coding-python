// src/styling/injector.ts
import { parseCcodingMetadata, parseEdgeMetadata } from "../types";
import type { PluginSettings } from "../types";
import { nodeClasses, edgeClasses } from "./class-mapper";
import { applyNodePatches, removeAllPatches } from "./patches";
import { injectMarkers, removeMarkers } from "./markers";

const PROCESSED_ATTR = "data-ccoding-processed";

/**
 * Manages CSS class injection and MutationObserver for the canvas.
 */
export class StyleInjector {
  private observer: MutationObserver | null = null;
  private canvasEl: HTMLElement | null = null;
  private settings: PluginSettings;

  constructor(settings: PluginSettings) {
    this.settings = settings;
  }

  updateSettings(settings: PluginSettings): void {
    this.settings = settings;
  }

  /**
   * Attach to a canvas view element. Scans existing nodes and starts observing.
   */
  attach(canvasEl: HTMLElement, canvasData: any): void {
    this.detach();
    this.canvasEl = canvasEl;

    // Build a lookup from node/edge id → ccoding metadata
    const nodeMetaMap = this.buildNodeMetaMap(canvasData);
    const edgeMetaMap = this.buildEdgeMetaMap(canvasData);

    // Process all existing nodes
    this.processAllNodes(canvasEl, nodeMetaMap);
    this.processAllEdges(canvasEl, edgeMetaMap);

    // Inject SVG markers
    const svgEl = canvasEl.querySelector("svg");
    if (svgEl) {
      injectMarkers(svgEl);
    }

    // Observe for new/changed DOM elements (viewport virtualization)
    this.observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const added of mutation.addedNodes) {
          if (added instanceof HTMLElement) {
            this.processAddedElement(added, nodeMetaMap, edgeMetaMap);
          }
        }
      }
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
      removeMarkers(this.canvasEl);
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
  }

  private buildNodeMetaMap(canvasData: any): Map<string, any> {
    const map = new Map<string, any>();
    if (canvasData?.nodes) {
      for (const node of canvasData.nodes) {
        const meta = parseCcodingMetadata(node.ccoding);
        if (meta) map.set(node.id, meta);
      }
    }
    return map;
  }

  private buildEdgeMetaMap(canvasData: any): Map<string, any> {
    const map = new Map<string, any>();
    if (canvasData?.edges) {
      for (const edge of canvasData.edges) {
        const meta = parseEdgeMetadata(edge.ccoding);
        if (meta) map.set(edge.id, meta);
      }
    }
    return map;
  }

  private processAllNodes(
    container: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    // Obsidian canvas nodes have a data-id attribute
    container
      .querySelectorAll<HTMLElement>(".canvas-node")
      .forEach((el) => {
        this.applyNodeStyling(el, metaMap);
      });
  }

  private processAllEdges(
    container: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    container
      .querySelectorAll<HTMLElement>(".canvas-edge")
      .forEach((el) => {
        this.applyEdgeStyling(el, metaMap);
      });
  }

  private processAddedElement(
    el: HTMLElement,
    nodeMetaMap: Map<string, any>,
    edgeMetaMap: Map<string, any>,
  ): void {
    if (el.classList.contains("canvas-node")) {
      this.applyNodeStyling(el, nodeMetaMap);
    } else if (el.classList.contains("canvas-edge")) {
      this.applyEdgeStyling(el, edgeMetaMap);
    }
    // Also check children (nodes may be nested in containers)
    el.querySelectorAll<HTMLElement>(".canvas-node").forEach((n) =>
      this.applyNodeStyling(n, nodeMetaMap),
    );
    el.querySelectorAll<HTMLElement>(".canvas-edge").forEach((e) =>
      this.applyEdgeStyling(e, edgeMetaMap),
    );
  }

  private applyNodeStyling(
    el: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    if (el.hasAttribute(PROCESSED_ATTR)) return;
    const id = el.dataset.id;
    if (!id) return;
    const meta = metaMap.get(id);
    if (!meta) return;

    const classes = nodeClasses(meta, this.settings.showRejectedNodes);
    el.classList.add(...classes);
    el.setAttribute(PROCESSED_ATTR, "true");

    // Set namespaced data attributes
    if (meta.kind) el.dataset.ccodingKind = meta.kind;
    if (meta.status) el.dataset.ccodingStatus = meta.status;

    // Apply DOM patches (badges, banners, footers)
    applyNodePatches(el, meta);
  }

  private applyEdgeStyling(
    el: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    if (el.hasAttribute(PROCESSED_ATTR)) return;
    const id = el.dataset.id;
    if (!id) return;
    const meta = metaMap.get(id);
    if (!meta) return;

    const classes = edgeClasses(meta);
    el.classList.add(...classes);
    el.setAttribute(PROCESSED_ATTR, "true");
  }
}

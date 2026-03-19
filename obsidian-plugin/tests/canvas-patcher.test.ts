// tests/canvas-patcher.test.ts
import { describe, it, expect, beforeEach, vi } from "vitest";
import { CanvasPatcher } from "../src/canvas-patcher";
import { DEFAULT_SETTINGS } from "../src/types";
import type { PluginSettings } from "../src/types";

// Polyfill requestAnimationFrame for Node/Vitest environment
if (typeof globalThis.requestAnimationFrame === "undefined") {
  globalThis.requestAnimationFrame = (cb: FrameRequestCallback) => setTimeout(cb, 0) as unknown as number;
  globalThis.cancelAnimationFrame = (id: number) => clearTimeout(id);
}

/** Create a mock DOM element with dataset and attribute support. */
function mockElement(): any {
  const dataset: Record<string, string> = {};
  const attrs: Record<string, string> = {};
  return {
    dataset,
    setAttribute(key: string, val: string) { attrs[key] = val; },
    removeAttribute(key: string) { delete attrs[key]; delete dataset[key]; },
    getAttribute(key: string) { return attrs[key] ?? null; },
    querySelectorAll() { return []; },
  };
}

/** Create a mock canvas with nodes/edges Maps and patchable methods. */
function mockCanvas(
  nodes: Array<{ id: string; unknownData?: any; nodeEl: any }>,
  edges: Array<{ id: string; unknownData?: any; lineGroupEl: any }>,
) {
  const canvas: any = {
    nodes: new Map(nodes.map((n) => [n.id, n])),
    edges: new Map(edges.map((e) => [e.id, e])),
    addNode: vi.fn(),
    addEdge: vi.fn(),
    setData: vi.fn(),
    wrapperEl: { querySelector: () => null },
  };
  return canvas;
}

/** Minimal plugin mock. */
function mockPlugin(): any {
  const registered: Array<() => void> = [];
  return {
    register(fn: () => void) { registered.push(fn); },
    _registered: registered,
  };
}

describe("CanvasPatcher", () => {
  let settings: PluginSettings;
  let plugin: any;

  beforeEach(() => {
    settings = { ...DEFAULT_SETTINGS };
    plugin = mockPlugin();
  });

  it("applies node data attributes on attach", () => {
    const nodeEl = mockElement();
    const canvas = mockCanvas(
      [{ id: "n1", unknownData: { ccoding: { kind: "class", status: "proposed", stereotype: "abstract" } }, nodeEl }],
      [],
    );

    const patcher = new CanvasPatcher(plugin, settings);
    patcher.attach(canvas);

    expect(nodeEl.dataset.ccodingKind).toBe("class");
    expect(nodeEl.dataset.ccodingStatus).toBe("proposed");
    expect(nodeEl.dataset.ccodingStereotype).toBe("abstract");
  });

  it("applies edge data attributes on attach", () => {
    const edgeEl = mockElement();
    const canvas = mockCanvas(
      [],
      [{ id: "e1", unknownData: { ccoding: { relation: "inherits", status: "accepted" } }, lineGroupEl: edgeEl }],
    );

    const patcher = new CanvasPatcher(plugin, settings);
    patcher.attach(canvas);

    expect(edgeEl.dataset.ccodingRelation).toBe("inherits");
    expect(edgeEl.dataset.ccodingStatus).toBe("accepted");
  });

  it("skips nodes without ccoding metadata", () => {
    const nodeEl = mockElement();
    const canvas = mockCanvas(
      [{ id: "n1", unknownData: {}, nodeEl }],
      [],
    );

    const patcher = new CanvasPatcher(plugin, settings);
    patcher.attach(canvas);

    expect(nodeEl.dataset.ccodingKind).toBeUndefined();
    expect(nodeEl.dataset.ccodingStatus).toBeUndefined();
  });

  it("sets rejected-hidden when hideRejected is true", () => {
    settings.showRejectedNodes = false;
    const nodeEl = mockElement();
    const canvas = mockCanvas(
      [{ id: "n1", unknownData: { ccoding: { kind: "class", status: "rejected" } }, nodeEl }],
      [],
    );

    const patcher = new CanvasPatcher(plugin, settings);
    patcher.attach(canvas);

    expect(nodeEl.dataset.ccodingStatus).toBe("rejected");
    expect(nodeEl.dataset.ccodingRejectedHidden).toBe("true");
  });

  it("does not set rejected-hidden when showRejected is true", () => {
    settings.showRejectedNodes = true;
    const nodeEl = mockElement();
    const canvas = mockCanvas(
      [{ id: "n1", unknownData: { ccoding: { kind: "class", status: "rejected" } }, nodeEl }],
      [],
    );

    const patcher = new CanvasPatcher(plugin, settings);
    patcher.attach(canvas);

    expect(nodeEl.dataset.ccodingStatus).toBe("rejected");
    expect(nodeEl.dataset.ccodingRejectedHidden).toBeUndefined();
  });

  it("reapplyAll updates attributes after settings change", () => {
    settings.showRejectedNodes = true;
    const nodeEl = mockElement();
    const canvas = mockCanvas(
      [{ id: "n1", unknownData: { ccoding: { kind: "class", status: "rejected" } }, nodeEl }],
      [],
    );

    const patcher = new CanvasPatcher(plugin, settings);
    patcher.attach(canvas);
    expect(nodeEl.dataset.ccodingRejectedHidden).toBeUndefined();

    // Change settings to hide rejected
    const newSettings = { ...settings, showRejectedNodes: false };
    patcher.updateSettings(newSettings);

    expect(nodeEl.dataset.ccodingRejectedHidden).toBe("true");
  });
});

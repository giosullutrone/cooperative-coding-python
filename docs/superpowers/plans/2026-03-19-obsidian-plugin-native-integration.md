# Obsidian Plugin Native Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace MutationObserver + DOM injection with `monkey-around` canvas patching and CSS-only styling so the plugin feels native to Obsidian.

**Architecture:** Patch Canvas prototype methods (`addNode`, `addEdge`, `setData`) to set data attributes on DOM elements. Move all visual treatment to CSS attribute selectors and pseudo-elements. Delete `injector.ts` and `patches.ts`.

**Tech Stack:** TypeScript, Obsidian API, `monkey-around`, CSS data-attribute selectors, Vitest

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/canvas-patcher.ts` | CREATE | Patches canvas prototype via `monkey-around`, sets data attributes on node/edge DOM elements |
| `src/styling/class-mapper.ts` | REWRITE | Returns `Record<string, string>` attribute maps instead of class arrays |
| `src/highlight/context.ts` | MODIFY | Use `dataset` properties instead of `classList` |
| `src/main.ts` | MODIFY | Replace injector wiring with patcher, remove injector imports |
| `styles.css` | REWRITE | Data-attribute selectors + pseudo-elements, remove DOM patch styles |
| `src/styling/injector.ts` | DELETE | Replaced by canvas-patcher |
| `src/styling/patches.ts` | DELETE | Replaced by CSS pseudo-elements |
| `tests/canvas-patcher.test.ts` | CREATE | Tests for monkey-around patching and attribute application |
| `tests/styling/class-mapper.test.ts` | REWRITE | Tests for attribute maps |
| `tests/highlight/context.test.ts` | MODIFY | Assertions use `dataset` instead of `classList` |
| `tests/integration.test.ts` | MODIFY | Update to use `nodeAttributes`/`edgeAttributes` |
| `package.json` | MODIFY | Add `monkey-around` dependency |

---

### Task 1: Add `monkey-around` dependency

**Files:**
- Modify: `obsidian-plugin/package.json`

- [ ] **Step 1: Install monkey-around**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npm install monkey-around@2.3.0 --save
```

- [ ] **Step 2: Verify installation**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && node -e "require('monkey-around')"
```

Expected: No error

**Note:** `monkey-around` must be bundled by esbuild (NOT added to the `external` list in `esbuild.config.mjs`) since it's not available in the Obsidian runtime. The current esbuild config only externalizes `obsidian`, `electron`, and codemirror packages, so `monkey-around` will be bundled correctly by default.

- [ ] **Step 3: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add package.json package-lock.json && git commit -m "feat(obsidian): add monkey-around dependency for canvas patching"
```

---

### Task 2: Rewrite class-mapper to return attribute maps

**Files:**
- Rewrite: `obsidian-plugin/src/styling/class-mapper.ts`
- Rewrite: `obsidian-plugin/tests/styling/class-mapper.test.ts`

- [ ] **Step 1: Write the failing tests**

Replace the entire content of `obsidian-plugin/tests/styling/class-mapper.test.ts` with:

```typescript
// tests/styling/class-mapper.test.ts
import { describe, it, expect } from "vitest";
import { nodeAttributes, edgeAttributes } from "../../src/styling/class-mapper";
import type { CcodingMetadata, EdgeMetadata } from "../../src/types";

describe("nodeAttributes", () => {
  it("returns kind and status for accepted nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-kind"]).toBe("class");
    expect(attrs["data-ccoding-status"]).toBe("accepted");
    expect(attrs["data-ccoding-rejected-hidden"]).toBeUndefined();
  });

  it("returns status for proposed nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "proposed" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("proposed");
  });

  it("returns rejected-hidden when hideRejected is true", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const attrs = nodeAttributes(meta, true);
    expect(attrs["data-ccoding-status"]).toBe("rejected");
    expect(attrs["data-ccoding-rejected-hidden"]).toBe("true");
  });

  it("does not return rejected-hidden when hideRejected is false", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("rejected");
    expect(attrs["data-ccoding-rejected-hidden"]).toBeUndefined();
  });

  it("returns stale status", () => {
    const meta: CcodingMetadata = { kind: "class", status: "stale" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("stale");
  });

  it("returns stereotype when present", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted", stereotype: "abstract" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-stereotype"]).toBe("abstract");
  });

  it("omits stereotype when not present", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-stereotype"]).toBeUndefined();
  });

  it("handles nodes with status only (no kind)", () => {
    const meta: CcodingMetadata = { status: "proposed" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("proposed");
    expect(attrs["data-ccoding-kind"]).toBeUndefined();
  });
});

describe("edgeAttributes", () => {
  it("returns relation and status for accepted edges", () => {
    const meta: EdgeMetadata = { relation: "inherits", status: "accepted" };
    const attrs = edgeAttributes(meta);
    expect(attrs["data-ccoding-relation"]).toBe("inherits");
    expect(attrs["data-ccoding-status"]).toBe("accepted");
  });

  it("returns proposed status", () => {
    const meta: EdgeMetadata = { relation: "composes", status: "proposed" };
    const attrs = edgeAttributes(meta);
    expect(attrs["data-ccoding-relation"]).toBe("composes");
    expect(attrs["data-ccoding-status"]).toBe("proposed");
  });

  it("omits status when undefined", () => {
    const meta: EdgeMetadata = { relation: "context" };
    const attrs = edgeAttributes(meta);
    expect(attrs["data-ccoding-relation"]).toBe("context");
    expect(attrs["data-ccoding-status"]).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run tests/styling/class-mapper.test.ts
```

Expected: FAIL — `nodeAttributes` and `edgeAttributes` are not exported

- [ ] **Step 3: Implement the attribute mapper**

Replace the entire content of `obsidian-plugin/src/styling/class-mapper.ts` with:

```typescript
// src/styling/class-mapper.ts
import type { CcodingMetadata, EdgeMetadata } from "../types";

/**
 * Compute data-attribute map for a ccoding canvas node.
 * Pure function — no DOM or Obsidian dependency.
 * Returns a Record where keys are data-attribute names and values are strings.
 * Undefined values should not be set on the DOM element.
 */
export function nodeAttributes(
  meta: CcodingMetadata,
  hideRejected: boolean,
): Record<string, string | undefined> {
  const attrs: Record<string, string | undefined> = {};

  if (meta.kind) attrs["data-ccoding-kind"] = meta.kind;
  if (meta.status) attrs["data-ccoding-status"] = meta.status;
  if (meta.stereotype) attrs["data-ccoding-stereotype"] = meta.stereotype;

  if (meta.status === "rejected" && hideRejected) {
    attrs["data-ccoding-rejected-hidden"] = "true";
  }

  return attrs;
}

/**
 * Compute data-attribute map for a ccoding canvas edge.
 */
export function edgeAttributes(
  meta: EdgeMetadata,
): Record<string, string | undefined> {
  const attrs: Record<string, string | undefined> = {};

  attrs["data-ccoding-relation"] = meta.relation;
  if (meta.status) attrs["data-ccoding-status"] = meta.status;

  return attrs;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run tests/styling/class-mapper.test.ts
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add src/styling/class-mapper.ts tests/styling/class-mapper.test.ts && git commit -m "refactor(obsidian): rewrite class-mapper to return data-attribute maps"
```

---

### Task 3: Create canvas-patcher

**Files:**
- Create: `obsidian-plugin/src/canvas-patcher.ts`
- Create: `obsidian-plugin/tests/canvas-patcher.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `obsidian-plugin/tests/canvas-patcher.test.ts`:

```typescript
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run tests/canvas-patcher.test.ts
```

Expected: FAIL — `CanvasPatcher` does not exist

- [ ] **Step 3: Implement canvas-patcher**

Create `obsidian-plugin/src/canvas-patcher.ts`:

```typescript
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
  private uninstallers: Array<() => void> = [];

  constructor(plugin: any, settings: PluginSettings) {
    this.plugin = plugin;
    this.settings = settings;
  }

  /**
   * Attach to a canvas instance — apply attributes to all existing
   * nodes/edges and patch prototype methods for future additions.
   */
  attach(canvas: any): void {
    this.canvas = canvas;

    // Apply attributes to all existing nodes/edges
    this.applyAllAttributes();

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

  /**
   * Re-apply all data attributes to current canvas nodes/edges.
   * Called after settings change or explicit reapply.
   */
  reapplyAll(): void {
    this.applyAllAttributes();
  }

  /**
   * Update settings reference. Triggers reapply if relevant settings changed.
   */
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
    this.uninstallers.push(uninstall);
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
    const el = (edge?.lineGroupEl ?? edge?.wrapperEl ?? edge?.edgeEl) as
      | HTMLElement
      | undefined;
    if (!el) return;

    const meta = parseEdgeMetadata(edge.unknownData?.ccoding);
    if (!meta) return;

    const attrs = edgeAttributes(meta);
    this.setDataAttributes(el, attrs);
  }

  /**
   * Set data attributes on a DOM element from an attribute map.
   * Keys like "data-ccoding-kind" become el.dataset.ccodingKind.
   * Undefined values cause the attribute to be removed.
   */
  private setDataAttributes(
    el: HTMLElement,
    attrs: Record<string, string | undefined>,
  ): void {
    for (const [key, value] of Object.entries(attrs)) {
      // Convert "data-ccoding-kind" → "ccodingKind" for dataset
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run tests/canvas-patcher.test.ts
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add src/canvas-patcher.ts tests/canvas-patcher.test.ts && git commit -m "feat(obsidian): add CanvasPatcher with monkey-around prototype patching"
```

---

### Task 4: Rewrite styles.css with data-attribute selectors

**Files:**
- Rewrite: `obsidian-plugin/styles.css`

- [ ] **Step 1: Rewrite styles.css**

Replace the entire content of `obsidian-plugin/styles.css` with:

```css
/* styles.css — CooperativeCoding Obsidian Plugin
 *
 * All styling via data-attribute selectors set by canvas-patcher.
 * No DOM injection — badges/banners use CSS pseudo-elements.
 * Uses Obsidian CSS variables for theming compatibility.
 */

/* ============================================
   Base transitions for smooth state changes
   ============================================ */

.canvas-node[data-ccoding-kind] {
  transition: opacity 0.2s ease;
}

.canvas-node[data-ccoding-kind] > .canvas-node-container {
  transition: border-style 0.2s ease, border-color 0.2s ease, box-shadow 0.3s ease;
}

/* ============================================
   Kind-based borders
   ============================================ */

.canvas-node[data-ccoding-kind="class"] > .canvas-node-container {
  border-color: #8b5cf6;
}

.canvas-node[data-ccoding-kind="interface"] > .canvas-node-container {
  border-color: #8b5cf6;
  border-style: dashed;
}

.canvas-node[data-ccoding-kind="method"] > .canvas-node-container {
  border-color: #f97316;
  border-radius: 12px;
}

.canvas-node[data-ccoding-kind="field"] > .canvas-node-container {
  border-color: #3b82f6;
  border-radius: 12px;
}

.canvas-node[data-ccoding-kind="package"] > .canvas-node-container {
  border-color: #22c55e;
}

.canvas-node[data-ccoding-kind="module"] > .canvas-node-container {
  border-color: #22c55e;
}

/* ============================================
   Status-based treatment
   ============================================ */

/* Proposed (ghost) nodes */
.canvas-node[data-ccoding-status="proposed"] > .canvas-node-container {
  border-style: dashed !important;
}

.canvas-node[data-ccoding-status="proposed"] {
  opacity: 0.7;
}

/* Rejected nodes */
.canvas-node[data-ccoding-status="rejected"] {
  opacity: 0.3;
}

.canvas-node[data-ccoding-rejected-hidden] {
  display: none !important;
}

/* Stale nodes */
.canvas-node[data-ccoding-status="stale"] > .canvas-node-container {
  border-color: #ca8a04;
}

.canvas-node[data-ccoding-status="stale"] {
  opacity: 0.5;
}

/* ============================================
   Pseudo-element badges and banners
   ============================================ */

/* Shared badge/banner styling */
.canvas-node[data-ccoding-stereotype] > .canvas-node-container::before,
.canvas-node[data-ccoding-stereotype] > .canvas-node-container::after,
.canvas-node[data-ccoding-status="proposed"] > .canvas-node-container::before,
.canvas-node[data-ccoding-status="stale"] > .canvas-node-container::before {
  display: block;
  width: 100%;
  text-align: center;
  font-size: var(--font-smallest);
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 2px 8px;
  box-sizing: border-box;
}

/* Stereotype badge — default position: ::before (when no status banner) */
.canvas-node[data-ccoding-status="accepted"][data-ccoding-stereotype] > .canvas-node-container::before,
.canvas-node:not([data-ccoding-status])[data-ccoding-stereotype] > .canvas-node-container::before {
  content: "\00AB" attr(data-ccoding-stereotype) "\00BB";
  color: var(--text-on-accent);
  background: var(--interactive-accent);
}

/* Stereotype badge — fallback position: ::after (when ::before is taken by status banner) */
.canvas-node[data-ccoding-status="proposed"][data-ccoding-stereotype] > .canvas-node-container::after,
.canvas-node[data-ccoding-status="stale"][data-ccoding-stereotype] > .canvas-node-container::after {
  content: "\00AB" attr(data-ccoding-stereotype) "\00BB";
  color: var(--text-on-accent);
  background: var(--interactive-accent);
}

/* PROPOSED banner */
.canvas-node[data-ccoding-status="proposed"] > .canvas-node-container::before {
  content: "PROPOSED";
  color: var(--text-on-accent);
  background: var(--interactive-accent);
  opacity: 0.85;
  letter-spacing: 1px;
  padding: 4px 8px;
}

/* STALE banner */
.canvas-node[data-ccoding-status="stale"] > .canvas-node-container::before {
  content: "STALE";
  color: var(--text-on-accent);
  background: var(--text-warning);
  letter-spacing: 1px;
  padding: 4px 8px;
}

/* ============================================
   Edge styling by relation type
   ============================================ */

.canvas-edge[data-ccoding-relation="inherits"] path {
  stroke: #e2e8f0;
  stroke-width: 2px;
}

.canvas-edge[data-ccoding-relation="implements"] path {
  stroke: #e2e8f0;
  stroke-width: 2px;
  stroke-dasharray: 6 4;
}

.canvas-edge[data-ccoding-relation="composes"] path {
  stroke: #8b5cf6;
  stroke-width: 2px;
}

.canvas-edge[data-ccoding-relation="depends"] path {
  stroke: #64748b;
  stroke-width: 1px;
  stroke-dasharray: 6 4;
}

.canvas-edge[data-ccoding-relation="calls"] path {
  stroke: #f97316;
  stroke-width: 1px;
  stroke-dasharray: 2 3;
}

.canvas-edge[data-ccoding-relation="detail"] path {
  stroke: #3b82f6;
  stroke-width: 1px;
}

.canvas-edge[data-ccoding-relation="context"] path {
  stroke: #475569;
  stroke-width: 1px;
}

/* Ghost edges */
.canvas-edge[data-ccoding-status="proposed"] {
  opacity: 0.7;
}

.canvas-edge[data-ccoding-status="proposed"] path {
  stroke-dasharray: 8 4 !important;
}

/* ============================================
   Context node highlighting (on selection)
   ============================================ */

.canvas-node[data-ccoding-context-highlight] > .canvas-node-container {
  box-shadow: 0 0 8px 2px var(--interactive-accent) !important;
}

.canvas-edge[data-ccoding-context-highlight] path {
  stroke: var(--interactive-accent) !important;
  stroke-width: 2px !important;
}

/* ============================================
   Status bar
   ============================================ */

.ccoding-status-bar {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ccoding-status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-error);
}

.ccoding-status-dot.is-connected {
  background: var(--text-success, #4ade80);
}
```

**Note on behavioral change:** The old `patches.ts` only applied stereotype badges when `meta.kind === "class"`. The new CSS applies stereotype badges to ANY node with `data-ccoding-stereotype` regardless of kind. This is an intentional expansion — stereotypes like `enum` and `protocol` make sense on interfaces and modules too.

**Note on SVG arrow markers:** The spec mentions SVG `<defs>` injection for custom arrow marker shapes. This is deferred to a follow-up task — the current implementation gets all styling working via CSS first. Arrow markers can be added later by extending the patcher's `attach()` method to inject a `<defs>` block into the canvas SVG element.

- [ ] **Step 2: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add styles.css && git commit -m "refactor(obsidian): rewrite styles.css with data-attribute selectors and pseudo-elements"
```

---

### Task 5: Simplify context highlighter to use data attributes

**Files:**
- Modify: `obsidian-plugin/src/highlight/context.ts`
- Modify: `obsidian-plugin/tests/highlight/context.test.ts`

- [ ] **Step 1: Update the tests**

Replace the entire content of `obsidian-plugin/tests/highlight/context.test.ts` with:

```typescript
// tests/highlight/context.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { ContextHighlighter } from "../../src/highlight/context";

function makeCanvasData(edges: any[]) {
  return { edges };
}

/** Create a mock canvas object with nodes and edges Maps. */
function mockCanvas(
  nodes: Array<{ id: string; nodeEl: any }>,
  edges: Array<{ id: string; lineGroupEl: any }>,
) {
  return {
    nodes: new Map(nodes.map((n) => [n.id, n])),
    edges: new Map(edges.map((e) => [e.id, e])),
  };
}

/** Create a mock DOM element with dataset support. */
function mockElement() {
  const dataset: Record<string, string | undefined> = {};
  return { dataset } as any;
}

describe("ContextHighlighter", () => {
  let highlighter: ContextHighlighter;

  beforeEach(() => {
    highlighter = new ContextHighlighter();
  });

  it("builds cache from context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
      { id: "e2", fromNode: "b", toNode: "ctx2", ccoding: { relation: "context" } },
      { id: "e3", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);
    // Cache built without errors — tested via onSelectionChange below
  });

  it("highlights context nodes via data attributes on selection", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
    ]);
    highlighter.buildCache(data);

    const nodeA = { id: "a", nodeEl: mockElement() };
    const nodeCtx = { id: "ctx1", nodeEl: mockElement() };
    const edgeE1 = { id: "e1", lineGroupEl: mockElement() };
    const canvas = mockCanvas([nodeA, nodeCtx], [edgeE1]);
    highlighter.attach(canvas);

    highlighter.onSelectionChange("a");
    expect(nodeCtx.nodeEl.dataset.ccodingContextHighlight).toBe("true");
    expect(edgeE1.lineGroupEl.dataset.ccodingContextHighlight).toBe("true");
  });

  it("clears highlights on selection change", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
    ]);
    highlighter.buildCache(data);

    const nodeCtx = { id: "ctx1", nodeEl: mockElement() };
    const canvas = mockCanvas(
      [{ id: "a", nodeEl: mockElement() }, nodeCtx],
      [{ id: "e1", lineGroupEl: mockElement() }],
    );
    highlighter.attach(canvas);

    highlighter.onSelectionChange("a");
    expect(nodeCtx.nodeEl.dataset.ccodingContextHighlight).toBe("true");

    highlighter.onSelectionChange(null);
    expect(nodeCtx.nodeEl.dataset.ccodingContextHighlight).toBeUndefined();
  });

  it("ignores non-context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);

    const nodeB = { id: "b", nodeEl: mockElement() };
    const canvas = mockCanvas([{ id: "a", nodeEl: mockElement() }, nodeB], []);
    highlighter.attach(canvas);

    highlighter.onSelectionChange("a");
    expect(nodeB.nodeEl.dataset.ccodingContextHighlight).toBeUndefined();
  });

  it("handles empty canvas data", () => {
    highlighter.buildCache({ edges: [] });
    highlighter.buildCache(null);
    highlighter.buildCache(undefined);
    // Should not throw
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run tests/highlight/context.test.ts
```

Expected: FAIL — highlighter still uses `classList`

- [ ] **Step 3: Update the context highlighter implementation**

Replace the entire content of `obsidian-plugin/src/highlight/context.ts` with:

```typescript
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run tests/highlight/context.test.ts
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add src/highlight/context.ts tests/highlight/context.test.ts && git commit -m "refactor(obsidian): simplify context highlighter to use data attributes"
```

---

### Task 6: Update main.ts — replace injector with patcher

**Files:**
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Update imports**

In `src/main.ts`, replace the import lines:

Replace:
```typescript
import { StyleInjector } from "./styling/injector";
```

With:
```typescript
import { CanvasPatcher } from "./canvas-patcher";
```

- [ ] **Step 2: Update class properties**

Replace the property declaration:
```typescript
  injector!: StyleInjector;
```

With:
```typescript
  patcher!: CanvasPatcher;
```

- [ ] **Step 3: Update onload()**

Replace in `onload()`:
```typescript
    this.injector = new StyleInjector(this.settings);
```

With:
```typescript
    this.patcher = new CanvasPatcher(this, this.settings);
```

- [ ] **Step 4: Update onunload()**

In `onunload()`, remove:
```typescript
    this.injector.detach();
```

(The patcher's cleanup is handled automatically by `plugin.register()`.)

- [ ] **Step 5: Update saveSettings()**

Replace:
```typescript
    this.injector?.updateSettings(this.settings);
```

With:
```typescript
    this.patcher?.updateSettings(this.settings);
```

- [ ] **Step 6: Update tryAttachToCanvas()**

In `tryAttachToCanvas()`, replace:
```typescript
    this.injector.attach(canvasEl, canvas);
```

With:
```typescript
    this.patcher.attach(canvas);
```

Remove the `canvasEl` variable declaration and its null check (lines 447-448 in current `main.ts`), as it is only used by the injector which is being replaced. The patcher's `attach()` only needs the `canvas` object. Remove:
```typescript
    const canvasEl = view.contentEl?.querySelector(".canvas") as HTMLElement;
    if (!canvasEl) return;
```

- [ ] **Step 7: Update refreshCanvas()**

Replace the entire `refreshCanvas()` method body with:
```typescript
  private refreshCanvas(): void {
    this.highlighter.detach();
    setTimeout(() => {
      this.tryAttachToCanvas();
      this.updateProposalCount();
    }, 150);
  }
```

The `injector.detach()` call is removed — the `setData()` patch handles reloads automatically. The highlighter still needs to detach/reattach to rebuild its cache.

- [ ] **Step 8: Run all tests**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run
```

Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add src/main.ts && git commit -m "refactor(obsidian): replace StyleInjector with CanvasPatcher in main.ts"
```

---

### Task 7: Delete old files and update integration test

**Files:**
- Delete: `obsidian-plugin/src/styling/injector.ts`
- Delete: `obsidian-plugin/src/styling/patches.ts`
- Modify: `obsidian-plugin/tests/integration.test.ts`

- [ ] **Step 1: Delete the old styling files**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && rm src/styling/injector.ts src/styling/patches.ts
```

- [ ] **Step 2: Update integration test**

Replace the entire content of `obsidian-plugin/tests/integration.test.ts` with:

```typescript
// tests/integration.test.ts
import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { parseCcodingMetadata, parseEdgeMetadata } from "../src/types";
import { nodeAttributes, edgeAttributes } from "../src/styling/class-mapper";
import { buildGraph, assignLayers, computePositions } from "../src/layout/graph";
import type { LayoutNode, LayoutEdge } from "../src/layout/graph";

// Use fixture file if available, otherwise create inline fixture
const fixturePath = join(__dirname, "../fixtures/sample.canvas");
const fixture = existsSync(fixturePath)
  ? JSON.parse(readFileSync(fixturePath, "utf-8"))
  : {
      nodes: [
        { id: "n1", x: 0, y: 0, width: 320, height: 280, type: "text", text: "DocumentParser", ccoding: { kind: "class", stereotype: "protocol", status: "accepted", qualifiedName: "parser.DocumentParser", language: "python", source: "src/parser.py" } },
        { id: "n2", x: 0, y: 0, width: 320, height: 200, type: "text", text: "parse", ccoding: { kind: "method", status: "accepted", qualifiedName: "parser.DocumentParser.parse" } },
        { id: "n3", x: 0, y: 0, width: 320, height: 280, type: "text", text: "CacheManager", ccoding: { kind: "class", status: "proposed", proposedBy: "agent", proposalRationale: "Extract caching", layoutPending: true } },
      ],
      edges: [
        { id: "e1", fromNode: "n1", toNode: "n2", ccoding: { relation: "detail", status: "accepted" } },
        { id: "e2", fromNode: "n1", toNode: "n3", ccoding: { relation: "composes", status: "proposed" } },
      ],
    };

describe("Integration: fixture → attributes → layout", () => {
  it("parses all ccoding nodes from fixture", () => {
    const ccodingNodes = fixture.nodes.filter(
      (n: any) => parseCcodingMetadata(n.ccoding) !== null,
    );
    expect(ccodingNodes.length).toBeGreaterThan(0);
  });

  it("generates data attributes for fixture nodes", () => {
    for (const node of fixture.nodes) {
      const meta = parseCcodingMetadata(node.ccoding);
      if (!meta) continue;
      const attrs = nodeAttributes(meta, false);
      expect(attrs["data-ccoding-status"]).toBeDefined();
    }
  });

  it("generates data attributes for fixture edges", () => {
    for (const edge of fixture.edges) {
      const meta = parseEdgeMetadata(edge.ccoding);
      if (!meta) continue;
      const attrs = edgeAttributes(meta);
      expect(attrs["data-ccoding-relation"]).toBeDefined();
    }
  });

  it("runs layout on fixture without errors", () => {
    const layoutNodes: LayoutNode[] = fixture.nodes
      .filter((n: any) => parseCcodingMetadata(n.ccoding))
      .map((n: any) => ({
        id: n.id,
        kind: n.ccoding?.kind,
        width: n.width || 320,
        height: n.height || 280,
      }));

    const layoutEdges: LayoutEdge[] = fixture.edges
      .filter((e: any) => parseEdgeMetadata(e.ccoding))
      .map((e: any) => ({
        id: e.id,
        from: e.fromNode,
        to: e.toNode,
        relation: e.ccoding.relation,
      }));

    const graph = buildGraph(layoutNodes, layoutEdges);
    const layers = assignLayers(graph);
    const positions = computePositions(layoutNodes, layers, graph);

    expect(positions.length).toBe(layoutNodes.length);
    for (const pos of positions) {
      expect(typeof pos.x).toBe("number");
      expect(typeof pos.y).toBe("number");
    }
  });
});
```

- [ ] **Step 3: Run all tests**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run
```

Expected: All tests PASS (no imports of deleted files remain)

- [ ] **Step 4: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add -A && git commit -m "refactor(obsidian): delete injector.ts and patches.ts, update integration test"
```

---

### Task 8: Update Obsidian mock and add register() method

**Files:**
- Modify: `obsidian-plugin/tests/__mocks__/obsidian.ts`

- [ ] **Step 1: Add register() to Plugin mock**

In `tests/__mocks__/obsidian.ts`, add the `register` method to the `Plugin` class:

```typescript
  register(_fn: () => void): void {}
```

Add it after the `registerEvent` method.

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add tests/__mocks__/obsidian.ts && git commit -m "test(obsidian): add register() to Plugin mock for canvas-patcher compatibility"
```

---

### Task 9: Build and deploy

**Files:**
- No new files

- [ ] **Step 1: Build the plugin**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npm run build
```

Expected: Build succeeds, `main.js` is generated

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && npx vitest run
```

Expected: All tests PASS

- [ ] **Step 3: Deploy to test vault**

```bash
cp /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin/main.js /Users/giosullutrone/Documents/shared/projects/ocr_fusion/.obsidian/plugins/obsidian-plugin/main.js
cp /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin/styles.css /Users/giosullutrone/Documents/shared/projects/ocr_fusion/.obsidian/plugins/obsidian-plugin/styles.css
cp /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin/manifest.json /Users/giosullutrone/Documents/shared/projects/ocr_fusion/.obsidian/plugins/obsidian-plugin/manifest.json
```

- [ ] **Step 4: Commit**

```bash
cd /Users/giosullutrone/Documents/shared/projects/CCode/obsidian-plugin && git add -A && git commit -m "chore(obsidian): build and deploy native integration refactoring"
```

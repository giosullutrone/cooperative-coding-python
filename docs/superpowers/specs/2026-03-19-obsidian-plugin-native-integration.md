# Obsidian Plugin Native Integration Refactoring

**Goal:** Refactor the CooperativeCoding Obsidian plugin to feel like a native part of Obsidian rather than a bolted-on extension, by replacing the MutationObserver + DOM injection approach with canvas prototype patching and CSS-only styling.

**Architecture:** Use `monkey-around` to patch Canvas prototype methods for data-attribute exposure on node/edge DOM elements. Move all visual treatment to CSS (attribute selectors + pseudo-elements). Keep native Obsidian APIs (workspace events for menus, vault events for file watching, Modal/Setting/Notice for UI).

**Tech Stack:** TypeScript, Obsidian API, `monkey-around` (canvas patching), CSS attribute selectors + pseudo-elements

---

## 1. Problem Statement

The current plugin implementation fights Obsidian's rendering rather than working with it:

- **MutationObserver** in `styling/injector.ts` fires on every DOM mutation (including scroll/zoom), walks the DOM tree to find canvas nodes, and applies classes. This is performance-heavy and fragile against Obsidian's virtualized node rendering.
- **DOM patches** in `styling/patches.ts` inject custom `<div>` elements (stereotype badges, proposed/stale banners, rationale footers) into canvas nodes. These get destroyed when nodes scroll off-screen, cause flicker on re-render, and conflict with Obsidian's internal layout.
- **`data-ccoding-processed` markers** track which nodes have been styled, requiring a full `reprocessAll()` cycle when settings change.

The result is a visual layer painted on top of Obsidian that clashes with native features rather than integrating with them.

## 2. Solution: Hybrid Canvas Patching

### 2.1 Canvas Prototype Patching with `monkey-around`

**New file:** `src/canvas-patcher.ts`

**New dependency:** `monkey-around` (~1KB, same library used by Advanced Canvas and other major Obsidian canvas plugins)

Patch three canvas prototype methods:

| Method | Patch behavior |
|--------|---------------|
| `Canvas.addNode()` | After original call, read `node.unknownData?.ccoding`, set `data-ccoding-kind`, `data-ccoding-status`, `data-ccoding-stereotype` on `node.nodeEl` |
| `Canvas.addEdge()` | After original call, read `edge.unknownData?.ccoding`, set `data-ccoding-relation`, `data-ccoding-status` on the edge SVG element (`edge.lineGroupEl ?? edge.wrapperEl ?? edge.edgeEl`) |
| `Canvas.setData()` | After original call, iterate all nodes/edges and re-apply data attributes (handles initial load, reload after CLI operations, and external file changes) |

Each patch follows the pattern:
```typescript
around(canvas, {
  addNode(next) {
    return function (node: any) {
      const result = next.call(this, node);
      applyNodeAttributes(node);
      return result;
    };
  },
});
```

The `around()` function from `monkey-around` returns an uninstaller registered with `plugin.register()` for automatic cleanup on plugin unload.

**Waiting for canvas:** The patcher hooks into the workspace `layout-change` event (already used in `main.ts`) to detect when a canvas view becomes active. On first canvas view, it patches the canvas instance's prototype. This follows the same pattern as the existing `tryAttachToCanvas()` but replaces the MutationObserver attachment with prototype patching.

### 2.2 CSS-Only Styling (replaces DOM injection)

**Deleted files:**
- `src/styling/injector.ts` — MutationObserver, rAF batching, processed-node tracking
- `src/styling/patches.ts` — DOM element injection for badges/banners/footers

**All visual treatment moves to `styles.css`** using CSS attribute selectors and pseudo-elements:

#### Node Styling (attribute selectors)

```css
/* Kind-based borders */
.canvas-node[data-ccoding-kind="class"] > .canvas-node-container { border-color: #8b5cf6; }
.canvas-node[data-ccoding-kind="method"] > .canvas-node-container { border-color: #f97316; border-radius: 12px; }
.canvas-node[data-ccoding-kind="field"] > .canvas-node-container { border-color: #3b82f6; border-radius: 12px; }
.canvas-node[data-ccoding-kind="package"] > .canvas-node-container { border-color: #22c55e; }
.canvas-node[data-ccoding-kind="interface"] > .canvas-node-container { border-color: #8b5cf6; border-style: dashed; }

/* Status-based treatment */
.canvas-node[data-ccoding-status="proposed"] > .canvas-node-container { border-style: dashed; opacity: 0.7; }
.canvas-node[data-ccoding-status="rejected"] { opacity: 0.3; }
.canvas-node[data-ccoding-status="rejected"][data-ccoding-rejected-hidden] { display: none; }
.canvas-node[data-ccoding-status="stale"] > .canvas-node-container { border-color: #ca8a04; }
.canvas-node[data-ccoding-status="stale"] { opacity: 0.5; }
```

#### Pseudo-Element Replacements

| Former DOM patch | CSS replacement |
|-----------------|-----------------|
| Stereotype badge `<div>` | `::before` on `.canvas-node[data-ccoding-stereotype] > .canvas-node-container` with `content: "«" attr(data-ccoding-stereotype) "»"` |
| "PROPOSED" banner `<div>` | `::before` on `.canvas-node[data-ccoding-status="proposed"] > .canvas-node-container` with `content: "PROPOSED"` |
| "STALE" banner `<div>` | `::before` on `.canvas-node[data-ccoding-status="stale"] > .canvas-node-container` with `content: "STALE"` |
| Rationale footer `<div>` | Dropped — rationale remains accessible via "Show rationale" context menu item |

When both stereotype and status need a pseudo-element, combine them: status banners (`PROPOSED`/`STALE`) take `::before`, stereotype badge takes `::after`. Obsidian's `.canvas-node-container` does not use `::before` or `::after` pseudo-elements (verified against Obsidian 1.5.x), so both are safe to use.

CSS for the `::after` stereotype case (when node also has a status banner on `::before`):
```css
/* Stereotype as ::after — used when ::before is taken by a status banner */
.canvas-node[data-ccoding-status="proposed"][data-ccoding-stereotype] > .canvas-node-container::after,
.canvas-node[data-ccoding-status="stale"][data-ccoding-stereotype] > .canvas-node-container::after {
  content: "«" attr(data-ccoding-stereotype) "»";
  /* same styling as the ::before stereotype badge */
}
/* Stereotype as ::before — default when no status banner competes */
.canvas-node[data-ccoding-status="accepted"][data-ccoding-stereotype] > .canvas-node-container::before,
.canvas-node:not([data-ccoding-status])[data-ccoding-stereotype] > .canvas-node-container::before {
  content: "«" attr(data-ccoding-stereotype) "»";
}
```

#### Edge Styling (attribute selectors)

Data attributes are set on the edge wrapper element (`edge.lineGroupEl ?? edge.wrapperEl ?? edge.edgeEl`). CSS targets descendant `<path>` elements via the wrapper's attributes:

```css
/* Relation-based styles — attribute on wrapper, style on descendant path */
.canvas-edge[data-ccoding-relation="inherits"] path { stroke: #e2e8f0; stroke-width: 2px; }
.canvas-edge[data-ccoding-relation="implements"] path { stroke: #e2e8f0; stroke-width: 2px; stroke-dasharray: 6 4; }
.canvas-edge[data-ccoding-relation="composes"] path { stroke: #8b5cf6; stroke-width: 2px; }
.canvas-edge[data-ccoding-relation="depends"] path { stroke: #64748b; stroke-width: 1px; stroke-dasharray: 6 4; }
.canvas-edge[data-ccoding-relation="calls"] path { stroke: #f97316; stroke-width: 1px; stroke-dasharray: 2 3; }
.canvas-edge[data-ccoding-relation="detail"] path { stroke: #3b82f6; stroke-width: 1px; }
.canvas-edge[data-ccoding-relation="context"] path { stroke: #475569; stroke-width: 1px; }

/* Ghost edges */
.canvas-edge[data-ccoding-status="proposed"] { opacity: 0.7; }
```

#### SVG Arrow Markers

SVG `<defs>` for custom arrow marker shapes (hollow triangle for inherits/implements, filled diamond for composes, open arrow for depends, filled arrow for calls, circle for detail) are injected once into the canvas SVG element by the patcher on attach. This is the one piece of DOM injection that remains — CSS cannot define SVG marker shapes. The patcher injects the `<defs>` block once and CSS references them via `marker-end`/`marker-start` properties targeting `[data-ccoding-relation]` selectors.

#### Context Highlighting (attribute selectors)

```css
.canvas-node[data-ccoding-context-highlight] > .canvas-node-container {
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.5);
}
```

### 2.3 Simplified `class-mapper.ts`

The class-mapper is renamed conceptually to an "attribute mapper". Instead of returning CSS class arrays, it returns a `Record<string, string>` of data-attribute key-value pairs:

```typescript
function nodeAttributes(meta: CcodingMetadata, hideRejected: boolean): Record<string, string>;
function edgeAttributes(meta: EdgeMetadata): Record<string, string>;
```

**Full attribute map returned by `nodeAttributes()`:**

| Key | Value | Source |
|-----|-------|--------|
| `data-ccoding-kind` | `"class"`, `"method"`, `"field"`, `"package"`, `"interface"`, `"module"` | `meta.kind` |
| `data-ccoding-status` | `"accepted"`, `"proposed"`, `"rejected"`, `"stale"` | `meta.status` |
| `data-ccoding-stereotype` | `"protocol"`, `"abstract"`, `"dataclass"`, `"enum"` | `meta.stereotype` (omitted if not set) |
| `data-ccoding-rejected-hidden` | `"true"` | Only when `meta.status === "rejected"` AND `hideRejected === true` |

**Full attribute map returned by `edgeAttributes()`:**

| Key | Value | Source |
|-----|-------|--------|
| `data-ccoding-relation` | `"inherits"`, `"implements"`, `"composes"`, `"depends"`, `"calls"`, `"detail"`, `"context"` | `meta.relation` |
| `data-ccoding-status` | `"accepted"`, `"proposed"`, `"rejected"` | `meta.status` |

The patcher calls these functions and applies the returned attributes to DOM elements. Attributes with `undefined` values are not set (and are removed if previously present).

### 2.4 Patcher Public API and `main.ts` Wiring

The `CanvasPatcher` class exposes this interface to `main.ts`:

```typescript
class CanvasPatcher {
  constructor(plugin: Plugin, settings: PluginSettings);

  /** Attach to a canvas view — patches prototype methods, applies attributes to existing nodes/edges. */
  attach(canvas: any): void;

  /** Re-apply all data attributes to current canvas nodes/edges (call after settings change). */
  reapplyAll(): void;

  /** Update the settings reference (e.g., after user changes showRejectedNodes). */
  updateSettings(settings: PluginSettings): void;
}
```

**Cleanup:** `monkey-around`'s `around()` returns an uninstaller function. The patcher registers this via `plugin.register()`, so Obsidian's plugin lifecycle handles cleanup automatically on unload. No explicit `detach()` needed.

**How `main.ts` changes:**

| Current code | New code |
|-------------|----------|
| `this.injector = new StyleInjector(this.settings)` | `this.patcher = new CanvasPatcher(this, this.settings)` |
| `this.injector.attach(canvasEl, canvas)` in `tryAttachToCanvas()` | `this.patcher.attach(canvas)` in `tryAttachToCanvas()` |
| `this.injector.detach()` in `refreshCanvas()` | Removed — `setData()` patch handles reloads automatically. `refreshCanvas()` only needs to call `tryAttachToCanvas()` for re-attaching highlighter/watcher. |
| `this.injector.detach()` in `onunload()` | Removed — `plugin.register()` handles cleanup |
| `this.injector.updateSettings()` in `saveSettings()` | `this.patcher.updateSettings(this.settings)` which calls `reapplyAll()` internally when relevant settings change |

**`setData()` patch timing:** Obsidian may re-create DOM elements asynchronously after `setData()` completes. The `addNode()`/`addEdge()` patches catch newly-created nodes/edges during this process. The `setData()` patch serves as a belt-and-suspenders fallback — it applies attributes after a `requestAnimationFrame` delay to allow Obsidian's rendering cycle to settle. If some nodes already received attributes from `addNode()`, re-applying is a no-op (idempotent).

### 2.5 Simplified Context Highlighter

The `ContextHighlighter` keeps its edge-to-node cache and selection logic but changes DOM manipulation from `classList.add/remove` to `dataset` property access:

- Highlight: `el.dataset.ccodingContextHighlight = "true"`
- Clear: `delete el.dataset.ccodingContextHighlight`

CSS handles the visual treatment via `[data-ccoding-context-highlight]` selectors.

### 2.6 What Stays Unchanged

These components already use native Obsidian APIs correctly:

| Component | Obsidian API used |
|-----------|-------------------|
| Context menus | `canvas:node-menu`, `canvas:edge-menu`, `canvas:menu` workspace events |
| File watching | `vault.on('modify'/'delete'/'rename')` + Obsidian `debounce()` |
| Settings UI | `PluginSettingTab`, `Setting` |
| User feedback | `Notice`, `Modal` |
| CLI bridge | `child_process.execFile` (Node API, required for desktop plugin) |
| Status bar | `addStatusBarItem()` |
| Layout algorithm | Pure logic, no Obsidian API |
| Async queue | Pure logic |
| Ghost modals | Obsidian `Modal` + `Setting` |
| Ghost actions | Calls CLI bridge, shows `Notice` |

### 2.7 Handling `showRejectedNodes` Setting

When `showRejectedNodes` changes, the patcher needs to update rejected node visibility. The patcher's `setData()` hook already re-applies all attributes on reload. For settings changes specifically, the patcher exposes a `reapplyAll()` method that iterates all current canvas nodes/edges and re-sets their data attributes. This replaces the old `reprocessAll()` in the injector.

The CSS handles visibility:
- `showRejectedNodes: true` → nodes get `data-ccoding-status="rejected"` → CSS shows at 0.3 opacity
- `showRejectedNodes: false` → nodes additionally get a `data-ccoding-rejected-hidden` attribute → CSS sets `display: none`

## 3. Module Structure

### Before (14 files, ~2100 LOC)

```
src/
  main.ts              (516 lines)
  types.ts             (98 lines)
  settings.ts          (93 lines)
  bridge/cli.ts        (264 lines)
  bridge/queue.ts      (39 lines)
  styling/injector.ts  (184 lines)  ← DELETE
  styling/patches.ts   (64 lines)   ← DELETE
  styling/class-mapper.ts (51 lines)
  ghost/actions.ts     (109 lines)
  ghost/modals.ts      (287 lines)
  watcher/canvas-watcher.ts (74 lines)
  highlight/context.ts (113 lines)
  layout/graph.ts      (192 lines)
  layout/hierarchical.ts (170 lines)
```

### After (13 files, ~1850 LOC estimated)

```
src/
  main.ts              (~350 lines, slimmed)
  types.ts             (98 lines, unchanged)
  settings.ts          (93 lines, unchanged)
  bridge/cli.ts        (264 lines, unchanged)
  bridge/queue.ts      (39 lines, unchanged)
  canvas-patcher.ts    (~120 lines, NEW)
  styling/class-mapper.ts (~45 lines, simplified)
  ghost/actions.ts     (109 lines, unchanged)
  ghost/modals.ts      (287 lines, unchanged)
  watcher/canvas-watcher.ts (74 lines, unchanged)
  highlight/context.ts (~80 lines, simplified)
  layout/graph.ts      (192 lines, unchanged)
  layout/hierarchical.ts (170 lines, unchanged)
```

**Net change:** -1 file, ~250 fewer lines of code, zero DOM injection.

## 4. Testing

### Modified Tests

- `tests/styling/class-mapper.test.ts` — assertions change from class arrays to attribute maps
- `tests/highlight/context.test.ts` — assertions change from `classList.add/remove` to `dataset` properties
- `tests/integration.test.ts` — minor updates if it references class-mapper output format

### New Test

- `tests/canvas-patcher.test.ts` — mock a canvas object with `addNode`/`addEdge` methods and mock node/edge objects with `nodeEl`/`lineGroupEl` DOM-like objects. Verify that after the patcher wraps these methods, calling them sets the expected data attributes. Test `reapplyAll()` for settings changes.

### Unchanged Tests

- `tests/bridge/cli.test.ts`
- `tests/bridge/queue.test.ts`
- `tests/ghost/actions.test.ts`
- `tests/layout/graph.test.ts`
- `tests/layout/hierarchical.test.ts`
- `tests/types.test.ts`

### Deleted Tests

- None currently exist for `injector.ts` or `patches.ts`, so no test deletion needed.

## 5. Migration Steps (High Level)

1. Add `monkey-around` dependency
2. Create `canvas-patcher.ts` with `addNode`/`addEdge`/`setData` patches
3. Rewrite `styles.css` — attribute selectors + pseudo-elements for all visual treatment
4. Simplify `class-mapper.ts` to return attribute maps
5. Simplify `context.ts` to use data attributes
6. Update `main.ts` — replace injector wiring with patcher init, remove injector imports
7. Delete `styling/injector.ts` and `styling/patches.ts`
8. Update tests
9. Build and verify

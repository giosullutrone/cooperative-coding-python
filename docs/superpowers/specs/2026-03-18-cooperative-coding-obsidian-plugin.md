# CooperativeCoding — Obsidian Plugin

*Obsidian canvas plugin for rendering, interacting with, and managing CooperativeCoding canvases.*

**Parent spec:** [CooperativeCoding Open Specification](2026-03-18-cooperative-coding-design.md)
**Sibling spec:** [CLI Extension](2026-03-18-cooperative-coding-cli-extension.md)

---

## 1. Overview

The Obsidian plugin is the visual layer of the CooperativeCoding system. It reads `.canvas` files containing `ccoding` metadata and renders them with kind-specific styling, provides ghost node accept/reject UX via context menus, and delegates all data operations to the `ccoding` CLI via shell execution.

The plugin is **self-contained** — it does not depend on Advanced Canvas or any other community plugin. It coexists safely with other canvas plugins by namespacing all custom CSS classes and data attributes under `ccoding-`.

**What the plugin owns:**
- Visual rendering of ccoding nodes and edges (styling, badges, ghost treatment)
- Ghost node interaction UX (context menu accept/reject/reconsider)
- Communication with the `ccoding` CLI (shell exec bridge)
- Canvas file watching and reload on external change
- Manual hierarchical layout of nodes
- Context node highlighting on selection

**What the plugin does NOT own:**
- Parsing or generating code (CLI's job)
- Sync state management (CLI's job)
- Conflict resolution logic (CLI's job)
- Canvas data model or JSON format (defined by core spec + JSON Canvas v1.0)

**Design note on event emission:** The core spec requires canvas tools to "emit events when nodes or edges are created, modified, or deleted (for sync triggers)." In the CooperativeCoding system, sync is on-demand — the user or agent explicitly triggers `ccoding sync`. The plugin does not automatically emit events or trigger sync on every canvas edit. Instead, the user runs sync when ready, and the CLI detects what changed via hash comparison. This avoids disruptive mid-editing syncs and keeps the plugin simpler. The `CooperativeCoding: Sync` command palette entry provides the manual trigger.

---

## 2. Plugin Structure

### 2.1 Package Identity

- **Plugin ID:** `obsidian-cooperative-coding`
- **Language:** TypeScript
- **Build:** esbuild (Obsidian standard toolchain)
- **Target:** Obsidian Desktop (requires `child_process` for CLI bridge)
- **Min Obsidian version:** Current stable at time of implementation

### 2.2 Internal Modules

| Module | File(s) | Responsibility |
|---|---|---|
| Entry | `main.ts` | Plugin lifecycle (`onload`/`onunload`), registers all components |
| Settings | `settings.ts` | Plugin settings tab, configuration persistence |
| Styling | `styling/injector.ts`, `styling/patches.ts`, `styles.css` | CSS injection + DOM patches for node/edge visuals |
| Ghost UX | `ghost/menu.ts`, `ghost/actions.ts` | Context menu registration, ghost interaction flow |
| CLI Bridge | `bridge/cli.ts` | Shell exec wrapper for `ccoding` CLI commands |
| Watcher | `watcher/canvas-watcher.ts` | File watcher on `.canvas` files, triggers reload |
| Layout | `layout/hierarchical.ts` | Hierarchical layout algorithm |

### 2.3 Lifecycle

**`onload()`:**
1. Load plugin settings from Obsidian's data store
2. Inject ccoding CSS stylesheet into the document
3. Register context menu items for ghost node actions
4. Register command palette commands (layout, accept-all, reject-all)
5. Register canvas view event listener to detect when a canvas opens
6. Verify `ccoding` CLI availability (background check, non-blocking)

**Canvas view opens:**
1. Scan all canvas nodes for `ccoding` metadata
2. Apply CSS classes based on `ccoding.kind` and `ccoding.status`
3. Inject DOM patches (stereotype badges, proposed banners, rationale footers)
4. Start file watcher on the active `.canvas` file
5. Register selection change listener for context node highlighting

**Canvas view closes:**
1. Stop file watcher
2. Remove selection change listener
3. Clean up injected DOM elements

**`onunload()`:**
1. Remove injected CSS
2. Stop all file watchers
3. Clean up all DOM patches
4. Deregister commands and menu items

### 2.4 Settings

| Setting | Type | Default | Description |
|---|---|---|---|
| `ccodingPath` | `string` | `""` (auto-detect from PATH) | Path to `ccoding` CLI binary |
| `projectRoot` | `string` | `""` (auto-detect from `.ccoding/` dir) | Project root directory |
| `showRejectedNodes` | `boolean` | `false` | Whether to show rejected ghost nodes |
| `autoReloadOnChange` | `boolean` | `true` | Reload canvas when file changes externally |
| `commandTimeout` | `number` | `30000` | CLI command timeout in milliseconds |

Auto-detection logic for `projectRoot`: walk up from the vault root looking for a `.ccoding/` directory. If not found, use the vault root itself.

---

## 3. Node Styling

The plugin applies visual treatment to canvas nodes based on their `ccoding` metadata. Styling uses a hybrid approach: CSS for colors/borders/opacity, minimal DOM patching for badges and custom elements that CSS alone cannot create.

### 3.1 CSS Class Mapping

The plugin reads `ccoding.kind` and `ccoding.status` from each node and adds CSS classes to the corresponding DOM element:

| Metadata | CSS Class | Visual Effect |
|---|---|---|
| `kind: "class"` | `ccoding-node-class` | Purple border (`#8b5cf6`), square corners |
| `kind: "method"` | `ccoding-node-method` | Orange border (`#f97316`), rounded corners (`12px`) |
| `kind: "field"` | `ccoding-node-field` | Blue border (`#3b82f6`), rounded corners (`12px`) |
| `kind: "package"` | `ccoding-node-package` | Green border (`#22c55e`), applied to group node |
| `status: "proposed"` | `ccoding-ghost` | Dashed border, reduced opacity (`0.7`) |
| `status: "rejected"` | `ccoding-rejected` | Greyed out (`opacity: 0.3`), or `display: none` if `showRejectedNodes` is false |
| `status: "accepted"` | `ccoding-accepted` | Normal rendering (default) |
| stale (no code backing) | `ccoding-stale` | Muted yellow border (`#ca8a04`), strikethrough on node title, "STALE" banner |

Classes are combined: a proposed class node gets both `ccoding-node-class` and `ccoding-ghost`.

**Nodes with `ccoding.status` but no `ccoding.kind`** (proposed context nodes):
Context nodes proposed by the agent carry a minimal `ccoding` object with only `status` and `proposedBy` (no `kind`). These nodes receive the `ccoding-ghost` class (dashed border, reduced opacity) and the proposed banner, but no kind-specific border color — they render with Obsidian's default node styling plus the ghost treatment overlay.

### 3.2 DOM Patches

DOM patches are injected elements that CSS alone cannot produce. The plugin applies these after Obsidian renders each canvas node:

**Stereotype badge** (class nodes with `ccoding.stereotype`):
- A small label injected at the top of the node: `«protocol»`, `«dataclass»`, `«abstract»`, `«enum»`
- Styled with the node's border color, smaller font, centered

**Proposed banner** (ghost nodes with `status: "proposed"`):
- A hatched-pattern banner at the top of the node reading "PROPOSED"
- Visually distinct from the stereotype badge — signals that this node needs review

**Rationale footer** (ghost nodes with `proposalRationale`):
- A footer section at the bottom of the node displaying the agent's rationale
- Prefixed with a lightbulb indicator and "Agent rationale:"
- Styled with a slightly different background to separate it from node content

**Stale banner** (nodes marked as stale by the sync engine):
- A banner at the top of the node reading "STALE" with a muted yellow background
- Indicates the backing code was deleted or moved — the node has no code counterpart
- The user can remove the node manually or keep it as a historical reference

**Detail marker** (the `●` symbol):
- The `●` marker in field/method lists already exists in the structured markdown content
- No DOM patching needed — it renders naturally as part of the node text
- The plugin may optionally make `●` markers clickable to navigate to the detail node (future enhancement)

### 3.3 Re-rendering

DOM patches must be re-applied when:
- The canvas is reloaded (file watcher trigger)
- The user scrolls and nodes enter/exit the viewport (Obsidian virtualizes off-screen nodes)
- A node's content changes (user edits the structured markdown)

The plugin uses a `MutationObserver` on the canvas container to detect when node DOM elements are added or modified, then applies patches to any unpatched ccoding nodes. This handles viewport virtualization and dynamic updates without polling.

---

## 4. Edge Styling

Edge styling is CSS-only. The plugin adds CSS classes to edge SVG elements and injects SVG marker definitions for arrow/endpoint styles.

### 4.1 CSS Class Mapping

| `ccoding.relation` | CSS Class | Line Style | Color |
|---|---|---|---|
| `inherits` | `ccoding-edge-inherits` | Solid, 2px | White (`#e2e8f0`) |
| `implements` | `ccoding-edge-implements` | Dashed, 2px | White (`#e2e8f0`) |
| `composes` | `ccoding-edge-composes` | Solid, 2px | Purple (`#8b5cf6`) |
| `depends` | `ccoding-edge-depends` | Dashed, 1px | Gray (`#64748b`) |
| `calls` | `ccoding-edge-calls` | Dotted, 1px | Orange (`#f97316`) |
| `detail` | `ccoding-edge-detail` | Solid, 1px | Blue (`#3b82f6`) |
| `context` | `ccoding-edge-context` | Solid, 1px | Dim gray (`#475569`) |

Ghost edges (`status: "proposed"`) additionally receive the `ccoding-ghost` class, reducing opacity to `0.7`.

### 4.2 SVG Arrow Markers

Arrow markers are defined as SVG `<defs>` and injected once into the canvas SVG container on canvas open:

| Relation | End Marker |
|---|---|
| `inherits` | Hollow triangle |
| `implements` | Hollow triangle |
| `composes` | Filled diamond (at source end) |
| `depends` | Open arrow |
| `calls` | Filled arrow |
| `detail` | Circle |
| `context` | None |

Markers are referenced via `marker-end` (or `marker-start` for `composes`) CSS properties on the edge path elements.

### 4.3 Edge Labels

Edge labels are rendered natively by Obsidian's canvas. The `label` field on edges carries rich descriptive text (e.g., `"plugins — Applied sequentially during parse(). Order matters."`). No custom rendering needed — Obsidian displays these as-is.

---

## 5. Ghost Node UX

Users interact with ghost nodes through Obsidian's native context menu. The plugin registers menu items that appear conditionally based on the node's `ccoding.status`.

### 5.1 Context Menu Items

**On nodes with `status: "proposed"`:**

| Menu Item | Action |
|---|---|
| Accept | Call `ccoding accept <node-id>` |
| Reject | Call `ccoding reject <node-id>` |
| Show Rationale | Display `proposalRationale` in an Obsidian Notice |

**On nodes with `status: "rejected"`:**

| Menu Item | Action |
|---|---|
| Reconsider | Call `ccoding reconsider <node-id>` |

**On edges with `status: "proposed"`:**

| Menu Item | Action |
|---|---|
| Accept | Call `ccoding accept <edge-id>` |
| Reject | Call `ccoding reject <edge-id>` |

**On edges with `status: "rejected"`:**

| Menu Item | Action |
|---|---|
| Reconsider | Call `ccoding reconsider <edge-id>` |

Accepted nodes and edges show no ghost-specific menu items.

### 5.2 Command Palette Commands

| Command | Action |
|---|---|
| `CooperativeCoding: Accept all proposals` | Call `ccoding accept-all` |
| `CooperativeCoding: Reject all proposals` | Call `ccoding reject-all` |
| `CooperativeCoding: Layout canvas` | Run hierarchical layout on current canvas |
| `CooperativeCoding: Sync` | Call `ccoding sync` |
| `CooperativeCoding: Check sync status` | Call `ccoding status`, show result in Notice |

### 5.3 Interaction Flow

When the user triggers an action (e.g., "Accept" from context menu):

1. Plugin reads the node/edge `id` from the canvas data
2. Plugin calls `ccoding accept <id>` via the CLI bridge (Section 6)
3. CLI updates the `.canvas` file (changes `status`, handles cascades)
4. File watcher (Section 7) detects the change
5. Canvas reloads from disk
6. Plugin re-applies styling — the node now renders as accepted (solid border, full opacity, no proposed banner)

**User feedback during the operation:**
- While the CLI command is running, the plugin shows an Obsidian `Notice`: "Accepting proposal..."
- On success: Notice disappears (the visual change on the node is feedback enough)
- On failure: Notice shows the error message from stderr

### 5.4 Error Handling

| Error | User-Facing Message |
|---|---|
| `ccoding` CLI not found | "ccoding CLI not found. Install it or set the path in plugin settings." |
| CLI returns non-zero exit | Show stderr content in a Notice |
| Canvas file locked/busy | Retry once after 500ms, then show "Canvas file is busy. Try again." |
| No `.ccoding/` project found | "No CooperativeCoding project found. Run `ccoding init` first." |
| Command timeout (>30s) | "Command timed out. The operation may still be running." |

---

## 6. CLI Bridge

The CLI bridge is a TypeScript module that wraps Node's `child_process.execFile` to invoke `ccoding` CLI commands.

### 6.1 Interface

```typescript
interface CommandResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
}

class CcodingBridge {
  constructor(settings: PluginSettings);

  // Ghost operations
  accept(id: string): Promise<CommandResult>;
  reject(id: string): Promise<CommandResult>;
  reconsider(id: string): Promise<CommandResult>;
  acceptAll(): Promise<CommandResult>;
  rejectAll(): Promise<CommandResult>;

  // Sync operations
  sync(): Promise<CommandResult>;
  status(): Promise<CommandResult>;
  check(): Promise<CommandResult>;

  // Utilities
  isAvailable(): Promise<boolean>;
  getVersion(): Promise<string>;
}
```

### 6.2 Execution Details

- **`execFile` not `exec`**: arguments are passed as an array, avoiding shell injection. The CLI binary path and each argument are separate parameters.
- **Working directory**: set to the detected project root (directory containing `.ccoding/`).
- **`--project` flag**: passed automatically from plugin settings so the CLI resolves the correct project.
- **Timeout**: 30 seconds per command. Configurable in settings for slow systems.
- **Environment**: inherits the system PATH. The `ccodingPath` setting overrides auto-detection.

### 6.3 Command Queuing

Commands are executed sequentially through a mutex/queue to prevent race conditions. The CLI reads and writes `.canvas` and `.ccoding/sync-state.json` — concurrent writes would corrupt state.

**Queue behavior:**
- Commands are enqueued in order of request
- Only one command runs at a time
- If a command is already running, new commands wait
- The queue processes FIFO
- No timeout on queue wait (commands complete quickly; the 30s timeout handles stuck commands)

### 6.4 Startup Validation

On plugin load, the bridge runs `ccoding --help` to verify the CLI is installed and reachable. If the check fails:
- A persistent Notice is shown: "ccoding CLI not found. Install it or set the path in CooperativeCoding plugin settings."
- All ghost menu items and commands are disabled (they'd fail anyway)
- The plugin still loads and applies visual styling (read-only mode)

---

## 7. Canvas Watcher

The watcher detects external changes to `.canvas` files and triggers a canvas reload.

### 7.1 Mechanism

- Uses Node's `fs.watch()` on the active `.canvas` file path
- **Debounced**: 300ms delay to coalesce rapid writes. The CLI may write the canvas file and sync state in quick succession; the debounce ensures a single reload after both writes complete.
- **External-only**: the plugin sets an internal `isWriting` flag before invoking CLI commands and clears it after the file watcher fires. Changes detected while `isWriting` is true still trigger a reload (since the CLI wrote the file), but the flag prevents infinite reload loops if the plugin itself ever writes to the canvas.

### 7.2 Lifecycle

| Event | Action |
|---|---|
| Canvas view opens | Start watching that `.canvas` file |
| Canvas view closes | Stop watcher |
| User switches canvas | Stop old watcher, start new watcher |
| External change detected | Trigger canvas re-read via Obsidian API |
| Plugin unloads | Stop all watchers |

### 7.3 Reload Mechanism

When an external change is detected, the plugin reloads the canvas from disk. The exact Obsidian API call should be determined during implementation — possibilities include reading the file via `app.vault.read()` and repopulating the canvas data, or triggering the canvas view's internal reload method. The intent is to **re-read the file from disk**, not to save in-memory state.

After reload, the `MutationObserver` (Section 3.3) detects new DOM elements and re-applies styling and DOM patches.

### 7.4 Edge Cases

- **Git operations**: `git checkout`, `git merge`, `git pull` may change the canvas file. The watcher handles these — the custom merge driver (from the CLI's git integration) ensures valid JSON after merges.
- **File deletion**: if the `.canvas` file is deleted, the watcher stops and the plugin shows a Notice.
- **Rapid successive changes**: the 300ms debounce coalesces these into a single reload.
- **`autoReloadOnChange` disabled**: when the user disables this setting, the watcher still runs but skips the reload. The user can manually reload by closing and reopening the canvas.

---

## 8. Hierarchical Layout

The layout engine arranges ccoding nodes in a top-to-bottom hierarchy based on relationship edges. It runs only on manual trigger — never automatically.

### 8.1 Triggers

| Trigger | Scope |
|---|---|
| Command palette: `CooperativeCoding: Layout canvas` | All nodes with `ccoding.layoutPending: true` |
| Context menu on canvas background: `Layout all nodes` | All ccoding nodes regardless of `layoutPending` |

### 8.2 Algorithm

**Step 1: Build directed graph.**
Extract nodes and edges from the canvas. Only ccoding edges with relation types that imply hierarchy are used: `inherits`, `implements`, `composes`, `detail`. Other relations (`depends`, `calls`, `context`) do not influence layout.

**Step 2: Topological sort for layer assignment.**
Nodes with no incoming hierarchical edges are assigned to layer 0 (top). Each subsequent layer contains nodes whose parents are all in previous layers. Cycles (which shouldn't exist in well-formed designs) are broken by placing the cycle-causing node at the deeper layer.

**Step 3: Order nodes within layers.**
Within each layer, nodes are ordered to minimize edge crossings using the barycenter heuristic: each node is positioned at the average x-coordinate of its connected nodes in adjacent layers.

**Step 4: Assign positions.**
- Vertical position: `layer * LAYER_GAP` where `LAYER_GAP = 400px`
- Horizontal position: centered within the layer, spaced by `NODE_GAP = 100px`

**Step 5: Position detail nodes.**
Method and field detail nodes are positioned directly below their parent class node, offset by `DETAIL_OFFSET_Y = 350px`. Multiple detail nodes for the same parent are arranged horizontally.

**Step 6: Position context nodes.**
Context nodes (connected via `context` edges) are positioned to the right of their linked ccoding node, offset by `CONTEXT_OFFSET_X = 350px`. Multiple context nodes stack vertically.

**Step 7: Position package groups.**
Nodes sharing the same package prefix in `ccoding.qualifiedName` are grouped. The group node (if it exists) is sized to contain its children with padding.

**Step 8: Clear `layoutPending`.**
After positioning, the plugin updates each positioned node's `ccoding.layoutPending` to `false` in the canvas data and saves.

### 8.3 Spacing Constants

| Constant | Value | Purpose |
|---|---|---|
| `LAYER_GAP` | `400px` | Vertical distance between hierarchy layers |
| `NODE_GAP` | `100px` | Horizontal distance between nodes in the same layer |
| `DETAIL_OFFSET_Y` | `350px` | Vertical offset for detail nodes below parent |
| `CONTEXT_OFFSET_X` | `350px` | Horizontal offset for context nodes beside target |
| `GROUP_PADDING` | `40px` | Padding inside package group boundaries |

### 8.4 Constraints

- **Respects manual positioning**: by default, only moves nodes with `layoutPending: true`. The "Layout all" command overrides this.
- **Excludes rejected/hidden nodes**: when `showRejectedNodes` is false, rejected nodes and their edges are excluded from layout calculations entirely. This prevents gaps from invisible nodes.
- **No animation**: nodes snap to new positions. Obsidian's canvas doesn't provide animation primitives for node movement.
- **No edge routing**: Obsidian handles edge path drawing natively. The layout only positions nodes; edges follow.

---

## 9. Context Node Highlighting

When a user selects a ccoding node, connected context nodes (linked via `context` edges) are visually highlighted.

### 9.1 Mechanism

1. Plugin registers a listener on Obsidian's canvas selection change event
2. On selection change, read the selected node's ID
3. Query the canvas data for all edges with `ccoding.relation: "context"` connecting to/from the selected node
4. Add CSS class `ccoding-context-highlight` to the DOM elements of those connected context nodes
5. Also add `ccoding-context-highlight` to the connecting `context` edge SVG elements
6. On deselection (or selecting a different node), remove all `ccoding-context-highlight` classes

### 9.2 Visual Treatment

| Element | Normal | Highlighted |
|---|---|---|
| Context node | Default Obsidian styling | Subtle glow border (soft blue outline, `box-shadow`) |
| Context edge | Dim gray (`#475569`), 1px | White (`#e2e8f0`), 1.5px |

### 9.3 Performance

The plugin caches the edge-to-node mapping (context edges indexed by node ID) when the canvas loads. Selection change lookups are O(1) hash map reads, not full edge scans. The cache is rebuilt on canvas reload.

---

## 10. Compatibility

### 10.1 Namespacing

All custom additions are namespaced to avoid conflicts with other canvas plugins:
- CSS classes: prefixed with `ccoding-` (e.g., `ccoding-node-class`, `ccoding-ghost`)
- Data attributes: prefixed with `data-ccoding-` (e.g., `data-ccoding-kind`, `data-ccoding-status`)
- SVG marker IDs: prefixed with `ccoding-marker-` (e.g., `ccoding-marker-inherits`)
- Command IDs: prefixed with `cooperative-coding:` (e.g., `cooperative-coding:layout`)

### 10.2 Advanced Canvas Compatibility

The plugin does not depend on Advanced Canvas but coexists with it:
- Advanced Canvas adds its own CSS classes and features (stickers, text formatting, etc.)
- The ccoding plugin only modifies nodes that have `ccoding` metadata — it never touches plain canvas nodes
- If both plugins add CSS to the same node, the ccoding styling takes precedence for border color/style (using higher specificity selectors) while leaving Advanced Canvas features like stickers intact

### 10.3 JSON Canvas v1.0 Compliance

The plugin reads and writes standard JSON Canvas v1.0 format. The `ccoding` field on nodes and edges is an extension — it lives alongside standard fields and is ignored by tools that don't understand it. The plugin preserves all unknown fields during save (round-trip fidelity), matching the CLI's behavior.

### 10.4 Live Bridge

The CLI extension includes an `ObsidianBridge` that can execute JavaScript in Obsidian's runtime via `obsidian eval`. This bridge operates through Obsidian's built-in eval mechanism and does not require plugin cooperation — the JS snippets call Obsidian's native APIs directly (e.g., triggering a canvas save/reload). The plugin does not need to expose a JavaScript API for the live bridge. The two integration paths are:

- **CLI → Plugin direction**: CLI writes to `.canvas` file; plugin's file watcher detects the change and reloads. For live operations, the CLI may additionally call `obsidian eval` to trigger an immediate reload.
- **Plugin → CLI direction**: Plugin calls `ccoding` CLI commands via shell exec (Section 6).

### 10.5 Obsidian API Stability

The plugin uses Obsidian's public plugin API where available. For canvas-specific operations (node DOM access, selection events), it relies on semi-public canvas APIs that may change between Obsidian versions. These touch points are isolated in `styling/patches.ts` so that Obsidian updates only require changes in one file.

---

## 11. Testing Strategy

### 11.1 Unit Tests

| Module | What to Test |
|---|---|
| CLI Bridge | Command construction, argument escaping, result parsing, queue ordering |
| Layout | Layer assignment, node ordering, position calculation, detail/context offset |
| Styling | CSS class mapping from metadata, patch application conditions |
| Watcher | Debounce behavior, external-vs-internal detection |

Unit tests run in Node.js without Obsidian. They test pure logic — no DOM, no Obsidian API.

### 11.2 Integration Tests

Integration tests require a running Obsidian instance (manual or semi-automated):

- Load a canvas with ccoding nodes → verify correct CSS classes applied
- Right-click a ghost node → verify context menu items appear
- Accept a ghost node → verify CLI called, canvas reloads, node re-renders as accepted
- External file change → verify canvas reloads
- Layout command → verify nodes repositioned

### 11.3 Test Fixtures

Reuse the existing canvas fixtures from the CLI package (`tests/fixtures/sample.canvas`, `tests/fixtures/sample_no_ccoding.canvas`) to ensure consistency between CLI and plugin.

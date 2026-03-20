# Obsidian Plugin Spec Gap Fixes — Design Spec

## Goal

Close all identified gaps between the CooperativeCoding specification and the Obsidian plugin, bringing the plugin to full spec compliance and adding workflow enhancements that the spec recommends or permits.

## Architecture

Nine independent additions to the existing plugin, all following established patterns (Modal classes for input, async action wrappers for CLI, data-attribute CSS styling, pure helpers for canvas manipulation). No structural refactoring — each gap is a contained addition.

## Scope

### High Priority (Spec Compliance)

1. Context edge creation UI
2. Conflict resolution modal

### Medium Priority (Spec Alignment)

3. Stereotype extensibility (open set)
4. Language binding selection
5. Selective bulk operations
6. Stale node recovery workflow
7. Module kind direct creation

### Low Priority (Polish)

8. Detail node demotion
9. Sync state display

## Compatibility

No backward compatibility required. The plugin is used internally only. Changes can assume the current CLI output format and break existing patterns freely.

---

## 1. Context Edge Creation UI

### Problem

The spec requires `context` edges connecting plain canvas notes (design rationale, references, decision logs) to code-element nodes. The plugin renders and highlights context edges bidirectionally (via ContextHighlighter), but provides no UI to create them. Users must edit the `.canvas` JSON manually.

### Spec Requirements

- `context` edges link a context node to a CooperativeCoding code-element node (01-data-model.md §6).
- At least one endpoint MUST be a context node — a node without `ccoding.kind` (01-data-model.md §6, validity rules).
- Context edges are canvas-only; they are never synced to code (01-data-model.md §6).
- Direction is flexible — either node may be `fromNode`.

### Design

**New modal: `ConnectContextModal`**

- Fields:
  - **Target node** — dropdown of eligible nodes. If source is a plain node, show only ccoding nodes. If source is a ccoding node, show only plain nodes. Reuses the node-picker pattern from `AddRelationModal`.
  - **Label** — optional text field for edge description.
- Validation: enforced by filtering — at least one endpoint is always a context node.
- On submit: calls `addEdgeToCanvasData()` with `relation: "context"`. No CLI involved.

**Context menu entries:**

- On plain canvas nodes (no `ccoding.kind`): "Connect to code element..." → opens `ConnectContextModal` with source = this node.
- On ccoding nodes (existing menu section near "Add relation..."): "Attach context note..." → opens `ConnectContextModal` with source = this node.

**Files:**

- New: `ghost/modals.ts` — add `ConnectContextModal` class
- Modify: `main.ts` — add context menu entries for plain nodes and ccoding nodes

---

## 2. Conflict Resolution Modal

### Problem

The spec says sync MUST detect conflicts, MUST NOT silently overwrite either side, and SHOULD present both versions for human resolution. Currently the plugin shows raw CLI error text in a notice.

### Spec Requirements

- A conflict exists when both canvas and code representations changed since last sync (03-sync.md §6.1).
- Conflicts MUST be detected at element level, not file level (03-sync.md §6.2).
- Implementations MUST NOT silently overwrite either side (03-sync.md §6.3).
- Implementations SHOULD present both versions to the human (03-sync.md §6.3).
- Implementations MAY offer automatic resolution strategies but MUST NOT apply without explicit human selection (03-sync.md §6.3).
- Permitted strategies: three-way merge, side selection, defer (03-sync.md §6.4).

### Design

**Sync output parsing:**

New file: `sync/conflict-parser.ts`

- `parseConflictOutput(result: CommandResult) → ConflictInfo[]`
- Each `ConflictInfo`: `qualifiedName`, `elementKind`, `canvasSummary`, `codeSummary`, `elementId`
- Parses the `ccoding sync` stdout/stderr for conflict markers in the CLI's output format.

**New modal: `ConflictResolutionModal`**

- Opens automatically when `syncCanvas` detects conflicts in the sync output (replaces the raw error notice).
- Layout: scrollable list of conflicted elements. Each conflict is an expandable section:
  - **Header:** Element qualified name + kind badge (e.g., "UserService (class)")
  - **Expanded content:**
    - "Canvas version:" — summary of the canvas-side changes
    - "Code version:" — summary of the code-side changes
    - Three buttons: **Keep Canvas** | **Keep Code** | **Skip**
  - After choosing, section collapses with a resolution indicator.
- Footer: **Apply Resolutions** button (disabled until all non-skipped conflicts have a choice) and **Skip All** button.

**Resolution execution:**

- "Keep Canvas": no action — the canvas already has the desired version. Next sync propagates canvas → code.
- "Keep Code": call `ccoding show <qualifiedName>` to get the code version, then `ccoding set-text <elementId>` to update the canvas node to match code. Next sync sees no diff.
- "Skip": leave as-is. Element stays conflicted until next manual resolution.
- After applying resolutions, re-run `ccoding sync` to complete the non-conflicted changes.

**Files:**

- New: `sync/conflict-parser.ts` — conflict output parsing
- New: `sync/conflict-modal.ts` — `ConflictResolutionModal` class
- Modify: `ghost/actions.ts` — `syncCanvas` action checks for conflicts and opens modal instead of showing raw notice
- Modify: `bridge/cli.ts` — add `show(qualifiedName)` and `setText(nodeId, text)` if not already present

---

## 3. Stereotype Extensibility

### Problem

The spec says "Implementations MUST NOT reject unknown stereotype values — the set is open and extensible." The plugin hardcodes 5 values in a dropdown: `""`, `protocol`, `abstract`, `dataclass`, `enum`.

### Spec Requirements

- Stereotype is an open set (01-data-model.md §3).
- Unknown stereotypes MUST NOT be rejected.
- Each language binding defines its recognized stereotypes; unrecognized stereotypes SHOULD be preserved and displayed as-is.

### Design

In all modals with a stereotype field (`ProposeModal`, `CreateElementModal`, `ElevateModal`):

- Replace the dropdown with a **text input** using Obsidian's `.addText()` API.
- Set placeholder: `"e.g., protocol, abstract, dataclass, enum"`.
- Attach an HTML `<datalist>` element to the input for autocomplete suggestions with the common values.
- Accept any string value or blank — no validation/rejection.

**Files:**

- Modify: `ghost/modals.ts` — change stereotype input in `ProposeModal`, `CreateElementModal`, `ElevateModal`

---

## 4. Language Binding Selection

### Problem

The spec supports per-canvas `language` default and per-node `language` override. The plugin has no UI for either.

### Spec Requirements

- Canvas-level `language` field is OPTIONAL; sets default for all nodes (01-data-model.md, canvas metadata).
- Individual nodes MAY override with their own `ccoding.language` field (01-data-model.md §3).
- When omitted, implementations SHOULD infer from the canvas-level default or the binding in use.

### Design

**Plugin settings:**

- Add a "Default language" text field to the settings tab (e.g., `python`, `typescript`, `go`).
- This value is written to the canvas-level context node metadata when the user sets it while a canvas is active.

**Per-node language override:**

- In `CreateElementModal` and `ProposeModal`, add an optional "Language" text field.
- When blank: inherits the canvas/settings default.
- When filled: sets `ccoding.language` on the individual node.

**Files:**

- Modify: `settings.ts` — add `defaultLanguage` setting
- Modify: `types.ts` — add `defaultLanguage` to `PluginSettings`
- Modify: `ghost/modals.ts` — add language field to `CreateElementModal`, `ProposeModal`
- Modify: `main.ts` — write canvas-level language metadata when setting changes

---

## 5. Selective Bulk Operations

### Problem

The plugin only supports global `accept-all` / `reject-all`. The spec permits selective bulk operations for accepting/rejecting subsets of proposals.

### Spec Requirements

- Implementations MAY support selective bulk operations (02-lifecycle.md §6.3).
- No specific selection mechanism prescribed — implementation's choice.
- Same transition rules as individual operations.

### Design

**New modal: `BulkOperationsModal`**

- Triggered via new command `bulk-manage` and canvas background context menu entry "Manage proposals..."
- Layout:
  - Filter bar at top: kind filter dropdown (all / class / interface / edge / etc.), text search field.
  - Scrollable list of all proposed elements. Each row: checkbox, element name, kind badge, proposer info.
  - Select All / Deselect All toggle.
- Footer: **Accept Selected** | **Reject Selected** | **Cancel**
- On submit: iterates selected items, calls `bridge.accept(id)` or `bridge.reject(id)` for each sequentially via the existing CLI queue.
- After completion: refreshes canvas.

**Files:**

- New: `ghost/bulk-modal.ts` — `BulkOperationsModal` class
- Modify: `main.ts` — register `bulk-manage` command, add background context menu entry

---

## 6. Stale Node Recovery Workflow

### Problem

The "Restore" context menu action immediately calls `bridge.restore(id)` with no guidance. The spec says the human decides whether to restore code, re-link, or remove the stale node.

### Spec Requirements

- Implementations MUST NOT auto-delete stale nodes (01-data-model.md §4).
- The human decides whether to remove, update, or restore (01-data-model.md §4).
- `stale → accepted` transition triggered by sync detecting code restoration or human manually re-linking (02-lifecycle.md §4.3).

### Design

**New modal: `RestoreModal`**

Replace the direct `bridge.restore(id)` call with a modal that presents the three options:

- Shows: element's `qualifiedName`, expected source path, explanation ("This element's code was deleted or moved.").
- Options:
  - **Restore code** — regenerate the code file. Calls `bridge.restore(id)`.
  - **Re-link** — text field for new qualified name or source path. Updates the node's `ccoding.qualifiedName` and/or `ccoding.source` in canvas data, then syncs.
  - **Remove from canvas** — deletes the stale node and its edges from canvas data. Direct canvas manipulation, no CLI.

**Files:**

- New: `ghost/restore-modal.ts` — `RestoreModal` class
- Modify: `main.ts` — stale node context menu opens `RestoreModal` instead of calling action directly

---

## 7. Module Kind Direct Creation

### Problem

The background context menu and command palette offer direct creation for class, interface, and package — but not module. Module is only available via CLI propose.

### Spec Requirements

- `module` is an extended kind for single-file modules/compilation units (01-data-model.md §3).
- No special creation workflow — same as classes.

### Design

- Add `add-module` command mirroring `add-class` / `add-interface` / `add-package`.
- Add "Add module..." entry to canvas background context menu alongside the existing kind entries.
- Both use `CreateElementModal` with `kind: "module"` — the modal already supports all `NODE_KINDS`.

**Files:**

- Modify: `main.ts` — register `add-module` command, add background context menu entry

---

## 8. Detail Node Demotion

### Problem

Users can promote methods/fields to detail nodes but cannot demote them back. The spec maps demotion to node deletion — the code-side method/field is untouched.

### Design

- Add context menu option on method/field detail nodes: "Remove detail node"
- Confirmation notice: "This will remove the detail node from the canvas. The method/field remains in the code. Continue?"
- On confirm: remove the node and its `detail` edge from canvas data. Direct canvas manipulation, no CLI.

**Files:**

- Modify: `main.ts` — add context menu entry for detail nodes (kind = method or field)

---

## 9. Sync State Display

### Problem

The spec says implementations SHOULD log/display what sync changed after each cycle. Currently sync output is shown as raw CLI text.

### Spec Requirements

- Implementations SHOULD log or display what sync changed so the user can verify (03-sync.md §8.3).

### Design

**Sync output parsing:**

New file: `sync/output-parser.ts`

- `parseSyncOutput(result: CommandResult) → SyncSummary`
- `SyncSummary`: `nodesUpdated`, `edgesAdded`, `edgesRemoved`, `conflicts`, `rawOutput`

**Structured notices:**

- After `ccoding sync` completes successfully: show a notice "Sync complete: 3 nodes updated, 1 edge added, 0 conflicts" instead of raw text.
- After `ccoding status`: show structured summary instead of raw CLI output.
- Both notices are clickable — clicking opens a modal with the full raw output for debugging.

**Files:**

- New: `sync/output-parser.ts` — sync and status output parsing
- Modify: `ghost/actions.ts` — use parser for sync and status actions, show structured notices

---

## File Summary

### New Files

| File | Purpose |
|------|---------|
| `sync/conflict-parser.ts` | Parse CLI sync output for conflict info |
| `sync/conflict-modal.ts` | `ConflictResolutionModal` class |
| `sync/output-parser.ts` | Parse CLI sync/status output for structured display |
| `ghost/bulk-modal.ts` | `BulkOperationsModal` for selective accept/reject |
| `ghost/restore-modal.ts` | `RestoreModal` for stale node recovery |

### Modified Files

| File | Changes |
|------|---------|
| `ghost/modals.ts` | Add `ConnectContextModal`, change stereotype to text+datalist, add language field |
| `ghost/actions.ts` | Sync action opens conflict modal, structured notices |
| `main.ts` | New commands (bulk-manage, add-module), new context menu entries (context edges, detail demotion, bulk manage), restore opens modal |
| `bridge/cli.ts` | Ensure `show()` and `setText()` methods exist |
| `settings.ts` | Add `defaultLanguage` setting |
| `types.ts` | Add `defaultLanguage` to `PluginSettings`, `ConflictInfo`, `SyncSummary` types |
| `styles.css` | No changes needed — existing data-attribute styling covers all new features |

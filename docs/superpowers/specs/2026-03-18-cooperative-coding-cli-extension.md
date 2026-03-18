# CooperativeCoding — CLI Extension (Python Package)

*Programmatic interface for canvas manipulation, bidirectional sync, and ghost node management.*

**Parent spec:** [CooperativeCoding Open Specification](2026-03-18-cooperative-coding-design.md)
**Language binding:** [Python Language Binding](2026-03-18-cooperative-coding-python-binding.md)

---

## 1. Overview

The CLI extension is the foundation of the CooperativeCoding reference implementation. It provides the sync engine, canvas manipulation, code parsing, and ghost node management that both the Obsidian plugin and the Claude Code skill depend on.

It ships as a Python package (`cooperative-coding`, import name `ccoding`) with two API surfaces:

1. **CLI** (`ccoding` command) — for humans and shell scripts
2. **Python API** (`import ccoding`) — for the Claude Code skill and other programmatic consumers

The Python API is the primary interface. The CLI is a thin wrapper — every CLI command maps to a public Python function. The Claude Code skill imports the library directly rather than shelling out.

### 1.1 Interaction Model: Hybrid

The CLI extension uses a hybrid approach for canvas interaction:

- **Direct JSON manipulation** for batch and offline operations (import, full sync, inspection). Reads and writes `.canvas` files as JSON. Works without Obsidian running.
- **Obsidian `eval` bridge** for live session operations (proposing ghost nodes, accepting/rejecting). Changes appear on the canvas in real-time via JavaScript executed in Obsidian's runtime.

Every live operation has a direct JSON fallback. If Obsidian isn't running, the operation writes to the `.canvas` file and succeeds silently. The live bridge is a UX enhancement, not a functional dependency.

### 1.2 Sync Timing: On-Demand with Smart Triggers

The sync engine does not run as a daemon. It runs at natural checkpoints:

- When the agent calls the Python API (every agent operation starts with a sync check)
- When the user runs any `ccoding` command (implicit freshness check)
- Via git pre-commit hook (validates canvas/code consistency before committing)

The Obsidian plugin handles live-side file watching. The CLI does not duplicate that responsibility.

---

## 2. Package Structure

```
ccoding/
├── __init__.py          # Public API re-exports
├── cli.py               # CLI entry point (ccoding command)
├── canvas/
│   ├── __init__.py
│   ├── model.py         # Canvas data model (Node, Edge, CcodingMetadata)
│   ├── reader.py        # Parse .canvas JSON → model objects
│   ├── writer.py        # Model objects → .canvas JSON
│   └── markdown.py      # Parse/generate structured markdown (node text)
├── code/
│   ├── __init__.py
│   ├── parser.py        # CodeParser protocol + PythonAstParser
│   └── generator.py     # Generate code skeletons from canvas nodes
├── sync/
│   ├── __init__.py
│   ├── engine.py        # Bidirectional sync orchestrator
│   ├── state.py         # .ccoding/sync-state.json management
│   ├── differ.py        # Diff canvas vs code, detect changes
│   └── conflict.py      # Conflict detection and resolution helpers
├── ghost/
│   ├── __init__.py
│   └── manager.py       # Propose, accept, reject ghost nodes/edges
├── live/
│   ├── __init__.py
│   └── obsidian.py      # Obsidian eval bridge (live operations)
├── git/
│   ├── __init__.py
│   ├── hooks.py         # Pre-commit hook logic
│   ├── merge.py         # Custom merge driver for .canvas files
│   └── diff.py          # Git-informed change detection
└── config.py            # Project config (.ccoding/config.json)
```

---

## 3. Canvas Engine

### 3.1 Data Model (`canvas/model.py`)

Core dataclasses mirroring JSON Canvas v1.0 + ccoding metadata:

- **`Canvas`** — top-level container: `nodes: list[Node]`, `edges: list[Edge]`
- **`Node`** — JSON Canvas fields (`id`, `type`, `x`, `y`, `width`, `height`, `text`) + `ccoding: CcodingMetadata | None`
- **`Edge`** — JSON Canvas fields (`id`, `fromNode`, `toNode`, `fromSide`, `toSide`, `label`) + `ccoding: EdgeMetadata | None`
- **`CcodingMetadata`** — `kind`, `stereotype`, `language`, `source`, `qualifiedName`, `status`, `proposedBy`, `proposalRationale`, `layoutPending`
- **`EdgeMetadata`** — `relation`, `status`, `proposedBy`, `proposalRationale`
- **`GroupNode`** — for `ccoding.kind: "package"`, extends Node with `label` and child containment

### 3.2 Reader / Writer (`canvas/reader.py`, `canvas/writer.py`)

- `read_canvas(path: Path) -> Canvas` — parse `.canvas` JSON, preserve unknown fields (forward-compatible with future JSON Canvas extensions and other tools like Advanced Canvas)
- `write_canvas(canvas: Canvas, path: Path) -> None` — serialize back to JSON, preserving field order and unknown fields that were read
- **Round-trip fidelity**: read then write produces identical JSON if no changes were made. This is critical — the engine must not corrupt fields from other tools.

### 3.3 Structured Markdown (`canvas/markdown.py`)

Parses and generates the structured markdown defined in the core spec (Section 3.3).

**Parsing:**

- `parse_class_node(text: str) -> ClassContent` — extracts stereotype, name, responsibility, fields list (with ● markers), methods list (with ● markers)
- `parse_method_node(text: str) -> MethodContent` — extracts name, responsibility, signature (IN/OUT/RAISES), pseudo code
- `parse_field_node(text: str) -> FieldContent` — extracts name, responsibility, type, constraints, default

**Rendering:**

- `render_class_node(content: ClassContent) -> str`
- `render_method_node(content: MethodContent) -> str`
- `render_field_node(content: FieldContent) -> str`

The parser is intentionally tolerant — handles missing sections, extra whitespace, and minor formatting variations. The renderer produces canonical formatting.

### 3.4 Node Lookup Helpers

Convenience methods on the `Canvas` object:

- `find_by_qualified_name(name: str) -> Node | None`
- `find_by_source(path: str) -> list[Node]`
- `find_detail_nodes(class_node_id: str) -> list[Node]`
- `edges_for(node_id: str) -> list[Edge]`
- `ghost_nodes() -> list[Node]` — all nodes with `status: "proposed"`

---

## 4. Code Parser

### 4.1 Parser Protocol (`code/parser.py`)

```python
class CodeParser(Protocol):
    def parse_file(self, path: Path) -> list[CodeElement]: ...
    def parse_directory(self, path: Path, recursive: bool = True) -> list[CodeElement]: ...
```

`CodeElement` is a union of:

- **`ClassElement`** — name, stereotype, base classes, docstring (parsed into sections), fields, methods, source path, line number
- **`MethodElement`** — name, parameters (name + type), return type, docstring (parsed into sections), decorators, is_abstract
- **`FieldElement`** — name, type annotation, default value, comment block (parsed into responsibility/constraints/default)
- **`ImportElement`** — what's imported, from where (used to infer `depends` edges)

The protocol makes it straightforward to add language-specific parsers later (e.g., `TreeSitterParser` for multi-language support) without changing the sync engine.

### 4.2 Python Implementation (`PythonAstParser`)

Uses `ast.parse()` + `ast.NodeVisitor`. Extraction rules follow the Python binding spec:

- **Stereotype inference**: `Protocol` base → `protocol`, `ABC` base → `abstract`, `@dataclass` decorator → `dataclass`, `Enum` base → `enum`, otherwise `class`
- **Method detection**: all `def` inside a class body. Skips dunder methods except architecturally significant ones: `__init__`, `__post_init__`, `__enter__`/`__exit__`, `__call__`, `__iter__`/`__next__`
- **Field detection**: class-level annotated assignments and `__init__` assignments with type annotations
- **Docstring parsing**: extracts Google-style sections including custom CooperativeCoding sections (`Responsibility:`, `Pseudo Code:`, `Collaborators:`, `Constraints:`)
- **Relationship inference**: base classes → `inherits`/`implements` edges; type annotations referencing project classes → `composes`/`depends` edges; import statements → `depends` edges

### 4.3 Docstring Section Parser

A shared utility that parses Google-style docstrings into `dict[str, str]` (section name → content). Handles standard sections (`Args`, `Returns`, `Raises`, `Attributes`) and custom sections (`Responsibility`, `Pseudo Code`, `Collaborators`, `Constraints`). Used by both the parser (reading code) and generator (writing code).

### 4.4 Code Generator (`code/generator.py`)

The inverse of parsing — generates Python source from canvas data:

- `generate_class(node: ClassContent, methods: list[MethodContent], fields: list[FieldContent]) -> str` — full class skeleton with docstring, field annotations, method stubs (`...` or `raise NotImplementedError` bodies)
- `generate_method(method: MethodContent) -> str` — method signature + full docstring with all sections
- `update_class(existing_source: str, changes: SyncDiff) -> str` — surgical updates to an existing file. Uses `ast` to locate exact positions, then string manipulation to preserve formatting outside changed regions.

Code generation rules from the Python binding spec:

- **File placement**: `ccoding.source` determines the file path. If not set, derived from `ccoding.qualifiedName` relative to the configured `sourceRoot`
- **Import management**: automatically adds required imports based on stereotypes, edges, and type annotations
- **Method stubs**: `...` body for protocol methods, `raise NotImplementedError` for abstract methods

---

## 5. Sync Engine

### 5.1 Sync State (`sync/state.py`)

The `.ccoding/sync-state.json` file stores per-element snapshots from the last successful sync:

```json
{
  "version": 1,
  "lastSync": "2026-03-18T14:30:00Z",
  "canvasFile": "design.canvas",
  "elements": {
    "parsers.document.DocumentParser": {
      "canvasHash": "a1b2c3",
      "codeHash": "d4e5f6",
      "canvasNodeId": "node-1",
      "sourcePath": "src/parsers/document.py",
      "lastSynced": "2026-03-18T14:30:00Z"
    }
  }
}
```

Hashes are computed from normalized content (stripped of whitespace variations, comment formatting) so that cosmetic changes don't trigger false conflicts.

### 5.2 Differ (`sync/differ.py`)

Compares current state against the sync snapshot to produce a `SyncDiff`:

- **`canvas_added`** — nodes on canvas with no sync state entry
- **`canvas_modified`** — canvas hash changed since last sync
- **`canvas_deleted`** — sync state entry exists but node gone from canvas
- **`code_added`** — elements in code with no sync state entry
- **`code_modified`** — code hash changed since last sync
- **`code_deleted`** — sync state entry exists but element gone from code
- **`conflicts`** — element changed on both sides since last sync
- **`in_sync`** — neither side changed

### 5.3 Conflict Detection (`sync/conflict.py`)

A conflict occurs when the same element's canvas hash AND code hash both differ from the sync state. The engine never silently resolves conflicts.

- `Conflict` object holds: `qualifiedName`, `canvasVersion`, `codeVersion`, `lastSyncedVersion`
- CLI presents both versions and asks the user to choose (keep canvas, keep code, or manual merge)
- Python API returns conflicts as data — the Claude Code skill can present them conversationally

### 5.4 Sync Orchestrator (`sync/engine.py`)

The `sync()` function runs this sequence:

1. Read current canvas and parse current code
2. Load sync state
3. Compute diff
4. If conflicts exist → stop, return conflicts for resolution
5. Apply non-conflicting changes:
   - `canvas_modified` → update code (re-generate affected sections)
   - `code_modified` → update canvas (update node text/metadata)
   - `canvas_added` (accepted nodes only) → generate code skeletons
   - `code_added` → create canvas nodes (with `layoutPending: true`)
   - `canvas_deleted` → mark code as deprecated (comment, not delete)
   - `code_deleted` → mark canvas node as stale (visual indicator)
6. Write updated canvas and code files
7. Update sync state with new hashes

**Key rules:**

- Ghost nodes (`status: "proposed"`) are never synced to code. They exist only on canvas until accepted.
- Accepting a ghost node transitions it to `accepted` and triggers code generation on the next sync.
- Deletions are always soft — canvas deletions deprecate code, code deletions mark canvas nodes stale. The human confirms hard deletes.

### 5.5 Import (`sync/engine.py`)

`import_codebase(source_dir: Path, canvas_path: Path) -> Canvas` is a special-case entry point:

1. Parses all code in `source_dir` using the configured `CodeParser`
2. Generates canvas nodes for all discovered classes, with method/field lists
3. Creates edges for all inferred relationships (inheritance, composition, dependencies)
4. Positions nodes using grid layout grouped by package, with `layoutPending: true`
5. All nodes created as `status: "accepted"` (the code already exists)
6. Initializes sync state with hashes for all elements
7. Writes the `.canvas` file and `.ccoding/sync-state.json`

---

## 6. Ghost Node Management

### 6.1 Core Operations (`ghost/manager.py`)

- **`propose_node(canvas, kind, name, content, rationale, proposed_by="agent") -> Node`** — creates a node with `status: "proposed"`, `proposedBy`, and `proposalRationale`. Positions near related nodes when possible (e.g., proposed method detail near its parent class), otherwise next grid slot. The `kind` parameter accepts all node kinds including context-type proposals (the core spec allows agents to propose context nodes like rationale notes or documentation links).

- **`propose_edge(canvas, from_node, to_node, relation, label, rationale, proposed_by="agent") -> Edge`** — creates a ghost edge. Both endpoints must exist (either accepted or proposed). A proposed edge between two accepted nodes is valid — it suggests a new relationship.

- **`accept_node(canvas, node_id) -> Node`** — sets `status: "accepted"`, clears `proposalRationale`. Associated ghost edges remain proposed — they must be accepted independently.

- **`accept_edge(canvas, edge_id) -> Edge`** — sets `status: "accepted"`, clears `proposalRationale`. Both endpoint nodes must already be accepted (raises error otherwise).

- **`reject_node(canvas, node_id) -> Node`** — sets `status: "rejected"`. Cascading reject: also rejects any edges where this node is an endpoint.

- **`reject_edge(canvas, edge_id) -> Edge`** — sets `status: "rejected"`. Nodes unaffected.

- **`reconsider_node(canvas, node_id) -> Node`** — moves rejected node back to `proposed`. Also reconsiders edges that were cascade-rejected with this node.

- **`reconsider_edge(canvas, edge_id) -> Edge`** — moves a rejected edge back to `proposed`. Both endpoint nodes must not be rejected (raises error otherwise — reconsider the node first).

- **`list_ghosts(canvas) -> list[Node | Edge]`** — all proposed nodes and edges.

### 6.2 Batch Operations

- `accept_all(canvas) -> list[Node | Edge]` — accepts all proposed nodes first, then all proposed edges
- `reject_all(canvas) -> list[Node | Edge]` — rejects all proposed nodes and edges

### 6.3 Integration with Sync

Ghost management only touches the canvas file. No code is generated until acceptance + sync:

1. Agent calls `propose_node()` / `propose_edge()` → canvas updated with ghosts
2. Human reviews on canvas (plugin UX) or via `ccoding ghosts` CLI command
3. Human accepts via plugin or `ccoding accept <id>`
4. Next `sync()` detects newly accepted nodes → generates code

---

## 7. Live Bridge

### 7.1 Obsidian Bridge (`live/obsidian.py`)

- **`ObsidianBridge`** class wrapping `obsidian eval` calls
- `is_available() -> bool` — checks if Obsidian CLI is installed and Obsidian is running
- `eval(js: str) -> str` — executes JavaScript in Obsidian's runtime, returns result

### 7.2 Mode Selection

| Operation | Mode | Reason |
|---|---|---|
| Import codebase | Direct JSON | Batch, offline-friendly |
| Full sync | Direct JSON | Batch, may touch many files |
| Propose ghost node | Live (fallback: JSON) | Real-time feedback on canvas |
| Accept/reject ghost | Live (fallback: JSON) | Immediate visual update |
| Read canvas state | Direct JSON | Simpler, no dependency |

### 7.3 Graceful Degradation

Every live operation has a direct JSON fallback. If Obsidian isn't running or the CLI isn't installed, the operation writes to the `.canvas` file directly and succeeds silently. This means:

- The library never requires Obsidian to be running
- Tests run without Obsidian
- CI/CD pipelines work (e.g., validating canvas/code consistency)
- The live bridge is a UX enhancement, not a functional dependency

### 7.4 Canvas Reload

For direct JSON writes, the Obsidian plugin (designed separately in the plugin spec) watches the `.canvas` file and reloads on change. When live mode is available, changes appear immediately without file-watch latency.

### 7.5 Security

The `eval` bridge only sends hardcoded JavaScript snippets — never user input. All JS templates are defined as constants in the module, parameterized with properly escaped values to prevent injection.

---

## 8. CLI Commands

### 8.1 Project Setup

- **`ccoding init`** — creates `.ccoding/` directory with `config.json` and empty `sync-state.json`. Optionally creates a starter `.canvas` file.
- **`ccoding init --hooks`** — also installs git pre-commit hook and configures the canvas merge driver

### 8.2 Canvas Operations

- **`ccoding create-node --kind <kind> --stereotype <stereotype> --name <name> --source <path>`** — create an accepted node
- **`ccoding create-edge --from <name> --to <name> --relation <relation> --label <label>`** — create an accepted edge

### 8.3 Ghost Operations

- **`ccoding propose --kind <kind> --name <name> --rationale <text>`** — create a ghost node
- **`ccoding propose-edge --from <name> --to <name> --relation <relation> --label <label> --rationale <text>`** — create a ghost edge
- **`ccoding accept <id>`** — accept a ghost node or edge
- **`ccoding reject <id>`** — reject a ghost node or edge
- **`ccoding reconsider <id>`** — move a rejected node or edge back to proposed for re-evaluation
- **`ccoding ghosts`** — list all pending proposals with rationales
- **`ccoding accept-all`** / **`ccoding reject-all`** — batch operations

### 8.4 Sync Operations

- **`ccoding sync`** — run bidirectional sync. Reports changes, stops on conflicts.
- **`ccoding sync --canvas-wins`** / **`--code-wins`** — resolve all conflicts in one direction
- **`ccoding import --source <dir> --canvas <file>`** — import existing codebase into canvas
- **`ccoding status`** — show sync state: changes on each side, pending conflicts

### 8.5 Inspection

- **`ccoding show <qualified-name>`** — display node content (canvas + code side by side)
- **`ccoding diff`** — show what sync would do without applying (dry run)

### 8.6 Git Operations

- **`ccoding check`** — validate canvas/code are in sync (used by pre-commit hook). Exit 0 if clean, exit 1 if drift detected.
- **`ccoding merge <base> <ours> <theirs>`** — custom merge driver for `.canvas` files (invoked by git, not typically called directly)

---

## 9. Git Integration

### 9.1 Pre-Commit Hook

The `ccoding check` command validates canvas/code sync state. When installed as a pre-commit hook:

- Prevents committing when canvas and code have drifted
- Reports which elements are out of sync
- Can also run in CI for pull request validation

### 9.2 Custom Merge Driver

Registered as a git merge driver for `.canvas` files via `.gitattributes`:

```
*.canvas merge=ccoding
```

Configured in `.git/config` by `ccoding init --hooks`:

```
[merge "ccoding"]
    name = CooperativeCoding canvas merge
    driver = ccoding merge %O %A %B
```

The merge driver works semantically:

- Parses base, ours, theirs as `Canvas` objects
- Non-overlapping changes auto-merge (different nodes added/modified)
- Same node modified on both sides → conflict, written inline with both versions preserved as adjacent nodes for human resolution
- Edge additions/removals auto-merge when endpoints aren't in conflict
- Node position changes: last writer wins (positions are cosmetic)
- **Exit codes**: returns 0 on successful auto-merge, non-zero when conflicts remain (per git merge driver contract). On conflict, writes the best partial merge with conflict markers so the user can resolve manually.

### 9.3 Git-Informed Change Detection

Optional enhancement to the differ:

- `ccoding sync --git-aware` uses `git diff` to identify changed files since a reference point
- Narrows the file set the parser examines — performance optimization for large codebases
- Helps after `git pull`: detects teammate changes even though local sync state doesn't know about them
- Falls back to full hash comparison when git isn't available or `--no-git` is passed

---

## 10. Configuration

### 10.1 Project Configuration (`.ccoding/config.json`)

```json
{
  "version": 1,
  "canvas": "design.canvas",
  "sourceRoot": "src/",
  "language": "python",
  "ignore": [
    "**/__pycache__/**",
    "**/test_*",
    "**/*_test.py"
  ],
  "liveMode": "auto",
  "git": {
    "preCommitHook": true,
    "mergeDriver": true,
    "gitAwareSync": true
  }
}
```

| Field | Purpose |
|---|---|
| `canvas` | Default canvas file path (overridable per command) |
| `sourceRoot` | Where source files live, used for path derivation from `qualifiedName` |
| `language` | Default language binding |
| `ignore` | Glob patterns for files/directories the code parser skips |
| `liveMode` | `"auto"` (Obsidian if available), `"always"` (fail if unavailable), `"never"` (always direct JSON) |
| `git.preCommitHook` | Enable pre-commit sync validation |
| `git.mergeDriver` | Enable semantic canvas merge driver |
| `git.gitAwareSync` | Enable git-informed change detection |

### 10.2 Version Control

- **`.ccoding/config.json`** — committed to git (shared team settings)
- **`.ccoding/sync-state.json`** — `.gitignore`'d (per-developer state)
- **`.gitattributes`** — committed (merge driver registration, shared with team)

### 10.3 Node Positioning

When the CLI generates canvas nodes from code (import or code→canvas sync):

- Nodes are placed in a grid layout grouped by package
- New nodes are annotated with `ccoding.layoutPending: true`
- The Obsidian plugin can optionally run a layout pass on pending nodes
- The CLI does not attempt graph layout algorithms — it handles data, the plugin handles visual polish

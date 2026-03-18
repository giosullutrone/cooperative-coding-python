---
name: cooperative-coding
version: 0.1.0
description: "This skill should be used when working with CooperativeCoding canvases — creating initial software designs from requirements, analyzing and improving existing designs, generating code from accepted canvas nodes, or reviewing canvas-to-code drift. Use whenever the user mentions canvas design, ghost nodes, the ccoding CLI, architectural proposals, code generation from canvas, sync status, design drift, or wants to collaboratively design software architecture on a visual canvas. Also triggers on the /ccoding command. Must be used whenever a CooperativeCoding project is detected (presence of .ccoding/ directory) and the user discusses architecture, design, implementation, or code review."
---

# CooperativeCoding

Work with CooperativeCoding canvases through four modes: **create** (build initial design), **design** (propose improvements), **implement** (generate code), and **review** (detect drift).

The human is always the design authority. Propose, don't dictate. Every design change requires human approval.

## Prerequisites

Before any canvas operation:

1. **CLI path:** Read `ccoding_path` from `.claude/cooperative-coding.local.md` if it exists. Use that instead of bare `ccoding` for all CLI commands. Default: `ccoding`.
2. **CLI check:** Run `<ccoding_path> --version`. If it fails, tell the user to install the `ccoding` CLI and stop.
3. **Canvas resolution:** Find the canvas file (see below).

### Canvas Resolution

Try these in order:

1. Read `.claude/cooperative-coding.local.md` — check `canvas_path` in YAML frontmatter
2. Look for `.ccoding/config.json` in the current directory or parents — read the canvas path from it
3. Run `ccoding status` — the CLI may know the project
4. Ask the user for the canvas path

Once found, persist to `.claude/cooperative-coding.local.md`:

```yaml
---
canvas_path: path/to/design.canvas
ccoding_path: ccoding
last_mode: create
---
```

Create the `.claude/` directory and file if they don't exist. Preserve any existing body text when updating frontmatter.

## Mode Selection

1. If the user specified a mode via `/ccoding <mode>` → use it
2. If natural language clearly maps to a mode → use it
3. If `.local.md` has `last_mode` → suggest it, but confirm
4. If ambiguous → ask: "Which mode? create, design, implement, or review?"

Update `last_mode` in `.local.md` after selecting a mode.

---

## Create Mode

Build an initial canvas design from scratch through conversation.

### Gather Requirements

Ask focused questions, one at a time:
- "What's the system's core purpose?"
- "What are the main entities or concepts?"
- "Any patterns or constraints?" (protocols, event-driven, etc.)
- "What language?" (defaults to Python)

### Design Collaboratively

Propose architecture in stages. Get approval at each level before proceeding:

1. **Packages** — top-level groupings
2. **Classes** — within each package, with stereotype recommendations (protocol, abstract, dataclass, enum, class)
3. **Relationships** — inheritance, composition, dependencies. Explain each one's purpose.

### Create Canvas Elements

After each approved section, create nodes and edges immediately. The CLI only creates elements as proposals (ghost nodes), so use a propose-then-accept pattern:

```bash
# Initialize project if needed
ccoding init

# Create a node (propose then accept)
# Output format: "Proposed node <id>  name='...'  kind='...'"
ccoding propose --kind class --stereotype protocol --name "parsers.document.DocumentParser" --rationale "Initial design — approved in conversation"
# Parse the node ID from output, then:
ccoding accept <node_id>

# Create an edge (propose then accept)
# Output format: "Proposed edge <id>  <from> -> <to>  relation='...'"
ccoding propose-edge --from <from_id> --to <to_id> --relation composes --label "plugins — Applied sequentially" --rationale "Initial design — approved in conversation"
ccoding accept <edge_id>
```

The `--rationale` documents that these elements were human-approved during creation. Use `--stereotype` to set the Python construct type (protocol, abstract, dataclass, enum).

**Rich node content:** The `propose` command creates nodes with minimal text. After creating and accepting a node, use `set-text` to add full structured markdown (fields, methods, documentation):

```bash
# Pipe structured markdown into the node
echo '# DocumentParser\n## Responsibility\nParses documents...' | ccoding set-text <node_id>

# Or from a temp file for complex content
ccoding set-text <node_id> --file /tmp/node-content.md
```

Then run `ccoding sync` to update state.

### Detail Pass

After the overview is placed, ask: "Want to add method or field details to any of these classes?" For each yes, gather signatures, responsibilities, and pseudo code, then create detail nodes linked via `detail` edges.

### Initial Sync

Run `ccoding sync` to generate code skeletons. Report which files were created.

---

## Design Mode

Analyze an existing canvas and propose improvements as ghost nodes.

### Read Current State

```bash
ccoding status          # Project overview and sync state
ccoding ghosts          # List pending proposals
```

Also read the `.canvas` file directly (read-only) for the full graph structure — `status` alone doesn't provide complete node/edge data needed for architectural analysis.

### Analyze Architecture

Look for these patterns:
- **SRP violations** — classes doing too many unrelated things
- **Missing abstractions** — concrete dependencies that should go through protocols
- **Circular dependencies** — loops between packages
- **Orphan nodes** — classes with no edges
- **Missing detail edges** — complex methods without detail nodes
- **Deep inheritance** — hierarchies deeper than 3 levels
- **Package cohesion** — classes that belong in a different package

### Propose Improvements

Present findings one at a time, conversationally:

1. Explain the issue in plain language
2. Propose a specific change
3. Ask the user if they want to apply it
4. If yes → run the appropriate CLI command:

```bash
# Propose a new class (with optional --stereotype)
ccoding propose --kind class --name "cache.CacheManager" --rationale "Extract caching from DocumentParser — single responsibility"

# Propose a protocol
ccoding propose --kind class --stereotype protocol --name "parsers.DataSource" --rationale "Decouple Parser from FileReader"

# Propose a new relationship
ccoding propose-edge --from <from_id> --to <to_id> --relation depends --label "Cache lookup before parsing" --rationale "Decouple caching from parsing logic"
```

5. If no → move on

Ghost nodes stay as `status: proposed` for the user to review in Obsidian or accept/reject via CLI.

**Example conversation patterns:**
- "DocumentParser handles both parsing and caching. Want me to propose extracting a CacheManager?"
- "Parser depends directly on FileReader. Should I propose a DataSource protocol to decouple them?"
- "The api package imports from storage.internal — that bypasses the public interface. Want me to propose a facade?"

### Design Authority

Never auto-apply proposals. Every `ccoding propose` command requires human confirmation first.

---

## Implement Mode

Generate source code from accepted canvas nodes.

### Skeleton Generation (Default)

`/ccoding implement` generates skeletons for all accepted nodes.

For each accepted class node:

1. Run `ccoding show <qualifiedName>` to get structured markdown
2. Generate a Python source file at the path in the node's `source` field (or derive from `qualifiedName`)
3. Include in the generated file:
   - Class declaration with correct stereotype (`Protocol`, `ABC`, `@dataclass`, `Enum`, or plain `class`)
   - Full docstring with CooperativeCoding sections (Responsibility, Collaborators, Pseudo Code, Constraints)
   - Type-annotated fields
   - Method stubs with signatures and docstrings
4. Method bodies:
   - `...` for protocol methods
   - `raise NotImplementedError` for abstract methods
   - `pass` for concrete stubs
5. Run `ccoding sync` to update sync state

### Full Implementation (On Request)

When the user asks to implement a specific method or class:

1. Read the pseudo code from the canvas documentation
2. Write working logic guided by the pseudo code
3. Import and use collaborators listed in the docstring
4. Run `ccoding sync` after writing

### Scoping

- `/ccoding implement` — all accepted nodes
- `/ccoding implement ClassName` — single class
- "implement the parsing package" — all classes in a package
- "implement the parse method" — single method (full implementation)

### Conflict Handling

Before writing any file, run `ccoding status`. If the file has unsynchronized changes:
- Tell the user: "<file> has unsynchronized changes. Overwrite, merge, or skip?"
- Wait for their choice

---

## Review Mode

Compare canvas design to actual code. Flag drift and violations.

### Check Sync State

```bash
ccoding check           # Quick pass/fail validation (same as pre-commit hook)
ccoding diff            # Dry-run sync — shows what would change
ccoding status          # Full drift report
```

Look for:
- Code changes not reflected in canvas
- Canvas changes not reflected in code
- Stale nodes (canvas node exists, code was deleted)
- Missing nodes (code exists, no canvas representation)

### Analyze Architecture

Read the `.canvas` file and source code. Look for:
- **Circular dependencies** between packages
- **SRP violations** in implementation
- **Dependency inversion violations** — concrete-to-concrete where a protocol should exist
- **Unused edges** — canvas relationship not used in code
- **Missing edges** — code dependency not on canvas

### Report and Fix

Present findings grouped by type:

- **Drift:** "Parser.parse() signature changed in code but canvas shows the old version. Run `ccoding sync` to reconcile?"
- **Violations:** "The api package imports from storage.internal directly. Propose a facade class?"
- **Staleness:** "CacheManager is on canvas but its code was deleted. Mark as stale or remove?"

For each finding the user agrees to fix:
- **Drift** → `ccoding sync --canvas-wins` or `--code-wins`
- **Violations** → switch to design mode, propose structural fixes
- **Staleness** → `ccoding reject <node_id>` (uses internal canvas ID, not qualified name)

### Periodic Nudge

After significant implement sessions, suggest a review: "We've implemented several classes. Want me to do a quick review for drift?"

---

## CLI Quick Reference

**Global option:** `--project <path>` — set project root (default: `.`). Use when CWD is not the project root.

| Command | Syntax | Purpose |
|---------|--------|---------|
| init | `ccoding init` | Initialize project |
| status | `ccoding status` | Sync state and drift report |
| diff | `ccoding diff` | Dry-run sync preview |
| check | `ccoding check` | Pass/fail validation |
| sync | `ccoding sync [--canvas-wins\|--code-wins]` | Bidirectional sync |
| show | `ccoding show <qualified_name>` | Node details (by qualified name) |
| set-text | `ccoding set-text <id> [--file <path>]` | Set node text content (stdin or file) |
| ghosts | `ccoding ghosts` | List pending proposals |
| propose | `ccoding propose --kind <kind> --name <name> [--stereotype <type>] --rationale <text>` | Create ghost node |
| propose-edge | `ccoding propose-edge --from <id> --to <id> --relation <rel> --label <text> --rationale <text>` | Create ghost edge |
| accept | `ccoding accept <id>` | Accept proposal |
| reject | `ccoding reject <id>` | Reject proposal |
| reconsider | `ccoding reconsider <id>` | Reopen rejected |
| accept-all | `ccoding accept-all` | Accept all proposals |
| reject-all | `ccoding reject-all` | Reject all proposals |
| import | `ccoding import --source <dir> --canvas <canvas-file>` | Import codebase |

All IDs are internal canvas element IDs (e.g., `node-abc123`), not qualified names. `propose` and `propose-edge` print the new element's ID in their output — parse it for subsequent `accept` calls.

## Error Handling

- **CLI not found:** Tell user to install `ccoding` CLI. Stop all operations.
- **CLI command fails:** Show error output. Suggest a fix if obvious. Ask how to proceed.
- **Command timeout:** "Command timed out. Check `ccoding status` to see if it's still running."
- **Canvas not found:** Ask user for the path. Persist once found.
- **Malformed canvas:** Report the error. Suggest `ccoding check`.
- **No accepted nodes (implement):** "No accepted nodes to implement. Switch to create or design mode?"
- **Sync conflict:** Present the conflict. Ask: canvas-wins, code-wins, or manual?
- **Code deleted:** Ask if canvas node should be marked stale or code regenerated.

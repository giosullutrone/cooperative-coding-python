# CooperativeCoding Claude Code Skill — Design Spec

## 1. Overview

The Claude Code skill is subsystem #3 of the CooperativeCoding initiative. It teaches Claude Code how to work with CooperativeCoding canvases through four modes: **create**, **design**, **implement**, and **review**. The skill is the agent-facing counterpart to the human-facing Obsidian plugin — where Obsidian gives the human visual control, the skill gives the agent structured access to the same canvas through the `ccoding` CLI.

**Form factor:** Standalone Claude Code plugin (own `plugin.json`, independent from Superpowers).

**Interaction with other subsystems:**
- All canvas operations go through the `ccoding` CLI (subsystem #1) — the skill never manipulates `.canvas` JSON directly.
- The Obsidian plugin (subsystem #2) reflects changes in real-time via its file watcher, so the user sees proposals appear as the agent works.

## 2. Plugin Structure

```
claude-code-skill/
├── plugin.json                    # Plugin manifest
├── skills/
│   └── cooperative-coding.md      # Main skill (auto-trigger + all 4 modes)
├── commands/
│   └── ccoding.md                 # /ccoding slash command
└── hooks/
    └── session-start.sh           # Detects .ccoding/ projects
```

### 2.1 Plugin Manifest (`plugin.json`)

```json
{
  "name": "cooperative-coding",
  "description": "Claude Code integration for CooperativeCoding — collaborative software design on visual canvases",
  "version": "0.1.0"
}
```

### 2.2 Slash Command (`commands/ccoding.md`)

Frontmatter:

```yaml
---
name: ccoding
description: Work with CooperativeCoding canvases — create, design, implement, or review
arguments:
  - name: mode
    description: "Mode: create, design, implement, review (optional — defaults to last used or asks)"
    required: false
---
```

The command body delegates to the `cooperative-coding` skill with the specified mode.

### 2.3 Session-Start Hook (`hooks/session-start.sh`)

```bash
#!/bin/bash
# Check if this is a CooperativeCoding project
if [ -d ".ccoding" ]; then
  echo "CooperativeCoding project detected."
fi
```

Output is injected into the session context, nudging the skill's auto-triggering when relevant. The hook is silent when `.ccoding/` does not exist.

## 3. Skill Triggering & Mode Selection

### 3.1 Skill Description (Triggering)

The skill's `description` field triggers on:
- Explicit `/ccoding` command invocations
- Natural language about canvas design: "analyze the canvas", "propose improvements", "what's on the canvas"
- Natural language about implementation: "implement the accepted nodes", "generate code from the canvas", "scaffold the classes"
- Natural language about review: "check for drift", "compare canvas to code", "are there design violations"
- Natural language about creation: "let's design a system", "create the initial architecture", "start a new canvas design"
- Session-start hook context indicating a `.ccoding/` project is present

### 3.2 Mode Selection Logic

1. If the user specified a mode via `/ccoding <mode>` → use that mode
2. If natural language clearly maps to a mode → use that mode
3. If ambiguous → ask the user which mode they want
4. If no mode specified and `.local.md` has `last_mode` → suggest that mode but confirm

### 3.3 Canvas Resolution (Runs Before Any Mode)

1. Check `.claude/cooperative-coding.local.md` for a persisted `canvas_path`
2. If not found, walk up from cwd looking for `.ccoding/config.json` and read the canvas path from it
3. If not found, run `ccoding status` to see if the CLI knows the project
4. If still not found, ask the user for the path and persist it to `.local.md`

### 3.4 CLI Availability Check

Before any operation, run `ccoding --version`. If it fails:
- Tell the user the `ccoding` CLI is required
- Suggest installation: `pip install ccoding` (or point to the project's install instructions)
- Stop — do not attempt any canvas operations

## 4. Create Mode

Create mode builds an initial canvas design from scratch through collaborative conversation.

### 4.1 Requirements Gathering

Ask focused questions to understand the system:
- "What's the system's core purpose?"
- "What are the main entities/concepts?"
- "Any specific patterns or constraints?" (e.g., must use protocols, event-driven)
- "What language?" (defaults to Python — the only binding currently implemented)

### 4.2 Design Conversation

Propose architecture in stages, getting approval at each level:

1. **Packages first** — top-level groupings. Present them conversationally, ask for confirmation.
2. **Key classes** — within each package. Include stereotype recommendations (protocol vs concrete, dataclass vs class, etc.).
3. **Relationships** — inheritance, composition, dependencies between classes. Explain each relationship's purpose.
4. **Stereotypes** — confirm whether classes should be protocols, abstract, dataclass, enum, or plain class.

### 4.3 Canvas Creation

After each approved section, immediately create nodes/edges via CLI:
- `ccoding init` if the project is not yet initialized
- `ccoding create-node` for each class/package
- `ccoding create-edge` for each relationship

All nodes are created with `status: accepted` — the human explicitly approved each piece in conversation. This distinguishes create mode from design mode, where suggestions arrive as ghost nodes for async review.

If the user has Obsidian open, the canvas watcher auto-reloads — they see the design populate in real-time.

### 4.4 Detail Pass

After the overview is placed, ask: "Want to add method/field details to any of these classes?"

For each class the user wants to detail:
- Gather method signatures, responsibilities, pseudo code
- Create detail nodes linked via `detail` edges

### 4.5 Initial Sync

Run `ccoding sync` to generate initial code skeletons from the accepted canvas. Report which files were created.

## 5. Design Mode

Design mode analyzes an existing canvas and proposes improvements as ghost nodes.

### 5.1 Read Current State

- Run `ccoding status` to get the project overview
- Read the `.canvas` file to understand the full architecture (nodes, edges, relationships, statuses)

### 5.2 Architectural Analysis

Analyze the canvas for common issues:
- **SRP violations** — classes with too many unrelated responsibilities
- **Missing abstractions** — concrete dependencies that should go through protocols/interfaces
- **Circular dependencies** — dependency chains that form loops between packages
- **Orphan nodes** — classes with no edges connecting them to anything
- **Missing detail edges** — classes with complex methods that lack detail nodes
- **Deep inheritance** — overly deep inheritance hierarchies
- **Package cohesion** — classes that belong in a different package based on their dependencies

### 5.3 Proposal Workflow

Present findings conversationally, one at a time:

1. Explain the issue in plain language
2. Propose a specific change (new class, split, new edge, etc.)
3. Ask the user if they want to apply it
4. If yes → execute via CLI: `ccoding propose "ClassName"` with appropriate flags, `ccoding propose-edge` for relationships
5. If no → move on to the next finding

**Conversation pattern examples:**
- "DocumentParser is doing parsing *and* caching. Want me to propose extracting a CacheManager?"
- "I notice Parser depends directly on FileReader. Should I propose a DataSource protocol to decouple them?"

### 5.4 Design Authority Principle

Every proposal requires human confirmation before the `ccoding propose` command runs. The skill never auto-applies design changes. This enforces the core principle: "Design authority is human."

## 6. Implement Mode

Implement mode generates source code from accepted canvas nodes.

### 6.1 Skeleton Generation (Default)

`/ccoding implement` with no further qualification generates skeletons for all accepted nodes:

For each accepted class node:
1. Run `ccoding show <qualifiedName>` to get the structured markdown (responsibility, fields, methods, stereotypes)
2. Generate a Python source file at the path in `ccoding.source` (or derive from `qualifiedName`)
3. Include:
   - Class declaration with correct stereotype (`Protocol`, `ABC`, `@dataclass`, `Enum`, plain `class`)
   - Full docstring with all CooperativeCoding sections (Responsibility, Collaborators, Pseudo Code, Constraints)
   - Type-annotated fields
   - Method stubs with signatures and docstrings
4. Method bodies:
   - `...` for protocol methods
   - `raise NotImplementedError` for abstract methods
   - `pass` for concrete stubs
5. Run `ccoding sync` to update sync state

### 6.2 Full Implementation (On Request)

When the user says "now implement the parse method" or "implement ClassName":
1. Read the method's pseudo code from the canvas documentation
2. Use the pseudo code as a guide to write actual working logic
3. Respect collaborators listed in the docstring — import and use them correctly
4. After writing, run `ccoding sync` to keep canvas and code aligned

### 6.3 Scoping

- `/ccoding implement` — all accepted nodes
- `/ccoding implement ClassName` — one class
- "implement the parsing package" — all classes in a package
- "implement the parse method" — one specific method (full implementation)

### 6.4 Conflict Handling

Before writing any file, check `ccoding status`. If the file already exists with unsynchronized changes:
- Warn the user: "parser.py has unsynchronized changes. Overwrite, merge, or skip?"
- Wait for the user's choice before proceeding

## 7. Review Mode

Review mode compares canvas design to actual code and flags drift or violations.

### 7.1 Sync Check

Run `ccoding status` to get the current drift report:
- Nodes with code changes not reflected in canvas
- Canvas changes not reflected in code
- Stale nodes (canvas node exists but code was deleted)
- Missing nodes (code exists but no canvas representation)

### 7.2 Architectural Analysis

Read the canvas and the code, then analyze:
- **Circular dependencies** between packages
- **SRP violations** — class with many unrelated methods
- **Dependency inversion violations** — concrete class depending on another concrete class where a protocol would be better
- **Unused edges** — relationship declared on canvas but never used in code
- **Missing edges** — code has a dependency not represented on canvas

### 7.3 Report Findings

Present issues conversationally, grouped by severity:

- **Drift:** "The `Parser.parse()` method signature changed in code but the canvas still shows the old version. Want me to run `ccoding sync` to reconcile?"
- **Violations:** "The `api` package imports directly from `storage.internal`. This bypasses the `storage` package's public interface. Should I propose a facade class?"
- **Staleness:** "`CacheManager` is on the canvas but the code file was deleted. Want me to mark it as stale or remove it?"

### 7.4 Fix Actions

For each finding the user agrees to fix:
- **Drift** → run `ccoding sync` with appropriate conflict resolution flag (`--canvas-wins` or `--code-wins`)
- **Violations** → switch to design mode to propose structural fixes as ghost nodes
- **Staleness** → run `ccoding reject <node>` or update the canvas

### 7.5 Periodic Review Suggestion

The skill prompt includes guidance that after significant implement sessions, Claude should conversationally suggest running a review. Not automatic — just a nudge: "We've implemented several classes. Want me to do a quick review to check for drift?"

## 8. Plugin Settings & Persistence

### 8.1 Per-Project Settings (`.claude/cooperative-coding.local.md`)

```yaml
---
canvas_path: design/architecture.canvas
ccoding_path: ccoding
last_mode: design
---
```

- **canvas_path** — persisted after first discovery or user specification. Updated if the user switches canvases.
- **ccoding_path** — custom CLI path if not in PATH. Defaults to `ccoding`.
- **last_mode** — last mode used. `/ccoding` with no argument defaults to this (with confirmation).

### 8.2 Settings Updates

The skill updates `.local.md` when:
- A canvas path is discovered or specified for the first time
- The user explicitly changes the canvas path
- A mode is used (updates `last_mode`)

No other persistent state is needed. The CLI manages its own state via `.ccoding/sync-state.json` and `.ccoding/config.json`.

## 9. Skill Content Guidelines

The skill file (`skills/cooperative-coding.md`) must account for the following to trigger and function reliably:

### 9.1 Description Field

The description must be broad enough to trigger on natural language across all four modes, and specific enough to not false-trigger on unrelated architecture discussions. It should mention: canvas, design, implement, review, code generation, ghost nodes, proposals, and the `ccoding` CLI.

### 9.2 Skill Body Structure

The skill body should use progressive disclosure:
- **Mode selection logic** at the top (short — decides which mode, resolves canvas)
- **Per-mode instructions** in clearly separated sections
- **CLI command reference** as a compact cheat sheet (not full docs — just the commands the skill uses with their flags)
- **Conversation pattern examples** showing how to phrase proposals, ask for confirmation, report findings

### 9.3 Tone Guidance

The skill should instruct Claude to:
- Be collaborative, not prescriptive ("Should I propose..." not "I will add...")
- Explain architectural reasoning in plain language
- Respect that the human is the design authority
- Suggest, don't dictate

## 10. Error Handling

### 10.1 CLI Errors

- **CLI not found** — tell user to install, stop
- **CLI command fails** — show the error output, suggest a fix if obvious, ask user how to proceed
- **Timeout** — "The command timed out. The operation may still be running. Want me to check status?"

### 10.2 Canvas Errors

- **Canvas file not found** — ask user for the path
- **Canvas file is malformed** — report the parse error, suggest running `ccoding check`
- **No accepted nodes** (implement mode) — "There are no accepted nodes to implement. Want to switch to create or design mode?"

### 10.3 Sync Conflicts

- **Both sides changed** — present the conflict, ask user for resolution strategy (`--canvas-wins`, `--code-wins`, or manual)
- **Code was deleted** — ask if canvas node should be marked stale or if code should be regenerated

## 11. Testing Considerations

### 11.1 Skill Triggering Tests

The skill should be tested for correct triggering on:
- Explicit `/ccoding` invocations with each mode
- Natural language phrases for each mode
- Edge cases: ambiguous phrases, unrelated architecture discussions (should NOT trigger)
- Projects with `.ccoding/` present vs absent

### 11.2 Functional Tests

Each mode should be tested against a sample canvas:
- **Create:** start from empty project, verify nodes/edges created via CLI
- **Design:** analyze a canvas with known issues, verify proposals are reasonable
- **Implement:** generate code from accepted nodes, verify file contents match canvas
- **Review:** introduce drift between canvas and code, verify it's detected

### 11.3 Test Fixture

Use the existing `tests/fixtures/sample.canvas` from the CLI package as a starting point for functional tests.

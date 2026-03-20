# Plugin Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the CooperativeCoding Claude Code plugin to split the monolithic skill into per-mode skills, add guardrail hooks, and add a review agent.

**Architecture:** All changes are to markdown/JSON files within `claude-code-skill/`. The monolithic SKILL.md is split into an entry point plus 4 mode files. Two prompt-based hooks are added to hooks.json. A new agent file is created for autonomous review. No Python code or tests — this is plugin configuration.

**Tech Stack:** Claude Code plugin API (markdown skills, JSON hooks, markdown agents)

**Spec:** `docs/superpowers/specs/2026-03-20-plugin-restructure-design.md`

---

## File Structure

```
claude-code-skill/
  skills/cooperative-coding/
    SKILL.md           # MODIFY: slim down to entry point (prerequisites, mode routing, CLI ref, errors)
    create.md          # CREATE: create mode instructions
    design.md          # CREATE: design mode instructions
    implement.md       # CREATE: implement mode instructions + auto-review nudge
    review.md          # CREATE: thin dispatcher to ccoding-review agent
  hooks/
    hooks.json         # MODIFY: add PreToolUse + PostToolUse entries
  agents/
    review.md          # CREATE: autonomous review agent
  commands/
    ccoding.md         # MODIFY: route to mode-specific skills
```

---

### Task 1: Create `create.md` mode skill

**Files:**
- Create: `claude-code-skill/skills/cooperative-coding/create.md`

- [ ] **Step 1: Create create.md**

Extract lines 53–115 from current SKILL.md (the "Create Mode" section) into a new skill file with proper frontmatter.

```markdown
---
name: cooperative-coding:create
description: "Use when building a new CooperativeCoding canvas design from scratch — gathering requirements, proposing architecture, creating nodes and edges"
---

# Create Mode

Build an initial canvas design from scratch through conversation.

See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling.

## Gather Requirements

Ask focused questions, one at a time:
- "What's the system's core purpose?"
- "What are the main entities or concepts?"
- "Any patterns or constraints?" (protocols, event-driven, etc.)
- "What language?" (defaults to Python)

## Design Collaboratively

Propose architecture in stages. Get approval at each level before proceeding:

1. **Packages** — top-level groupings
2. **Classes** — within each package, with stereotype recommendations (protocol, abstract, dataclass, enum, class)
3. **Relationships** — inheritance, composition, dependencies. Explain each one's purpose.

## Create Canvas Elements

After each approved section, create nodes and edges immediately. The CLI only creates elements as proposals (ghost nodes), so use a propose-then-accept pattern:

` ` `bash
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
` ` `

The `--rationale` documents that these elements were human-approved during creation. Use `--stereotype` to set the Python construct type (protocol, abstract, dataclass, enum).

**Rich node content:** The `propose` command creates nodes with minimal text. After creating and accepting a node, use `set-text` to add full structured markdown (fields, methods, documentation):

` ` `bash
# Pipe structured markdown into the node
echo '# DocumentParser\n## Responsibility\nParses documents...' | ccoding set-text <node_id>

# Or from a temp file for complex content
ccoding set-text <node_id> --file /tmp/node-content.md
` ` `

Then run `ccoding sync` to update state.

## Detail Pass

After the overview is placed, ask: "Want to add method or field details to any of these classes?" For each yes, gather signatures, responsibilities, and pseudo code, then create detail nodes linked via `detail` edges.

## Initial Sync

Run `ccoding sync` to generate code skeletons. Report which files were created.
```

Note: The triple backticks inside the code blocks above are escaped with spaces for plan readability. In the actual file, use proper triple backticks (` ``` `).

- [ ] **Step 2: Verify file was created correctly**

Run: `head -5 claude-code-skill/skills/cooperative-coding/create.md`
Expected: YAML frontmatter with `name: cooperative-coding:create`

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/skills/cooperative-coding/create.md
git commit -m "feat(plugin): extract create mode into separate skill file"
```

---

### Task 2: Create `design.md` mode skill

**Files:**
- Create: `claude-code-skill/skills/cooperative-coding/design.md`

- [ ] **Step 1: Create design.md**

Extract lines 117–174 from current SKILL.md (the "Design Mode" section) into a new skill file with proper frontmatter.

```markdown
---
name: cooperative-coding:design
description: "Use when analyzing an existing CooperativeCoding canvas and proposing improvements as ghost nodes"
---

# Design Mode

Analyze an existing canvas and propose improvements as ghost nodes.

See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling.

## Read Current State

` ` `bash
ccoding status          # Project overview and sync state
ccoding ghosts          # List pending proposals
` ` `

Also read the `.canvas` file directly (read-only) for the full graph structure — `status` alone doesn't provide complete node/edge data needed for architectural analysis.

## Analyze Architecture

Look for these patterns:
- **SRP violations** — classes doing too many unrelated things
- **Missing abstractions** — concrete dependencies that should go through protocols
- **Circular dependencies** — loops between packages
- **Orphan nodes** — classes with no edges
- **Missing detail edges** — complex methods without detail nodes
- **Deep inheritance** — hierarchies deeper than 3 levels
- **Package cohesion** — classes that belong in a different package

## Propose Improvements

Present findings one at a time, conversationally:

1. Explain the issue in plain language
2. Propose a specific change
3. Ask the user if they want to apply it
4. If yes → run the appropriate CLI command:

` ` `bash
# Propose a new class (with optional --stereotype)
ccoding propose --kind class --name "cache.CacheManager" --rationale "Extract caching from DocumentParser — single responsibility"

# Propose a protocol
ccoding propose --kind class --stereotype protocol --name "parsers.DataSource" --rationale "Decouple Parser from FileReader"

# Propose a new relationship
ccoding propose-edge --from <from_id> --to <to_id> --relation depends --label "Cache lookup before parsing" --rationale "Decouple caching from parsing logic"
` ` `

5. If no → move on

Ghost nodes stay as `status: proposed` for the user to review in Obsidian or accept/reject via CLI.

**Example conversation patterns:**
- "DocumentParser handles both parsing and caching. Want me to propose extracting a CacheManager?"
- "Parser depends directly on FileReader. Should I propose a DataSource protocol to decouple them?"
- "The api package imports from storage.internal — that bypasses the public interface. Want me to propose a facade?"

## Design Authority

Never auto-apply proposals. Every `ccoding propose` command requires human confirmation first.
```

Note: Use proper triple backticks in the actual file (spaces shown here for plan readability).

- [ ] **Step 2: Verify file was created correctly**

Run: `head -5 claude-code-skill/skills/cooperative-coding/design.md`
Expected: YAML frontmatter with `name: cooperative-coding:design`

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/skills/cooperative-coding/design.md
git commit -m "feat(plugin): extract design mode into separate skill file"
```

---

### Task 3: Create `implement.md` mode skill

**Files:**
- Create: `claude-code-skill/skills/cooperative-coding/implement.md`

- [ ] **Step 1: Create implement.md**

Extract lines 176–221 from current SKILL.md (the "Implement Mode" section) into a new skill file with proper frontmatter. Add an auto-review nudge at the end (per spec section 4).

```markdown
---
name: cooperative-coding:implement
description: "Use when generating code from accepted CooperativeCoding canvas nodes — skeleton or full implementation"
---

# Implement Mode

Generate source code from accepted canvas nodes.

See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling.

## Skeleton Generation (Default)

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

## Full Implementation (On Request)

When the user asks to implement a specific method or class:

1. Read the pseudo code from the canvas documentation
2. Write working logic guided by the pseudo code
3. Import and use collaborators listed in the docstring
4. Run `ccoding sync` after writing

## Scoping

- `/ccoding implement` — all accepted nodes
- `/ccoding implement ClassName` — single class
- "implement the parsing package" — all classes in a package
- "implement the parse method" — single method (full implementation)

## Conflict Handling

Before writing any file, run `ccoding status`. If the file has unsynchronized changes:
- Tell the user: "<file> has unsynchronized changes. Overwrite, merge, or skip?"
- Wait for their choice

## Post-Implementation Review

After implementing multiple classes, dispatch the `ccoding-review` agent to check alignment between the canvas and the generated code. This catches drift early before it accumulates.
```

Note: Use proper triple backticks in the actual file (spaces shown here for plan readability).

- [ ] **Step 2: Verify file was created correctly**

Run: `head -5 claude-code-skill/skills/cooperative-coding/implement.md`
Expected: YAML frontmatter with `name: cooperative-coding:implement`

Run: `tail -5 claude-code-skill/skills/cooperative-coding/implement.md`
Expected: Post-Implementation Review section mentioning `ccoding-review` agent

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/skills/cooperative-coding/implement.md
git commit -m "feat(plugin): extract implement mode into separate skill file with auto-review nudge"
```

---

### Task 4: Create `review.md` dispatcher skill

**Files:**
- Create: `claude-code-skill/skills/cooperative-coding/review.md`

- [ ] **Step 1: Create review.md as thin dispatcher**

This is NOT a verbatim extraction from SKILL.md. The review mode becomes a thin dispatcher that routes to the `ccoding-review` agent. The agent does the heavy analysis work.

```markdown
---
name: cooperative-coding:review
description: "Use when checking CooperativeCoding canvas-to-code drift, architectural violations, or staleness"
---

# Review Mode

Compare canvas design to actual code. Flag drift and violations.

See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling.

## Dispatch Review Agent

This mode delegates analysis to the `ccoding-review` agent, which runs autonomously with read-only access. Dispatch it with:

1. The project root path (directory containing `.ccoding/`)
2. The canvas path (from `.claude/cooperative-coding.local.md` or canvas resolution)

The agent reads the canvas, runs CLI diagnostics, reads tracked source files, and returns a structured findings report grouped by type (drift, staleness, missing nodes, architectural violations) with severity levels (error/warning/info).

## After the Report

Once the agent returns its report, present findings to the user and offer to fix them:

- **Drift** → `ccoding sync --canvas-wins` or `--code-wins`
- **Violations** → switch to design mode, propose structural fixes
- **Staleness** → `ccoding reject <node_id>` (uses internal canvas ID, not qualified name)
```

- [ ] **Step 2: Verify file was created correctly**

Run: `head -5 claude-code-skill/skills/cooperative-coding/review.md`
Expected: YAML frontmatter with `name: cooperative-coding:review`

Run: `grep -c "ccoding-review" claude-code-skill/skills/cooperative-coding/review.md`
Expected: At least 1 match (references the agent)

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/skills/cooperative-coding/review.md
git commit -m "feat(plugin): create review mode as thin dispatcher to ccoding-review agent"
```

---

### Task 5: Slim down SKILL.md to entry point

**Files:**
- Modify: `claude-code-skill/skills/cooperative-coding/SKILL.md`

- [ ] **Step 1: Rewrite SKILL.md**

Replace the entire file with this content (original frontmatter preserved, mode sections removed, mode routing added):

````markdown
---
name: cooperative-coding
version: 0.1.0
description: "This skill should be used when working with CooperativeCoding canvases — creating initial software designs from requirements, analyzing and improving existing designs, generating code from accepted canvas nodes, or reviewing canvas-to-code drift. Use whenever the user mentions canvas design, ghost nodes, the ccoding CLI, architectural proposals, code generation from canvas, sync status, design drift, or wants to collaboratively design software architecture on a visual canvas. Also triggers on the /ccoding command. Must be used whenever a CooperativeCoding project is detected (presence of .ccoding/ directory) and the user discusses architecture, design, implementation, or code review."
---

# CooperativeCoding

Work with CooperativeCoding canvases through four modes: **create** (build initial design), **design** (propose improvements), **implement** (generate code), and **review** (detect drift). Each mode has its own skill with detailed instructions.

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

Once the mode is determined, follow the corresponding skill:
- **create** → follow the `cooperative-coding:create` skill
- **design** → follow the `cooperative-coding:design` skill
- **implement** → follow the `cooperative-coding:implement` skill
- **review** → follow the `cooperative-coding:review` skill

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
````

- [ ] **Step 2: Verify the slimmed file**

Run: `wc -l claude-code-skill/skills/cooperative-coding/SKILL.md`
Expected: Approximately 80–100 lines (down from 304)

Run: `grep -c "Create Mode\|Design Mode\|Implement Mode\|Review Mode" claude-code-skill/skills/cooperative-coding/SKILL.md`
Expected: 0 (mode sections removed)

Run: `grep -c "cooperative-coding:create\|cooperative-coding:design\|cooperative-coding:implement\|cooperative-coding:review" claude-code-skill/skills/cooperative-coding/SKILL.md`
Expected: 4 (routing references to sub-skills)

Run: `grep -c "CLI Quick Reference\|Error Handling" claude-code-skill/skills/cooperative-coding/SKILL.md`
Expected: 2 (shared sections retained)

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/skills/cooperative-coding/SKILL.md
git commit -m "refactor(plugin): slim SKILL.md to entry point, remove mode sections"
```

---

### Task 6: Update `ccoding.md` command routing

**Files:**
- Modify: `claude-code-skill/commands/ccoding.md`

- [ ] **Step 1: Update ccoding.md**

Replace the current body of `ccoding.md` with mode-specific skill routing. Keep the frontmatter unchanged.

New content after the frontmatter:

```markdown
The user wants to work with a CooperativeCoding canvas.

**Mode requested:** $ARGUMENTS

If a mode was specified, route directly to the corresponding skill:
- `create` → follow the `cooperative-coding:create` skill
- `design` → follow the `cooperative-coding:design` skill
- `implement` → follow the `cooperative-coding:implement` skill
- `review` → follow the `cooperative-coding:review` skill

If no mode was specified, follow the `cooperative-coding` skill (it handles mode resolution via `last_mode` or asking the user).
```

- [ ] **Step 2: Verify the update**

Run: `cat claude-code-skill/commands/ccoding.md`
Expected: Frontmatter preserved, body routes to mode-specific skills with fallthrough to main skill

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/commands/ccoding.md
git commit -m "feat(plugin): update /ccoding command to route to mode-specific skills"
```

---

### Task 7: Add PreToolUse and PostToolUse hooks

**Files:**
- Modify: `claude-code-skill/hooks/hooks.json`

- [ ] **Step 1: Replace hooks.json with full content**

Write the complete hooks.json with all three event types (SessionStart unchanged, PreToolUse and PostToolUse added):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-start.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if the file_path parameter ends with '.canvas'. If it does, respond ONLY with: 'USE_CLI: Use ccoding CLI commands (set-text, propose, sync) instead of editing .canvas files directly — direct edits bypass sync state and cause drift.' If the file does NOT end with '.canvas', respond with an empty string.",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if the file_path parameter ends with '.py'. If it does, respond ONLY with: 'SYNC_REMINDER: Consider running ccoding sync to keep the canvas in sync with code changes.' Otherwise respond with an empty string.",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON syntax**

Run: `python3 -c "import json; json.load(open('claude-code-skill/hooks/hooks.json'))"`
Expected: No output (valid JSON)

- [ ] **Step 3: Verify hook structure**

Run: `python3 -c "import json; d=json.load(open('claude-code-skill/hooks/hooks.json')); print(list(d['hooks'].keys()))"`
Expected: `['SessionStart', 'PreToolUse', 'PostToolUse']`

- [ ] **Step 4: Commit**

```bash
git add claude-code-skill/hooks/hooks.json
git commit -m "feat(plugin): add PreToolUse canvas protection and PostToolUse sync nudge hooks"
```

---

### Task 8: Create review agent

**Files:**
- Create: `claude-code-skill/agents/review.md`

- [ ] **Step 1: Create agents directory and review.md**

```bash
mkdir -p claude-code-skill/agents
```

Write `claude-code-skill/agents/review.md`:

```markdown
---
name: ccoding-review
description: "Use this agent to review CooperativeCoding canvas-to-code alignment. Dispatched automatically after implement sessions or manually when the user asks for architectural review, drift checking, or design analysis. Runs autonomously, reads the canvas and all tracked source files, and returns a structured findings report."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# CooperativeCoding Review Agent

You are an autonomous review agent for CooperativeCoding projects. Your job is to analyze the alignment between a canvas design and the actual codebase, then return a structured findings report.

You have **read-only** access. Do not modify any files.

## Inputs

You receive:
- **Project root:** the directory containing `.ccoding/`
- **Canvas path:** the `.canvas` file to analyze

## Process

### 1. Gather Sync State

Run these CLI commands from the project root:

` ` `bash
ccoding status          # Overall project state and drift summary
ccoding diff            # Dry-run sync — shows what would change
ccoding check           # Pass/fail validation (same as pre-commit)
` ` `

### 2. Read the Canvas

Read the `.canvas` file directly. Parse the JSON to build the complete node/edge graph:
- Node IDs, qualified names, kinds, stereotypes
- Edge relationships (composes, depends, inherits, implements, detail)
- Ghost node status (proposed/accepted/rejected)

### 3. Read Tracked Source Files

For each accepted class node on the canvas, locate and read the corresponding source file. Use the `source` field from node metadata or derive the path from the qualified name.

### 4. Analyze

Check for each of these finding types:

**Drift (severity: error)**
- Code changes not reflected in canvas (new methods, changed signatures, renamed classes)
- Canvas changes not reflected in code (accepted nodes without corresponding code)

**Staleness (severity: error)**
- Canvas nodes whose corresponding code files have been deleted
- Canvas edges referencing deleted or renamed classes

**Missing Nodes (severity: warning)**
- Code classes/modules not represented on the canvas
- New files added since last sync

**Missing Edges (severity: warning)**
- Import dependencies in code that have no corresponding canvas edge
- Inheritance/protocol conformance in code without canvas representation

**Unused Edges (severity: warning)**
- Canvas relationships not reflected in actual code imports or usage

**Circular Dependencies (severity: warning)**
- Import cycles between packages (use grep for import statements, build dependency graph)

**SRP Violations (severity: info)**
- Classes with too many methods (> 10) or too many responsibilities
- Files exceeding 300 lines

**Deep Inheritance (severity: info)**
- Class hierarchies deeper than 3 levels

## Output Format

Return a structured report grouped by finding type:

` ` `
## Review Report: <canvas-name>

### Summary
- X errors, Y warnings, Z info findings
- Overall sync status: IN_SYNC | DRIFTED | STALE

### Errors

#### Drift
- <finding 1>
- <finding 2>

#### Staleness
- <finding 1>

### Warnings

#### Missing Nodes
- <finding 1>

#### Missing Edges
- <finding 1>

#### Unused Edges
- <finding 1>

#### Circular Dependencies
- <finding 1>

### Info

#### SRP Violations
- <finding 1>

#### Deep Inheritance
- <finding 1>

### Recommended Actions
1. Run `ccoding sync` to reconcile drift
2. ...
` ` `

If a category has no findings, omit it from the report.
```

Note: Use proper triple backticks in the actual file (spaces shown here for plan readability).

- [ ] **Step 2: Verify file was created correctly**

Run: `head -7 claude-code-skill/agents/review.md`
Expected: YAML frontmatter with `name: ccoding-review`, `model: sonnet`, `tools: Bash, Read, Grep, Glob`

Run: `grep -c "severity:" claude-code-skill/agents/review.md`
Expected: 8 (one per finding type)

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/agents/review.md
git commit -m "feat(plugin): add ccoding-review agent for autonomous architectural analysis"
```

---

### Task 9: Update README

**Files:**
- Modify: `claude-code-skill/README.md`

- [ ] **Step 1: Update the plugin structure section**

In `claude-code-skill/README.md`, find the "Plugin structure" section and replace the directory tree with the new structure:

```
claude-code-skill/
  .claude-plugin/
    plugin.json          # Plugin metadata
  agents/
    review.md            # Autonomous review agent
  commands/
    ccoding.md           # /ccoding slash command
  hooks/
    hooks.json           # Session start, canvas protection, sync nudge hooks
    scripts/
      session-start.sh   # Detects .ccoding/ directories
  skills/
    cooperative-coding/
      SKILL.md           # Entry point: prerequisites, mode routing, CLI reference
      create.md          # Create mode instructions
      design.md          # Design mode instructions
      implement.md       # Implement mode instructions
      review.md          # Review mode dispatcher
```

- [ ] **Step 2: Verify update**

Run: `grep -c "agents/" claude-code-skill/README.md`
Expected: At least 1

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/README.md
git commit -m "docs(plugin): update README with new plugin structure after restructure"
```

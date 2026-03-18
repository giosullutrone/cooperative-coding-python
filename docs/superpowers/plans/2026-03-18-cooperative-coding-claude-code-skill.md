# CooperativeCoding Claude Code Skill — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Claude Code plugin that teaches Claude how to work with CooperativeCoding canvases through four modes (create, design, implement, review).

**Architecture:** A Claude Code plugin consisting of a manifest, one skill file (SKILL.md), one slash command, and a session-start hook. The skill encodes all four modes with CLI command references and conversation patterns. A one-line CLI fix adds the `--version` flag prerequisite.

**Tech Stack:** Claude Code plugin system (markdown + JSON + shell), Python Click CLI (one-line fix)

---

### Task 1: CLI Prerequisite — Add `--version` Flag

The skill's availability check runs `ccoding --version`. The CLI has `__version__ = "0.1.0"` in `__init__.py` but no Click version option wired up.

**Files:**
- Modify: `ccoding/cli.py:9` (add version_option decorator)
- Test: `tests/test_cli.py` (if exists, add version test)

- [ ] **Step 1: Add the version option**

In `ccoding/cli.py`, add `@click.version_option()` before the `@click.group()` decorator. Click auto-discovers `__version__` from the package:

```python
@click.group()
@click.version_option(package_name="ccoding")
@click.option("--project", type=click.Path(exists=True, path_type=Path), default=".")
@click.pass_context
def main(ctx: click.Context, project: Path) -> None:
```

If `package_name` fails (not installed as package), use the explicit form:

```python
from ccoding import __version__

@click.group()
@click.version_option(version=__version__)
@click.option("--project", type=click.Path(exists=True, path_type=Path), default=".")
@click.pass_context
def main(ctx: click.Context, project: Path) -> None:
```

- [ ] **Step 2: Verify it works**

Run: `cd /path/to/project && python -m ccoding.cli --version`
Expected output: `main, version 0.1.0` (or similar)

If the CLI is installed: `ccoding --version`

- [ ] **Step 3: Run existing tests**

Run: `cd /path/to/project && python -m pytest tests/ -v`
Expected: All existing tests pass (no regressions)

- [ ] **Step 4: Commit**

```bash
git add ccoding/cli.py
git commit -m "feat(cli): add --version flag for availability checks"
```

---

### Task 2: Plugin Scaffold

Create the plugin directory structure and manifest.

**Files:**
- Create: `claude-code-skill/.claude-plugin/plugin.json`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p claude-code-skill/.claude-plugin
mkdir -p claude-code-skill/skills/cooperative-coding
mkdir -p claude-code-skill/commands
mkdir -p claude-code-skill/hooks/scripts
```

- [ ] **Step 2: Write plugin manifest**

Create `claude-code-skill/.claude-plugin/plugin.json`:

```json
{
  "name": "cooperative-coding",
  "description": "Claude Code integration for CooperativeCoding — collaborative software design on visual canvases with four modes: create, design, implement, and review",
  "version": "0.1.0",
  "author": {
    "name": "CooperativeCoding"
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/
git commit -m "feat: scaffold Claude Code plugin directory structure"
```

---

### Task 3: Session-Start Hook

Create the hook that detects CooperativeCoding projects.

**Files:**
- Create: `claude-code-skill/hooks/hooks.json`
- Create: `claude-code-skill/hooks/scripts/session-start.sh`

- [ ] **Step 1: Write hooks.json**

Create `claude-code-skill/hooks/hooks.json`:

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
    ]
  }
}
```

- [ ] **Step 2: Write session-start script**

Create `claude-code-skill/hooks/scripts/session-start.sh`:

```bash
#!/bin/bash
# Detect CooperativeCoding projects by checking for .ccoding/ directory.
# Output is injected into session context to nudge skill auto-triggering.

if [ -d ".ccoding" ]; then
  echo "CooperativeCoding project detected. Use /ccoding or ask about the canvas design to get started."
fi
```

- [ ] **Step 3: Make script executable**

```bash
chmod +x claude-code-skill/hooks/scripts/session-start.sh
```

- [ ] **Step 4: Commit**

```bash
git add claude-code-skill/hooks/
git commit -m "feat: add session-start hook for ccoding project detection"
```

---

### Task 4: Slash Command

Create the `/ccoding` command that delegates to the skill.

**Files:**
- Create: `claude-code-skill/commands/ccoding.md`

- [ ] **Step 1: Write command file**

Create `claude-code-skill/commands/ccoding.md`:

````markdown
---
description: Work with CooperativeCoding canvases — create, design, implement, or review
argument-hint: "[create|design|implement|review]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

The user wants to work with a CooperativeCoding canvas.

**Mode requested:** $ARGUMENTS

If a mode was specified (create, design, implement, or review), proceed directly with that mode. If no mode was specified, check `.claude/cooperative-coding.local.md` for `last_mode` and suggest it, or ask which mode the user wants.

Follow the `cooperative-coding` skill instructions for the selected mode.
````

- [ ] **Step 2: Commit**

```bash
git add claude-code-skill/commands/ccoding.md
git commit -m "feat: add /ccoding slash command"
```

---

### Task 5: SKILL.md — Core Skill File

This is the main deliverable. The skill file encodes all four modes, mode selection, canvas resolution, CLI reference, conversation patterns, and tone guidance.

**Files:**
- Create: `claude-code-skill/skills/cooperative-coding/SKILL.md`

- [ ] **Step 1: Write the complete SKILL.md**

Create `claude-code-skill/skills/cooperative-coding/SKILL.md`:

````markdown
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
ccoding propose --kind class --name "parsers.document.DocumentParser" --rationale "Initial design — approved in conversation"
# Note the node ID from output, then:
ccoding accept <node_id>

# Create an edge (propose then accept)
ccoding propose-edge --from <from_id> --to <to_id> --relation composes --label "plugins — Applied sequentially" --rationale "Initial design — approved in conversation"
ccoding accept <edge_id>
```

The `--rationale` documents that these elements were human-approved during creation.

**Rich node content:** The `propose` command creates nodes with minimal text. After creating and accepting a node, if it needs full structured markdown (fields, methods, documentation), read and edit the `.canvas` file directly to set the node's `text` field, then run `ccoding sync` to update state. This is the one exception to the "no direct canvas writes" rule.

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
# Propose a new class
ccoding propose --kind class --name "cache.CacheManager" --rationale "Extract caching from DocumentParser — single responsibility"

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

| Command | Syntax | Purpose |
|---------|--------|---------|
| init | `ccoding init` | Initialize project |
| status | `ccoding status` | Sync state and drift report |
| diff | `ccoding diff` | Dry-run sync preview |
| check | `ccoding check` | Pass/fail validation |
| sync | `ccoding sync [--canvas-wins\|--code-wins]` | Bidirectional sync |
| show | `ccoding show <qualified_name>` | Node details |
| ghosts | `ccoding ghosts` | List pending proposals |
| propose | `ccoding propose --kind <kind> --name <name> --rationale <text>` | Create ghost node |
| propose-edge | `ccoding propose-edge --from <id> --to <id> --relation <rel> --label <text> --rationale <text>` | Create ghost edge |
| accept | `ccoding accept <id>` | Accept proposal |
| reject | `ccoding reject <id>` | Reject proposal |
| reconsider | `ccoding reconsider <id>` | Reopen rejected |
| accept-all | `ccoding accept-all` | Accept all proposals |
| reject-all | `ccoding reject-all` | Reject all proposals |
| import | `ccoding import --source <dir> --canvas <canvas-file>` | Import codebase |

All IDs are internal canvas element IDs (e.g., `node-abc123`), not qualified names.

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

- [ ] **Step 2: Review skill length**

The SKILL.md should be under 500 lines. Count lines:

```bash
wc -l claude-code-skill/skills/cooperative-coding/SKILL.md
```

Expected: ~280-320 lines. If over 500, move the CLI Quick Reference table to `skills/cooperative-coding/references/cli.md` and reference it from SKILL.md.

- [ ] **Step 3: Commit**

```bash
git add claude-code-skill/skills/
git commit -m "feat: add cooperative-coding SKILL.md with all four modes"
```

---

### Task 6: Final Verification

Verify the complete plugin structure and file contents.

**Files:**
- All files in `claude-code-skill/`

- [ ] **Step 1: Verify directory structure**

```bash
find claude-code-skill/ -type f | sort
```

Expected output:
```
claude-code-skill/.claude-plugin/plugin.json
claude-code-skill/commands/ccoding.md
claude-code-skill/hooks/hooks.json
claude-code-skill/hooks/scripts/session-start.sh
claude-code-skill/skills/cooperative-coding/SKILL.md
```

- [ ] **Step 2: Verify plugin.json is valid JSON**

```bash
python3 -c "import json; json.load(open('claude-code-skill/.claude-plugin/plugin.json'))"
```

Expected: No error output.

- [ ] **Step 3: Verify hooks.json is valid JSON**

```bash
python3 -c "import json; json.load(open('claude-code-skill/hooks/hooks.json'))"
```

Expected: No error output.

- [ ] **Step 4: Verify SKILL.md frontmatter has required fields**

```bash
head -5 claude-code-skill/skills/cooperative-coding/SKILL.md
```

Expected: YAML frontmatter with `name` and `description` fields.

- [ ] **Step 5: Verify session-start.sh is executable**

```bash
test -x claude-code-skill/hooks/scripts/session-start.sh && echo "OK"
```

Expected: `OK`

- [ ] **Step 6: Verify CLI --version works**

```bash
python -m ccoding.cli --version
```

Expected: Output containing `0.1.0`

- [ ] **Step 7: Final commit**

```bash
git add -A claude-code-skill/
git commit -m "feat: complete CooperativeCoding Claude Code plugin"
```

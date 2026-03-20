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

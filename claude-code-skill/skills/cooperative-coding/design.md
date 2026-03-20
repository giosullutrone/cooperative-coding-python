---
name: cooperative-coding:design
description: "Use when analyzing an existing CooperativeCoding canvas and proposing improvements as ghost nodes"
---

See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling.

## Design Mode

Analyze an existing canvas and propose improvements as ghost nodes.

## Read Current State

```bash
ccoding status          # Project overview and sync state
ccoding ghosts          # List pending proposals
```

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

## Design Authority

Never auto-apply proposals. Every `ccoding propose` command requires human confirmation first.

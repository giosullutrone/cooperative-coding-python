---
name: cooperative-coding:review
description: "Use when checking CooperativeCoding canvas-to-code drift, architectural violations, or staleness"
---

Before starting, ensure the prerequisites from the `cooperative-coding` skill have been completed (CLI check, canvas resolution).

# Review Mode

Compare canvas design to actual code. Flag drift and violations.

## Use Review Agent

This mode delegates analysis to the `ccoding-review` agent, which runs autonomously with read-only access. Use the agent and provide it with:

1. The project root path (directory containing `.ccoding/`)
2. The canvas path (from `.claude/cooperative-coding.local.md` or canvas resolution)
3. The CLI path (`ccoding_path` from `.claude/cooperative-coding.local.md`, default: `ccoding`)

The agent reads the canvas, runs CLI diagnostics, reads tracked source files, and returns a structured findings report grouped by type (drift, staleness, missing nodes, architectural violations) with severity levels (error/warning/info).

## After the Report

Once the agent returns its report, present findings to the user and offer to fix them:

- **Drift** → `ccoding sync --canvas-wins` or `--code-wins`
- **Violations** → switch to design mode, propose structural fixes
- **Staleness** → `ccoding reject <node_id>` (uses internal canvas ID, not qualified name)

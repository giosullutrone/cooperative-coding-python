# Claude Code Plugin Restructure — Design Spec

**Goal:** Restructure the CooperativeCoding Claude Code plugin to split the monolithic skill into per-mode skills, add guardrail hooks, and add a review agent.

**Scope:** Four independent changes to `claude-code-skill/`:

1. Split SKILL.md into per-mode skills
2. PreToolUse hook for canvas file protection
3. PostToolUse hook for sync nudge after Python edits
4. Review agent for autonomous architectural analysis

---

## 1. Skill Split

### Problem

The current `skills/cooperative-coding/SKILL.md` is 304 lines covering all 4 modes (create, design, implement, review), prerequisites, CLI reference, and error handling. The entire file loads into context even when only one mode is needed.

### Design

Split into 5 files:

```
skills/
  cooperative-coding/
    SKILL.md          # Entry point: prerequisites, canvas resolution, mode routing, CLI reference, error handling
    create.md         # Create mode instructions
    design.md         # Design mode instructions
    implement.md      # Implement mode instructions
    review.md         # Review mode instructions
```

**SKILL.md** (entry point) retains:
- Skill frontmatter with the broad triggering description (unchanged)
- Prerequisites section (CLI path, CLI check, canvas resolution)
- Canvas resolution logic and `.local.md` persistence
- Mode selection logic (explicit → natural language → last_mode → ask)
- CLI quick reference table
- Error handling section

Each mode file references back: "See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling."

**Mode files** each get full skill frontmatter:

```yaml
# create.md
---
name: cooperative-coding:create
description: "Use when building a new CooperativeCoding canvas design from scratch — gathering requirements, proposing architecture, creating nodes and edges"
---

# design.md
---
name: cooperative-coding:design
description: "Use when analyzing an existing CooperativeCoding canvas and proposing improvements as ghost nodes"
---

# implement.md
---
name: cooperative-coding:implement
description: "Use when generating code from accepted CooperativeCoding canvas nodes — skeleton or full implementation"
---

# review.md
---
name: cooperative-coding:review
description: "Use when checking CooperativeCoding canvas-to-code drift, architectural violations, or staleness"
---
```

**`/ccoding` command** updates to route to mode-specific skills:

```
If mode is "create" → follow the cooperative-coding:create skill
If mode is "design" → follow the cooperative-coding:design skill
If mode is "implement" → follow the cooperative-coding:implement skill
If mode is "review" → follow the cooperative-coding:review skill
If no mode specified → follow the cooperative-coding skill (SKILL.md handles mode resolution via last_mode / ask)
```

### Content split

Each mode file contains only the instructions for that mode, extracted verbatim from the current SKILL.md sections:
- Create Mode → `create.md` (lines 53–115 of current SKILL.md)
- Design Mode → `design.md` (lines 117–174)
- Implement Mode → `implement.md` (lines 176–221)
- Review Mode → `review.md` (lines 223–266)

---

## 2. PreToolUse Hook — Canvas Protection

### Problem

When Claude uses `Edit` or `Write` on a `.canvas` file, it bypasses the ccoding sync engine. The sync state file doesn't know about the change, causing silent drift.

### Design

Add a prompt-based PreToolUse hook in `hooks/hooks.json`.

**Behavior:** This doesn't hard-block the tool. It injects a warning that steers Claude toward using the CLI. The user can still approve the edit if they want.

---

## 3. PostToolUse Hook — Sync Nudge

### Problem

After Claude writes or edits Python files in a ccoding project, the canvas may be out of sync. There's no reminder to run `ccoding sync`.

### Design

Add a prompt-based PostToolUse hook in `hooks/hooks.json`.

**Behavior:** Light-touch nudge. Claude sees the reminder and can decide whether to sync now or defer. Not every Python edit warrants a sync — the agent uses judgment. The session-start hook already detects whether this is a ccoding project, so the PostToolUse hook simply checks for `.py` file extension — no filesystem check needed.

---

### Complete hooks.json after changes

The full `hooks/hooks.json` after adding both hooks:

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

---

## 4. Review Agent

### Problem

The review mode currently runs inline, consuming context window with file reads across the entire project. Large projects may require reading 20+ files for a thorough review.

### Design

Add a dedicated agent at `agents/review.md`:

**Frontmatter:**
```yaml
---
name: ccoding-review
description: "Use this agent to review CooperativeCoding canvas-to-code alignment. Dispatched automatically after implement sessions or manually when the user asks for architectural review, drift checking, or design analysis. Runs autonomously, reads the canvas and all tracked source files, and returns a structured findings report."
model: sonnet
tools: Bash, Read, Grep, Glob
---
```

**System prompt content:**

The agent receives the project root and canvas path. It:

1. Runs `ccoding status`, `ccoding diff`, `ccoding check` to get sync state
2. Reads the `.canvas` file to build the full node/edge graph
3. Reads tracked source files referenced by canvas nodes
4. Analyzes for:
   - **Drift:** code changes not reflected in canvas and vice versa
   - **Staleness:** canvas nodes whose code was deleted
   - **Missing nodes:** code classes not represented on canvas
   - **Circular dependencies:** import cycles between packages
   - **SRP violations:** classes with too many responsibilities
   - **Missing edges:** code dependencies not on canvas
   - **Unused edges:** canvas relationships not used in code
   - **Deep inheritance:** hierarchies deeper than 3 levels
5. Returns a structured report grouped by finding type with severity (error/warning/info)

**Triggering:**

- **Manual:** User says "review the architecture", "check for drift", "is the canvas in sync?" — the review skill dispatches to the agent
- **Automatic:** The implement mode's instructions include a closing nudge: "After implementing multiple classes, dispatch the ccoding-review agent to check alignment."

**Review skill → agent relationship:** The `skills/cooperative-coding/review.md` file becomes a thin dispatcher — it describes when review is appropriate, then instructs Claude to dispatch the `ccoding-review` agent with the project root and canvas path. All heavy analysis happens in the agent, keeping the skill's context footprint minimal.

**Agent tools:** Read-only — `Bash` (for ccoding CLI), `Read`, `Grep`, `Glob`. No `Write` or `Edit`.

---

## File Changes Summary

| Action | File |
|--------|------|
| Rewrite | `skills/cooperative-coding/SKILL.md` (slim down to entry point) |
| Create | `skills/cooperative-coding/create.md` |
| Create | `skills/cooperative-coding/design.md` |
| Create | `skills/cooperative-coding/implement.md` |
| Create | `skills/cooperative-coding/review.md` |
| Update | `hooks/hooks.json` (add PreToolUse + PostToolUse) |
| Create | `agents/review.md` |
| Update | `commands/ccoding.md` (route to mode-specific skills) |

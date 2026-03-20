# CooperativeCoding Plugin for Claude Code

A Claude Code plugin that integrates [CooperativeCoding](https://github.com/giosullutrone/cooperative-coding) — an open standard for human-AI collaborative software design using visual canvases.

## What it does

This plugin adds four modes to Claude Code for working with CooperativeCoding canvases:

- **Create** — Build initial software designs from requirements through conversation
- **Design** — Analyze existing designs and propose improvements as ghost nodes
- **Implement** — Generate code from accepted canvas nodes (skeletons or full implementations)
- **Review** — Detect canvas-to-code drift, architectural violations, and staleness

## Prerequisites

1. **Claude Code** — [Install Claude Code](https://docs.anthropic.com/en/docs/claude-code)
2. **ccoding CLI** — The CooperativeCoding Python CLI:
   ```bash
   pip install ccoding
   ```

## Installation

### From the plugin registry (recommended)

```bash
claude plugin add cooperative-coding
```

### Manual installation

Clone or copy this directory, then add it to your Claude Code plugins:

```bash
# Clone the repo
git clone https://github.com/giosullutrone/cooperative-coding-python.git

# Add the plugin
claude plugin add ./cooperative-coding-python/claude-code-skill
```

## Usage

### Quick start

```bash
# Initialize a new CooperativeCoding project
cd your-project
ccoding init

# Start Claude Code — the plugin auto-detects .ccoding/ projects
claude

# Use the /ccoding command
/ccoding create    # Design a new system from scratch
/ccoding design    # Analyze and improve existing designs
/ccoding implement # Generate code from the canvas
/ccoding review    # Check for drift between canvas and code
```

### Auto-detection

When you open Claude Code in a directory with a `.ccoding/` folder, the plugin automatically detects it and suggests getting started. You can also just ask naturally:

- "Show me the current design"
- "Propose a new class for caching"
- "Generate code for the accepted nodes"
- "Is the canvas in sync with the code?"

### Configuration

The plugin stores per-project settings in `.claude/cooperative-coding.local.md`:

```yaml
---
canvas_path: design.canvas
ccoding_path: ccoding
last_mode: create
---
```

- `canvas_path` — Path to the canvas file (auto-discovered)
- `ccoding_path` — Path to the ccoding CLI binary (default: `ccoding`)
- `last_mode` — Last used mode (suggested on next session)

## How it works

CooperativeCoding separates **design** (human strength) from **implementation** (agent strength):

1. The human designs on a visual canvas (simplified UML in JSON Canvas format)
2. The agent proposes changes as ghost nodes (requiring human approval)
3. A bidirectional sync engine keeps canvas and code aligned
4. The canvas is the source of truth for architecture; code is the source of truth for implementation

The plugin acts as the bridge between Claude Code and the ccoding CLI, providing a conversational interface over the four collaboration modes.

## Plugin structure

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

## License

MIT

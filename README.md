# cooperative-coding-python

The Python reference implementation of [CooperativeCoding](https://github.com/giosullutrone/cooperative-coding) — an open standard for human-AI collaborative software design.

> Implements CooperativeCoding Spec v1.0

## Components

This repository contains three integrated components:

- **`ccoding` CLI** — Command-line tool for canvas manipulation, bidirectional sync, and ghost node management
- **Obsidian Plugin** — Visual canvas plugin that renders CooperativeCoding nodes with native Obsidian styling (data attributes + CSS pseudo-elements)
- **Claude Code Skill** — Agentic integration that teaches Claude Code to work within the CooperativeCoding paradigm (create, design, implement, review modes)

## Installation

### CLI

```bash
pip install -e .
```

> (Not yet published to PyPI — install from source)

### Obsidian Plugin

1. Build the plugin:
   ```bash
   cd obsidian-plugin
   npm install
   npm run build
   ```
2. Copy `main.js`, `styles.css`, and `manifest.json` to your vault's `.obsidian/plugins/obsidian-cooperative-coding/` directory
3. Enable "CooperativeCoding" in Obsidian's Community Plugins settings

### Claude Code Skill

Copy the `claude-code-skill/` directory into your Claude Code plugins directory, or symlink it:

```bash
ln -s $(pwd)/claude-code-skill ~/.claude/plugins/cooperative-coding
```

## Quickstart

```bash
# Initialize a CooperativeCoding project
ccoding init

# Design your architecture on the Obsidian canvas...

# Sync canvas design to code
ccoding sync

# Check sync status
ccoding status

# Propose a new element
ccoding propose --kind class --name MyClass

# Accept or reject proposals
ccoding accept <node-id>
ccoding reject <node-id>
```

## CLI Reference

### Core

| Command | Description |
|---------|-------------|
| `init` | Initialise a new ccoding project in the current directory |
| `sync` | Perform bidirectional sync between canvas and code |
| `status` | Show the sync status between canvas and code |
| `diff` | Dry-run sync: show what would change without applying changes |
| `import` | Import an existing codebase into a canvas file |

### Proposals

| Command | Description |
|---------|-------------|
| `propose` | Propose a new ghost node in the canvas |
| `propose-edge` | Propose a new ghost edge between two nodes in the canvas |
| `accept` | Accept a proposed ghost node or edge by ID |
| `reject` | Reject a proposed ghost node or edge by ID |
| `reconsider` | Restore a rejected ghost node or edge to proposed status |
| `accept-all` | Accept all pending ghost proposals in the canvas |
| `reject-all` | Reject all pending ghost proposals in the canvas |
| `restore` | Restore a stale node back to accepted status |
| `ghosts` | List all ghost (proposed) nodes and edges in the canvas |

### Utilities

| Command | Description |
|---------|-------------|
| `show` | Show the canvas content for a node identified by its qualified name |
| `set-text` | Set the text content of a canvas node by ID |
| `check` | Check whether canvas and code are in sync (used by git pre-commit hook) |

## Development

### Python CLI

```bash
pip install -e ".[dev]"
pytest
```

### Obsidian Plugin

```bash
cd obsidian-plugin
npm install
npm run build    # production build
npm run dev      # watch mode
npm test         # run tests
```

## License

[MIT](LICENSE)

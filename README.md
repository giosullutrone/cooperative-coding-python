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
pip install cooperative-coding
```

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

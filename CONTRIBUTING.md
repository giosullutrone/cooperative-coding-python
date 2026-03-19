# Contributing to cooperative-coding-python

Thank you for your interest in contributing! This guide covers development setup, testing, and PR guidelines for each component.

## Development Setup

### Python CLI

```bash
# Clone the repo
git clone https://github.com/giosullutrone/cooperative-coding-python.git
cd cooperative-coding-python

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Obsidian Plugin

```bash
cd obsidian-plugin
npm install
```

## Running Tests

### Python CLI

```bash
pytest
```

To run with coverage:

```bash
pytest --cov=ccoding
```

### Obsidian Plugin

```bash
cd obsidian-plugin
npm test
```

## Building

### Obsidian Plugin

```bash
cd obsidian-plugin
npm run build    # production build
npm run dev      # watch mode for development
```

## Pull Request Guidelines

- **One feature per PR.** Keep changes focused and reviewable.
- **Include tests.** All new functionality should have corresponding tests.
- **Follow conventional commits.** Use prefixes like `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:` in your commit messages.
- **Keep PRs small.** If a change is large, consider splitting it into multiple PRs.
- **Describe the "why".** PR descriptions should explain the motivation, not just what changed.

## Architecture Questions

For questions about the CooperativeCoding specification, design decisions, or the standard itself, please refer to the [spec repo](https://github.com/giosullutrone/cooperative-coding). Implementation-specific discussions belong here; protocol-level discussions belong in the spec repo.

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to build something useful together.

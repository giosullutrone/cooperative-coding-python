---
name: cooperative-coding:create
description: "Use when building a new CooperativeCoding canvas design from scratch — gathering requirements, proposing architecture, creating nodes and edges"
---

See the `cooperative-coding` skill for prerequisites, CLI reference, and error handling.

## Create Mode

Build an initial canvas design from scratch through conversation.

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

```bash
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
```

The `--rationale` documents that these elements were human-approved during creation. Use `--stereotype` to set the Python construct type (protocol, abstract, dataclass, enum).

**Rich node content:** The `propose` command creates nodes with minimal text. After creating and accepting a node, use `set-text` to add full structured markdown (fields, methods, documentation):

```bash
# Pipe structured markdown into the node
echo '# DocumentParser\n## Responsibility\nParses documents...' | ccoding set-text <node_id>

# Or from a temp file for complex content
ccoding set-text <node_id> --file /tmp/node-content.md
```

Then run `ccoding sync` to update state.

## Detail Pass

After the overview is placed, ask: "Want to add method or field details to any of these classes?" For each yes, gather signatures, responsibilities, and pseudo code, then create detail nodes linked via `detail` edges.

## Initial Sync

Run `ccoding sync` to generate code skeletons. Report which files were created.

# CooperativeCoding — Open Specification

*A language-agnostic, tool-agnostic standard for human-agent collaborative software design.*

---

## 1. Vision & Objective

CooperativeCoding is a paradigm for human-agent collaborative software design where the human focuses on architecture and the agent handles implementation.

The core insight: **code design and code implementation are different skills that benefit from different tools.** Humans excel at architectural thinking — defining responsibilities, drawing boundaries, seeing the big picture. Agents excel at translating precise specifications into correct, complete code. Today, both happen in the same text editor, forcing the human to think at the wrong level of abstraction.

CooperativeCoding separates these concerns:

- **The human works on a visual canvas** — a simplified UML where classes, interfaces, methods, fields, and their relationships are first-class objects. Each element carries a documentation block with its responsibility and pseudo code. The canvas shows what truly matters: the architecture, the contracts, the design intent.
- **The agent works on the code** — it reads the canvas design, proposes improvements as ghost nodes, implements the underlying source code, and keeps canvas and code in bidirectional sync.
- **They cooperate** — the agent doesn't just execute orders. It proposes design changes (ghost nodes on canvas), flags architectural issues, and suggests alternatives. The human remains the design authority — accepting, rejecting, or modifying proposals before anything gets implemented.

### 1.1 Scope of This Specification

This document defines the **open CooperativeCoding standard** — a community contribution that can be adopted and implemented by any canvas tool, any programming language, and any agentic system. It is intentionally tool-agnostic and language-agnostic.

Concrete implementations require three things:

1. **A canvas tool implementation** — a plugin or extension for a visual canvas application (e.g., Obsidian, Excalidraw, tldraw, VS Code) that renders CooperativeCoding nodes and supports the cooperation UX
2. **A language binding** — a mapping from the abstract spec to a specific programming language's idioms (e.g., Python docstrings, TypeScript JSDoc, Rust doc comments)
3. **An agent integration** — a skill, plugin, or configuration that teaches an agentic coding tool to work within the CooperativeCoding paradigm

### 1.2 Reference Implementation

The first reference implementation targets:

- **Canvas tool:** Obsidian (self-contained plugin + extended Obsidian CLI)
- **Language:** Python (PEP-compliant docstrings, type hints, protocols)
- **Agent:** Claude Code (skill for design, proposal, and implementation)

Details specific to this reference implementation are in the appendices.

---

## 2. Core Principles

1. **Design Authority is Human** — The human always has final say on architecture. The agent proposes, the human disposes. No design change is applied without human approval (accept/reject ghost nodes).

2. **Progressive Detail** — Not everything deserves the same level of attention. Class nodes give the overview. Method nodes add detail only where it matters. The canvas highlights architecture, not every line of code.

3. **Documentation as Contract** — The documentation block is the bridge between canvas and code. It contains the responsibility, pseudo code, and type signatures that both the human and agent rely on. If the documentation is clear, the implementation follows.

4. **Bidirectional Truth** — Canvas and code are two views of the same system. Changes in either propagate to the other. Neither is "primary" — they are kept in sync through a shared data model.

5. **Visual Simplicity** — The canvas shows a simplified UML focused on what matters for design: classes, interfaces, packages, dependencies, and method call flow. It deliberately omits what doesn't serve architectural thinking.

6. **Any Entry Point** — Start from a blank canvas, describe a system in natural language, or import existing code. The paradigm meets you where you are.

7. **Language-Agnostic, Tool-Agnostic** — The concepts (nodes, edges, documentation blocks, ghost proposals) are universal. Each programming language and canvas tool gets a concrete binding that maps to its idioms and capabilities.

---

## 3. Data Model

The CooperativeCoding data model is a semantic layer on top of the [JSON Canvas v1.0](https://jsoncanvas.org/spec/1.0/) open specification. Any canvas tool that supports JSON Canvas can adopt CooperativeCoding by reading the `ccoding` metadata fields.

A `.canvas` file produced by CooperativeCoding is:

- Valid **JSON Canvas v1.0** — any tool can read the basics
- Enriched with **`ccoding` metadata** — semantic information for the sync engine, agent, and canvas tool

### 3.1 Semantic Layer: `ccoding` Metadata

Every CooperativeCoding node and edge carries a `ccoding` object with semantic information. Standard tools safely ignore these fields; CooperativeCoding-aware tools read them.

**Node metadata:**

```json
{
  "id": "node-1",
  "type": "text",
  "x": 100, "y": 200, "width": 300, "height": 400,
  "text": "...(structured markdown)...",
  "ccoding": {
    "kind": "class",
    "stereotype": "protocol",
    "language": "python",
    "source": "src/parsers/document.py",
    "qualifiedName": "parsers.document.DocumentParser",
    "status": "accepted",
    "proposedBy": null,
    "proposalRationale": null
  }
}
```

Fields:

- **`kind`**: `class` | `method` | `field` | `package` — the type of code element this node represents
- **`stereotype`**: language-specific subtype (see language binding appendices for valid values per language). Common values: `class` | `interface` | `abstract` | `enum`
- **`language`**: identifier for the programming language (e.g., `python`, `typescript`, `rust`, `go`)
- **`source`**: relative path to the source file this node maps to
- **`qualifiedName`**: fully qualified name in the target language (e.g., `parsers.document.DocumentParser`)
- **`status`**: `accepted` | `proposed` | `rejected` — ghost nodes have `proposed`
- **`proposedBy`**: `"agent"` | `"human"` | `null`
- **`proposalRationale`**: string explaining why this node/edge was proposed (ghost nodes only, `null` for accepted)

**Edge metadata:**

```json
{
  "id": "edge-1",
  "fromNode": "node-1", "toNode": "node-2",
  "fromSide": "bottom", "toSide": "top",
  "ccoding": {
    "relation": "inherits",
    "status": "accepted",
    "proposedBy": null
  }
}
```

**Relation types:**

- **`inherits`** — class extends another class
- **`implements`** — class implements an interface/protocol/trait
- **`composes`** — class contains another as a field (has-a relationship)
- **`depends`** — class uses another (import/dependency)
- **`calls`** — method calls another method (method call flow)
- **`detail`** — class node → method detail node link (the ● connection)
- **`context`** — links a context node (text/file/link) to a ccoding node for reference. Multiple context nodes can attach to the same target node.

### 3.2 Context Nodes

Alongside `ccoding`-specific nodes (class, method, package), a CooperativeCoding canvas supports **standard JSON Canvas nodes** for collaboration context:

- **Text nodes** — free-form notes for design rationale, decision logs, open questions, TODOs
- **File nodes** — embedded images, PDFs, diagrams from other tools, reference screenshots, architecture sketches, whiteboard photos
- **Link nodes** — external URLs to documentation, API references, related repos, issue trackers

Context nodes:

- Have **no `ccoding` metadata by default** — they are plain JSON Canvas nodes
- Are **not synced** to code — they exist only on the canvas as collaboration artifacts
- Can be **connected via `context` edges** to `ccoding` nodes. Multiple context nodes can attach to the same target (e.g., a class node may have a rationale note, a reference PDF, and a whiteboard photo all linked to it)
- Can be **proposed as ghosts** by the agent (e.g., the agent attaches a note explaining a design tradeoff, or links relevant documentation). In this case, the node carries a minimal `ccoding` object with only `status` and `proposedBy`:

```json
{
  "id": "note-1",
  "type": "text",
  "x": 400, "y": 200, "width": 250, "height": 150,
  "text": "Protocol chosen over ABC because...",
  "ccoding": {
    "status": "proposed",
    "proposedBy": "agent"
  }
}
```

### 3.3 Node Content: Structured Markdown

The canvas node `text` field uses structured markdown that is both human-readable on the canvas and parseable for sync. This format is language-agnostic — it uses generic sections that each language binding maps to its idioms.

**Class node content:**

```markdown
«interface»
## DocumentParser

> Responsible for parsing raw documents into structured AST nodes

### Fields
- config: `ParserConfig`
- _cache: `Map<String, AST>`
- plugins: `List<ParserPlugin>`

### Methods
- parse(source: `String`) -> `AST` ●
- validate(ast: `AST`) -> `Boolean`
- register_plugin(p: `ParserPlugin`) -> `Void`
```

**Method node content:**

```markdown
## DocumentParser.parse

### Responsibility
Transform raw source into a validated AST, applying all registered plugins in order.

### Signature
- **IN:** source: `String` — raw document text
- **OUT:** `AST` — parsed syntax tree
- **RAISES:** `ParseError` — on malformed input

### Pseudo Code
1. Check _cache for source hash
2. If cached, return cached AST
3. Tokenize source using config.tokenizer
4. Build raw AST from token stream
5. For each plugin: ast = plugin.transform(ast)
6. Validate final AST structure
7. Cache and return
```

**Package node:** Uses JSON Canvas group nodes with `ccoding.kind: "package"`. Label = module/package path. Contains child class nodes.

The structured markdown sections (`### Responsibility`, `### Pseudo Code`, `### Signature`, `### Fields`, `### Methods`) are part of the spec. Language bindings define how these map to language-specific documentation formats (e.g., Python docstrings, JSDoc comments, Rust doc comments).

### 3.4 Recommended Visual Representation

The spec recommends (but does not mandate) the following visual conventions for canvas tool implementations. Tools may adapt these to their rendering capabilities.

**Node visual styles:**

- **Class nodes**: UML box shape, purple border. Stereotype label (`«interface»`, `«abstract»`, etc.)
- **Method nodes**: Rounded shape, orange border
- **Package groups**: Styled group node with module path label
- **Ghost nodes** (`status: "proposed"`): Dashed border, reduced opacity, accept/reject overlay
- **Rejected nodes**: Greyed out, collapsible or hidden

**Edge visual styles:**

- **`inherits`**: solid line, hollow triangle arrow
- **`implements`**: dashed line, hollow triangle arrow
- **`composes`**: solid line, filled diamond
- **`depends`**: dashed line, open arrow
- **`calls`**: dotted line, filled arrow
- **`detail`**: solid line, circle endpoint
- **`context`**: thin grey line, no arrow

**Context nodes** (text/file/link without `ccoding.kind`) render with the canvas tool's default styling. When a ccoding node is selected, its linked context nodes should be visually highlighted to show the association. Multiple context nodes can attach to the same target.

### 3.5 Sync Mapping: Abstract Rules

Bidirectional sync maps canvas elements to code elements. The abstract rules below apply regardless of language; each language binding defines the concrete mapping.

| Canvas Element | Code Element |
|---|---|
| Class node `text` | Class/type definition + documentation block |
| Method node `text` | Method/function signature + documentation block |
| Class `### Fields` | Class attributes/fields + type annotations |
| Method `### Pseudo Code` | Documentation block `Pseudo Code` section |
| Method `### Signature` | Method signature + parameter/return documentation |
| Package group | Module/package/namespace directory |
| Edge `inherits` | Inheritance declaration |
| Edge `implements` | Interface/protocol/trait implementation |
| Edge `composes` | Field with composed type |
| Edge `depends` | Import/use/require statement |
| `ccoding.status: proposed` | Not yet in code (ghost) |
| Context nodes (text/file/link) | Not synced — canvas-only collaboration artifacts |
| Edge `context` | Not synced — canvas-only association |

---

## 4. Cooperation Workflow

### 4.1 Entry Points

Three ways to start a CooperativeCoding session:

**From blank canvas (human sketches first):**

1. Human creates class/method nodes manually on canvas
2. Human fills in responsibility, fields, methods, pseudo code
3. Human asks the agent to implement → agent reads canvas, generates source files, sync establishes

**From natural language (agent proposes):**

1. Human describes the system in text: "I need a document parser with plugin support and caching"
2. Agent generates an initial design as ghost nodes (all `status: "proposed"`)
3. Human reviews the canvas — accepts, rejects, or modifies individual nodes and edges
4. Once the human is satisfied, they ask the agent to implement the accepted design

**From existing code (import):**

1. Human points the tool at existing source files: "Import src/parsers/ into the canvas"
2. The sync engine parses the code — extracts classes, methods, fields, type annotations, documentation, relationships
3. Generates canvas nodes with `status: "accepted"` (since the code already exists)
4. Human and agent can now iterate on the design visually

### 4.2 The Cooperation Loop

```
Human edits canvas  ──→  Sync updates code
       ↑                        ↓
  Human accepts/          Agent reads code
  rejects proposals       + canvas state
       ↑                        ↓
Agent proposes      ←──  Agent identifies
ghost nodes               improvements
```

**Human actions on canvas:**

- Create, edit, delete nodes and edges
- Edit documentation blocks, pseudo code, responsibility directly in node text
- Accept a ghost node (`status` → `accepted`, triggers code generation)
- Reject a ghost node (`status` → `rejected`, node greys out or hides)
- Request agent input: "What's missing from this design?" or "Implement this class"

**Agent actions:**

- **Propose** — create ghost nodes/edges (`status: "proposed"`, `proposedBy: "agent"`) with a rationale
- **Implement** — generate or update source code from accepted canvas nodes
- **Sync** — detect code changes and update canvas, or detect canvas changes and update code
- **Analyze** — flag design issues (circular dependencies, missing interfaces, SRP violations)
- **Never** modify accepted nodes without human approval — all changes come as proposals

### 4.3 Ghost Node Lifecycle

```
proposed  ──accept──→  accepted  ──→  code generated/updated
    │                                        ↓
    │                                  bidirectional sync active
    │
    └──reject──→  rejected  ──→  greyed out / hidden
                      │
                      └──reconsider──→  proposed (back to review)
```

- Ghost nodes carry a `proposalRationale` field in their `ccoding` metadata explaining why the agent proposed them
- Multiple ghost nodes can be proposed at once (e.g., "I suggest splitting this class into two" creates two new class ghosts + edges)
- The human can modify a ghost node before accepting it (edit the responsibility, rename, change fields) — it stays `proposed` until explicitly accepted

### 4.4 Bidirectional Sync Rules

**Canvas → Code** (triggered when human or agent edits canvas):

- New accepted class node → generate new source file with class skeleton + documentation block
- Edit class fields/methods → update class definition in source
- Edit method pseudo code → update documentation block
- New edge `inherits` → update inheritance declaration in code
- Delete accepted node → mark code as deprecated (not deleted — human must delete manually for safety)

**Code → Canvas** (triggered when agent or human edits source files):

- New class in source → create new class node on canvas
- New method added → update class node's method list (and create method detail node if documentation contains pseudo code)
- Changed documentation sections → update corresponding canvas node text
- Changed type annotations / signatures → update canvas fields and method signatures
- Deleted class/method → mark canvas node as stale (visual indicator, not auto-deleted)

**Conflict resolution:**

- If both canvas and code changed for the same element since last sync → flag a conflict
- Agent presents both versions to human and asks which to keep (or merge)
- Never silently overwrite either side

---

## 5. Implementation Guide

Any complete CooperativeCoding implementation requires three components. This section defines what each must support.

### 5.1 Canvas Tool Implementation

A canvas tool plugin/extension must:

- **Render** `ccoding` nodes according to their `kind` and `stereotype` (using the recommended visual styles or tool-appropriate equivalents)
- **Render** edges according to their `relation` type with visually distinguishable styles
- **Support ghost node UX** — visually distinguish `proposed` nodes (e.g., dashed borders), provide accept/reject controls
- **Preserve** `ccoding` metadata in the `.canvas` file through save/load cycles
- **Emit events** when nodes or edges are created, modified, or deleted (for sync triggers)
- **Render context nodes** (text/file/link) with the tool's native styling, visually highlighting linked context nodes when a ccoding node is selected
- **Coexist safely** with other canvas plugins/extensions — namespace all custom attributes, avoid overriding shared styles

### 5.2 Programmatic Interface (CLI / API)

A programmatic interface must support:

- **Canvas CRUD** — create, read, update, delete nodes and edges in `.canvas` files
- **Ghost node management** — propose, accept, reject nodes via commands
- **Sync engine** — bidirectional sync between canvas and source files, following the abstract sync mapping rules
- **Code parsing** — extract classes, methods, fields, type annotations, documentation from source files to generate canvas nodes
- **Canvas parsing** — read structured markdown from canvas nodes to generate/update source files
- **Import** — parse an existing codebase into canvas representation
- **Conflict detection** — identify canvas/code conflicts and surface them for resolution

### 5.3 Agent Integration

An agent skill/integration must:

- **Know the spec** — understand node types, edge semantics, documentation format, sync rules
- **Know the programmatic interface** — be able to call the CLI/API for all canvas and sync operations
- **Design mode** — read canvas, analyze architecture, propose improvements as ghost nodes with rationales
- **Implement mode** — read accepted canvas nodes, generate source code following the documentation contract
- **Review mode** — compare canvas design to actual code, flag drift or violations
- **Conversation patterns** — know how to ask the human for design decisions, present proposals, and suggest architectural improvements

### 5.4 Language Binding

A language binding must define:

- **Stereotype mapping** — which `stereotype` values are valid for the language (e.g., Python: `class` | `protocol` | `abstract` | `dataclass` | `enum`; TypeScript: `class` | `interface` | `abstract` | `type` | `enum`)
- **Documentation format** — how `Responsibility`, `Pseudo Code`, `Collaborators`, and signature information map to the language's documentation conventions
- **Sync mapping** — concrete rules for how each canvas element maps to language-specific code constructs
- **Type notation** — how types in the structured markdown `### Fields` and `### Signature` sections correspond to the language's type system

---

## Appendix A: Python Language Binding

### A.1 Stereotype Mapping

| `ccoding.stereotype` | Python Construct |
|---|---|
| `class` | `class Foo:` |
| `protocol` | `class Foo(Protocol):` |
| `abstract` | `class Foo(ABC):` |
| `dataclass` | `@dataclass class Foo:` |
| `enum` | `class Foo(Enum):` |

### A.2 Documentation Format

Python uses [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) extended with custom sections.

**Class docstring:**

```python
class DocumentParser(Protocol):
    """Parse raw documents into structured AST nodes.

    Responsibility:
        Owns the full parsing pipeline from raw text to validated AST,
        including plugin application and caching.

    Collaborators:
        ParserConfig: Provides tokenizer and parsing settings.
        ParserPlugin: Transforms AST during parsing pipeline.

    Attributes:
        config: Parser configuration and settings.
        _cache: Memoization cache keyed by source hash.
        plugins: Ordered list of transform plugins.
    """
```

**Method docstring:**

```python
def parse(self, source: str) -> AST:
    """Transform raw source into a validated AST.

    Responsibility:
        Parse raw document text into structured AST nodes,
        applying all registered plugins in order.

    Pseudo Code:
        1. Check _cache for source hash
        2. If cached, return cached AST
        3. Tokenize source using config.tokenizer
        4. Build raw AST from token stream
        5. For each plugin: ast = plugin.transform(ast)
        6. Validate final AST structure
        7. Cache and return

    Args:
        source: Raw document text to parse.

    Returns:
        Parsed and validated abstract syntax tree.

    Raises:
        ParseError: If the source is malformed.
    """
```

Custom sections: **`Responsibility:`**, **`Pseudo Code:`**, **`Collaborators:`** (for classes).

### A.3 Sync Mapping

| Canvas Element | Python Code |
|---|---|
| Class node `text` | Class definition + class docstring |
| Method node `text` | Method signature + method docstring |
| Class `### Fields` | Class attributes + type annotations |
| Method `### Pseudo Code` | Docstring `Pseudo Code:` section |
| Method `### Signature` | Method signature + `Args:`/`Returns:`/`Raises:` |
| Package group | Python package directory (`__init__.py`) |
| Edge `inherits` | `class Foo(Bar)` |
| Edge `implements` | `class Foo(Protocol)` |
| Edge `composes` | Field with composed type |
| Edge `depends` | `import` / `from ... import` statement |
| `ccoding.stereotype: protocol` | `typing.Protocol` |
| `ccoding.stereotype: dataclass` | `@dataclasses.dataclass` |
| `ccoding.stereotype: abstract` | `abc.ABC` + `@abstractmethod` |

### A.4 Type Notation

Canvas structured markdown uses Python type hint syntax directly:

- `str`, `int`, `float`, `bool` for primitives
- `list[T]`, `dict[K, V]`, `tuple[T, ...]` for collections
- `Optional[T]` or `T | None` for optional types
- Custom types use their class name (e.g., `ParserConfig`, `AST`)

---

## Appendix B: Obsidian Canvas Tool Implementation

### B.1 Architecture

The Obsidian implementation is a self-contained plugin that extends Obsidian's Canvas directly. It does not require the Advanced Canvas plugin but is designed to coexist with it.

```
CooperativeCoding Plugin (semantic model + rendering)
    ↓ extends directly
Obsidian Canvas / JSON Canvas v1.0
    ↓ optionally coexists with
Advanced Canvas (detected at runtime, avoids conflicts)
```

### B.2 Rendering

The plugin handles:

- Custom node rendering based on `ccoding.kind` and `ccoding.stereotype` (UML-style class boxes, method detail cards)
- Custom edge rendering based on `ccoding.relation` (inheritance arrows, composition diamonds, etc.)
- Ghost node UX: dashed borders, reduced opacity, accept/reject controls for `status: "proposed"` nodes
- Canvas event hooks for bidirectional sync triggers

### B.3 Clash Prevention Strategy

**Namespace isolation:**

- All CSS classes use the `ccoding-` prefix (e.g., `ccoding-class-node`, `ccoding-ghost`, `ccoding-edge-inherits`)
- All `data-*` attributes use `data-ccoding-*` (e.g., `data-ccoding-kind`, `data-ccoding-status`)
- Canvas metadata lives exclusively in the `ccoding` object — we never read or write Advanced Canvas's own metadata fields

**Patch chaining, not overwriting:**

- Use the `monkey-around` library, which wraps existing methods rather than replacing them
- Our patches call `next()` to pass through to the original (or Advanced Canvas's patch), only adding behavior for nodes/edges that have `ccoding` metadata
- If a node has no `ccoding` field, our patch is a no-op passthrough

```
Canvas method call
  → CooperativeCoding patch (acts only on ccoding nodes, else passes through)
    → Advanced Canvas patch (acts on its own nodes, else passes through)
      → Original Obsidian Canvas method
```

**Load order independence:**

- Works correctly regardless of which plugin loads first
- On startup, we detect Advanced Canvas but never call its internals directly — we only avoid double-patching shared entry points
- If Advanced Canvas is removed later, our plugin continues working without changes

**Defensive CSS:**

- Our styles target only elements with `[data-ccoding-kind]` selectors
- We never use generic `.canvas-node` selectors without also requiring our namespace attribute
- No `!important` overrides on shared properties

### B.4 Extended Obsidian CLI

The Obsidian CLI is extended with `ccoding` subcommands for programmatic canvas manipulation:

```bash
# Create a class node
obsidian ccoding create-node --kind class --stereotype protocol \
  --name DocumentParser --source src/parsers/document.py

# Propose a method node (ghost)
obsidian ccoding propose-node --kind method \
  --name "DocumentParser.parse" --rationale "Core parsing entry point"

# Accept a ghost node
obsidian ccoding accept-node --id node-42

# Run bidirectional sync
obsidian ccoding sync --canvas design.canvas --source src/

# Import existing code to canvas
obsidian ccoding import --source src/parsers/ --canvas design.canvas
```

The CLI owns the sync engine logic. The plugin provides the visual layer.

---

## Appendix C: Claude Code Agent Integration

### C.1 Skill Overview

The Claude Code skill teaches the agent to cooperate within the CooperativeCoding paradigm:

- Knows the full spec: node types, edge semantics, documentation format, sync rules
- Knows how to call the Obsidian CLI `ccoding` subcommands for all canvas and sync operations
- **Design mode:** reads canvas, analyzes architecture, proposes improvements as ghost nodes with rationales
- **Implement mode:** reads accepted canvas nodes, generates Python code following the documentation contract
- **Review mode:** compares canvas design to actual code, flags drift or violations
- **Conversation patterns:** how to ask the human for design decisions, how to present proposals, when to suggest splitting a class vs. keeping it

### C.2 Build Order

```
Spec (this document — defines everything, no dependencies)
 ├── Obsidian Plugin (reads spec to render correctly)
 ├── Obsidian CLI extension (reads spec to sync correctly)
 └── Claude Code Skill (reads spec + uses CLI to cooperate)

Build order:
  1. Spec               (defines the standard)
  2. CLI extension      (needs spec, enables programmatic canvas work)
  3. Obsidian Plugin    (needs spec, can develop in parallel with CLI)
  4. Claude Code Skill  (needs spec + CLI to be functional)
```

The CLI and Plugin can be developed in parallel after the spec is done — they share the data model but don't depend on each other. The Skill comes last because it needs to call the CLI.

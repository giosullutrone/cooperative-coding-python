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

### 1.2 Companion Documents

Each concrete implementation is defined in its own specification:

- **Language bindings** — separate specs per language (e.g., *CooperativeCoding Python Language Binding*)
- **Canvas tool implementations** — separate specs per tool (e.g., an Obsidian plugin spec)
- **Agent integrations** — separate specs per agent (e.g., a Claude Code skill spec)

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

- **`kind`**: `class` | `method` | `field` | `package` — the type of code element this node represents. Note: `field` is not a standalone node type — fields appear inline within class nodes' `### Fields` section. The `field` kind exists for edge targets and metadata queries.
- **`stereotype`**: language-specific subtype. Each language binding defines its own valid values (e.g., Python: `protocol`, `dataclass`; TypeScript: `interface`, `type`). This is an open set — not limited to the examples here.
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
    "proposedBy": null,
    "proposalRationale": null
  }
}
```

Edges carry the same `status`, `proposedBy`, and `proposalRationale` fields as nodes. A proposed edge can carry a rationale (e.g., "This inheritance reduces duplication between these two classes").

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

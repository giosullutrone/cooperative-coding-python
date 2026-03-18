# CooperativeCoding Initiative — Design Specification

## 1. Vision & Objective

CooperativeCoding is a paradigm for human-agent collaborative software design where the human focuses on architecture and the agent handles implementation.

The core insight: **code design and code implementation are different skills that benefit from different tools.** Humans excel at architectural thinking — defining responsibilities, drawing boundaries, seeing the big picture. Agents excel at translating precise specifications into correct, complete code. Today, both happen in the same text editor, forcing the human to think at the wrong level of abstraction.

CooperativeCoding separates these concerns:

- **The human works on a visual canvas** — a simplified UML where classes, interfaces, methods, fields, and their relationships are first-class objects. Each element carries a docstring with its responsibility and pseudo code. The canvas shows what truly matters: the architecture, the contracts, the design intent.
- **The agent works on the code** — it reads the canvas design, proposes improvements as ghost nodes, implements the underlying Python (and eventually other languages), and keeps canvas and code in bidirectional sync.
- **They cooperate** — the agent doesn't just execute orders. It proposes design changes (ghost nodes on canvas), flags architectural issues, and suggests alternatives. The human remains the design authority — accepting, rejecting, or modifying proposals before anything gets implemented.

The deliverable is an ecosystem of 4 subsystems:

1. **The CooperativeCoding Spec** — the data model, formats, and conventions that all tools share
2. **An Obsidian plugin** — extending Obsidian Canvas with CooperativeCoding node types and UX
3. **An extended Obsidian CLI** — programmatic canvas manipulation and bidirectional sync engine
4. **A Claude Code skill** — teaching the agent to design, propose, and implement in this paradigm

---

## 2. Core Principles

1. **Design Authority is Human** — The human always has final say on architecture. The agent proposes, the human disposes. No design change is applied without human approval (accept/reject ghost nodes).

2. **Progressive Detail** — Not everything deserves the same level of attention. Class nodes give the overview. Method nodes add detail only where it matters. The canvas highlights architecture, not every line of code.

3. **Docstring as Contract** — The docstring is the bridge between canvas and code. It contains the responsibility, pseudo code, and type signatures that both the human and agent rely on. If the docstring is clear, the implementation follows. Extended Google/NumPy style with `Responsibility:` and `Pseudo Code:` sections.

4. **Bidirectional Truth** — Canvas and code are two views of the same system. Changes in either propagate to the other. Neither is "primary" — they are kept in sync through a shared data model.

5. **Visual Simplicity** — The canvas shows a simplified UML focused on what matters for design: classes, interfaces, packages, dependencies, and method call flow. It deliberately omits what doesn't serve architectural thinking.

6. **Any Entry Point** — Start from a blank canvas, describe a system in natural language, or import existing code. The paradigm meets you where you are.

7. **Language-Agnostic Paradigm, Concrete Implementations** — The concepts (nodes, edges, docstrings, ghost proposals) are universal. Each language gets a concrete implementation that maps to its idioms. Python is the first supported language (protocols, PEP docstrings, type hints); other languages follow.

---

## 3. Data Model

The CooperativeCoding data model is a semantic layer on top of Obsidian's JSON Canvas format. The plugin is self-contained — it does not require Advanced Canvas but coexists with it without conflicts.

```
CooperativeCoding Plugin (semantic model + rendering)
    ↓ extends directly
Obsidian Canvas / JSON Canvas v1.0
    ↓ optionally coexists with
Advanced Canvas (detected at runtime, avoids conflicts)
```

A `.canvas` file produced by CooperativeCoding is:

- Valid **JSON Canvas v1.0** — any tool can read the basics
- Enriched with **`ccoding` metadata** — semantic information for the CLI, skill, and sync engine
- Optionally compatible with **Advanced Canvas** — both plugins can coexist

### 3.1 Semantic Layer: `ccoding` Metadata

Every CooperativeCoding node and edge carries a `ccoding` object with semantic information. Standard tools safely ignore these fields; our plugin, CLI, and skill read them.

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

- **`kind`**: `class` | `method` | `field` | `package`
- **`stereotype`** (class nodes): `class` | `protocol` | `abstract` | `dataclass` | `enum`
- **`language`**: `python` (extensible to other languages)
- **`source`**: relative path to the source file this node maps to
- **`qualifiedName`**: fully qualified Python name (e.g., `parsers.document.DocumentParser.parse`)
- **`status`**: `accepted` | `proposed` | `rejected`
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
- **`implements`** — class implements a protocol/interface
- **`composes`** — class contains another as a field
- **`depends`** — class uses another
- **`calls`** — method calls another method (method call flow)
- **`detail`** — class node → method detail node link (the ● connection)

### 3.2 Rendering Layer: Self-Contained with Optional Compatibility

CooperativeCoding implements its own canvas rendering extensions, patching only what it needs from Obsidian's Canvas internals. It does not require Advanced Canvas.

**Our plugin handles:**

- Custom node rendering based on `ccoding.kind` and `ccoding.stereotype` (UML-style class boxes, method detail cards)
- Custom edge rendering based on `ccoding.relation` (inheritance arrows, composition diamonds, etc.)
- Ghost node UX: dashed borders, reduced opacity, accept/reject controls for `status: "proposed"` nodes
- Canvas event hooks for bidirectional sync triggers

**Node visual styles:**

- **Class nodes**: UML box shape, purple border. Stereotype shown as `«protocol»`, `«abstract»`, etc.
- **Method nodes**: Rounded shape, orange border
- **Package groups**: Styled group node with module path label
- **Ghost nodes**: Dashed border, reduced opacity, accept/reject overlay
- **Rejected nodes**: Greyed out, collapsible

**Edge visual styles:**

- **`inherits`**: solid line, hollow triangle arrow
- **`implements`**: dashed line, hollow triangle arrow
- **`composes`**: solid line, filled diamond
- **`depends`**: dashed line, open arrow
- **`calls`**: dotted line, filled arrow
- **`detail`**: solid line, circle endpoint

### 3.2.1 Clash Prevention Strategy

**Namespace isolation:**

- All CSS classes use the `ccoding-` prefix (e.g., `ccoding-class-node`, `ccoding-ghost`, `ccoding-edge-inherits`)
- All `data-*` attributes use `data-ccoding-*` (e.g., `data-ccoding-kind`, `data-ccoding-status`)
- Canvas metadata lives exclusively in the `ccoding` object — we never read or write Advanced Canvas's own metadata fields

**Patch chaining, not overwriting:**

- Use the `monkey-around` library (same one Advanced Canvas uses), which wraps existing methods rather than replacing them
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

### 3.3 Node Content: Structured Markdown

The canvas node `text` field uses structured markdown that is both human-readable on the canvas and parseable for sync.

**Class node content:**

```markdown
«protocol»
## DocumentParser

> Responsible for parsing raw documents into structured AST nodes

### Fields
- config: `ParserConfig`
- _cache: `dict[str, AST]`
- plugins: `list[ParserPlugin]`

### Methods
- parse(source: `str`) -> `AST` ●
- validate(ast: `AST`) -> `bool`
- register_plugin(p: `ParserPlugin`) -> `None`
```

**Method node content:**

```markdown
## DocumentParser.parse

### Responsibility
Transform raw source into a validated AST, applying all registered plugins in order.

### Signature
- **IN:** source: `str` — raw document text
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

**Package node:** Uses JSON Canvas group nodes with `ccoding.kind: "package"`. Label = module path (e.g., `parsers.document`). Contains child class nodes.

### 3.4 Docstring Format (Python Implementation)

The docstring in `.py` files mirrors the canvas node content. This is the bridge for bidirectional sync — changes to either side propagate through the sync engine.

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

Custom sections added to standard Google style: **`Responsibility:`**, **`Pseudo Code:`**, and **`Collaborators:`** (for classes).

### 3.5 Sync Mapping Summary

| Canvas | Python Code |
|---|---|
| Class node `text` | Class definition + class docstring |
| Method node `text` | Method signature + method docstring |
| Class `### Fields` | Class attributes + type annotations |
| Method `### Pseudo Code` | Docstring `Pseudo Code:` section |
| Method `### Signature` | Method signature + `Args:`/`Returns:`/`Raises:` |
| Package group | Python module/package directory |
| Edge `inherits` | `class Foo(Bar)` |
| Edge `implements` | `class Foo(Protocol)` |
| Edge `composes` | Field with composed type |
| Edge `depends` | Import statement |
| `ccoding.status: proposed` | Not yet in code (ghost) |

---

## 4. Cooperation Workflow

### 4.1 Entry Points

Three ways to start a CooperativeCoding session:

**From blank canvas (human sketches first):**

1. Human creates class/method nodes manually on canvas
2. Human fills in responsibility, fields, methods, pseudo code
3. Human asks the agent to implement → agent reads canvas, generates `.py` files, sync establishes

**From natural language (agent proposes):**

1. Human describes the system in text: "I need a document parser with plugin support and caching"
2. Agent generates an initial design as ghost nodes (all `status: "proposed"`)
3. Human reviews the canvas — accepts, rejects, or modifies individual nodes and edges
4. Once the human is satisfied, they ask the agent to implement the accepted design

**From existing code (import):**

1. Human points the tool at existing `.py` files: "Import src/parsers/ into the canvas"
2. CLI/skill parses the code — extracts classes, methods, fields, type hints, docstrings, relationships
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
- Edit docstrings, pseudo code, responsibility directly in node text
- Accept a ghost node (`status` → `accepted`, triggers code generation)
- Reject a ghost node (`status` → `rejected`, node greys out or hides)
- Request agent input: "What's missing from this design?" or "Implement this class"

**Agent actions:**

- **Propose** — create ghost nodes/edges (`status: "proposed"`, `proposedBy: "agent"`) with a rationale in the node text
- **Implement** — generate or update `.py` code from accepted canvas nodes
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

**Canvas → Code** (triggered when human edits canvas):

- New accepted class node → generate new `.py` file with class skeleton + docstring
- Edit class fields/methods → update class definition in `.py`
- Edit method pseudo code → update `Pseudo Code:` section in method docstring
- New edge `inherits` → update class inheritance in code
- Delete accepted node → mark code as deprecated (not deleted — human must delete code manually for safety)

**Code → Canvas** (triggered when agent or human edits `.py` files):

- New class in `.py` → create new class node on canvas
- New method added → update class node's method list (and create method detail node if it has `Pseudo Code:` in docstring)
- Changed docstring sections → update corresponding canvas node text
- Changed type hints / signatures → update canvas fields and method signatures
- Deleted class/method → mark canvas node as stale (visual indicator, not auto-deleted)

**Conflict resolution:**

- If both canvas and code changed for the same element since last sync → flag a conflict
- Agent presents both versions to human and asks which to keep (or merge)
- Never silently overwrite either side

---

## 5. Subsystem Architecture & Responsibilities

Each subsystem owns a clear domain and communicates through the shared `.canvas` + `.py` files.

### 5.1 The CooperativeCoding Spec (this document)

**Owns:** The contract that all subsystems follow.

- `ccoding` metadata schema (node and edge fields, valid values)
- Structured markdown format for node content
- Extended docstring format (Responsibility, Pseudo Code, Collaborators sections)
- Edge relation types and their visual + code mappings
- Ghost node lifecycle and status transitions
- Sync mapping rules (canvas ↔ code)
- Clash prevention rules for Obsidian plugin coexistence

### 5.2 The Obsidian Plugin

**Owns:** Visual canvas experience and real-time editing UX.

- Renders `ccoding` nodes with UML-style visuals (class boxes, method cards, edge styles)
- Ghost node UX: dashed rendering, accept/reject controls, proposal rationale display
- Structured markdown editing within nodes (fields, methods, docstrings)
- Canvas event hooks: emits filesystem events or signals when nodes/edges change
- Detects and avoids clashing with Advanced Canvas (namespace isolation, patch chaining)
- Package group rendering with module path labels

Does not own: Sync logic, code generation, or agent cooperation. It is a visual tool.

### 5.3 The Extended Obsidian CLI

**Owns:** Programmatic canvas manipulation and the bidirectional sync engine.

- **Canvas operations:** create/read/update/delete nodes and edges in `.canvas` files via CLI commands
- **Sync engine:** watches `.canvas` and `.py` files, applies sync mapping rules, detects conflicts
- **Code parsing:** extracts classes, methods, fields, type hints, docstrings from `.py` files to generate/update canvas nodes
- **Canvas parsing:** reads structured markdown from canvas nodes to generate/update `.py` code
- **Ghost node management:** CLI commands to propose nodes (`--status proposed`), accept, reject
- **Import:** parse existing Python codebase into canvas representation

Example CLI commands:

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

Does not own: Visual rendering or agent workflow orchestration.

### 5.4 The Claude Code Skill

**Owns:** Teaching the agent to cooperate within the CooperativeCoding paradigm.

- Knows the full spec: node types, edge semantics, docstring format, sync rules
- Knows how to call the extended CLI for all canvas and sync operations
- **Design mode:** reads canvas, analyzes architecture, proposes improvements as ghost nodes with rationales
- **Implement mode:** reads accepted canvas nodes, generates Python code following the docstring contract
- **Review mode:** compares canvas design to actual code, flags drift or violations
- **Conversation patterns:** how to ask the human for design decisions, how to present proposals, when to suggest splitting a class vs. keeping it

Does not own: The CLI itself or the plugin UX.

### 5.5 Subsystem Dependencies

```
Spec (data model contract)
 ├── Plugin (reads spec to render correctly)
 ├── CLI (reads spec to sync correctly)
 └── Skill (reads spec to cooperate correctly)

Build order:
  1. Spec        (defines everything, no dependencies)
  2. CLI         (needs spec, enables programmatic canvas work)
  3. Plugin      (needs spec, can develop in parallel with CLI)
  4. Skill       (needs spec + CLI to be functional)
```

The CLI and Plugin can be developed in parallel after the spec is done — they share the data model but don't depend on each other. The Skill comes last because it needs to call the CLI.

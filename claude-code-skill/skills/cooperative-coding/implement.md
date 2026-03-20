---
name: cooperative-coding:implement
description: "Use when generating code from accepted CooperativeCoding canvas nodes — skeleton or full implementation"
---

Before starting, ensure the prerequisites from the `cooperative-coding` skill have been completed (CLI check, canvas resolution).

# Implement Mode

Generate source code from accepted canvas nodes.

## Skeleton Generation (Default)

`/ccoding implement` generates skeletons for all accepted nodes.

For each accepted class node:

1. Run `ccoding show <qualifiedName>` to get structured markdown
2. Generate a Python source file at the path in the node's `source` field (or derive from `qualifiedName`)
3. Include in the generated file:
   - Class declaration with correct stereotype (`Protocol`, `ABC`, `@dataclass`, `Enum`, or plain `class`)
   - Full docstring with CooperativeCoding sections (Responsibility, Collaborators, Pseudo Code, Constraints)
   - Type-annotated fields
   - Method stubs with signatures and docstrings
4. Method bodies:
   - `...` for protocol methods
   - `raise NotImplementedError` for abstract methods
   - `pass` for concrete stubs
5. Run `ccoding sync` to update sync state

## Full Implementation (On Request)

When the user asks to implement a specific method or class:

1. Read the pseudo code from the canvas documentation
2. Write working logic guided by the pseudo code
3. Import and use collaborators listed in the docstring
4. Run `ccoding sync` after writing

## Scoping

- `/ccoding implement` — all accepted nodes
- `/ccoding implement ClassName` — single class
- "implement the parsing package" — all classes in a package
- "implement the parse method" — single method (full implementation)

## Conflict Handling

Before writing any file, run `ccoding status`. If the file has unsynchronized changes:
- Tell the user: "<file> has unsynchronized changes. Overwrite, merge, or skip?"
- Wait for their choice

## Post-Implementation Review

After implementing multiple classes, use the `ccoding-review` agent to check alignment between the canvas and the generated code. This catches drift early before it accumulates.

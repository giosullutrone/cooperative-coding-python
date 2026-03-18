# CooperativeCoding — Python Language Binding

*Concrete mapping of the CooperativeCoding open specification to Python idioms.*

**Parent spec:** [CooperativeCoding Open Specification](2026-03-18-cooperative-coding-design.md)

---

## 1. Overview

This document defines how the language-agnostic CooperativeCoding standard maps to Python. It covers stereotype mapping, documentation format, sync rules, and type notation — everything a tool implementation needs to support CooperativeCoding for Python codebases.

---

## 2. Stereotype Mapping

The `ccoding.stereotype` field maps to Python constructs:

| `ccoding.stereotype` | Python Construct | Import Required |
|---|---|---|
| `class` | `class Foo:` | — |
| `protocol` | `class Foo(Protocol):` | `from typing import Protocol` |
| `abstract` | `class Foo(ABC):` | `from abc import ABC, abstractmethod` |
| `dataclass` | `@dataclass class Foo:` | `from dataclasses import dataclass` |
| `enum` | `class Foo(Enum):` | `from enum import Enum` |

The `ccoding.language` field must be `"python"` for all nodes using this binding.

---

## 3. Documentation Format

Python uses [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) extended with CooperativeCoding-specific sections. This format is compatible with standard Python documentation tools (Sphinx, pdoc, mkdocstrings) while carrying the additional design information that the canvas displays.

### 3.1 Class Docstring

Maps to the class node's structured markdown on canvas.

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

**Section mapping:**

| Docstring Section | Canvas Node Section | Purpose |
|---|---|---|
| First line | `## ClassName` heading + blockquote | One-line summary |
| `Responsibility:` | `> Responsible for...` blockquote | What this class owns |
| `Collaborators:` | Inferred from edges | Other classes this one works with |
| `Attributes:` | `### Fields` | Class fields with descriptions |

### 3.2 Method Docstring

Maps to the method detail node's structured markdown on canvas.

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

**Section mapping:**

| Docstring Section | Canvas Node Section | Purpose |
|---|---|---|
| First line | `## ClassName.method` heading | One-line summary |
| `Responsibility:` | `### Responsibility` | What this method is responsible for |
| `Pseudo Code:` | `### Pseudo Code` | Step-by-step algorithm description |
| `Args:` | `### Signature` IN fields | Input parameters |
| `Returns:` | `### Signature` OUT fields | Return value |
| `Raises:` | `### Signature` RAISES fields | Exceptions |

### 3.3 Custom Sections

Three sections are added to the standard Google docstring style:

- **`Responsibility:`** — appears on both class and method docstrings. Describes what this element *owns* in the system. This is the most important section for design — it defines the boundaries.
- **`Pseudo Code:`** — appears on method docstrings only. Numbered step-by-step description of the algorithm. Deliberately not real code — it describes *what* happens, not *how* in language-specific terms.
- **`Collaborators:`** — appears on class docstrings only. Lists other classes this one works with and why. On the canvas, this information is primarily conveyed through edges, but the docstring captures it in prose for readability in code.

These sections are designed to be safely ignored by standard Python documentation tools that don't recognize them — they simply appear as additional text in the rendered docstring.

---

## 4. Sync Mapping

Concrete rules for bidirectional sync between canvas elements and Python code:

| Canvas Element | Python Code |
|---|---|
| Class node `text` | Class definition + class docstring |
| Method node `text` | Method signature + method docstring |
| Class `### Fields` | Class attributes with type annotations |
| Method `### Pseudo Code` | Docstring `Pseudo Code:` section |
| Method `### Signature` IN | Method parameters with type hints + `Args:` docstring section |
| Method `### Signature` OUT | Return type hint + `Returns:` docstring section |
| Method `### Signature` RAISES | `Raises:` docstring section |
| Package group | Python package directory with `__init__.py` |
| Edge `inherits` | `class Foo(Bar):` |
| Edge `implements` | `class Foo(SomeProtocol):` (Protocol inheritance) |
| Edge `composes` | Class attribute with the composed type annotation. Edge label carries the field name (e.g., `"plugins"` → `self.plugins: list[ParserPlugin]`) |
| Edge `depends` | `import` / `from ... import` statement |
| `ccoding.stereotype: protocol` | `typing.Protocol` base class |
| `ccoding.stereotype: dataclass` | `@dataclasses.dataclass` decorator |
| `ccoding.stereotype: abstract` | `abc.ABC` base class + `@abstractmethod` on abstract methods |
| `ccoding.stereotype: enum` | `enum.Enum` base class |

### 4.1 Code Generation Rules

When generating Python code from an accepted canvas node:

- **File placement**: `ccoding.source` determines the file path. If not set, derive from `ccoding.qualifiedName` relative to a configurable project source root (e.g., with source root `src/`, `parsers.document.DocumentParser` → `src/parsers/document.py`)
- **Import management**: automatically add required imports based on stereotypes, edges, and type annotations
- **Class skeleton**: generate class definition, docstring, and attribute stubs with type annotations. Method bodies are initially `...` (ellipsis) or `raise NotImplementedError`
- **Method skeleton**: generate method signature with full type hints, docstring with all sections, and `...` body

### 4.2 Code Parsing Rules

When importing existing Python code to canvas:

- **Class detection**: any `class` statement. Stereotype inferred from base classes (`Protocol` → `protocol`, `ABC` → `abstract`, `Enum` → `enum`) and decorators (`@dataclass` → `dataclass`)
- **Method detection**: any `def` inside a class body. Skip dunder methods except those with architectural intent: `__init__`, `__post_init__` (dataclasses), `__enter__`/`__exit__` (context managers), `__call__`, `__iter__`/`__next__`
- **Field detection**: class-level annotated assignments and `__init__` assignments with type annotations
- **Relationship detection**: base classes → `inherits`/`implements` edges. Type annotations referencing other project classes → `composes`/`depends` edges. Import statements → `depends` edges
- **Documentation extraction**: parse existing Google-style docstrings. Map standard sections (`Args:`, `Returns:`, `Raises:`, `Attributes:`) and custom sections (`Responsibility:`, `Pseudo Code:`, `Collaborators:`) to canvas node content

---

## 5. Type Notation

Canvas structured markdown uses Python type hint syntax directly in `### Fields` and `### Signature` sections:

- **Primitives**: `str`, `int`, `float`, `bool`, `bytes`, `None`
- **Collections**: `list[T]`, `dict[K, V]`, `tuple[T, ...]`, `set[T]`
- **Optional**: `T | None` (preferred) or `Optional[T]`
- **Union**: `T | U` (preferred) or `Union[T, U]`
- **Callable**: `Callable[[ArgTypes], ReturnType]`
- **Custom types**: class name as-is (e.g., `ParserConfig`, `AST`)
- **Generics**: `T` for type variables, `list[T]` for parameterized types

Types on the canvas should match the exact syntax used in the Python source code to minimize sync friction.

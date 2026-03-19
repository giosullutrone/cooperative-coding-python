"""Bidirectional mapper between canvas language-neutral types and Python type annotations.

Canvas generic syntax uses angle brackets: ``List<T>``, ``Map<K, V>``
Python generic syntax uses square brackets: ``list[T]``, ``dict[K, V]``

Special cases
-------------
- ``Optional<T>``  ↔  ``T | None``
- ``Union<T, U>``  ↔  ``T | U``
- ``Callable<[Args], Return>``  ↔  ``Callable[[Args], Return]``
- ``Void``  ↔  ``None``
- Custom types (e.g. ``ParserConfig``, ``AST``) pass through unchanged in both directions.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Primitive lookup tables
# ---------------------------------------------------------------------------

_CANVAS_TO_PYTHON_PRIMITIVES: dict[str, str] = {
    "String": "str",
    "Integer": "int",
    "Boolean": "bool",
    "Float": "float",
    "Void": "None",
}

_PYTHON_TO_CANVAS_PRIMITIVES: dict[str, str] = {v: k for k, v in _CANVAS_TO_PYTHON_PRIMITIVES.items()}

# Canvas generic container names → Python equivalents (not for Optional/Union/Callable)
_CANVAS_GENERIC_TO_PYTHON: dict[str, str] = {
    "List": "list",
    "Map": "dict",
    "Set": "set",
    "Tuple": "tuple",
}

_PYTHON_GENERIC_TO_CANVAS: dict[str, str] = {v: k for k, v in _CANVAS_GENERIC_TO_PYTHON.items()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_top_level_args(args: str, delimiter: str = ",") -> list[str]:
    """Split *args* on *delimiter* only at the top nesting level.

    Respects both angle brackets ``<>`` and square brackets ``[]``.

    Examples::

        >>> _split_top_level_args("String, Integer")
        ['String', ' Integer']
        >>> _split_top_level_args("Map<String, Integer>, Boolean")
        ['Map<String, Integer>', ' Boolean']
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    i = 0
    while i < len(args):
        ch = args[i]
        if ch in ("<", "["):
            depth += 1
            current.append(ch)
        elif ch in (">", "]"):
            depth -= 1
            current.append(ch)
        elif ch == delimiter[0] and depth == 0:
            # Check full delimiter match (single-char delimiters used here)
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    if current or parts:
        parts.append("".join(current))
    return parts


def _parse_canvas_generic(type_str: str) -> tuple[str, str] | None:
    """Return ``(name, inner_args)`` if *type_str* is a canvas generic, else ``None``."""
    m = re.fullmatch(r"([A-Za-z_]\w*)<(.+)>", type_str, re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return None


def _parse_python_generic(type_str: str) -> tuple[str, str] | None:
    """Return ``(name, inner_args)`` if *type_str* is a Python generic, else ``None``."""
    m = re.fullmatch(r"([A-Za-z_]\w*)\[(.+)\]", type_str, re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return None


# ---------------------------------------------------------------------------
# canvas_to_python
# ---------------------------------------------------------------------------


def canvas_to_python(canvas_type: str) -> str:
    """Translate a canvas type expression to its Python annotation equivalent.

    If the input is already a valid Python type (e.g. ``str``, ``list[str]``)
    it is returned unchanged.
    """
    canvas_type = canvas_type.strip()

    # --- Primitives (canvas side) ---
    if canvas_type in _CANVAS_TO_PYTHON_PRIMITIVES:
        return _CANVAS_TO_PYTHON_PRIMITIVES[canvas_type]

    # --- Already a Python primitive or None literal ---
    if canvas_type in _PYTHON_TO_CANVAS_PRIMITIVES:
        return canvas_type  # already python

    # --- Try to parse as a canvas generic  Name<...> ---
    parsed = _parse_canvas_generic(canvas_type)
    if parsed is not None:
        name, inner = parsed

        # Optional<T> → T | None
        if name == "Optional":
            inner_py = canvas_to_python(inner.strip())
            return f"{inner_py} | None"

        # Union<T, U, ...> → T | U | ...
        if name == "Union":
            parts = _split_top_level_args(inner)
            translated = [canvas_to_python(p.strip()) for p in parts]
            return " | ".join(translated)

        # Callable<[Args], Return>
        if name == "Callable":
            return _canvas_callable_to_python(inner)

        # Standard containers: List, Map, Set, Tuple
        if name in _CANVAS_GENERIC_TO_PYTHON:
            py_name = _CANVAS_GENERIC_TO_PYTHON[name]
            parts = _split_top_level_args(inner)
            translated = [canvas_to_python(p.strip()) for p in parts]
            return f"{py_name}[{', '.join(translated)}]"

        # Unknown generic — pass through as-is (custom generic canvas type)
        return canvas_type

    # --- Try to parse as a Python generic name[...] (already Python) ---
    parsed_py = _parse_python_generic(canvas_type)
    if parsed_py is not None:
        # It's already a Python generic — return as-is
        return canvas_type

    # --- Handle Python union syntax already present (str | None) ---
    if " | " in canvas_type:
        return canvas_type

    # --- Custom / unknown type: pass through ---
    return canvas_type


def _canvas_callable_to_python(inner: str) -> str:
    """Translate the inner part of ``Callable<...>`` to Python syntax."""
    # inner looks like: [String, Integer], Boolean
    # We need to find the closing ] that matches the opening [
    if not inner.startswith("["):
        # Malformed — best-effort passthrough
        parts = _split_top_level_args(inner)
        translated = [canvas_to_python(p.strip()) for p in parts]
        return f"Callable[[{', '.join(translated[:-1])}], {translated[-1]}]"

    # Find the matching ]
    depth = 0
    close_idx = -1
    for i, ch in enumerate(inner):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                close_idx = i
                break

    args_str = inner[1:close_idx]  # strip outer [ ]
    rest = inner[close_idx + 1 :].strip()  # should start with ", Return"
    if rest.startswith(","):
        rest = rest[1:].strip()
    return_type_py = canvas_to_python(rest)

    arg_parts = _split_top_level_args(args_str) if args_str.strip() else []
    translated_args = [canvas_to_python(p.strip()) for p in arg_parts]
    return f"Callable[[{', '.join(translated_args)}], {return_type_py}]"


# ---------------------------------------------------------------------------
# python_to_canvas
# ---------------------------------------------------------------------------


def python_to_canvas(python_type: str) -> str:
    """Translate a Python type annotation to its canvas equivalent.

    If the input is already a canvas type (e.g. ``String``, ``List<String>``)
    it is returned unchanged.
    """
    python_type = python_type.strip()

    # --- Python primitives ---
    if python_type in _PYTHON_TO_CANVAS_PRIMITIVES:
        return _PYTHON_TO_CANVAS_PRIMITIVES[python_type]

    # --- Already a canvas primitive ---
    if python_type in _CANVAS_TO_PYTHON_PRIMITIVES:
        return python_type

    # --- Union syntax: T | U  (must check before generic parsing) ---
    if " | " in python_type and not _parse_python_generic(python_type):
        return _python_union_to_canvas(python_type)

    # --- Python generic name[...] ---
    parsed = _parse_python_generic(python_type)
    if parsed is not None:
        name, inner = parsed

        # Callable[[Args], Return]
        if name == "Callable":
            return _python_callable_to_canvas(inner)

        if name in _PYTHON_GENERIC_TO_CANVAS:
            canvas_name = _PYTHON_GENERIC_TO_CANVAS[name]
            parts = _split_top_level_args(inner)
            translated = [python_to_canvas(p.strip()) for p in parts]
            return f"{canvas_name}<{', '.join(translated)}>"

        # Unknown Python generic — pass through
        return python_type

    # --- Canvas generic Name<...> (already canvas) ---
    parsed_canvas = _parse_canvas_generic(python_type)
    if parsed_canvas is not None:
        return python_type

    # --- Custom / unknown type: pass through ---
    return python_type


def _python_union_to_canvas(union_str: str) -> str:
    """Translate ``T | U | ...`` (Python union) to canvas syntax."""
    # Split on top-level " | "
    parts = _split_top_level_union(union_str)
    if len(parts) == 2 and parts[1].strip() == "None":
        # str | None → Optional<T>
        inner_canvas = python_to_canvas(parts[0].strip())
        return f"Optional<{inner_canvas}>"
    # General union
    translated = [python_to_canvas(p.strip()) for p in parts]
    return f"Union<{', '.join(translated)}>"


def _split_top_level_union(union_str: str) -> list[str]:
    """Split a union string on ' | ' only at the top nesting level."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    i = 0
    while i < len(union_str):
        ch = union_str[i]
        if ch in ("<", "["):
            depth += 1
            current.append(ch)
        elif ch in (">", "]"):
            depth -= 1
            current.append(ch)
        elif ch == "|" and depth == 0:
            # Expect surrounding spaces: ' | '
            if i > 0 and union_str[i - 1] == " " and i + 1 < len(union_str) and union_str[i + 1] == " ":
                # Remove trailing space from current
                if current and current[-1] == " ":
                    current.pop()
                parts.append("".join(current))
                current = []
                i += 2  # skip the space after |
                continue
            else:
                current.append(ch)
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts


def _python_callable_to_canvas(inner: str) -> str:
    """Translate the inner part of ``Callable[...]`` to canvas syntax."""
    # inner looks like: [str, int], bool
    if not inner.startswith("["):
        # Malformed — best-effort
        parts = _split_top_level_args(inner)
        translated = [python_to_canvas(p.strip()) for p in parts]
        return f"Callable<[{', '.join(translated[:-1])}], {translated[-1]}>"

    # Find matching ]
    depth = 0
    close_idx = -1
    for i, ch in enumerate(inner):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                close_idx = i
                break

    args_str = inner[1:close_idx]
    rest = inner[close_idx + 1 :].strip()
    if rest.startswith(","):
        rest = rest[1:].strip()
    return_type_canvas = python_to_canvas(rest)

    arg_parts = _split_top_level_args(args_str) if args_str.strip() else []
    translated_args = [python_to_canvas(p.strip()) for p in arg_parts]
    return f"Callable<[{', '.join(translated_args)}], {return_type_canvas}>"

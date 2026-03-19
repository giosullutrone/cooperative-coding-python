"""Generate Python source files from canvas node content.

Translates ClassContent and MethodContent objects (produced by the canvas
markdown parser) into valid, importable Python source text.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

from ccoding.canvas.markdown import ClassContent, MethodContent, MethodEntry, SignatureEntry
from ccoding.code.docstring import render_docstring
from ccoding.code.types import canvas_to_python


@dataclass
class EdgeInfo:
    """Edge data passed from the sync engine to the code generator."""

    relation: str       # inherits, implements, composes, depends
    target_name: str    # Simple class name (e.g., "BaseParser")
    target_qname: str   # Fully qualified name (e.g., "parsers.base.BaseParser")
    label: str | None   # Edge label (used for composes field name)


def _import_from_qname(qname: str) -> str:
    """Derive an import statement from a fully-qualified name.

    Example: ``"parsers.base.BaseParser"`` → ``"from parsers.base import BaseParser"``
    """
    dot_idx = qname.rfind(".")
    if dot_idx == -1:
        # Top-level name — no module prefix, nothing to import
        return f"import {qname}"
    module = qname[:dot_idx]
    name = qname[dot_idx + 1:]
    return f"from {module} import {name}"


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


def _field_name_from_label(label: str | None, target_name: str) -> str:
    """Extract a field name from an edge label per spec Data Model §7.

    - If *label* contains `` \u2014 `` (space + em-dash + space), the
      substring before the first occurrence is the field name.
    - If *label* has no such separator, the entire label is the field name.
    - If *label* is ``None``, derive the field name from *target_name* (snake_cased).
    """
    if label is None:
        return _camel_to_snake(target_name)
    separator = " \u2014 "
    if separator in label:
        return label.split(separator, 1)[0]
    return label


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Matches a signature fragment like "(source: str, x: int) -> AST"
_SIG_RE = re.compile(
    r"^\s*\((?P<params>[^)]*)\)\s*(?:->\s*(?P<ret>.+))?\s*$"
)


def _parse_method_signature(sig: str) -> tuple[list[tuple[str, str]], str]:
    """Parse a MethodEntry.signature string into (params, return_type).

    *sig* has the format ``(param: type, ...) -> return_type`` as it appears
    in a canvas class node.  Returns a list of ``(name, type)`` pairs and the
    return-type string (empty string if absent).
    """
    m = _SIG_RE.match(sig)
    if not m:
        return [], ""

    params_raw = m.group("params").strip()
    ret = (m.group("ret") or "").strip()

    params: list[tuple[str, str]] = []
    if params_raw:
        for part in params_raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                name, _, type_ = part.partition(":")
                params.append((name.strip(), type_.strip()))
            else:
                params.append((part, ""))

    return params, ret


def _build_def_line(method_name: str, params: list[tuple[str, str]], ret: str) -> str:
    """Build a ``def`` line from components (no trailing newline, no body)."""
    param_parts = ["self"]
    for name, type_ in params:
        if type_:
            param_parts.append(f"{name}: {type_}")
        else:
            param_parts.append(name)
    param_str = ", ".join(param_parts)

    if ret:
        return f"def {method_name}({param_str}) -> {ret}:"
    return f"def {method_name}({param_str}):"


def _render_method_stub(
    entry: MethodEntry,
    body_lines: list[str],
    indent: int = 4,
    decorators: list[str] | None = None,
) -> list[str]:
    """Return indented lines for a method stub."""
    pad = " " * indent
    lines: list[str] = []

    for dec in decorators or []:
        lines.append(pad + dec)

    params, ret = _parse_method_signature(entry.signature)
    params = [(name, canvas_to_python(type_) if type_ else "") for name, type_ in params]
    ret = canvas_to_python(ret) if ret else ret
    def_line = _build_def_line(entry.name, params, ret)
    lines.append(pad + def_line)

    for body_line in body_lines:
        lines.append(pad + pad + body_line)

    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_method_bodies(source_path: Path, class_name: str) -> dict[str, list[str]]:
    """Extract non-stub method body lines from an existing source file.

    Returns a dict mapping method name to a list of body lines (dedented
    relative to the method body indentation). Only methods with real
    implementations (not just ``...``, ``pass``, or ``raise NotImplementedError``)
    are included.
    """
    import ast as _ast
    text = source_path.read_text()
    try:
        tree = _ast.parse(text)
    except SyntaxError:
        return {}
    lines = text.splitlines()

    bodies: dict[str, list[str]] = {}
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            if not isinstance(item, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                continue

            # Get body statements, skipping docstring
            body_stmts = item.body
            if (
                body_stmts
                and isinstance(body_stmts[0], _ast.Expr)
                and isinstance(body_stmts[0].value, _ast.Constant)
                and isinstance(body_stmts[0].value.value, str)
            ):
                body_stmts = body_stmts[1:]

            if not body_stmts:
                continue

            # Check if body is just a stub
            if len(body_stmts) == 1:
                stmt = body_stmts[0]
                if isinstance(stmt, _ast.Expr) and isinstance(
                    getattr(stmt, "value", None), _ast.Constant
                ) and getattr(stmt.value, "value", None) is ...:
                    continue
                if isinstance(stmt, _ast.Pass):
                    continue
                if isinstance(stmt, _ast.Raise):
                    exc = getattr(stmt, "exc", None)
                    if (
                        exc
                        and isinstance(exc, _ast.Call)
                        and isinstance(exc.func, _ast.Name)
                        and exc.func.id == "NotImplementedError"
                    ):
                        continue

            # Extract source lines for the real body
            start_line = body_stmts[0].lineno - 1
            end_line = body_stmts[-1].end_lineno
            body_source = lines[start_line:end_line]

            # Dedent: find minimum indentation and strip it
            non_empty = [l for l in body_source if l.strip()]
            if non_empty:
                min_indent = min(len(l) - len(l.lstrip()) for l in non_empty)
                body_source = [l[min_indent:] if len(l) > min_indent else l.lstrip() for l in body_source]

            bodies[item.name] = body_source

    return bodies


def generate_class(
    content: ClassContent,
    language: str = "python",
    edges: list[EdgeInfo] | None = None,
    preserve_bodies: dict[str, list[str]] | None = None,
) -> str:
    """Generate a complete Python source file from a ClassContent node.

    Args:
        content: Parsed class canvas node.
        language: Target language (only ``"python"`` is supported).
        edges: Optional list of :class:`EdgeInfo` objects describing
            relationships to other classes.  Each edge may add import
            statements, base classes, or field declarations to the
            generated source.

    Returns:
        A string containing a complete, valid Python source file.
    """
    if language != "python":
        raise ValueError(f"Unsupported language: {language!r}")

    stereotype = (content.stereotype or "").lower()

    # --- imports -----------------------------------------------------------
    import_lines: list[str] = []
    if stereotype == "protocol":
        import_lines.append("from typing import Protocol")
    elif stereotype == "dataclass":
        import_lines.append("from dataclasses import dataclass")
    elif stereotype == "abstract":
        import_lines.append("from abc import ABC, abstractmethod")
    elif stereotype == "enum":
        import_lines.append("from enum import Enum")

    # --- class header ------------------------------------------------------
    base_map = {
        "protocol": "Protocol",
        "dataclass": "",
        "abstract": "ABC",
        "enum": "Enum",
    }
    stereotype_base = base_map.get(stereotype, "")

    # Collect edge-derived bases and fields
    edge_bases: list[str] = []
    edge_field_lines: list[str] = []

    for edge in edges or []:
        import_stmt = _import_from_qname(edge.target_qname)
        if import_stmt not in import_lines:
            import_lines.append(import_stmt)

        if edge.relation in ("inherits", "implements"):
            if edge.target_name not in edge_bases:
                edge_bases.append(edge.target_name)
        elif edge.relation == "composes":
            field_name = _field_name_from_label(edge.label, edge.target_name)
            edge_field_lines.append(f"    {field_name}: {canvas_to_python(edge.target_name)}")
        # "depends" → import only (already added above)

    # Build the full bases list: stereotype base first, then edge bases
    all_bases = [b for b in [stereotype_base] + edge_bases if b]

    class_decorator_lines: list[str] = []
    if stereotype == "dataclass":
        class_decorator_lines.append("@dataclass")

    if all_bases:
        class_header = f"class {content.name}({', '.join(all_bases)}):"
    else:
        class_header = f"class {content.name}:"

    # --- class docstring ---------------------------------------------------
    docstring_sections: dict[str, str] = {
        "summary": content.responsibility,
    }
    if content.responsibility:
        docstring_sections["responsibility"] = content.responsibility

    # Build Collaborators section from edges (spec Python binding §3.1)
    if edges:
        collab_parts: list[str] = []
        for edge in edges:
            if edge.relation == "inherits":
                collab_parts.append(f"{edge.target_name}: Base class.")
            elif edge.relation == "implements":
                collab_parts.append(f"{edge.target_name}: Implemented protocol.")
            elif edge.relation == "composes":
                field_name = _field_name_from_label(edge.label, edge.target_name)
                collab_parts.append(f"{edge.target_name}: Composed as {field_name}.")
            elif edge.relation == "depends":
                collab_parts.append(f"{edge.target_name}: Dependency.")
        if collab_parts:
            docstring_sections["collaborators"] = "\n".join(collab_parts)

    docstring_body = render_docstring(docstring_sections, indent=4)
    docstring_lines = ['    """' + docstring_body + '    """']

    # --- fields ------------------------------------------------------------
    # Content fields first, then edge-derived composition fields
    field_lines: list[str] = []
    for f in content.fields:
        field_lines.append(f"    {f.name}: {canvas_to_python(f.type)}")
    field_lines.extend(edge_field_lines)

    # --- methods -----------------------------------------------------------
    method_lines: list[str] = []
    if stereotype == "protocol":
        body = ["..."]
    elif stereotype == "abstract":
        body = ["raise NotImplementedError"]
    else:
        body = ["..."]

    for i, m in enumerate(content.methods):
        if i > 0 or field_lines:
            method_lines.append("")

        extra_decorators: list[str] = []
        if stereotype == "abstract":
            extra_decorators = ["@abstractmethod"]

        # Use preserved body if available
        if preserve_bodies and m.name in preserve_bodies:
            method_body = preserve_bodies[m.name]
        else:
            method_body = body  # the default stub

        stub = _render_method_stub(m, method_body, indent=4, decorators=extra_decorators)
        method_lines.extend(stub)

    # --- class body --------------------------------------------------------
    # If there are no fields and no methods, add a pass
    has_body = bool(field_lines) or bool(method_lines)

    # --- assemble ----------------------------------------------------------
    parts: list[str] = []

    if import_lines:
        parts.extend(import_lines)
        parts.append("")
        parts.append("")

    parts.extend(class_decorator_lines)
    parts.append(class_header)
    parts.extend(docstring_lines)

    if field_lines:
        parts.append("")
        parts.extend(field_lines)

    if method_lines:
        parts.extend(method_lines)

    if not has_body:
        parts.append("    pass")

    parts.append("")  # trailing newline

    return "\n".join(parts)


def generate_method(content: MethodContent) -> str:
    """Generate a standalone method definition from a MethodContent node.

    The output is a ``def`` block (without class context) suitable for
    inspection or insertion into a class body.

    Args:
        content: Parsed method canvas node.

    Returns:
        A string containing a Python method definition.
    """
    # Parse ClassName.method_name format
    raw_name = content.name
    if "." in raw_name:
        method_name = raw_name.rsplit(".", 1)[-1]
    else:
        method_name = raw_name

    # --- build def line ----------------------------------------------------
    param_parts = ["self"]
    for entry in content.signature_in:
        if entry.type:
            param_parts.append(f"{entry.name}: {canvas_to_python(entry.type)}")
        else:
            param_parts.append(entry.name)
    param_str = ", ".join(param_parts)

    ret_type = ""
    if content.signature_out and content.signature_out.type:
        ret_type = canvas_to_python(content.signature_out.type)

    if ret_type:
        def_line = f"def {method_name}({param_str}) -> {ret_type}:"
    else:
        def_line = f"def {method_name}({param_str}):"

    # --- build docstring ---------------------------------------------------
    docstring_sections: dict[str, str] = {
        "summary": content.responsibility,
    }

    if content.responsibility:
        docstring_sections["responsibility"] = content.responsibility

    if content.pseudo_code:
        docstring_sections["pseudo code"] = content.pseudo_code

    if content.signature_in:
        args_lines = []
        for entry in content.signature_in:
            if entry.description:
                args_lines.append(f"{entry.name}: {entry.description}")
            else:
                args_lines.append(f"{entry.name}: {entry.type}")
        docstring_sections["args"] = "\n".join(args_lines)

    if content.signature_out and content.signature_out.type:
        desc = content.signature_out.description or content.signature_out.type
        docstring_sections["returns"] = desc

    if content.raises:
        raises_lines = []
        for entry in content.raises:
            if entry.description:
                raises_lines.append(f"{entry.type}: {entry.description}")
            else:
                raises_lines.append(entry.type)
        docstring_sections["raises"] = "\n".join(raises_lines)

    docstring_body = render_docstring(docstring_sections, indent=4)
    docstring = '    """' + docstring_body + '    """'

    # --- assemble ----------------------------------------------------------
    lines = [def_line, docstring, "    ..."]
    return "\n".join(lines)


def deprecate_class(source_path: Path, class_name: str) -> None:
    """Add a deprecation marker to a class in an existing source file.

    Only handles class-kind elements. Non-class elements are silently skipped.
    """
    import ast
    text = source_path.read_text()
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            # Add import at top of file if not present
            if "import warnings" not in text:
                lines.insert(0, "import warnings\n")
                insert_line = node.lineno  # +1 for inserted import, -1 for 0-index = same
            else:
                insert_line = node.lineno - 1

            deprecation_comment = (
                f"# DEPRECATED: {class_name} was removed from the design canvas.\n"
            )
            lines.insert(insert_line, deprecation_comment)
            source_path.write_text("".join(lines))
            return

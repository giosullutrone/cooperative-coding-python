"""Generate Python source files from canvas node content.

Translates ClassContent and MethodContent objects (produced by the canvas
markdown parser) into valid, importable Python source text.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from ccoding.canvas.markdown import ClassContent, MethodContent, MethodEntry, SignatureEntry
from ccoding.code.docstring import render_docstring


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
    def_line = _build_def_line(entry.name, params, ret)
    lines.append(pad + def_line)

    for body_line in body_lines:
        lines.append(pad + pad + body_line)

    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_class(content: ClassContent, language: str = "python") -> str:
    """Generate a complete Python source file from a ClassContent node.

    Args:
        content: Parsed class canvas node.
        language: Target language (only ``"python"`` is supported).

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
    base = base_map.get(stereotype, "")

    class_decorator_lines: list[str] = []
    if stereotype == "dataclass":
        class_decorator_lines.append("@dataclass")

    if base:
        class_header = f"class {content.name}({base}):"
    else:
        class_header = f"class {content.name}:"

    # --- class docstring ---------------------------------------------------
    docstring_sections: dict[str, str] = {
        "summary": content.responsibility,
    }
    if content.responsibility:
        docstring_sections["responsibility"] = content.responsibility

    docstring_body = render_docstring(docstring_sections, indent=4)
    docstring_lines = ['    """' + docstring_body + '    """']

    # --- fields ------------------------------------------------------------
    field_lines: list[str] = []
    for f in content.fields:
        field_lines.append(f"    {f.name}: {f.type}")

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

        stub = _render_method_stub(m, body, indent=4, decorators=extra_decorators)
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
            param_parts.append(f"{entry.name}: {entry.type}")
        else:
            param_parts.append(entry.name)
    param_str = ", ".join(param_parts)

    ret_type = ""
    if content.signature_out and content.signature_out.type:
        ret_type = content.signature_out.type

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

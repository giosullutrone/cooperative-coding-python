"""Code parser protocol and Python AST implementation."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Union

from ccoding.code.docstring import parse_docstring

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ParameterInfo:
    """Represents a single function/method parameter."""

    name: str
    type_annotation: str | None = None
    default: str | None = None


@dataclass
class FieldElement:
    """Represents a class-level field (attribute annotation)."""

    name: str
    type_annotation: str | None = None
    default_value: str | None = None
    comment_sections: dict[str, str] = field(default_factory=dict)


@dataclass
class MethodElement:
    """Represents a method inside a class."""

    name: str
    parameters: list[ParameterInfo]
    return_type: str | None = None
    docstring_sections: dict[str, str] = field(default_factory=dict)
    decorators: list[str] = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class ImportElement:
    """Represents an import statement."""

    module: str
    names: list[str]


@dataclass
class ClassElement:
    """Represents a class definition."""

    name: str
    stereotype: str
    base_classes: list[str]
    docstring_sections: dict[str, str]
    fields: list[FieldElement]
    methods: list[MethodElement]
    source_path: str | None = None
    line_number: int = 0


# Union type alias
CodeElement = Union[ClassElement, MethodElement, FieldElement, ImportElement]

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

# Dunders that are architecturally meaningful and should NOT be skipped.
_KEEP_DUNDERS = frozenset(
    {"__init__", "__post_init__", "__enter__", "__exit__", "__call__", "__iter__", "__next__"}
)


class CodeParser(Protocol):
    def parse_file(self, path: Path) -> list[CodeElement]: ...
    def parse_directory(self, path: Path, recursive: bool = True) -> list[CodeElement]: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QUOTE_RE = re.compile(r"^['\"](.+)['\"]$")


def _strip_quotes(s: str) -> str:
    """Remove surrounding single or double quotes from a string annotation."""
    m = _QUOTE_RE.match(s)
    return m.group(1) if m else s


def _annotation_to_str(node: ast.expr) -> str:
    """Convert an annotation AST node to a string, stripping quotes."""
    raw = ast.unparse(node)
    return _strip_quotes(raw)


def _decorator_name(dec: ast.expr) -> str:
    """Return a simple string representation of a decorator node."""
    return ast.unparse(dec)


def _infer_stereotype(
    node: ast.ClassDef,
    base_names: list[str],
    decorator_names: list[str],
) -> str:
    """Infer class stereotype from bases and decorators."""
    if "Protocol" in base_names:
        return "protocol"
    if "ABC" in base_names or "ABCMeta" in base_names:
        return "abstract"
    if any("Enum" in b for b in base_names):
        return "enum"
    if any("dataclass" in d for d in decorator_names):
        return "dataclass"
    return "class"


def _parse_method(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> MethodElement:
    """Parse a function/method node into a MethodElement."""
    # Parameters: skip self / cls
    params: list[ParameterInfo] = []
    args = func_node.args

    # Build defaults mapping: last N positional args have defaults
    # args.defaults covers the last len(defaults) of args.args (excl. posonlyargs for simplicity)
    all_args = args.posonlyargs + args.args
    n_defaults = len(args.defaults)
    n_args = len(all_args)

    for i, arg in enumerate(all_args):
        if arg.arg in ("self", "cls"):
            continue
        type_ann = _annotation_to_str(arg.annotation) if arg.annotation else None
        # Default: aligned from the right
        default_idx = i - (n_args - n_defaults)
        default_val: str | None = None
        if default_idx >= 0:
            default_val = ast.unparse(args.defaults[default_idx])
        params.append(ParameterInfo(name=arg.arg, type_annotation=type_ann, default=default_val))

    # kwonly args
    for j, kwarg in enumerate(args.kwonlyargs):
        if kwarg.arg in ("self", "cls"):
            continue
        type_ann = _annotation_to_str(kwarg.annotation) if kwarg.annotation else None
        kw_default = args.kw_defaults[j]
        default_val = ast.unparse(kw_default) if kw_default is not None else None
        params.append(ParameterInfo(name=kwarg.arg, type_annotation=type_ann, default=default_val))

    # Return type
    return_type: str | None = None
    if func_node.returns:
        return_type = _annotation_to_str(func_node.returns)

    # Docstring
    raw_doc = ast.get_docstring(func_node) or ""
    doc_sections = parse_docstring(raw_doc) if raw_doc else {}

    # Decorators
    decorators = [_decorator_name(d) for d in func_node.decorator_list]

    # Abstract detection
    is_abstract = any("abstractmethod" in d for d in decorators)

    return MethodElement(
        name=func_node.name,
        parameters=params,
        return_type=return_type,
        docstring_sections=doc_sections,
        decorators=decorators,
        is_abstract=is_abstract,
    )


_COMMENT_SECTION_RE = re.compile(r"^#\s*(?P<key>[A-Za-z][A-Za-z ]+?):\s*(?P<value>.*)$")


def _parse_field_comment_sections(source_lines: list[str], field_lineno: int) -> dict[str, str]:
    """Parse comment lines above a field declaration into section key/value pairs.

    Scans upward from *field_lineno* (1-based) collecting contiguous ``#`` comment
    lines.  Each line matching ``# Key: value`` starts or continues a section.
    Continuation lines (``# more text``) that don't match the pattern are appended
    to the most recent section.
    """
    # Collect contiguous comment lines above the field declaration
    comment_lines: list[str] = []
    idx = field_lineno - 2  # convert to 0-based, then step one line up
    while idx >= 0:
        stripped = source_lines[idx].strip()
        if stripped.startswith("#"):
            comment_lines.append(stripped)
            idx -= 1
        elif stripped == "":
            # Allow blank lines within the comment block
            idx -= 1
        else:
            break

    # Reverse so they are in top-to-bottom order
    comment_lines.reverse()

    sections: dict[str, str] = {}
    current_key: str | None = None
    current_parts: list[str] = []

    for line in comment_lines:
        # Strip the leading '# ' or '#'
        text = line.lstrip("#").strip()
        m = _COMMENT_SECTION_RE.match(line)
        if m:
            # Flush previous section
            if current_key is not None:
                sections[current_key] = " ".join(current_parts).strip()
            current_key = m.group("key").lower()
            value = m.group("value").strip()
            current_parts = [value] if value else []
        elif current_key is not None:
            # Continuation of the current section
            current_parts.append(text)

    # Flush last section
    if current_key is not None:
        sections[current_key] = " ".join(current_parts).strip()

    return sections


def _parse_class(node: ast.ClassDef, source_path: str | None = None) -> ClassElement:
    """Parse a class AST node into a ClassElement."""
    # Base classes
    base_names = [ast.unparse(b) for b in node.bases]

    # Decorators
    decorator_names = [_decorator_name(d) for d in node.decorator_list]

    # Stereotype
    stereotype = _infer_stereotype(node, base_names, decorator_names)

    # Docstring
    raw_doc = ast.get_docstring(node) or ""
    doc_sections = parse_docstring(raw_doc) if raw_doc else {}

    # Fields: class-level AnnAssign nodes
    fields: list[FieldElement] = []
    seen_field_names: set[str] = set()

    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            fname = item.target.id
            ftype = _annotation_to_str(item.annotation) if item.annotation else None
            fdefault = ast.unparse(item.value) if item.value else None
            fields.append(FieldElement(name=fname, type_annotation=ftype, default_value=fdefault))
            seen_field_names.add(fname)

    # Also collect self.x: T = ... assignments inside __init__
    for item in node.body:
        if (
            isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == "__init__"
        ):
            for stmt in item.body:
                if (
                    isinstance(stmt, ast.AnnAssign)
                    and isinstance(stmt.target, ast.Attribute)
                    and isinstance(stmt.target.value, ast.Name)
                    and stmt.target.value.id == "self"
                ):
                    fname = stmt.target.attr
                    if fname not in seen_field_names:
                        ftype = _annotation_to_str(stmt.annotation) if stmt.annotation else None
                        fdefault = ast.unparse(stmt.value) if stmt.value else None
                        fields.append(
                            FieldElement(name=fname, type_annotation=ftype, default_value=fdefault)
                        )
                        seen_field_names.add(fname)

    # Second pass: populate comment_sections for class-level fields
    if source_path:
        try:
            source_lines = Path(source_path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            source_lines = []
        if source_lines:
            field_by_name = {f.name: f for f in fields}
            for item in node.body:
                if (
                    isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.target.id in field_by_name
                ):
                    sections = _parse_field_comment_sections(source_lines, item.lineno)
                    if sections:
                        field_by_name[item.target.id].comment_sections = sections

    # Methods
    methods: list[MethodElement] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = item.name
            # Skip non-architectural dunders
            if name.startswith("__") and name.endswith("__") and name not in _KEEP_DUNDERS:
                continue
            methods.append(_parse_method(item))

    return ClassElement(
        name=node.name,
        stereotype=stereotype,
        base_classes=base_names,
        docstring_sections=doc_sections,
        fields=fields,
        methods=methods,
        source_path=source_path,
        line_number=node.lineno,
    )


# ---------------------------------------------------------------------------
# PythonAstParser
# ---------------------------------------------------------------------------


class PythonAstParser:
    """Parse Python source files into structured CodeElement lists."""

    def parse_file(self, path: Path) -> list[CodeElement]:
        """Parse a single Python source file and return its code elements."""
        source = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        elements: list[CodeElement] = []
        source_str = str(path)

        # Walk only top-level statements for classes; imports at module level
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                elements.append(_parse_class(node, source_path=source_str))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    elements.append(ImportElement(module=alias.name, names=[alias.name]))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                elements.append(ImportElement(module=module, names=names))

        return elements

    def parse_directory(self, path: Path, recursive: bool = True) -> list[CodeElement]:
        """Parse all Python files in a directory and return combined elements."""
        directory = Path(path)
        pattern = "**/*.py" if recursive else "*.py"
        elements: list[CodeElement] = []
        for py_file in sorted(directory.glob(pattern)):
            # Skip __init__.py files (usually empty or just re-exports)
            if py_file.name == "__init__.py":
                continue
            elements.extend(self.parse_file(py_file))
        return elements

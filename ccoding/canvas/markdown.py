"""Structured markdown parser and renderer for canvas node text fields.

Parses the markdown format defined in the CooperativeCoding spec Section 3.3,
which describes class nodes, method nodes, and field nodes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FieldEntry:
    name: str
    type: str
    has_detail: bool = False


@dataclass
class MethodEntry:
    name: str
    signature: str = ""
    has_detail: bool = False


@dataclass
class SignatureEntry:
    name: str
    type: str
    description: str = ""


@dataclass
class ClassContent:
    name: str
    stereotype: str | None
    responsibility: str
    fields: list[FieldEntry] = field(default_factory=list)
    methods: list[MethodEntry] = field(default_factory=list)


@dataclass
class MethodContent:
    name: str
    responsibility: str
    signature_in: list[SignatureEntry] = field(default_factory=list)
    signature_out: SignatureEntry | None = None
    raises: list[SignatureEntry] = field(default_factory=list)
    pseudo_code: str = ""


@dataclass
class FieldContent:
    name: str
    responsibility: str
    type: str
    constraints: str
    default: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_sections(text: str) -> dict[str, str]:
    """Split *text* into a dict mapping section header -> section body.

    The special key ``""`` holds the preamble (content before the first
    ``### `` header).
    """
    sections: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("### "):
            sections[current_key] = "\n".join(current_lines)
            current_key = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_key] = "\n".join(current_lines)
    return sections


def _strip_blank(text: str) -> str:
    """Strip leading/trailing blank lines and whitespace."""
    return text.strip()


# ---------------------------------------------------------------------------
# Class node
# ---------------------------------------------------------------------------

# Matches:  - config: `ParserConfig` ●
_FIELD_LINE_RE = re.compile(
    r"^-\s+(?P<name>\S+?):\s+`(?P<type>[^`]+)`\s*(?P<detail>●?)$"
)

# Matches:  - parse(source: `str`) -> `AST` ●
# or:       - validate(ast: `AST`) -> `bool`
# or:       - simpleName ●
_METHOD_LINE_RE = re.compile(
    r"^-\s+(?P<raw>.+?)\s*(?P<detail>●?)$"
)

# Extract the bare method name (everything before the first '(' or whitespace)
_METHOD_NAME_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)")


def _parse_field_line(line: str) -> FieldEntry | None:
    m = _FIELD_LINE_RE.match(line.strip())
    if not m:
        return None
    return FieldEntry(
        name=m.group("name"),
        type=m.group("type"),
        has_detail=bool(m.group("detail")),
    )


def _parse_method_line(line: str) -> MethodEntry | None:
    line = line.strip()
    if not line.startswith("- "):
        return None
    content = line[2:].strip()

    # Detect trailing ●
    has_detail = content.endswith("●")
    if has_detail:
        content = content[:-1].strip()

    # Extract method name
    nm = _METHOD_NAME_RE.match(content)
    if not nm:
        return None

    name = nm.group("name")
    # Everything after the name is the signature fragment
    sig = content[len(name):].strip()

    return MethodEntry(name=name, signature=sig, has_detail=has_detail)


def parse_class_node(text: str) -> ClassContent:
    sections = _split_sections(text)
    preamble = sections.get("", "")

    # --- stereotype (optional): «protocol»
    stereotype: str | None = None
    m = re.search(r"«([^»]+)»", preamble)
    if m:
        stereotype = m.group(1)

    # --- name from ## heading
    name = ""
    for line in preamble.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            break

    # --- responsibility from > blockquote
    responsibility = ""
    for line in preamble.splitlines():
        stripped = line.strip()
        if stripped.startswith("> "):
            responsibility = stripped[2:].strip()
            break

    # --- fields
    fields: list[FieldEntry] = []
    fields_text = sections.get("Fields", "")
    for line in fields_text.splitlines():
        entry = _parse_field_line(line)
        if entry is not None:
            fields.append(entry)

    # --- methods
    methods: list[MethodEntry] = []
    methods_text = sections.get("Methods", "")
    for line in methods_text.splitlines():
        entry = _parse_method_line(line)
        if entry is not None:
            methods.append(entry)

    return ClassContent(
        name=name,
        stereotype=stereotype,
        responsibility=responsibility,
        fields=fields,
        methods=methods,
    )


def render_class_node(content: ClassContent) -> str:
    parts: list[str] = []

    if content.stereotype:
        parts.append(f"«{content.stereotype}»")

    parts.append(f"## {content.name}")
    parts.append("")

    if content.responsibility:
        parts.append(f"> {content.responsibility}")
        parts.append("")

    parts.append("### Fields")
    for f in content.fields:
        detail = " ●" if f.has_detail else ""
        parts.append(f"- {f.name}: `{f.type}`{detail}")
    parts.append("")

    parts.append("### Methods")
    for m in content.methods:
        detail = " ●" if m.has_detail else ""
        sig = f" {m.signature}" if m.signature else ""
        parts.append(f"- {m.name}{sig}{detail}")
    parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Method node
# ---------------------------------------------------------------------------

# - **IN:** source: `str` — raw document text
_SIG_IN_RE = re.compile(
    r"^\*\*IN:\*\*\s+(?P<name>\S+?):\s+`(?P<type>[^`]+)`(?:\s+—\s+(?P<desc>.+))?$"
)

# - **OUT:** `AST` — parsed syntax tree
_SIG_OUT_RE = re.compile(
    r"^\*\*OUT:\*\*\s+`(?P<type>[^`]+)`(?:\s+—\s+(?P<desc>.+))?$"
)

# - **RAISES:** `ParseError` — on malformed input
_SIG_RAISES_RE = re.compile(
    r"^\*\*RAISES:\*\*\s+`(?P<type>[^`]+)`(?:\s+—\s+(?P<desc>.+))?$"
)


def _parse_sig_line(line: str) -> tuple[str, SignatureEntry] | None:
    """Return (kind, entry) or None. kind is 'in', 'out', or 'raises'."""
    line = line.strip()
    if not line.startswith("- "):
        return None
    content = line[2:].strip()

    m = _SIG_IN_RE.match(content)
    if m:
        return ("in", SignatureEntry(
            name=m.group("name"),
            type=m.group("type"),
            description=m.group("desc") or "",
        ))

    m = _SIG_OUT_RE.match(content)
    if m:
        return ("out", SignatureEntry(
            name="",
            type=m.group("type"),
            description=m.group("desc") or "",
        ))

    m = _SIG_RAISES_RE.match(content)
    if m:
        return ("raises", SignatureEntry(
            name="",
            type=m.group("type"),
            description=m.group("desc") or "",
        ))

    return None


def parse_method_node(text: str) -> MethodContent:
    sections = _split_sections(text)
    preamble = sections.get("", "")

    # name from ## heading
    name = ""
    for line in preamble.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            break

    # responsibility
    responsibility = _strip_blank(sections.get("Responsibility", ""))

    # signature
    signature_in: list[SignatureEntry] = []
    signature_out: SignatureEntry | None = None
    raises: list[SignatureEntry] = []
    sig_text = sections.get("Signature", "")
    for line in sig_text.splitlines():
        parsed = _parse_sig_line(line)
        if parsed is None:
            continue
        kind, entry = parsed
        if kind == "in":
            signature_in.append(entry)
        elif kind == "out":
            signature_out = entry
        elif kind == "raises":
            raises.append(entry)

    # pseudo code (raw)
    pseudo_code = _strip_blank(sections.get("Pseudo Code", ""))

    return MethodContent(
        name=name,
        responsibility=responsibility,
        signature_in=signature_in,
        signature_out=signature_out,
        raises=raises,
        pseudo_code=pseudo_code,
    )


def render_method_node(content: MethodContent) -> str:
    parts: list[str] = []

    parts.append(f"## {content.name}")
    parts.append("")

    parts.append("### Responsibility")
    parts.append(content.responsibility)
    parts.append("")

    parts.append("### Signature")
    for entry in content.signature_in:
        desc = f" — {entry.description}" if entry.description else ""
        parts.append(f"- **IN:** {entry.name}: `{entry.type}`{desc}")
    if content.signature_out is not None:
        desc = f" — {content.signature_out.description}" if content.signature_out.description else ""
        parts.append(f"- **OUT:** `{content.signature_out.type}`{desc}")
    for entry in content.raises:
        desc = f" — {entry.description}" if entry.description else ""
        parts.append(f"- **RAISES:** `{entry.type}`{desc}")
    parts.append("")

    if content.pseudo_code:
        parts.append("### Pseudo Code")
        parts.append(content.pseudo_code)
        parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Field node
# ---------------------------------------------------------------------------

def parse_field_node(text: str) -> FieldContent:
    sections = _split_sections(text)
    preamble = sections.get("", "")

    # name from ## heading
    name = ""
    for line in preamble.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            break

    # responsibility
    responsibility = _strip_blank(sections.get("Responsibility", ""))

    # type — strip backticks
    type_raw = _strip_blank(sections.get("Type", ""))
    type_val = type_raw.strip("`")

    # constraints (raw text, stripped)
    constraints = _strip_blank(sections.get("Constraints", ""))

    # default (raw text, stripped)
    default = _strip_blank(sections.get("Default", ""))

    return FieldContent(
        name=name,
        responsibility=responsibility,
        type=type_val,
        constraints=constraints,
        default=default,
    )


def render_field_node(content: FieldContent) -> str:
    parts: list[str] = []

    parts.append(f"## {content.name}")
    parts.append("")

    parts.append("### Responsibility")
    parts.append(content.responsibility)
    parts.append("")

    parts.append("### Type")
    parts.append(f"`{content.type}`")
    parts.append("")

    if content.constraints:
        parts.append("### Constraints")
        parts.append(content.constraints)
        parts.append("")

    if content.default:
        parts.append("### Default")
        parts.append(content.default)
        parts.append("")

    return "\n".join(parts)

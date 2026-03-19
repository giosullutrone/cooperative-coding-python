"""Sync engine — orchestrates bidirectional sync between canvas and code.

This is the heart of the CooperativeCoding CLI extension. It ties together
parsing, canvas reading/writing, hashing, diffing, and code generation to
keep the Obsidian canvas and the Python source tree in sync.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from ccoding.canvas.markdown import (
    ClassContent,
    FieldEntry,
    MethodEntry,
    render_class_node,
    parse_class_node,
)
from ccoding.canvas.model import (
    Canvas,
    Node,
    Edge,
    CcodingMetadata,
    EdgeMetadata,
)
from ccoding.canvas.reader import read_canvas
from ccoding.canvas.writer import write_canvas
from ccoding.code.generator import generate_class, deprecate_class
from ccoding.code.parser import PythonAstParser, ClassElement
from ccoding.config import load_config
from ccoding.sync.conflict import ConflictResolution, resolve_conflict
from ccoding.sync.differ import Conflict, SyncDiff, compute_diff
from ccoding.sync.hasher import content_hash
from ccoding.sync.state import (
    SyncState,
    ElementState,
    load_sync_state,
    save_sync_state,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SyncResult:
    canvas_to_code: list[str] = field(default_factory=list)
    code_to_canvas: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GRID_SPACING_X = 400
_GRID_SPACING_Y = 400
_GRID_COLUMNS = 4
_NODE_WIDTH = 320
_NODE_HEIGHT = 280


def _new_id() -> str:
    return f"node-{uuid4().hex[:8]}"


def _edge_id() -> str:
    return f"edge-{uuid4().hex[:8]}"


def _qualified_name(source_path: Path, class_name: str, source_root: Path) -> str:
    """Build a dotted qualified name from the file path and class name.

    Example: source_root=project/src, source_path=project/src/parsers/document.py,
    class_name=DocumentParser -> parsers.document.DocumentParser
    """
    try:
        rel = source_path.relative_to(source_root)
    except ValueError:
        rel = source_path
    # Convert path to dotted module: parsers/document.py -> parsers.document
    module = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
    return f"{module}.{class_name}"


def _element_to_class_content(elem: ClassElement) -> ClassContent:
    """Convert a parsed ClassElement into a ClassContent for canvas rendering."""
    # Responsibility from docstring
    responsibility = elem.docstring_sections.get("responsibility", "")
    if not responsibility:
        responsibility = elem.docstring_sections.get("summary", "")

    # Fields
    fields = [
        FieldEntry(
            name=f.name,
            type=f.type_annotation or "Any",
        )
        for f in elem.fields
    ]

    # Methods
    methods = []
    for m in elem.methods:
        # Build a signature string like (param: type, ...) -> ReturnType
        param_parts = []
        for p in m.parameters:
            if p.type_annotation:
                param_parts.append(f"{p.name}: {p.type_annotation}")
            else:
                param_parts.append(p.name)
        sig_params = ", ".join(param_parts)
        if m.return_type:
            sig = f"({sig_params}) -> {m.return_type}" if sig_params else f"() -> {m.return_type}"
        elif sig_params:
            sig = f"({sig_params})"
        else:
            sig = ""
        methods.append(MethodEntry(name=m.name, signature=sig))

    return ClassContent(
        name=elem.name,
        stereotype=elem.stereotype if elem.stereotype != "class" else None,
        responsibility=responsibility,
        fields=fields,
        methods=methods,
    )


def _hash_class_element(elem: ClassElement) -> str:
    """Hash a ClassElement for code-side comparison."""
    parts = [elem.name]
    for f in elem.fields:
        parts.append(f"field:{f.name}:{f.type_annotation or ''}")
    for m in elem.methods:
        parts.append(f"method:{m.name}:{m.return_type or ''}")
    for section_key in sorted(elem.docstring_sections.keys()):
        parts.append(f"doc:{section_key}:{elem.docstring_sections[section_key]}")
    return content_hash("\n".join(parts))


def _grid_position(index: int) -> tuple[int, int]:
    """Return (x, y) for a grid-based layout given the index."""
    col = index % _GRID_COLUMNS
    row = index // _GRID_COLUMNS
    return col * _GRID_SPACING_X, row * _GRID_SPACING_Y


def _source_rel(source_path: str | None, project_root: Path) -> str:
    """Return the source path relative to project_root."""
    if source_path is None:
        return ""
    try:
        return str(Path(source_path).relative_to(project_root))
    except ValueError:
        return source_path


# ---------------------------------------------------------------------------
# import_codebase
# ---------------------------------------------------------------------------


def import_codebase(
    source_dir: Path,
    canvas_path: Path,
    project_root: Path,
    language: str = "python",
) -> SyncResult:
    """Import an existing codebase into a canvas file.

    Parses all classes in *source_dir*, creates canvas nodes for each one,
    writes the canvas, and initialises sync state.
    """
    parser = PythonAstParser()
    elements = parser.parse_directory(source_dir)

    # Filter to ClassElement only
    class_elements = [e for e in elements if isinstance(e, ClassElement)]

    canvas = Canvas()
    state = SyncState(canvas_file=str(canvas_path.name))
    result = SyncResult()

    # Build a map from class name to node id for edge creation
    name_to_node_id: dict[str, str] = {}

    for idx, elem in enumerate(class_elements):
        node_id = _new_id()
        x, y = _grid_position(idx)

        qname = _qualified_name(
            Path(elem.source_path) if elem.source_path else source_dir,
            elem.name,
            source_dir,
        )

        content = _element_to_class_content(elem)
        text = render_class_node(content)

        source_rel = _source_rel(elem.source_path, project_root)

        node = Node(
            id=node_id,
            type="text",
            x=x,
            y=y,
            width=_NODE_WIDTH,
            height=_NODE_HEIGHT,
            text=text,
            ccoding=CcodingMetadata(
                kind="class",
                stereotype=elem.stereotype if elem.stereotype != "class" else None,
                language=language,
                source=source_rel,
                qualified_name=qname,
                status="accepted",
                layout_pending=True,
            ),
        )
        canvas.nodes.append(node)
        name_to_node_id[elem.name] = node_id

        # Compute hashes
        canvas_hash = content_hash(text)
        code_hash_val = _hash_class_element(elem)

        state.elements[qname] = ElementState(
            canvas_hash=canvas_hash,
            code_hash=code_hash_val,
            canvas_node_id=node_id,
            source_path=source_rel,
        )

        result.code_to_canvas.append(qname)

    # Create edges for inheritance / implements relationships
    for elem in class_elements:
        from_id = name_to_node_id.get(elem.name)
        if not from_id:
            continue
        for base in elem.base_classes:
            # Strip module path if present (e.g. 'abc.ABC' -> 'ABC')
            base_simple = base.rsplit(".", 1)[-1] if "." in base else base
            to_id = name_to_node_id.get(base_simple)
            if to_id:
                # Determine relation type: Protocol -> implements, else inherits
                relation = "implements" if base_simple == "Protocol" else "inherits"
                edge = Edge(
                    id=_edge_id(),
                    from_node=from_id,
                    to_node=to_id,
                    label=relation,
                    ccoding=EdgeMetadata(relation=relation, status="accepted"),
                )
                canvas.edges.append(edge)

    write_canvas(canvas, canvas_path)
    save_sync_state(state, project_root)

    return result


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


def sync(
    canvas_path: Path,
    project_root: Path,
    strategy: str | None = None,
) -> SyncResult:
    """Perform bidirectional sync between canvas and code.

    1. Load config, canvas, code, and sync state.
    2. Compute hashes and diff.
    3. Apply non-conflicting changes.
    4. Return the SyncResult.
    """
    config = load_config(project_root)
    source_root = project_root / config.source_root

    # Parse canvas
    canvas = read_canvas(canvas_path)

    # Parse code
    parser = PythonAstParser()
    code_elements: list[ClassElement] = []
    if source_root.exists():
        all_elements = parser.parse_directory(source_root)
        code_elements = [e for e in all_elements if isinstance(e, ClassElement)]

    # Load sync state
    state = load_sync_state(project_root)

    # Build current hash maps
    canvas_hashes: dict[str, str] = {}
    canvas_node_map: dict[str, Node] = {}
    all_canvas_qnames: set[str] = set()
    for node in canvas.nodes:
        if node.ccoding and node.ccoding.qualified_name:
            all_canvas_qnames.add(node.ccoding.qualified_name)
            # Skip ghost/proposed/rejected nodes
            if node.ccoding.status in ("proposed", "rejected"):
                continue
            qname = node.ccoding.qualified_name
            canvas_hashes[qname] = content_hash(node.text)
            canvas_node_map[qname] = node

    code_hashes: dict[str, str] = {}
    code_element_map: dict[str, ClassElement] = {}
    for elem in code_elements:
        qname = _qualified_name(
            Path(elem.source_path) if elem.source_path else source_root,
            elem.name,
            source_root,
        )
        code_hashes[qname] = _hash_class_element(elem)
        code_element_map[qname] = elem

    # Compute diff
    diff = compute_diff(state, canvas_hashes, code_hashes)

    result = SyncResult()

    # Handle conflicts
    if diff.conflicts:
        for conflict in diff.conflicts:
            resolution = resolve_conflict(conflict, strategy)
            if resolution == ConflictResolution.USE_CANVAS:
                # Treat as canvas-modified: regenerate code from canvas
                diff.canvas_modified.append(conflict.element_name)
            elif resolution == ConflictResolution.USE_CODE:
                # Treat as code-modified: update canvas from code
                diff.code_modified.append(conflict.element_name)
            else:
                # Manual — surface as unresolved conflict
                result.conflicts.append(conflict)
        if result.conflicts:
            return result

    # Apply changes: code_added -> create new canvas nodes
    for qname in diff.code_added:
        elem = code_element_map[qname]
        node_id = _new_id()
        idx = len(canvas.nodes)
        x, y = _grid_position(idx)

        content = _element_to_class_content(elem)
        text = render_class_node(content)
        source_rel = _source_rel(elem.source_path, project_root)

        node = Node(
            id=node_id,
            type="text",
            x=x,
            y=y,
            width=_NODE_WIDTH,
            height=_NODE_HEIGHT,
            text=text,
            ccoding=CcodingMetadata(
                kind="class",
                stereotype=elem.stereotype if elem.stereotype != "class" else None,
                language=config.language,
                source=source_rel,
                qualified_name=qname,
                status="accepted",
                layout_pending=True,
            ),
        )
        canvas.nodes.append(node)

        canvas_hash = content_hash(text)
        code_hash_val = code_hashes[qname]

        state.elements[qname] = ElementState(
            canvas_hash=canvas_hash,
            code_hash=code_hash_val,
            canvas_node_id=node_id,
            source_path=source_rel,
        )
        result.code_to_canvas.append(qname)

    # Apply changes: code_modified -> update canvas node text
    for qname in diff.code_modified:
        elem = code_element_map[qname]
        node = canvas_node_map.get(qname)
        if node:
            content = _element_to_class_content(elem)
            text = render_class_node(content)
            node.text = text
            state.elements[qname].canvas_hash = content_hash(text)
            state.elements[qname].code_hash = code_hashes[qname]
            result.code_to_canvas.append(qname)

    # Apply changes: canvas_added (accepted nodes only) -> generate code
    for qname in diff.canvas_added:
        node = canvas_node_map.get(qname)
        if not node or not node.ccoding:
            continue
        if node.ccoding.status != "accepted":
            continue

        content = parse_class_node(node.text)
        code_text = generate_class(content, config.language)

        # Determine output path from the qualified name
        parts = qname.rsplit(".", 1)
        if len(parts) == 2:
            module_path, _class_name = parts
        else:
            module_path = parts[0]

        rel_path = module_path.replace(".", "/") + ".py"
        target = source_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code_text)

        source_rel = str(Path(config.source_root) / rel_path)
        canvas_hash = canvas_hashes[qname]
        code_hash_val = content_hash(code_text)

        state.elements[qname] = ElementState(
            canvas_hash=canvas_hash,
            code_hash=code_hash_val,
            canvas_node_id=node.id,
            source_path=source_rel,
        )
        result.canvas_to_code.append(qname)

    # Apply changes: canvas_modified -> regenerate code from canvas
    for qname in diff.canvas_modified:
        node = canvas_node_map.get(qname)
        if not node or not node.ccoding:
            continue

        content = parse_class_node(node.text)
        code_text = generate_class(content, config.language)

        # Find existing source path from state
        elem_state = state.elements.get(qname)
        if elem_state and elem_state.source_path:
            target = project_root / elem_state.source_path
        else:
            parts = qname.rsplit(".", 1)
            module_path = parts[0] if len(parts) == 2 else parts[0]
            rel_path = module_path.replace(".", "/") + ".py"
            target = source_root / rel_path

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code_text)

        state.elements[qname].canvas_hash = canvas_hashes[qname]
        state.elements[qname].code_hash = content_hash(code_text)
        result.canvas_to_code.append(qname)

    # Handle code_deleted: mark canvas nodes as stale
    for qname in diff.code_deleted:
        node = canvas_node_map.get(qname)
        if node and node.ccoding:
            node.ccoding.status = "stale"
            result.code_to_canvas.append(qname)

    # Handle canvas_deleted: deprecate corresponding code
    for qname in diff.canvas_deleted:
        # Skip nodes that are still present in the canvas but excluded from active
        # sync (e.g. rejected/proposed). Only act on nodes truly removed from canvas.
        if qname in all_canvas_qnames:
            continue
        elem_state = state.elements.get(qname)
        if elem_state and elem_state.source_path:
            source_file = project_root / elem_state.source_path
            if source_file.exists():
                class_name = qname.rsplit(".", 1)[-1]
                deprecate_class(source_file, class_name)
                result.canvas_to_code.append(qname)
        # Remove from state tracking
        state.elements.pop(qname, None)

    # Write updated canvas and state
    write_canvas(canvas, canvas_path)
    save_sync_state(state, project_root)

    return result


# ---------------------------------------------------------------------------
# sync_status
# ---------------------------------------------------------------------------


def sync_status(project_root: Path) -> str:
    """Return a human-readable status report for the CLI status command."""
    config = load_config(project_root)
    canvas_path = project_root / config.canvas
    source_root = project_root / config.source_root

    if not canvas_path.exists():
        return "No canvas file found."

    canvas = read_canvas(canvas_path)

    parser = PythonAstParser()
    code_elements: list[ClassElement] = []
    if source_root.exists():
        all_elements = parser.parse_directory(source_root)
        code_elements = [e for e in all_elements if isinstance(e, ClassElement)]

    state = load_sync_state(project_root)

    # Build hashes
    canvas_hashes: dict[str, str] = {}
    for node in canvas.nodes:
        if node.ccoding and node.ccoding.qualified_name:
            if node.ccoding.status in ("proposed", "rejected"):
                continue
            canvas_hashes[node.ccoding.qualified_name] = content_hash(node.text)

    code_hashes: dict[str, str] = {}
    for elem in code_elements:
        qname = _qualified_name(
            Path(elem.source_path) if elem.source_path else source_root,
            elem.name,
            source_root,
        )
        code_hashes[qname] = _hash_class_element(elem)

    diff = compute_diff(state, canvas_hashes, code_hashes)

    lines: list[str] = []
    lines.append(f"Canvas: {config.canvas}")
    lines.append(f"Source: {config.source_root}")
    lines.append(f"Tracked elements: {len(state.elements)}")
    lines.append("")

    if diff.in_sync:
        lines.append(f"In sync: {len(diff.in_sync)}")
    if diff.canvas_modified:
        lines.append(f"Canvas modified: {', '.join(diff.canvas_modified)}")
    if diff.code_modified:
        lines.append(f"Code modified: {', '.join(diff.code_modified)}")
    if diff.canvas_added:
        lines.append(f"Canvas added: {', '.join(diff.canvas_added)}")
    if diff.code_added:
        lines.append(f"Code added: {', '.join(diff.code_added)}")
    if diff.canvas_deleted:
        lines.append(f"Canvas deleted: {', '.join(diff.canvas_deleted)}")
    if diff.code_deleted:
        lines.append(f"Code deleted: {', '.join(diff.code_deleted)}")
    if diff.conflicts:
        lines.append(f"Conflicts: {', '.join(c.qualified_name for c in diff.conflicts)}")

    if not any([
        diff.canvas_modified, diff.code_modified,
        diff.canvas_added, diff.code_added,
        diff.canvas_deleted, diff.code_deleted,
        diff.conflicts,
    ]):
        lines.append("Everything is in sync.")

    return "\n".join(lines)

"""Sync engine — orchestrates bidirectional sync between canvas and code.

This is the heart of the CooperativeCoding CLI extension. It ties together
parsing, canvas reading/writing, hashing, diffing, and code generation to
keep the Obsidian canvas and the Python source tree in sync.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from ccoding.canvas.markdown import (
    ClassContent,
    FieldEntry,
    MethodEntry,
    MethodContent,
    SignatureEntry,
    render_class_node,
    render_method_node,
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
from ccoding.code.generator import generate_class, deprecate_class, EdgeInfo
from ccoding.code.types import python_to_canvas
from ccoding.code.parser import PythonAstParser, ClassElement, MethodElement, ImportElement
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


def _element_to_class_content(
    elem: ClassElement,
    promoted_methods: set[str] | None = None,
) -> ClassContent:
    """Convert a parsed ClassElement into a ClassContent for canvas rendering.

    Args:
        elem: The parsed class element.
        promoted_methods: Optional set of method names that have been promoted to
            detail nodes. When a method name is in this set, its MethodEntry will
            have ``has_detail=True``, which causes the ``●`` marker to appear.
    """
    # Responsibility from docstring
    responsibility = elem.docstring_sections.get("responsibility", "")
    if not responsibility:
        responsibility = elem.docstring_sections.get("summary", "")

    # Fields
    fields = [
        FieldEntry(
            name=f.name,
            type=python_to_canvas(f.type_annotation) if f.type_annotation else "Any",
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
                param_parts.append(f"{p.name}: {python_to_canvas(p.type_annotation)}")
            else:
                param_parts.append(p.name)
        sig_params = ", ".join(param_parts)
        ret_type = python_to_canvas(m.return_type) if m.return_type else ""
        if ret_type:
            sig = f"({sig_params}) -> {ret_type}" if sig_params else f"() -> {ret_type}"
        elif sig_params:
            sig = f"({sig_params})"
        else:
            sig = ""
        has_detail = promoted_methods is not None and m.name in promoted_methods
        methods.append(MethodEntry(name=m.name, signature=sig, has_detail=has_detail))

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


def _is_significant_method(method: MethodElement) -> bool:
    """Return True if the method has a non-empty 'responsibility' or 'pseudo code' section."""
    return bool(
        method.docstring_sections.get("responsibility", "").strip()
        or method.docstring_sections.get("pseudo code", "").strip()
    )


def _method_to_detail_node(
    method: MethodElement,
    class_qname: str,
    x: int,
    y: int,
    language: str,
) -> Node:
    """Create a canvas Node for a significant method detail."""
    method_qname = f"{class_qname}.{method.name}"

    # Build signature_in from parameters (skip 'self' / 'cls')
    signature_in: list[SignatureEntry] = [
        SignatureEntry(
            name=p.name,
            type=python_to_canvas(p.type_annotation) if p.type_annotation else "Any",
            description="",
        )
        for p in method.parameters
        if p.name not in ("self", "cls")
    ]

    # Build signature_out from return_type
    signature_out: SignatureEntry | None = None
    if method.return_type:
        signature_out = SignatureEntry(name="", type=python_to_canvas(method.return_type), description="")

    # Parse raises from docstring section "raises": each line "ExcType: description"
    raises: list[SignatureEntry] = []
    raises_raw = method.docstring_sections.get("raises", "").strip()
    if raises_raw:
        for line in raises_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                exc_type, _, desc = line.partition(":")
                raises.append(SignatureEntry(name="", type=exc_type.strip(), description=desc.strip()))
            else:
                raises.append(SignatureEntry(name="", type=line, description=""))

    content = MethodContent(
        name=f"{class_qname.rsplit('.', 1)[-1]}.{method.name}",
        responsibility=method.docstring_sections.get("responsibility", "").strip(),
        signature_in=signature_in,
        signature_out=signature_out,
        raises=raises,
        pseudo_code=method.docstring_sections.get("pseudo code", "").strip(),
    )

    text = render_method_node(content)

    return Node(
        id=_new_id(),
        type="text",
        x=x,
        y=y,
        width=_NODE_WIDTH,
        height=_NODE_HEIGHT,
        text=text,
        ccoding=CcodingMetadata(
            kind="method",
            language=language,
            qualified_name=method_qname,
            status="accepted",
            layout_pending=True,
        ),
    )


_ALLOWED_RELATIONS = ("inherits", "implements", "composes", "depends")


def _collect_edge_info(canvas: "Canvas", node_id: str) -> list[EdgeInfo]:
    """Return EdgeInfo objects for accepted edges originating from *node_id*.

    Only edges whose ``ccoding.relation`` is in the allow-list and whose
    ``ccoding.status`` is ``"accepted"`` are included.  The target node is
    looked up to obtain ``target_name`` (last segment of its qualified name)
    and ``target_qname``.
    """
    # Build a quick id->node lookup
    node_by_id: dict[str, Node] = {n.id: n for n in canvas.nodes}

    result: list[EdgeInfo] = []
    for edge in canvas.edges:
        if edge.from_node != node_id:
            continue
        if not edge.ccoding:
            continue
        if edge.ccoding.status != "accepted":
            continue
        if edge.ccoding.relation not in _ALLOWED_RELATIONS:
            continue

        target_node = node_by_id.get(edge.to_node)
        if not target_node or not target_node.ccoding:
            continue
        target_qname = target_node.ccoding.qualified_name or ""
        target_name = target_qname.rsplit(".", 1)[-1] if target_qname else target_node.id

        result.append(EdgeInfo(
            relation=edge.ccoding.relation,
            target_name=target_name,
            target_qname=target_qname,
            label=edge.label,
        ))

    return result


# ---------------------------------------------------------------------------
# Relationship edge helpers
# ---------------------------------------------------------------------------


def _create_relationship_edges(
    canvas: Canvas,
    elem: ClassElement,
    node_id: str,
    name_to_node_id: dict[str, str],
    all_elements: list[ClassElement],
    import_elements: list[ImportElement] | None = None,
) -> None:
    """Create composes and depends edges from code analysis."""
    # Composes: fields whose type matches a tracked class name
    tracked_class_names = set(name_to_node_id.keys())
    for f in elem.fields:
        if not f.type_annotation:
            continue
        type_name = f.type_annotation.strip("'\"")
        # Word-boundary matching to avoid false positives
        for class_name in tracked_class_names:
            if re.search(rf'\b{re.escape(class_name)}\b', type_name) and class_name != elem.name:
                to_id = name_to_node_id[class_name]
                # Don't create duplicate edges
                existing = any(
                    e for e in canvas.edges
                    if e.ccoding and e.ccoding.relation == "composes"
                    and e.from_node == node_id and e.to_node == to_id
                )
                if not existing:
                    edge = Edge(
                        id=_edge_id(),
                        from_node=node_id,
                        to_node=to_id,
                        label=f.name,
                        ccoding=EdgeMetadata(relation="composes", status="accepted"),
                    )
                    canvas.edges.append(edge)
                break

    # Depends: imports that reference tracked classes
    if import_elements:
        for imp in import_elements:
            for name in imp.names:
                simple_name = name.rsplit(".", 1)[-1] if "." in name else name
                if simple_name in tracked_class_names and simple_name != elem.name:
                    to_id = name_to_node_id[simple_name]
                    existing = any(
                        e for e in canvas.edges
                        if e.ccoding and e.ccoding.relation == "depends"
                        and e.from_node == node_id and e.to_node == to_id
                    )
                    if not existing:
                        edge = Edge(
                            id=_edge_id(),
                            from_node=node_id,
                            to_node=to_id,
                            label=name,
                            ccoding=EdgeMetadata(relation="depends", status="accepted"),
                        )
                        canvas.edges.append(edge)


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

        # Determine which methods are significant enough to promote
        significant_methods = [m for m in elem.methods if _is_significant_method(m)]
        promoted_methods: set[str] = {m.name for m in significant_methods}

        content = _element_to_class_content(elem, promoted_methods if promoted_methods else None)
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

        # Create detail nodes for significant methods
        for method_idx, method in enumerate(significant_methods):
            detail_node = _method_to_detail_node(
                method=method,
                class_qname=qname,
                x=x + _NODE_WIDTH + _GRID_SPACING_X,
                y=y + method_idx * (_NODE_HEIGHT + 20),
                language=language,
            )
            canvas.nodes.append(detail_node)
            detail_edge = Edge(
                id=_edge_id(),
                from_node=node_id,
                to_node=detail_node.id,
                label=method.name,
                ccoding=EdgeMetadata(relation="detail", status="accepted"),
            )
            canvas.edges.append(detail_edge)

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

    # Create composes / depends edges from field types and imports
    # Group class elements by source file for per-file import lookup
    files_seen: set[str] = set()
    file_imports: dict[str, list[ImportElement]] = {}
    for elem in class_elements:
        if elem.source_path and elem.source_path not in files_seen:
            files_seen.add(elem.source_path)
            per_file = parser.parse_file(Path(elem.source_path))
            file_imports[elem.source_path] = [
                e for e in per_file if isinstance(e, ImportElement)
            ]

    for elem in class_elements:
        from_id = name_to_node_id.get(elem.name)
        if not from_id:
            continue
        imports = file_imports.get(elem.source_path or "", [])
        _create_relationship_edges(
            canvas=canvas,
            elem=elem,
            node_id=from_id,
            name_to_node_id=name_to_node_id,
            all_elements=class_elements,
            import_elements=imports,
        )

    # Set canvas-level metadata per spec Data Model §2
    canvas._extra.setdefault("ccoding", {})["specVersion"] = "1.0.0"

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
            # Only class nodes participate in the bidirectional sync diff.
            # Method/field detail nodes are managed by the class node and must
            # not be treated as independent canvas-added elements.
            if node.ccoding.kind != "class":
                continue
            # Skip ghost/proposed/rejected/stale nodes
            if node.ccoding.status in ("proposed", "rejected", "stale"):
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
                diff.canvas_modified.append(conflict.qualified_name)
            elif resolution == ConflictResolution.USE_CODE:
                # Treat as code-modified: update canvas from code
                diff.code_modified.append(conflict.qualified_name)
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

        # Determine which methods are significant enough to promote
        significant_methods = [m for m in elem.methods if _is_significant_method(m)]
        promoted_methods_set: set[str] = {m.name for m in significant_methods}

        content = _element_to_class_content(elem, promoted_methods_set if promoted_methods_set else None)
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

        # Create detail nodes for significant methods
        for method_idx, method in enumerate(significant_methods):
            detail_node = _method_to_detail_node(
                method=method,
                class_qname=qname,
                x=x + _NODE_WIDTH + _GRID_SPACING_X,
                y=y + method_idx * (_NODE_HEIGHT + 20),
                language=config.language,
            )
            canvas.nodes.append(detail_node)
            detail_edge = Edge(
                id=_edge_id(),
                from_node=node_id,
                to_node=detail_node.id,
                label=method.name,
                ccoding=EdgeMetadata(relation="detail", status="accepted"),
            )
            canvas.edges.append(detail_edge)

        canvas_hash = content_hash(text)
        code_hash_val = code_hashes[qname]

        state.elements[qname] = ElementState(
            canvas_hash=canvas_hash,
            code_hash=code_hash_val,
            canvas_node_id=node_id,
            source_path=source_rel,
        )
        result.code_to_canvas.append(qname)

        # Build name_to_node_id from all current canvas nodes for edge creation
        name_to_node_id: dict[str, str] = {}
        for n in canvas.nodes:
            if n.ccoding and n.ccoding.qualified_name and n.ccoding.kind == "class":
                simple = n.ccoding.qualified_name.rsplit(".", 1)[-1]
                name_to_node_id[simple] = n.id

        # Get per-file imports for the new element
        imports: list[ImportElement] = []
        if elem.source_path:
            per_file = parser.parse_file(Path(elem.source_path))
            imports = [e for e in per_file if isinstance(e, ImportElement)]

        _create_relationship_edges(
            canvas=canvas,
            elem=elem,
            node_id=node_id,
            name_to_node_id=name_to_node_id,
            all_elements=code_elements,
            import_elements=imports,
        )

    # Apply changes: code_modified -> update canvas node text
    for qname in diff.code_modified:
        elem = code_element_map[qname]
        node = canvas_node_map.get(qname)
        if node:
            # Determine which methods are significant enough to promote
            significant_methods = [m for m in elem.methods if _is_significant_method(m)]
            promoted_methods_set: set[str] = {m.name for m in significant_methods}

            content = _element_to_class_content(elem, promoted_methods_set if promoted_methods_set else None)
            text = render_class_node(content)
            node.text = text
            state.elements[qname].canvas_hash = content_hash(text)
            state.elements[qname].code_hash = code_hashes[qname]
            result.code_to_canvas.append(qname)

            # Build a map of existing detail nodes for this class (by method name)
            # so we can update them in place or create new ones.
            existing_detail_nodes: dict[str, Node] = {}
            for edge in canvas.edges:
                if (
                    edge.from_node == node.id
                    and edge.ccoding
                    and edge.ccoding.relation == "detail"
                ):
                    target = next(
                        (n for n in canvas.nodes if n.id == edge.to_node), None
                    )
                    if target and target.ccoding:
                        method_name = (target.ccoding.qualified_name or "").rsplit(".", 1)[-1]
                        existing_detail_nodes[method_name] = target

            for method_idx, method in enumerate(significant_methods):
                if method.name in existing_detail_nodes:
                    # Update the existing detail node text
                    detail_node = existing_detail_nodes[method.name]
                    updated = _method_to_detail_node(
                        method=method,
                        class_qname=qname,
                        x=detail_node.x,
                        y=detail_node.y,
                        language=config.language,
                    )
                    detail_node.text = updated.text
                else:
                    # Create a new detail node and edge
                    detail_node = _method_to_detail_node(
                        method=method,
                        class_qname=qname,
                        x=node.x + _NODE_WIDTH + _GRID_SPACING_X,
                        y=node.y + method_idx * (_NODE_HEIGHT + 20),
                        language=config.language,
                    )
                    canvas.nodes.append(detail_node)
                    detail_edge = Edge(
                        id=_edge_id(),
                        from_node=node.id,
                        to_node=detail_node.id,
                        label=method.name,
                        ccoding=EdgeMetadata(relation="detail", status="accepted"),
                    )
                    canvas.edges.append(detail_edge)

    # Apply changes: canvas_added (accepted nodes only) -> generate code
    for qname in diff.canvas_added:
        node = canvas_node_map.get(qname)
        if not node or not node.ccoding:
            continue
        if node.ccoding.status != "accepted":
            continue

        content = parse_class_node(node.text)
        edge_info = _collect_edge_info(canvas, node.id)
        code_text = generate_class(content, config.language, edges=edge_info)

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
        edge_info = _collect_edge_info(canvas, node.id)
        code_text = generate_class(content, config.language, edges=edge_info)

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

    # Ensure specVersion is set on every write (spec Data Model §2)
    canvas._extra.setdefault("ccoding", {}).setdefault("specVersion", "1.0.0")

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
            # Only class nodes participate in the bidirectional sync diff.
            # Method/field detail nodes are managed by the class node and must
            # not be treated as independent canvas-added elements.
            if node.ccoding.kind != "class":
                continue
            if node.ccoding.status in ("proposed", "rejected", "stale"):
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

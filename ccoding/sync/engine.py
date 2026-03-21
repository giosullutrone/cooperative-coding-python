"""Sync engine — orchestrates bidirectional sync between canvas and code.

This is the heart of the CooperativeCoding CLI extension. It ties together
parsing, canvas reading/writing, hashing, diffing, and code generation to
keep the Obsidian canvas and the Python source tree in sync.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from ccoding.canvas.markdown import (
    ClassContent,
    FieldContent,
    FieldEntry,
    MethodEntry,
    MethodContent,
    SignatureEntry,
    render_class_node,
    render_field_node,
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
from ccoding.code.parser import PythonAstParser, ClassElement, FieldElement, MethodElement, ImportElement
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

def _topological_sort(
    elements: list[str],
    edges: list[tuple[str, str]],
) -> list[str]:
    """Sort elements in dependency order. Detect and warn about cycles.

    Returns elements in topological order. If a cycle is detected, the
    cycle members are included in a stable (sorted) order with a warning.
    """
    deps: dict[str, set[str]] = {e: set() for e in elements}
    element_set = set(elements)
    for from_e, to_e in edges:
        if from_e in element_set and to_e in element_set:
            deps[from_e].add(to_e)

    result: list[str] = []
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycle_members: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in in_stack:
            cycle_members.add(node)
            return
        in_stack.add(node)
        for dep in sorted(deps.get(node, [])):
            visit(dep)
        in_stack.discard(node)
        visited.add(node)
        result.append(node)

    for elem in sorted(elements):
        visit(elem)

    if cycle_members:
        warnings.warn(
            f"Circular dependency detected among: {', '.join(sorted(cycle_members))}. "
            f"Processing in stable order.",
            stacklevel=2,
        )

    return result


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
    promoted_fields: set[str] | None = None,
) -> ClassContent:
    """Convert a parsed ClassElement into a ClassContent for canvas rendering.

    Args:
        elem: The parsed class element.
        promoted_methods: Optional set of method names that have been promoted to
            detail nodes. When a method name is in this set, its MethodEntry will
            have ``has_detail=True``, which causes the ``●`` marker to appear.
        promoted_fields: Optional set of field names that have been promoted to
            detail nodes. When a field name is in this set, its FieldEntry will
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
            has_detail=promoted_fields is not None and f.name in promoted_fields,
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


def _is_significant_field(field_elem: FieldElement) -> bool:
    """Return True if the field has significant design documentation."""
    return bool(
        field_elem.comment_sections.get("responsibility", "").strip()
        or field_elem.comment_sections.get("constraints", "").strip()
    )


def _field_to_detail_node(
    field_elem: FieldElement,
    class_qname: str,
    x: int,
    y: int,
    language: str,
) -> Node:
    """Create a canvas Node for a significant field detail."""
    field_qname = f"{class_qname}.{field_elem.name}"

    content = FieldContent(
        name=f"{class_qname.rsplit('.', 1)[-1]}.{field_elem.name}",
        responsibility=field_elem.comment_sections.get("responsibility", "").strip(),
        type=python_to_canvas(field_elem.type_annotation) if field_elem.type_annotation else "Any",
        constraints=field_elem.comment_sections.get("constraints", "").strip(),
        default=field_elem.default_value or "",
    )

    text = render_field_node(content)

    return Node(
        id=_new_id(),
        type="text",
        x=x,
        y=y,
        width=_NODE_WIDTH,
        height=_NODE_HEIGHT,
        text=text,
        ccoding=CcodingMetadata(
            kind="field",
            language=language,
            qualified_name=field_qname,
            status="accepted",
            layout_pending=True,
        ),
    )


def _detect_renames(
    diff: SyncDiff,
    code_element_map: dict[str, ClassElement],
    canvas_node_map: dict[str, Node],
    state: SyncState,
) -> list[tuple[str, str]]:
    """Detect potential renames by matching code-deleted elements with code-added elements.

    When a class is renamed in source, the old qualified name disappears from code
    (code_deleted) and a new one appears (code_added). If the old canvas node and
    the new code element are structurally similar (same fields/methods, same file),
    we treat it as a rename rather than a delete + add.

    Returns a list of (old_qname, new_qname) pairs.
    """
    if not diff.code_deleted or not diff.code_added:
        return []

    renames: list[tuple[str, str]] = []
    used_added: set[str] = set()

    for old_qname in list(diff.code_deleted):
        old_state = state.elements.get(old_qname)
        if not old_state:
            continue

        best_match: str | None = None
        best_score = 0.0

        for new_qname in diff.code_added:
            if new_qname in used_added:
                continue
            new_elem = code_element_map.get(new_qname)
            if not new_elem:
                continue

            old_node = canvas_node_map.get(old_qname)
            if not old_node:
                continue

            # Same source file is a strong signal
            old_source = old_state.source_path
            new_source = new_elem.source_path or ""
            same_file = bool(
                old_source and new_source and (
                    Path(old_source).name == Path(new_source).name
                    or str(old_source) == str(new_source)
                )
            )

            # Structural similarity: compare field names and method names
            new_field_names = {f.name for f in new_elem.fields}
            new_method_names = {m.name for m in new_elem.methods}

            # Parse old node to get its structure
            old_content = parse_class_node(old_node.text)
            old_field_names = {f.name for f in old_content.fields}
            old_method_names = {m.name for m in old_content.methods}

            # Jaccard similarity on fields + methods
            all_names = old_field_names | old_method_names | new_field_names | new_method_names
            if not all_names:
                score = 0.5 if same_file else 0.0
            else:
                common = (old_field_names & new_field_names) | (old_method_names & new_method_names)
                score = len(common) / len(all_names)

            if same_file:
                score += 0.3  # strong bonus for same file

            if score > best_score and score >= 0.5:
                best_score = score
                best_match = new_qname

        if best_match:
            renames.append((old_qname, best_match))
            used_added.add(best_match)

    return renames


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
    """Create inherits, implements, composes and depends edges from code analysis."""
    tracked_class_names = set(name_to_node_id.keys())

    # Inherits / implements: base classes that match tracked class names
    for base in elem.base_classes:
        base_simple = base.rsplit(".", 1)[-1] if "." in base else base
        if base_simple in tracked_class_names and base_simple != elem.name:
            to_id = name_to_node_id[base_simple]
            # Determine relation: check if target node has protocol stereotype
            target_node = next(
                (n for n in canvas.nodes if n.id == to_id), None
            )
            is_protocol = (
                target_node is not None
                and target_node.text
                and "«protocol»" in target_node.text.lower()
            )
            relation = "implements" if is_protocol else "inherits"
            existing = any(
                e for e in canvas.edges
                if e.ccoding and e.ccoding.relation == relation
                and e.from_node == node_id and e.to_node == to_id
            )
            if not existing:
                edge = Edge(
                    id=_edge_id(),
                    from_node=node_id,
                    to_node=to_id,
                    label=relation,
                    ccoding=EdgeMetadata(relation=relation, status="accepted"),
                )
                canvas.edges.append(edge)

    # Composes: fields whose type matches a tracked class name
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

        # Determine which fields are significant enough to promote
        significant_fields = [f for f in elem.fields if _is_significant_field(f)]
        promoted_fields: set[str] = {f.name for f in significant_fields}

        content = _element_to_class_content(
            elem,
            promoted_methods if promoted_methods else None,
            promoted_fields if promoted_fields else None,
        )
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

        # Create detail nodes for significant fields
        detail_y_offset = len(significant_methods) * (_NODE_HEIGHT + 20)
        for field_idx, field_elem in enumerate(significant_fields):
            detail_node = _field_to_detail_node(
                field_elem=field_elem,
                class_qname=qname,
                x=x + _NODE_WIDTH + _GRID_SPACING_X,
                y=y + detail_y_offset + field_idx * (_NODE_HEIGHT + 20),
                language=language,
            )
            canvas.nodes.append(detail_node)
            detail_edge = Edge(
                id=_edge_id(),
                from_node=node_id,
                to_node=detail_node.id,
                label=field_elem.name,
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
                # Determine relation: check if target node has protocol stereotype
                target_node = next(
                    (n for n in canvas.nodes if n.id == to_id), None
                )
                is_protocol = (
                    target_node is not None
                    and target_node.text
                    and "«protocol»" in target_node.text.lower()
                )
                relation = "implements" if is_protocol else "inherits"
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

    # Detect renames before processing deletes/adds
    renames = _detect_renames(diff, code_element_map, canvas_node_map, state)
    for old_qname, new_qname in renames:
        node = canvas_node_map.get(old_qname)
        if node and node.ccoding:
            # Update qualified name
            node.ccoding.qualified_name = new_qname
            # Update text content from new code
            new_elem = code_element_map[new_qname]
            content = _element_to_class_content(new_elem)
            node.text = render_class_node(content)
            # Update source path
            new_source = _source_rel(new_elem.source_path, project_root)

            # Update state: remove old, add new
            old_state_elem = state.elements.pop(old_qname, None)
            if old_state_elem:
                state.elements[new_qname] = ElementState(
                    canvas_hash=content_hash(node.text),
                    code_hash=code_hashes.get(new_qname, ""),
                    canvas_node_id=node.id,
                    source_path=new_source,
                )

            # Remove from diff lists so they're not double-processed
            if old_qname in diff.code_deleted:
                diff.code_deleted.remove(old_qname)
            if new_qname in diff.code_added:
                diff.code_added.remove(new_qname)

            # Update maps for downstream processing
            canvas_node_map[new_qname] = node
            canvas_hashes[new_qname] = content_hash(node.text)

            result.code_to_canvas.append(new_qname)

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

    # Order elements by dependency (spec §9.2, §10.1 cycle detection)
    edge_pairs: list[tuple[str, str]] = []
    for edge in canvas.edges:
        if edge.ccoding and edge.ccoding.relation in ("inherits", "implements"):
            from_qname = next(
                (n.ccoding.qualified_name for n in canvas.nodes
                 if n.id == edge.from_node and n.ccoding),
                None,
            )
            to_qname = next(
                (n.ccoding.qualified_name for n in canvas.nodes
                 if n.id == edge.to_node and n.ccoding),
                None,
            )
            if from_qname and to_qname:
                edge_pairs.append((from_qname, to_qname))

    if diff.code_added:
        diff.code_added = _topological_sort(diff.code_added, edge_pairs)

    # Apply changes: code_added -> create new canvas nodes
    for qname in diff.code_added:
        elem = code_element_map[qname]
        node_id = _new_id()
        idx = len(canvas.nodes)
        x, y = _grid_position(idx)

        # Determine which methods are significant enough to promote
        significant_methods = [m for m in elem.methods if _is_significant_method(m)]
        promoted_methods_set: set[str] = {m.name for m in significant_methods}

        # Determine which fields are significant enough to promote
        significant_fields = [f for f in elem.fields if _is_significant_field(f)]
        promoted_fields_set: set[str] = {f.name for f in significant_fields}

        content = _element_to_class_content(
            elem,
            promoted_methods_set if promoted_methods_set else None,
            promoted_fields_set if promoted_fields_set else None,
        )
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

        # Create detail nodes for significant fields
        detail_y_offset = len(significant_methods) * (_NODE_HEIGHT + 20)
        for field_idx, field_elem in enumerate(significant_fields):
            detail_node = _field_to_detail_node(
                field_elem=field_elem,
                class_qname=qname,
                x=x + _NODE_WIDTH + _GRID_SPACING_X,
                y=y + detail_y_offset + field_idx * (_NODE_HEIGHT + 20),
                language=config.language,
            )
            canvas.nodes.append(detail_node)
            detail_edge = Edge(
                id=_edge_id(),
                from_node=node_id,
                to_node=detail_node.id,
                label=field_elem.name,
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

            # Determine which fields are significant enough to promote
            significant_fields = [f for f in elem.fields if _is_significant_field(f)]
            promoted_fields_set: set[str] = {f.name for f in significant_fields}

            content = _element_to_class_content(
                elem,
                promoted_methods_set if promoted_methods_set else None,
                promoted_fields_set if promoted_fields_set else None,
            )
            text = render_class_node(content)
            node.text = text
            state.elements[qname].canvas_hash = content_hash(text)
            state.elements[qname].code_hash = code_hashes[qname]
            result.code_to_canvas.append(qname)

            # Build a map of existing detail nodes for this class (by member name)
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
                        member_name = (target.ccoding.qualified_name or "").rsplit(".", 1)[-1]
                        existing_detail_nodes[member_name] = target

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

            # Handle field detail nodes
            detail_y_offset = len(significant_methods) * (_NODE_HEIGHT + 20)
            for field_idx, field_elem in enumerate(significant_fields):
                if field_elem.name in existing_detail_nodes:
                    # Update the existing detail node text
                    detail_node = existing_detail_nodes[field_elem.name]
                    updated = _field_to_detail_node(
                        field_elem=field_elem,
                        class_qname=qname,
                        x=detail_node.x,
                        y=detail_node.y,
                        language=config.language,
                    )
                    detail_node.text = updated.text
                else:
                    # Create a new detail node and edge
                    detail_node = _field_to_detail_node(
                        field_elem=field_elem,
                        class_qname=qname,
                        x=node.x + _NODE_WIDTH + _GRID_SPACING_X,
                        y=node.y + detail_y_offset + field_idx * (_NODE_HEIGHT + 20),
                        language=config.language,
                    )
                    canvas.nodes.append(detail_node)
                    detail_edge = Edge(
                        id=_edge_id(),
                        from_node=node.id,
                        to_node=detail_node.id,
                        label=field_elem.name,
                        ccoding=EdgeMetadata(relation="detail", status="accepted"),
                    )
                    canvas.edges.append(detail_edge)

    # Order canvas_added by dependency (spec §9.2)
    if diff.canvas_added:
        diff.canvas_added = _topological_sort(diff.canvas_added, edge_pairs)

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

    # Order canvas_modified by dependency (spec §9.2)
    if diff.canvas_modified:
        diff.canvas_modified = _topological_sort(diff.canvas_modified, edge_pairs)

    # Apply changes: canvas_modified -> regenerate code from canvas
    for qname in diff.canvas_modified:
        node = canvas_node_map.get(qname)
        if not node or not node.ccoding:
            continue

        content = parse_class_node(node.text)
        edge_info = _collect_edge_info(canvas, node.id)

        # Extract existing method bodies to preserve implementations
        elem_state = state.elements.get(qname)
        preserve_bodies: dict[str, list[str]] = {}
        if elem_state and elem_state.source_path:
            _target_for_extract = project_root / elem_state.source_path
            if _target_for_extract.exists():
                from ccoding.code.generator import extract_method_bodies
                class_name = qname.rsplit(".", 1)[-1]
                preserve_bodies = extract_method_bodies(_target_for_extract, class_name)

        code_text = generate_class(
            content, config.language, edges=edge_info,
            preserve_bodies=preserve_bodies if preserve_bodies else None,
        )

        # Find existing source path from state
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


def compute_project_diff(project_root: Path) -> tuple[SyncDiff, dict]:
    """Compute the sync diff for a project. Returns (diff, metadata).

    Shared logic used by both ``status`` and ``diff`` CLI commands.
    The metadata dict contains canvas path, source root, and tracked count.
    """
    config = load_config(project_root)
    canvas_path = project_root / config.canvas
    source_root = project_root / config.source_root

    if not canvas_path.exists():
        return SyncDiff(), {"canvas": str(config.canvas), "source": str(config.source_root), "tracked": 0, "canvas_exists": False}

    canvas = read_canvas(canvas_path)

    parser = PythonAstParser()
    code_elements: list[ClassElement] = []
    if source_root.exists():
        all_elements = parser.parse_directory(source_root)
        code_elements = [e for e in all_elements if isinstance(e, ClassElement)]

    state = load_sync_state(project_root)

    canvas_hashes: dict[str, str] = {}
    for node in canvas.nodes:
        if node.ccoding and node.ccoding.qualified_name:
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
    meta = {
        "canvas": str(config.canvas),
        "source": str(config.source_root),
        "tracked": len(state.elements),
        "canvas_exists": True,
    }
    return diff, meta


def sync_status(project_root: Path) -> str:
    """Return a human-readable status report for the CLI status command."""
    diff, meta = compute_project_diff(project_root)

    if not meta["canvas_exists"]:
        return "No canvas file found."

    lines: list[str] = []
    lines.append(f"Canvas: {meta['canvas']}")
    lines.append(f"Source: {meta['source']}")
    lines.append(f"Tracked elements: {meta['tracked']}")
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
